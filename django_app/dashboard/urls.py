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
    path('junkyards/<int:junkyard_id>/test-notification/', views.test_junkyard_notification, name='test_junkyard_notification'),
    path('junkyards/<int:junkyard_id>/diagnose/', views.diagnose_junkyard_issues, name='diagnose_junkyard_issues'),
    path('junkyards/<int:junkyard_id>/quick-fix/', views.quick_fix_junkyard, name='quick_fix_junkyard'),
    path('junkyards/<int:junkyard_id>/edit/', views.edit_junkyard, name='edit_junkyard'),
    path('junkyards/fix-user-types/', views.fix_junkyard_user_types, name='fix_junkyard_user_types'),
    path('junkyards/debug-edit-issue/', views.debug_junkyard_edit_issue, name='debug_junkyard_edit_issue'),
    path('junkyards/add/', views.add_junkyard, name='add_junkyard'),
    
    # Users
    path('users/', views.users_list, name='users_list'),
    path('users/add/', views.add_user, name='add_user'),
    path('users/<int:user_id>/toggle-status/', views.toggle_user_status, name='toggle_user_status'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    
    # Settings
    path('settings/', views.settings_view, name='settings'),
    
    # Testing
    path('test-order-workflow/', views.test_order_workflow, name='test_order_workflow'),
    
    # Analytics
    path('analytics/', views.analytics_view, name='analytics'),
    
    # Telegram Media
    path('telegram/image/<str:file_id>/', views.telegram_image, name='telegram_image'),
    path('telegram/video/<str:file_id>/', views.telegram_video, name='telegram_video'),
    
    # API endpoints
    path('api/stats/', views.api_stats, name='api_stats'),
]

