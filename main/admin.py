from django.contrib import admin
from .models import Course, Prerequisite

# Register your models here.


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('term', 'code', 'title', 'enrolled', 'updated_at')
    list_filter = ('term',)
    search_fields = ('code', 'title')
    ordering = ('code',)
    

@admin.register(Prerequisite)
class PrerequisiteAdmin(admin.ModelAdmin):
    list_display = ("course_code", "prereq_1", "prereq_2")
    search_fields = ("course_code", "prereq_1", "prereq_2")
    