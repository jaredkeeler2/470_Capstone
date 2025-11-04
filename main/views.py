from django.shortcuts import render, redirect
from django.http import HttpResponse
import csv
from django.utils import timezone
from django.conf import settings
from django.contrib import messages
from datetime import timedelta
from .models import Course ,GraduationData
from .csce_scraper import build_term_codes_past_years
from .forms import GraduationForm
from datetime import datetime
import json
import os
import io

#homepage
def home(request):
    #get all terms for the past 5 years
    all_terms = [term for term, label in build_term_codes_past_years(years=5)]

    #determine which terms are already in the database
    existing_terms = set(Course.objects.values_list('term', flat=True))

    #find missing terms
    missing_terms = [term for term in all_terms if term not in existing_terms]

    #only scrape missing terms
    if missing_terms:
        print(f"Scraping missing terms: {missing_terms}")
        Course.save_courses(subj="CSCE")
    else:
        print("All terms already present. No scraping needed.")

    #get unique course codes for dropdown
    courses = Course.objects.values_list('code', flat=True).distinct().order_by('code')

    #load ARIMA forecast data for Plotly
    forecast_path = os.path.join("main", "forecast_data.json")
    if os.path.exists(forecast_path):
        with open(forecast_path, "r") as f:
            raw_data = json.load(f)
            course_data = json.dumps(raw_data)  #convert to JSON string
    else:
        print("No forecast_data.json found. Run arima.py first.")
        course_data = "[]"

    #render home page with dropdown + chart data
    return render(request, 'home.html', {
        'courses': courses,
        'course_data': course_data
    })
    
    
def rescrape_data(request):
    if request.method == 'POST':
        all_terms = [term for term, label in build_term_codes_past_years(years=5)]
        existing_terms = set(Course.objects.values_list('term', flat=True))
        missing_terms = [term for term in all_terms if term not in existing_terms]

        if missing_terms:
            Course.save_courses(subj="CSCE")
            messages.success(request, f"Rescraped missing terms: {', '.join(missing_terms)}")
        else:
            messages.info(request, "No missing terms to rescrape.")

    return redirect('data')

def graduate_data(request):
    error = None
    GRADUATE_PASSWORD = getattr(settings, 'GRADUATE_PASSWORD', 'grad123')  # new key

    # Auto-fill database
    current_year = datetime.now().year
    for year in range(2021, current_year + 1):
        GraduationData.objects.get_or_create(year=year, defaults={'graduates': 0})

    if request.method == 'POST':
        password = request.POST.get('graduate_password', '').strip()
        if password != GRADUATE_PASSWORD:
            error = "Invalid password. You are not authorized to submit graduation data."
        else:
            form = GraduationForm(request.POST)
            if form.is_valid():
                year = form.cleaned_data['year']
                graduates = form.cleaned_data['graduates']
                GraduationData.objects.update_or_create(
                    year=year, defaults={'graduates': graduates}
                )
                return redirect('graduates')
    else:
        form = GraduationForm()

    data = GraduationData.objects.all().order_by('-year')

    return render(request, "graduates.html", {'form': form, 'data': data, 'error': error})



#Fetch data from Courses
def sanitize_csv_value(value):
    if value and value[0] in ('=', '+', '-', '@'):
        value = "'" + value  # prefix with apostrophe to neutralize Excel formulas
    return value.strip()


# Fetch data from Courses
def data(request):
    message = None
    error = None
    UPLOAD_PASSWORD = getattr(settings, 'UPLOAD_PASSWORD', 'admin123')

    if request.method == 'POST' and 'csv_file' in request.FILES:
        password = request.POST.get('upload_password', '').strip()

        if password != UPLOAD_PASSWORD:
            error = "Invalid password."
        else:
            csv_file = request.FILES['csv_file']
            if not csv_file.name.endswith('.csv'):
                error = "Error: File is not CSV type."
            else:
                try:
                    data_set = csv_file.read().decode('UTF-8')
                    io_string = io.StringIO(data_set)
                    reader = csv.DictReader(io_string)

                    required_columns = {'Term', 'Code', 'Title', 'Enrolled'}
                    if not required_columns.issubset(reader.fieldnames):
                        error = f"Error: CSV must contain columns: {', '.join(required_columns)}."
                    else:
                        updated_count = 0
                        skipped_count = 0
                        for row in reader:
                            term = sanitize_csv_value(row.get('Term', ''))
                            code = sanitize_csv_value(row.get('Code', ''))
                            title = sanitize_csv_value(row.get('Title', ''))
                            enrolled = row.get('Enrolled', '').strip()
                            if not term or not code or not title or not enrolled:
                                skipped_count += 1
                                continue
                            try:
                                enrolled = int(enrolled)
                                if enrolled < 0:
                                    skipped_count += 1
                                    continue
                            except ValueError:
                                skipped_count += 1
                                continue
                            Course.objects.update_or_create(
                                code=code,
                                term=term,
                                defaults={'title': title, 'enrolled': enrolled}
                            )
                            updated_count += 1
                        message = f"CSV uploaded successfully. {updated_count} rows updated, {skipped_count} rows skipped."
                except Exception as e:
                    error = f"Error processing CSV: {str(e)}"

    courses = Course.objects.all().order_by('-term', 'code')
    terms = {}
    for c in courses:
        terms.setdefault(c.term, []).append(c)

    return render(request, 'data.html', {'terms': terms, 'message': message, 'error': error})


def download_data(request):
    # Download all courses as CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="course_data.csv"'

    writer = csv.writer(response)
    writer.writerow(['Term', 'Code', 'Title', 'Enrolled'])

    for course in Course.objects.all().order_by('-term', 'code'):
        writer.writerow([
            sanitize_csv_value(course.term),
            sanitize_csv_value(course.code),
            sanitize_csv_value(course.title),
            course.enrolled
        ])

    return response
