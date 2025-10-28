import os
import sys
import django
import pandas as pd
import warnings
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import root_mean_squared_error
from csce_scraper import build_term_codes_past_years

warnings.filterwarnings("ignore")

#django setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Capstone.settings')
django.setup()

from main.models import Course

#converts numeric term to non-numeric term (e.g. 202503 ---> Fall 2025)
def term_name_from_code(term):
    term = int(term)
    year, sem = divmod(term, 100)
    names = {1: "Spring", 2: "Summer", 3: "Fall"}
    return f"{names.get(sem, 'Unknown')} {year}"

#finds next term
def next_term_code():
    #using the scraper current term to get current semester
    terms = build_term_codes_past_years(years=1, include_current=True)
    current_real_term = int(terms[-1][0])  #last tuple in list, e.g. ("202503", "Fall 2025")
    year, sem = divmod(current_real_term, 100)
    if sem == 1:      #Spring → Summer
        return year * 100 + 2
    elif sem == 2:    #Summer → Fall
        return year * 100 + 3
    elif sem == 3:    #Fall → next Spring
        return (year + 1) * 100 + 1

#load data from the Course model
qs = Course.objects.all().values('code', 'term', 'enrolled')
df = pd.DataFrame(qs)

if df.empty:
    print("No data found in Course table.")
    exit()

#clean + sort chronologically
df['term'] = df['term'].astype(int)
df['term_name'] = df['term'].apply(term_name_from_code)
df = df.sort_values(['code', 'term'])

all_MAES = [] #list for the average MAEs
all_RMSE = [] #list for the average RMSE
results = []
for code, group in df.groupby('code'):
    y = group['enrolled'].astype(float).values
    terms = group['term'].astype(int).values

    try:
        if len(y) < 4:
            #mark as insufficient data
            results.append({
                "code": code,
                "term": None,
                "term_name": "Insufficient data",
                "enrolled": None
            })
            continue

        #normal ARIMA forecast
        model = ARIMA(y, order=(1, 1, 1))
        fit = model.fit()
        forecast = fit.forecast(steps=1)[0] #predict 1 term ahead
        forecast = max(round(forecast, 0), 0) #round number to 0, and replace negative value with 0 if there is one
        next_term = next_term_code() #gets next term code based on previous one

        mae = None
        rmse = None

        #Only calculate metrics if there’s enough data (e.g., >= 4 terms)
        if len(y) >= 4:
            train, test = y[:-2], y[-2:]  #train on all but last 2, test on last 
            try:
                model_eval = ARIMA(train, order=(1, 1, 1)).fit()
                preds = model_eval.forecast(steps=len(test))

                test = np.ravel(test)
                preds = np.ravel(preds)

                mae = mean_absolute_error(test, preds)
                rmse = root_mean_squared_error(test, preds)

                all_MAES.append(mae)
                all_RMSE.append(rmse)

                print(f"{code}: MAE={mae:.2f}, RMSE={rmse:.2f}")

            except Exception as inner_e:
                print(f"Metrics didn't calculate for {code}: {inner_e}")

        #stores forecast info
        results.append({
            "code": code,
            "term": next_term,
            "term_name": term_name_from_code(next_term),
            "enrolled": forecast,
            "mae": round(mae, 2) if mae is not None else None,
            "rmse": round(rmse, 2) if rmse is not None else None
        })

    except Exception as e:
        print(f"Error with {code}: {e}")

#calculate the average MAE
average_MAE = 0
n = 0
for mae in all_MAES:
    average_MAE += mae
    n += 1
average_MAE = round((average_MAE / n), 2)

#calculate the average RMSE
average_RMSE = 0
n = 0
for rmse in all_RMSE:
    average_RMSE += rmse
    n += 1
average_RMSE = round((average_RMSE / n), 2)


#combine forecasts with existing data
forecast_df = pd.DataFrame(results)
combined_df = pd.concat([df[['code', 'term', 'term_name', 'enrolled']], forecast_df])

#save combined dataset to the .json file
output_path = os.path.join("main", "forecast_data.json")
combined_df.to_json(output_path, orient="records", indent=4)

print(f"Saved combined data to {output_path}")
print(f"Generated forecasts for {len(results)} courses.")
