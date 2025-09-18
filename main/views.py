from django.shortcuts import render

#homepage
def home(request): 
    return render(request, "home.html")