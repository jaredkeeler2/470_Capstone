import os
import sys
import django
import pandas as pd
import warnings
from statsmodels.tsa.arima.model import ARIMA

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
def next_term_code(current_term):
    year, sem = divmod(int(current_term), 100)
    if sem == 1:      #Spring -> Summer
        return year * 100 + 2
    elif sem == 2:    #Summer -> Fall
        return year * 100 + 3
    elif sem == 3:    #Fall -> next year's Spring
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

results = []
for code, group in df.groupby('code'):
    y = group['enrolled'].astype(float).values
    terms = group['term'].astype(int).values

    try:
        if len(y) < 2:
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
        next_term = next_term_code(terms[-1]) #gets next term code based on previous one

        #stores forecast info
        results.append({
            "code": code,
            "term": next_term,
            "term_name": term_name_from_code(next_term),
            "enrolled": forecast
        })

    except Exception as e:
        print(f"Error with {code}: {e}")

#combine forecasts with existing data
forecast_df = pd.DataFrame(results)
combined_df = pd.concat([df[['code', 'term', 'term_name', 'enrolled']], forecast_df])

#save combined dataset to the .json file
output_path = os.path.join("main", "forecast_data.json")
combined_df.to_json(output_path, orient="records", indent=4)

print(f"Saved combined data to {output_path}")
print(f"Generated forecasts for {len(results)} courses.")
