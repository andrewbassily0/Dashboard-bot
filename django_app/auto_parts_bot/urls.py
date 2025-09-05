"""
URL configuration for auto_parts_bot project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.shortcuts import redirect

def health_check(request):
    """Health check endpoint for Docker"""
    return JsonResponse({"status": "healthy", "service": "auto_parts_bot"})

def root_redirect(request):
    """Redirect root URL to dashboard"""
    return redirect('dashboard:public_dashboard')

urlpatterns = [
    path('', root_redirect, name='root'),
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('bot/', include('bot.urls')),
    path('dashboard/', include('dashboard.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
