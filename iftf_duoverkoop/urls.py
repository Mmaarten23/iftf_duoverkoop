"""iftf_duoverkoop URL Configuration"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve

from iftf_duoverkoop.src.views.auth import login_view, logout_view
from iftf_duoverkoop.src.views.order import order, main, get_last_customer
from iftf_duoverkoop.src.views.history import purchase_history, edit_purchase, delete_purchase
from iftf_duoverkoop.src.views.export import export
from iftf_duoverkoop.src.views.verify import verify_code
from iftf_duoverkoop.src.views.api import db_info, get_performances_by_association, get_performance_prices
from iftf_duoverkoop.src.dashboard.urls import urlpatterns as dashboard_urlpatterns
from iftf_duoverkoop import urls_dev

urlpatterns = [
    path('', main, name='main'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('admin/', admin.site.urls),
    path('dashboard/', include((dashboard_urlpatterns, 'dashboard'))),

    # Core app pages
    path('order/', order, name='order'),
    path('purchase_history/', purchase_history, name='purchase_history'),
    path('purchase_history/edit/<int:purchase_id>/', edit_purchase, name='edit_purchase'),
    path('purchase_history/delete/<int:purchase_id>/', delete_purchase, name='delete_purchase'),
    path('verify/', verify_code, name='verify_code'),
    path('export/', export, name='export'),

    # Internal JSON API
    path('api/db-info/', db_info, name='db_info'),
    path('api/performances-by-association/<str:association_name>/', get_performances_by_association, name='get_performances_by_association'),
    path('api/performance-prices/', get_performance_prices, name='get_performance_prices'),
    path('api/last-customer/', get_last_customer, name='get_last_customer'),
]

if settings.DEBUG:
    urlpatterns = [
        path('--DEBUG--/', include(urls_dev.urls(), namespace='debug')),
    ] + urlpatterns

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += [
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]
