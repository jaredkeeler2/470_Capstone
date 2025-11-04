"""
URL configuration for Capstone project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from main.views import home, graduate_data, data, download_data,rescrape_data


#url routes
urlpatterns = [
    #path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('graduates/', graduate_data, name='graduates'),
    path('data/', data, name='data'),
    path('download/', download_data, name='download_data'),
    path('rescrape/',rescrape_data, name='rescrape_data'), # Rescrape missing terms
]