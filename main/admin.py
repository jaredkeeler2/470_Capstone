from django.contrib import admin
from .models import Course
# Register your models here.


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('term', 'code', 'title', 'enrolled', 'updated_at')
    list_filter = ('term',)
    search_fields = ('code', 'title')
    ordering = ('code',)