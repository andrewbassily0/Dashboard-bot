from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.public_dashboard, name='public_dashboard'),
    path('admin-dashboard/', views.dashboard_home, name='home'),
    
    # Requests
    path('requests/', views.requests_list, name='requests_list'),
    path('requests/<int:request_id>/', views.request_detail, name='request_detail'),
    
    # Junkyards
    path('junkyards/', views.junkyards_list, name='junkyards_list'),
    path('junkyards/<int:junkyard_id>/', views.junkyard_detail, name='junkyard_detail'),
    path('junkyards/add/', views.add_junkyard, name='add_junkyard'),
    
    # Users
    path('users/', views.users_list, name='users_list'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
    
    # Analytics
    path('analytics/', views.analytics_view, name='analytics'),
    
    # API endpoints
    path('api/stats/', views.api_stats, name='api_stats'),
]

