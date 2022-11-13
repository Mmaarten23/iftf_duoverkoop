from django.urls import path

from iftf_duoverkoop import views_dev


def urls():
    return get_urls(), "iftf_duoverkoop"


def get_urls():
    urlpatterns = [path("load_db/", views_dev.load_db, name='debug_load_db')]
    return urlpatterns
