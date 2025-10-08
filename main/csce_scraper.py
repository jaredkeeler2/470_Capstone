import requests
from bs4 import BeautifulSoup
from collections import defaultdict
import re
from datetime import datetime

'''
#Catalog CSCE page
URL = "https://catalog.uaa.alaska.edu/undergraduateprograms/coeng/bs-computerscience/"

#CSCE catalog scraper function
def csce_courses(url=URL):
    response = requests.get(url, timeout=20)    #downloads the html (will wait 20 seconds before timeout)
    response.raise_for_status()    #throws error if the download failed
    soup = BeautifulSoup(response.text, "html.parser")     #converts html page into a searchable object
    codes = set()   #The set will only store unique values without duplicated

    #this loops through all of the <a> tags in <td class="codecol">
    for a in soup.select("td.codecol a"):   #got the class links in code column
        text = a.get_text(" ", strip=True).replace("\xa0", " ")    #retrieves the text and replaces weird \xa0 spaces with normal spaces
        if not text.startswith(("CSCE", "CSCE/")):    #skips anything not starting with CSCE or CSCE/
            continue

        parts = text.split()    #this splits the text into parts and reconstructs anything like CSCE/EE A241 ---> CSCE A241
        if "/" in parts[0] and len(parts) > 1:
            text = "CSCE " + " ".join(parts[1:])
        codes.add(text)    #adds and saves the new text to the course codes

    return sorted(codes)    #sorted order of the list
'''

def build_term_codes_past_years(years=5, include_current=True):
    now = datetime.now()    #get the current semester
    y_now = now.year
    m = now.month #determine wheter its spring/summer/fall
    if m <= 4:
        sem_now = "01" 
    elif m <= 8:
        sem_now = "02"
    else:
        sem_now = "03"
    cutoff = int(str(y_now) + sem_now)  #e.g., 202503

    semester_map = {"01": "Spring", "02": "Summer", "03": "Fall"}   #setup term labels
    terms = []
    start_year = y_now - (years - 1)    #e.g. if years = 5 and it's 2025 then start_year = 2021

    #Build all terms for the last n years
    for year in range(start_year, y_now + 1):
        for s in ("01", "02", "03"):
            code = str(year) + s
            code_int = int(code)
            if code_int > cutoff:
                continue
            label = semester_map[s] + " " + str(year)
            terms.append((code, label))  #oldest -> newest
    return terms

def schedule_scraper(term="202503", subj="CSCE"):
    url = "https://curric.uaa.alaska.edu/ajax/ajaxScheduleSearch.php"   #API url
    params = {"term": term, "subj": subj}
    response = requests.get(url, params=params, timeout=20)     #requesting the specific parameters from the API, timeout if it takes more than 20s
    response.raise_for_status() #throws error if the download failed

    rows = response.json()  #convert json array of objects to python list of dictionaries
    totals = defaultdict(int)   #totals keep track of total students per course, each new key value is set to 0
    for row in rows:    #iterates through the dictonaries to extract subject, course, title, and enrollment number
        if row.get("subj").upper() == "CSCE":   #only for CSCE
            crs = row["crs"].upper()
            if not crs.endswith("L"):   #if it is a lab it skips (since the same students in the lab class are in the normal class)
                num = int(re.search(r'\d+', crs).group())  #regular expression that finds the string of numbers, and converts to integers
                if 100 <= num < 500:    #since we are only gathering data for 100-400 level courses
                    code = row['subj'].upper() + " " + row['crs']   #concatenates the subject and the course (e.g. CSCE A101)
                    title = row['title']
                    enrolled = int(row.get("enrolled")) 
                    totals[code, title] += enrolled  #sums up the enrollment for one course
    results = []
    for key, total in sorted(totals.items()):
        code, title = key
        results.append((code, title, total))
    
    """for item in sorted(totals.items()):
        #current item looks like (("CSCE A101", "Intro to CS"), 54)
        key = item[0]       #first index of item is ("CSCE A101", "Intro to CS")
        total = item[1]     #second index is the enrollment count (e.g. 54)
        code = key[0]       #first part in the key is the course name (e.g. "CSCE A101")
        title = key[1]      #second part in the key is course title (e.g. "Intro to CS")

        course_data = (code, title, total)
        results.append(course_data)     #add the data to the results list
    """
    return results

#Example usage

"""
if __name__ == "__main__":
    subj = "CSCE"
    terms = build_term_codes_past_years(years=5, include_current=True)

for code, label in terms:
    results = schedule_scraper(term=code, subj=subj)
    print("\n===== " + label + " (" + code + ") (" + subj + ") =====")
    print("\n".join(map(str, results)))
    
"""