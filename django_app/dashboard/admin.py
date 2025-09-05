from django.contrib import admin
from .models import DashboardStats


@admin.register(DashboardStats)
class DashboardStatsAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_users', 'total_requests', 'total_offers', 'total_junkyards', 'created_at')
    list_filter = ('date', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'
    
    def has_add_permission(self, request):
        # Allow only one stats record per day
        return not DashboardStats.objects.filter(date=DashboardStats.objects.latest('date').date).exists() if DashboardStats.objects.exists() else True
