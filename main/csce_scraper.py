import requests
from bs4 import BeautifulSoup
from collections import defaultdict
from main.models import Course
from datetime import datetime
import re

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
    for item in sorted(totals.items()):
        #current item looks like (("CSCE A101", "Intro to CS"), 54)
        key = item[0]       #first index of item is ("CSCE A101", "Intro to CS")
        total = item[1]     #second index is the enrollment count (e.g. 54)
        code = key[0]       #first part in the key is the course name (e.g. "CSCE A101")
        title = key[1]      #second part in the key is course title (e.g. "Intro to CS")
        
        Course.objects.update_or_create(
            term=term,
            code=code,
            defaults={
                "title": title,
                "enrolled": total
            }
        )

        course_data = (code, title, total)
        results.append(course_data)     #add the data to the results list
    return results


def generate_last_5_year_terms():
    current_year = datetime.now().year
    terms = []
    for year in range(current_year - 4, current_year + 1):  # last 5 years
        for sem in ["01", "02", "03"]:  # Spring, Summer, Fall
            term_code = f"{year}{sem}"
            terms.append(term_code)
    return terms


def save_courses_for_terms(terms=None):
    if terms is None:
        terms = generate_last_5_year_terms()

    all_courses_list = []

    for term in terms:
        # Optional: delete existing courses for this term to avoid duplicates
        Course.objects.filter(term=term).delete()
        term_courses = schedule_scraper(term=term)
        # Scrape and save
        term_courses = schedule_scraper(term=term)
        for code, title, enrolled in term_courses:
            Course.objects.create(term=term, code=code, title=title, enrolled=enrolled)
            all_courses_list.append((term, code, title, enrolled))

        print(f"Saved {len(term_courses)} courses for term {term}")

    return all_courses_list


# Run directly
if __name__ == "__main__":
    terms = generate_last_5_year_terms()
    courses_list = save_courses_for_terms(terms=terms)
    print("\nAll saved courses:")
    for course in courses_list:
        print(course)
"""
#Example usage
if __name__ == "__main__":
    terms = ["202503", "202502", "202501"]  #fall, summer, spring
    whole_year = {} #dictionary to store the scraper's results

    for t in terms:     #iterate through each term
        whole_year[t] = schedule_scraper(term=t)    #stores each term with the results for that term

    # print results
    for term, results in whole_year.items():    #splits the tuple value into two variables (the term and the results)
        print("\n===== Term " + term + " =====")
        for course_data in results:     #prints all of the results for each term
            print(course_data)
"""