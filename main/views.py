from django.shortcuts import render
from .csce_scraper import schedule_scraper

#homepage
def home(request):
    results = schedule_scraper()  #scrapes that page
    course_codes = []
    for course in results:      #loops through each tuple in the results and gets the first value and adds it to the list for the course name dropdown
        code = course[0]
        course_codes.append(code)
    return render(request, "home.html", {"courses": course_codes})
