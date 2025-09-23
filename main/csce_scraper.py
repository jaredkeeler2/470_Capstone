import requests
from bs4 import BeautifulSoup
from .models import Course

#Catalog CSCE page
URL = "https://catalog.uaa.alaska.edu/undergraduateprograms/coeng/bs-computerscience/"

#CSCE scraper function
def csce_courses(url=URL):
    response = requests.get(url, timeout=20)    #downloads the html (will wait 20 seconds before timeout)
    response.raise_for_status()    #throws error if the download failed
    soup = BeautifulSoup(response.text, "html.parser")     #converts html page into a searchable object
    codes = set()   #The set will only store unique values without duplicated

    #this loops through all of the <a> tags in <td class="codecol">
    for a in soup.select("td.codecol a"):
        text = a.get_text(" ", strip=True).replace("\xa0", " ")    #retrieves the text and replaces weird \xa0 spaces with normal spaces
        if not text.startswith(("CSCE", "CSCE/")):    #skips anything not starting with CSCE or CSCE/
            continue

        parts = text.split()    #this splits the text into parts and reconstructs anything like CSCE/EE A241 ---> CSCE A241
        if "/" in parts[0] and len(parts) > 1:
            text = "CSCE " + " ".join(parts[1:])
        codes.add(text)    #adds and saves the new text to the course codes
        
        saved_courses = []  #creating an empty lists
        for code in sorted(codes): #Loop through the sorted(code)
            course, created = Course.objects.get_or_create(code=code)  # skip if object exists else create in DB
            saved_courses.append(course)
        
    return sorted(codes)    #sorted order of the list
