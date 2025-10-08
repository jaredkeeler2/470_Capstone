import requests
from datetime import datetime

'''
def graduation_scraper():
    url = "https://public.tableau.com/app/profile/asdk12/viz/GraduationRate_16370266007000/ASDGradRateoverview"   #API url
    response = requests.get(url, timeout=20)     #request for the API, timeout if it takes more than 20s
    response.raise_for_status() #throws error if the download failed
    if response:
        print("successful")
    else:
        print("not successful")
    if 'Content-Type' in response.headers:
        content_type = response.headers['Content-Type']
        print(f"Content-Type: {content_type}")
    else:
        print("Content-Type header not found in response.")

if __name__ == "__main__":
    graduation_scraper()
'''

def input_graduation_data():
    data = {}
    current_year = datetime.now().year
    print("Enter ASD graduation numbers for the last 5 years (up to " + str(current_year) + ")")

    for i in range(5):
        year = current_year - i
        while True:
                grads = int(input(str(year) + ": "))
        data[year] = grads

    print("\nASD Graduation Data:")
    for year in sorted(data.keys(), reverse=True):
        print(str(year) + ": " + str(data[year]))

    return data


if __name__ == "__main__":
    graduation_dict = input_graduation_data()
    print("\nFinal dictionary:")
    print(graduation_dict)