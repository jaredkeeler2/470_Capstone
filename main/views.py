from django.shortcuts import render
from .csce_scraper import csce_courses

#homepage
def home(request):
    courses = csce_courses()  #scrapes that page
    return render(request, "home.html", {"courses": courses})
