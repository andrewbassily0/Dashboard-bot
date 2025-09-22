from django.urls import path
from . import views

app_name = 'bot'

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('health/queue/', views.health_queue, name='health_queue'),
    path('health/notifications/', views.health_notifications, name='health_notifications'),
    # Telegram webhook
    path('webhook/telegram/', views.TelegramWebhookView.as_view(), name='telegram_webhook'),
    
    # n8n endpoints deprecated - using workflow service instead
    # path('webhook/n8n/new-request/', views.n8n_webhook_new_request, name='n8n_new_request'),
    # path('webhook/n8n/new-offer/', views.n8n_webhook_new_offer, name='n8n_new_offer'),
    
    # API endpoints (keeping some for dashboard/debug purposes)
    path('api/requests/active/', views.get_active_requests, name='active_requests'),
    path('api/junkyards/', views.get_junkyards_by_city, name='junkyards_by_city'),
    # path('api/telegram/send-message/', views.send_telegram_message, name='send_telegram_message'),
    path('api/stats/', views.get_system_stats, name='system_stats'),
    
    # Debug endpoints
    path('api/debug/junkyards/', views.debug_junkyards_in_city, name='debug_junkyards'),
]

