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
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from iftf_duoverkoop import views, urls_dev

urlpatterns = [
    path('', views.main, name='main'),
    path('admin/', admin.site.urls),
    path('order/', views.order, name='order'),
    path('purchase_history/', views.purchase_history, name='purchase_history'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns = [
        path('--DEBUG--/', include(urls_dev.urls(), namespace='debug')),
    ] + urlpatterns
