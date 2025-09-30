from django.shortcuts import render
from .csce_scraper import schedule_scraper,save_courses_for_terms

#homepage
def home(request):
    results = save_courses_for_terms()  #scrapes that page  #need to be change
    course_codes = []
    for course in results:      #loops through each tuple in the results and gets the first value and adds it to the list for the course name dropdown
        code = course[0]
        course_codes.append(code)
    return render(request, "home.html", {"courses": course_codes})
