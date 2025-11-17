from django.conf import settings

def add_prefix(request):
    return {"URL_PREFIX": settings.URL_PREFIX}
