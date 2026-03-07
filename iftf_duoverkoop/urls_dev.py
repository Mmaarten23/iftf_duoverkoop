from django.urls import path
from iftf_duoverkoop.src.views.dev import load_db


def urls():
    return get_urls(), "iftf_duoverkoop"


def get_urls():
    return [path("load_db/", load_db, name='debug_load_db')]
