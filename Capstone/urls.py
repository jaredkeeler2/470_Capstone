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
from main.views import home, graduate_data, data, download_data,rescrape_data, model_info
from django.conf import settings

prefix = settings.URL_PREFIX

#url routes
urlpatterns = [
    path(f'{prefix}/', home, name='home'),
    path(f'{prefix}/graduates/', graduate_data, name='graduates'),
    path(f'{prefix}/data/', data, name='data'),
    path(f'{prefix}/model_info/', model_info, name='model_info'),
    path(f'{prefix}/download/', download_data, name='download_data'),
    path(f'{prefix}/rescrape/', rescrape_data, name='rescrape_data'),
]