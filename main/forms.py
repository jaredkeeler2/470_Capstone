from django import forms
from .models import GraduationData
from datetime import datetime

class GraduationForm(forms.ModelForm):
    current_year = datetime.now().year

    #Dropdown choices: start with blank placeholder, then valid years
    YEAR_CHOICES = [("", "Select a Year")] + [
        (y, str(y)) for y in range(2021, current_year + 1)
    ]

    #Dropdown field
    year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        label="Year",
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = GraduationData
        fields = ['year', 'graduates']

    def clean_year(self):
        """Validate year from dropdown"""
        year = self.cleaned_data['year']

        #Handle empty selection
        if not year:
            raise forms.ValidationError("Please select a year.")

        year = int(year)
        current_year = datetime.now().year
        current_month = datetime.now().month

        if year < 2021 or year > current_year:
            raise forms.ValidationError(f"Year must be between 2021 and {current_year}.")

        if year == current_year and current_month < 7:
            raise forms.ValidationError(
                f"You can’t enter graduation data for {year} until after July."
            )

        return year

    def validate_unique(self):
        pass
