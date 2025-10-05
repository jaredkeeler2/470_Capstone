from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from .models import Course
from .csce_scraper import build_term_codes_past_years

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