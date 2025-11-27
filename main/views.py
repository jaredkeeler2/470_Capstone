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
import sys
import subprocess
import io

#homepage
def home(request):
    #get all terms for the past 5 years
    data_changed = False
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
        
    if data_changed:
        script_path = os.path.join(settings.BASE_DIR, "main", "arima.py")
        subprocess.run([sys.executable, script_path], check=True)
    else:
        print("No change in database.")

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
        # Delete all existing course data
        Course.objects.all().delete()

        # Scrape all terms for past 5 years
        all_terms = [term for term, label in build_term_codes_past_years(years=5)]
        Course.save_courses(subj="CSCE")  # your existing scraping function

        script_path = os.path.join(settings.BASE_DIR, "main", "arima.py")
        subprocess.run([sys.executable, script_path], check=True)
        
        messages.success(request, f"All courses have been removed and rescraped for terms: {', '.join(all_terms)}")
        

    return redirect('home')

def graduate_data(request):
    error = None
    GRADUATE_PASSWORD = getattr(settings, 'GRADUATE_PASSWORD', 'grad123')

    # Auto-fill database
    current_year = datetime.now().year
    for year in range(2021, current_year + 1):
        GraduationData.objects.get_or_create(year=year, defaults={'graduates': 0})

    if request.method == 'POST':
        password = request.POST.get('graduate_password', '').strip()

        # If password is wrong → stay on same page + show message
        if password != GRADUATE_PASSWORD:
            error = "Invalid password."
            form = GraduationForm(request.POST)  # keeps the values user typed
        else:
            form = GraduationForm(request.POST)
            if form.is_valid():
                year = form.cleaned_data['year']
                graduates = form.cleaned_data['graduates']
                GraduationData.objects.update_or_create(
                    year=year,
                    defaults={'graduates': graduates}
                )
                script_path = os.path.join(settings.BASE_DIR, "main", "arima.py") #Run Arima.py when ASD data is change. 
                subprocess.run([sys.executable, script_path], check=True)
                return redirect('graduates')
        
    else:
        form = GraduationForm()

    data = GraduationData.objects.all().order_by('-year')

    return render(request, "graduates.html", {
        'form': form,
        'data': data,
        'error': error
    })



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

    # Handle CSV upload
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

                    if not reader.fieldnames or len(reader.fieldnames) < 3:
                        error = "CSV must have at least Code, Title, and one Term column."
                    else:
                        term_columns = reader.fieldnames[2:]  # Columns after Code and Title
                        updated_count = 0
                        skipped_count = 0
                        for row in reader:
                            code = sanitize_csv_value(row.get('Code', ''))
                            title = sanitize_csv_value(row.get('Title', ''))
                            if not code or not title:
                                skipped_count += 1
                                continue

                            for term in term_columns:
                                enrolled = row.get(term, '').strip()
                                if enrolled in ('', '-'):
                                    continue
                                try:
                                    enrolled = int(enrolled)
                                except ValueError:
                                    skipped_count += 1
                                    continue

                                # Update or create course
                                Course.objects.update_or_create(
                                    code=code,
                                    term=term,
                                    defaults={'title': title, 'enrolled': enrolled}
                                )
                                updated_count += 1
                        script_path = os.path.join(settings.BASE_DIR, "main", "arima.py") #Run Arima.py when data is change before return
                        subprocess.run([sys.executable, script_path], check=True)
                        message = f"CSV uploaded successfully. {updated_count} values updated, {skipped_count} skipped."

                except Exception as e:
                    error = f"Error processing CSV: {str(e)}"

    # Prepare pivot table for display
    all_terms = sorted(Course.objects.values_list('term', flat=True).distinct(), reverse=True)
    courses_dict = {}

    for c in Course.objects.all().order_by('code'):
        if c.code not in courses_dict:
            courses_dict[c.code] = {'title': c.title, 'enrolled_list': []}

    for code, info in courses_dict.items():
        enrolled_list = []
        for term in all_terms:
            course = Course.objects.filter(code=code, term=term).first()
            enrolled_list.append(course.enrolled if course else '-')
        info['enrolled_list'] = enrolled_list
        
    
    return render(request, 'data.html', {
        'courses_dict': courses_dict,
        'all_terms': all_terms,
        'message': message,
        'error': error
    })


def download_data(request):
    all_terms = sorted(Course.objects.values_list('term', flat=True).distinct(), reverse=True)
    courses_dict = {}

    for c in Course.objects.all().order_by('code'):
        if c.code not in courses_dict:
            courses_dict[c.code] = {'title': c.title, 'enrolled_list': []}

    for code, info in courses_dict.items():
        enrolled_list = []
        for term in all_terms:
            course = Course.objects.filter(code=code, term=term).first()
            enrolled_list.append(course.enrolled if course else '-')
        info['enrolled_list'] = enrolled_list

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="course_data.csv"'
    writer = csv.writer(response)
    writer.writerow(['Code', 'Title'] + all_terms)

    for code, course in courses_dict.items():
        writer.writerow([code, course['title']] + course['enrolled_list'])

    return response

def model_info(request):
    return render(request, 'model_info.html')