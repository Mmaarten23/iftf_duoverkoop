"""
dashboard/urls.py – URL patterns for the staff management dashboard.

Mounted at /dashboard/ with the 'dashboard' namespace.
"""
from django.urls import path
from iftf_duoverkoop.src.dashboard import views as v

urlpatterns = [
    # Overview
    path('', v.dashboard_home, name='dashboard_home'),

    # Associations
    path('associations/', v.dashboard_associations, name='dashboard_associations'),
    path('associations/create/', v.dashboard_association_create, name='dashboard_association_create'),
    path('associations/<str:name>/edit/', v.dashboard_association_edit, name='dashboard_association_edit'),
    path('associations/<str:name>/delete/', v.dashboard_association_delete, name='dashboard_association_delete'),
    path('associations/upload-logo/', v.dashboard_logo_upload, name='dashboard_logo_upload'),

    # Performances
    path('performances/', v.dashboard_performances, name='dashboard_performances'),
    path('performances/create/', v.dashboard_performance_create, name='dashboard_performance_create'),
    path('performances/<str:key>/edit/', v.dashboard_performance_edit, name='dashboard_performance_edit'),
    path('performances/<str:key>/delete/', v.dashboard_performance_delete, name='dashboard_performance_delete'),

    # Users
    path('users/', v.dashboard_users, name='dashboard_users'),
    path('users/create/', v.dashboard_user_create, name='dashboard_user_create'),
    path('users/<int:user_id>/edit/', v.dashboard_user_edit, name='dashboard_user_edit'),
    path('users/<int:user_id>/delete/', v.dashboard_user_delete, name='dashboard_user_delete'),

    # Audit log
    path('audit/', v.dashboard_audit, name='dashboard_audit'),
    path('audit/<int:log_id>/', v.dashboard_audit_detail, name='dashboard_audit_detail'),

    # System
    path('system/', v.dashboard_system, name='dashboard_system'),
    path('system/sync-permissions/', v.dashboard_sync_permissions, name='dashboard_sync_permissions'),
]

