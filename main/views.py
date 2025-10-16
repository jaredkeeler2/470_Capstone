from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from .models import Course
from .csce_scraper import build_term_codes_past_years
from .forms import GraduationForm
from .models import GraduationData
from datetime import datetime

#homepage
def home(request):
    # Get all terms for the past 5 years
    all_terms = [term for term, label in build_term_codes_past_years(years=5)]

    # Determine which terms are already in the database
    existing_terms = set(Course.objects.values_list('term', flat=True))

    # Find missing terms
    missing_terms = [term for term in all_terms if term not in existing_terms]

    # Only scrape missing terms
    if missing_terms:
        print(f"Scraping missing terms: {missing_terms}")
        Course.save_courses(subj="CSCE")
    else:
        print("All terms already present. No scraping needed.")

    # Get unique course codes for dropdown
    courses = Course.objects.values_list('code', flat=True).distinct().order_by('code')
    return render(request, 'home.html', {'courses': courses})

def graduate_data(request):
    #auto-fill database with empty entries from 2021 → current year
    current_year = datetime.now().year
    for year in range(2021, current_year + 1):
        GraduationData.objects.get_or_create(year=year, defaults={'graduates': 0})

    #handle user input from the form
    if request.method == 'POST':
        form = GraduationForm(request.POST)
        if form.is_valid():
            year = form.cleaned_data['year']
            graduates = form.cleaned_data['graduates']

            #update if year exists, otherwise create a new one
            obj, created = GraduationData.objects.update_or_create(
                year=year, defaults={'graduates': graduates}
            )

            return redirect('graduates')  # reload page after submit
    else:
        form = GraduationForm()

    #fetch all stored data
    data = GraduationData.objects.all().order_by('-year')

    #render page with form and data
    return render(request, "graduates.html", {'form': form, 'data': data})
