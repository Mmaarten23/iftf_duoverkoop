"""iftf_duoverkoop URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
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
from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve

from iftf_duoverkoop import views, urls_dev

urlpatterns = [
    path('', views.main, name='main'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('admin/', admin.site.urls),
    path(r'order/', views.order, name='order'),
    path('purchase_history/', views.purchase_history, name='purchase_history'),
    path('purchase_history/edit/<int:purchase_id>/', views.edit_purchase, name='edit_purchase'),
    path('purchase_history/delete/<int:purchase_id>/', views.delete_purchase, name='delete_purchase'),
    path('verify/', views.verify_code, name='verify_code'),
    path('export/', views.export, name='export'),
    path('db-info/', views.db_info, name='db_info'),
    path('get_performances_by_association/<str:association_name>/', views.get_performances_by_association, name='get_performances_by_association'),
    path('get_performance_prices/', views.get_performance_prices, name='get_performance_prices'),
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
