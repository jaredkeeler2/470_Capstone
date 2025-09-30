from django.contrib import admin
from .models import Course
# Register your models here.

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("id", "term", "code", "title", "enrolled")
    search_fields = ("code", "title")
    list_filter = ("term",)
