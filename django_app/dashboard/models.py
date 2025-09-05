from django.db import models

# Create your models here.


class DashboardStats(models.Model):
    """Dashboard statistics model"""
    date = models.DateField(auto_now_add=True, unique=True)
    total_users = models.IntegerField(default=0)
    total_requests = models.IntegerField(default=0)
    total_offers = models.IntegerField(default=0)
    total_junkyards = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'إحصائيات الداشبورد'
        verbose_name_plural = 'إحصائيات الداشبورد'
        ordering = ['-date']
    
    def __str__(self):
        return f'إحصائيات {self.date}'
