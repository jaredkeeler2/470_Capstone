from django import forms
from .models import GraduationData
from datetime import datetime

#form for graduation model
class GraduationForm(forms.ModelForm):
    class Meta:
        model = GraduationData
        fields = ['year', 'graduates'] #only displays these two fields in the form (when using form.as_p it only sees those 2 fields)

    def clean_year(self): #validates user input
        year = self.cleaned_data['year']
        current_year = datetime.now().year
        current_month = datetime.now().month

        #restrict to 2021 → current year
        if year < 2021 or year > current_year:
            raise forms.ValidationError(f"Year must be between 2021 and {current_year}.")

        #don't allow entering current year's data before July
        if year == current_year and current_month < 12:
            raise forms.ValidationError(
                f"You can’t enter graduation data for {year} until after July."
            )

        return year

    #this overrides djangos duplicate check
    def validate_unique(self):
        pass
