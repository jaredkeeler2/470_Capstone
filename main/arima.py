import os
import sys
import django
import pandas as pd
import warnings
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import root_mean_squared_error
from csce_scraper import build_term_codes_past_years
warnings.filterwarnings("ignore")

#django setup
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Capstone.settings')
django.setup()

from main.models import Course, Prerequisite
from main.models import GraduationData

hs_qs = GraduationData.objects.all().values('year', 'graduates')
hs_map = {row['year']: row['graduates'] for row in hs_qs}

def hs_value_for_term(term):
    term = int(term)
    year, sem = divmod(term, 100)

    #Spring term uses previous year's graduates
    if sem == 1:
        hs_year = year - 1
    else:
        hs_year = year

    return hs_map.get(hs_year, np.nan)

#converts numeric term to non-numeric term (e.g. 202503 ---> Fall 2025)
def term_name_from_code(term):
    term = int(term)
    year, sem = divmod(term, 100)
    names = {1: "Spring", 2: "Summer", 3: "Fall"}
    return f"{names.get(sem, 'Unknown')} {year}"

#builds next term based on current term 
def next_term_code(course_num, spring_count, summer_count, fall_count, yearly_course):
    last_term = int(group['term'].max())
    year, sem = divmod(last_term, 100)
    
    if yearly_course:
        if spring_count > 0 and summer_count == 0 and fall_count == 0: 
            return (year + 1) * 100 + 1 if sem == 1 else year * 100 + 1
        if spring_count == 0 and summer_count > 0 and fall_count == 0: 
            return (year + 1) * 100 + 2 if sem == 2 else year * 100 + 2
        if spring_count == 0 and summer_count == 0 and fall_count > 0: 
            return (year + 1) * 100 + 3 if sem == 3 else year * 100 + 3

    if course_num > 201:
        if sem == 1:      #Spring → Fall
            return year * 100 + 3
        elif sem == 2:    #Summer → Fall
            return year * 100 + 3
        else:
            return (year + 1) * 100 + 1
    else:
        if sem == 1:      #Spring → Summer
            return year * 100 + 2
        elif sem == 2:    #Summer → Fall
            return year * 100 + 3
        else:
            return (year + 1) * 100 + 1

#calculates previous term code        
def previous_term_code(term_code):
    term_code = int(term_code)
    year, sem = divmod(term_code, 100)
    if sem == 1:   #Spring → previous Fall
        return (year - 1) * 100 + 3
    elif sem == 2: #Summer → previous Spring
        return year * 100 + 1
    elif sem == 3: #Fall → same year Summer
        return year * 100 + 2

#get previous term code with option to skip summers for upper-level courses
def get_previous_term(term, steps_back, upper_level=False):
    lag_term = term
    for _ in range(steps_back):
        lag_term = previous_term_code(lag_term)

        #For upper-level courses (200+), skip *only* summers if they're not in the dataset
        if upper_level and (lag_term % 100 == 2):
            #Only skip summer if previous Fall or Spring exists
            lag_term = previous_term_code(lag_term)
    return lag_term

#load data from the Course model
qs = Course.objects.all().values('code', 'term', 'enrolled', 'title')
df = pd.DataFrame(qs)

#load prerequisite data into a DataFrame
prereq_qs = Prerequisite.objects.all().values('course_code', 'prereq_1', 'prereq_2')
prereq_df = pd.DataFrame(prereq_qs)

#clean + sort chronologically
df['term'] = df['term'].astype(int)
df['term_name'] = df['term'].apply(term_name_from_code)
# Add numeric course number column
df['course_num'] = df['code'].str.extract(r'A(\d+)').astype(int)

#Remove Summer terms for upper-level courses (A211+)
df = df[~(
    (df['course_num'] > 201) &
    (df['term_name'].str.contains("Summer", case=False, na=False))
)]

df = df.sort_values(['code', 'term'])

all_MAES = {"arima": [], "sarima": [], "arimax": [], "sarimax": []}
prereq_map = prereq_df.set_index('course_code')[['prereq_1', 'prereq_2']].to_dict('index')
results = []

for code, group in df.groupby('code'):
    course_num = int(code.split('A')[-1])

    prereqs = prereq_map.get(code, {})
    pr1, pr2 = prereqs.get('prereq_1'), prereqs.get('prereq_2')
    m = 3 if course_num <= 201 else 2
    y = group['enrolled'].astype(float).values
    terms = group['term'].astype(int).values

    exog_values = []
    #Add HS grads as exog ONLY for A101
    if code == "CSCE A101":
        hs_vals = []
        for term in group['term']:
            hs_raw = hs_value_for_term(term)

            if not np.isnan(hs_raw):
                hs_vals.append(hs_raw / 50)
            else:
                hs_vals.append(0)

        exog_values.append(hs_vals)

    #Prereq_1/2 → lag 1/2 (two-term back)
    for i, prereq_code in enumerate([pr1, pr2]):
        if prereq_code:
            lagged_values = []
            for term in group['term']:
                lag_term = get_previous_term(term, i + 1, course_num > 201)
                enroll_row = df[(df['code'] == prereq_code) & (df['term'] == lag_term)]

                #Get the enrollment value or set 0 if missing
                if not enroll_row.empty:
                    value = float(enroll_row['enrolled'].values[0])
                else:
                    value = np.nan  

                lagged_values.append(value)

                #Print for verification
                print(
                    f"{code} term {term} → lag {i+1} ({prereq_code}) term {lag_term}: "
                    f"{value if value != 0 else 'MISSING (set 0)'}"
                )

            exog_values.append(lagged_values)
        else:
            exog_values.append(np.zeros(len(group)))

    exog = np.column_stack(exog_values) if exog_values else np.zeros((len(group), 1))
    if course_num <= 201:
        valid_idx = ~np.isnan(exog).any(axis=1)
        y = y[valid_idx]
        exog = exog[valid_idx]
    else:
        #For upper-level courses like A470, fill missing prereq enrollments with 0
        exog = np.nan_to_num(exog, nan=0.0)
    
    #Skip exogenous variables for courses with no prerequisites (except A101)

    arima_mae = None
    sarima_mae = None
    arimax_mae = None
    sarimax_mae = None

    try:
        if len(y) < 4:
            results.append({
                "code": code,
                "title": group['title'].iloc[0],
                "term": None,
                "term_name": "Insufficient data",
                "arima_forecast": None,
                "sarima_forecast": None,
                "arimax_forecast": None,
                "sarimax_forecast": None,
                "arima_mae": None,
                "sarima_mae": None,
                "arimax_mae": None,
                "sarimax_mae": None,
                "best_accuracy": None
            })
            continue
        
        spring_count = 0 
        summer_count = 0 
        fall_count = 0 
        yearly_course = False
        for term in group['term']: 
            temp = divmod(term, 100) 
            temp = temp[1] 
            if temp == 1: 
                spring_count += 1 
            elif temp == 2: 
                summer_count += 1 
            elif temp == 3: fall_count += 1 
        if spring_count > 0 and summer_count == 0 and fall_count == 0: 
            yearly_course = True
        elif spring_count == 0 and summer_count > 0 and fall_count == 0: 
            yearly_course = True
        elif spring_count == 0 and summer_count == 0 and fall_count > 0: 
            yearly_course = True
        else:
            yearly_course = False
        next_term = next_term_code(course_num, spring_count, summer_count, fall_count, yearly_course)

        models_accuracy = []

        #ARIMA forecast
        model = ARIMA(y, order=(1, 1, 1))
        fit = model.fit()
        arima_forecast = fit.forecast(steps=1)[0]
        arima_forecast = max(round(arima_forecast, 0), 0)
        arima_val_terms, arima_val_preds = None, None  #store testing info

        if len(y) >= 4:
            try:
                train, test = y[:-2], y[-2:]
                train_terms, test_terms = terms[:-2], terms[-2:]
                model_eval = ARIMA(train, order=(1, 1, 1)).fit()
                preds = model_eval.forecast(steps=len(test))
                test = np.ravel(test)
                preds = np.ravel(preds)

                arima_mae = mean_absolute_error(test, preds)

                all_MAES["arima"].append(arima_mae)
                preds = [max(round(p, 0), 0) for p in preds]
                arima_val_terms = test_terms.tolist()
                arima_val_preds = preds

                arima_accuracy = 100 - (arima_mae / y[-2:].mean() * 100)
                models_accuracy.append(arima_accuracy)
                print(f"{code}: ARIMA MAE={arima_mae:.1f}")
            except Exception as inner_e:
                print(f"Metrics didn't calculate for {code}: {inner_e}")

        #SARIMA forecast
        model = SARIMAX(y, order=(1, 1, 1), seasonal_order=(1, 1, 1, m))
        fit = model.fit(disp=False)
        sarima_forecast = fit.forecast(steps=1)[0]
        sarima_forecast = max(round(sarima_forecast, 0), 0)
        sarima_val_terms, sarima_val_preds = None, None

        if len(y) >= 4:
            try:
                train, test = y[:-2], y[-2:]
                train_terms, test_terms = terms[:-2], terms[-2:]
                model_eval = SARIMAX(train, order=(1, 1, 1), seasonal_order=(1, 1, 1, m)).fit()
                preds = model_eval.forecast(steps=len(test))
                test = np.ravel(test)
                preds = np.ravel(preds)

                sarima_mae = mean_absolute_error(test, preds)

                all_MAES["sarima"].append(sarima_mae)
                preds = [max(round(p, 0), 0) for p in preds]
                sarima_val_terms = test_terms.tolist()
                sarima_val_preds = preds
                sarima_accuracy = 100 - (sarima_mae / y[-2:].mean() * 100)
                models_accuracy.append(sarima_accuracy)
                print(f"{code}: SARIMA MAE={sarima_mae:.1f}")
            except Exception as inner_e:
                print(f"Metrics didn't calculate for {code}: {inner_e}")

        #ARIMAX forecast (uses prerequisite enrollment as exogenous variable)
        model = ARIMA(y, exog=exog, order=(1, 1, 1))
        fit = model.fit()
        next_exog = exog[-1].reshape(1, -1)
        arimax_forecast = fit.forecast(steps=1, exog=next_exog)[0]
        arimax_forecast = max(round(arimax_forecast, 0), 0)
        arimax_val_terms, arimax_val_preds = None, None

        if len(y) >= 4:
            try:
                train, test = y[:-2], y[-2:]
                train_exog, test_exog = exog[:-2], exog[-2:]
                train_terms, test_terms = terms[:-2], terms[-2:]
                model_eval = ARIMA(train, exog=train_exog, order=(1, 1, 1)).fit()
                preds = model_eval.forecast(steps=len(test), exog=test_exog)
                test = np.ravel(test)
                preds = np.ravel(preds)

                arimax_mae = mean_absolute_error(test, preds)

                all_MAES.setdefault("arimax", []).append(arimax_mae)
                preds = [max(round(p, 0), 0) for p in preds]
                arimax_val_terms = test_terms.tolist()
                arimax_val_preds = preds
                arimax_accuracy = 100 - (arimax_mae / y[-2:].mean() * 100)
                models_accuracy.append(arimax_accuracy)
                print(f"{code}: ARIMAX MAE={arimax_mae:.1f}")
            except Exception as inner_e:
                print(f"Metrics didn't calculate for {code} (ARIMAX): {inner_e}")

        #SARIMAX forecast
        if code == "CSCE A201":
            model = SARIMAX(y, exog=exog,
                            order=(1, 1, 1),
                            seasonal_order=(1, 0, 1, 2))
        else:
            model = SARIMAX(y, exog=exog,
                            order=(1, 1, 1),
                            seasonal_order=(1, 1, 1, m))

        fit = model.fit(disp=False)
        next_exog = exog[-1].reshape(1, -1)
        sarimax_forecast = fit.forecast(steps=1, exog=next_exog)[0]
        sarimax_forecast = max(round(sarimax_forecast, 0), 0)
        sarimax_val_terms, sarimax_val_preds = None, None

        #SARIMAX validation
        if len(y) >= 4:
            try:
                train, test = y[:-2], y[-2:]
                train_exog, test_exog = exog[:-2], exog[-2:]
                train_terms, test_terms = terms[:-2], terms[-2:]

                #Special case for A201 again in validation
                if code == "CSCE A201":
                    model_eval = SARIMAX(train, exog=train_exog,
                                        order=(1, 1, 1),
                                        seasonal_order=(1, 0, 1, 2)).fit()
                else:
                    model_eval = SARIMAX(train, exog=train_exog,
                                        order=(1, 1, 1),
                                        seasonal_order=(1, 1, 1, m)).fit()

                preds = model_eval.forecast(steps=len(test), exog=test_exog)
                test = np.ravel(test)
                preds = np.ravel(preds)

                sarimax_mae = mean_absolute_error(test, preds)

                all_MAES["sarimax"].append(sarimax_mae)
                preds = [max(round(p, 0), 0) for p in preds]
                sarimax_val_terms = test_terms.tolist()
                sarimax_val_preds = preds
                sarimax_accuracy = 100 - (sarimax_mae / y[-2:].mean() * 100)
                models_accuracy.append(sarimax_accuracy)

                print(f"{code}: SARIMAX MAE={sarimax_mae:.1f}")

            except Exception as inner_e:
                print(f"Metrics didn't calculate for {code}: {inner_e}")


        if arima_mae is not None:
            arima_mae = round(arima_mae, 2)
        if sarima_mae is not None:
            sarima_mae = round(sarima_mae, 2)
        if arimax_mae is not None: 
            arimax_mae = round(arimax_mae, 2)
        if sarimax_mae is not None:
            sarimax_mae = round(sarimax_mae, 2)

        best_accuracy = max(models_accuracy) if models_accuracy else None

        
        #json data storage
        results.append({
            "code": code,
            "title": group['title'].iloc[0],
            "term": next_term,
            "term_name": term_name_from_code(next_term),
            "arima_forecast": arima_forecast,
            "sarima_forecast": sarima_forecast,
            "arimax_forecast": arimax_forecast,
            "sarimax_forecast": sarimax_forecast,
            "arima_mae": arima_mae,
            "sarima_mae": sarima_mae,
            "arimax_mae": arimax_mae,
            "sarimax_mae": sarimax_mae,
            "arima_val_terms": arima_val_terms,
            "arima_val_preds": arima_val_preds,
            "sarima_val_terms": sarima_val_terms,
            "sarima_val_preds": sarima_val_preds,
            "arimax_val_terms": arimax_val_terms,
            "arimax_val_preds": arimax_val_preds,
            "sarimax_val_terms": sarimax_val_terms,
            "sarimax_val_preds": sarimax_val_preds,
            "yearly_course": yearly_course,
            "best_accuracy": best_accuracy
        })

    except Exception as e:
        print(f"Error with {code}: {e}")

forecast_df = pd.DataFrame(results)
combined_df = pd.concat([df[['code', 'term', 'term_name', 'enrolled', 'title']], forecast_df])

output_path = os.path.join("main", "forecast_data.json")
combined_df.to_json(output_path, orient="records", indent=4)

'''
print(f"Saved combined data to {output_path}")
print(f"Generated forecasts for {len(results)} courses.")

#average model performance
print("\n===== Average Model Performance =====")
for model_name in ["arima", "sarima", "arimax", "sarimax"]:
    mae_list = all_MAES.get(model_name, [])
    if mae_list:
        avg_mae = np.mean(mae_list)
        print(f"{model_name.upper():6} → MAE={avg_mae:.1f}")
    else:
        print(f"{model_name.upper():6} → No valid results")
print("======================================\n")
'''
