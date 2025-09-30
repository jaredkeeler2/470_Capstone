from django.db import models

# Create your models here.
class Course(models.Model):
    term = models.CharField(max_length=6,blank=True)       # e.g., "202503"
    code = models.CharField(max_length=20,blank=True)      # e.g., "CSCE A101"
    title = models.CharField(max_length=255,blank=True)    # e.g., "Intro to CS"
    enrolled = models.IntegerField(default=0,blank=True)

class Meta:
    unique_together = ("term", "code")
    
def __str__(self):
    return f"{self.term} | {self.code} - {self.title} ({self.enrolled})"