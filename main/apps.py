from django.apps import AppConfig
import threading


class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'
    
    def ready(self):
        # Run the scraper in the background when the server starts
        from main.models import Prerequisite
        from main.prereq_scraper import build_two_prereq_map

        threading.Thread(target=Prerequisite.scrape_if_empty, args=(build_two_prereq_map,)).start()
