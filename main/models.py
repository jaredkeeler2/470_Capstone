from django.db import models
from django.utils import timezone
from datetime import datetime

# Create your models here.
# File: main/models.py
from django.db import models
from django.utils import timezone
from datetime import datetime

class Course(models.Model):
    term = models.CharField(max_length=10)
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=255)
    enrolled = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.title} ({self.enrolled})"

    @classmethod
    def save_courses(cls, subj="CSCE"):
        from .csce_scraper import schedule_scraper, build_term_codes_past_years

        # Get all terms for the past 5 years
        all_terms = build_term_codes_past_years(years=5)

        # Determine which terms are already in the database
        existing_terms = set(Course.objects.values_list('term', flat=True))

        # Filter only missing terms
        missing_terms = [term for term, label in all_terms if term not in existing_terms]

        if not missing_terms:
            print("All semesters are already in there. No scraping needed.")
            return

        for term_code in missing_terms:
            print(f"Scraping missing term: {term_code}")
            results = schedule_scraper(term=term_code, subj=subj)
            print(f"Found {len(results)} courses for {term_code}")

            for code, title, enrolled in results:
                cls.objects.update_or_create(
                    code=code,
                    term=term_code,
                    defaults={'title': title, 'enrolled': enrolled}
                )
