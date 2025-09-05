from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import (
    User, City, Brand, Model, Junkyard, Request, 
    Offer, Conversation, JunkyardRating, SystemSetting, TelegramMessage
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'user_type', 'telegram_id', 'is_active_telegram', 'date_joined')
    list_filter = ('user_type', 'is_active_telegram', 'is_staff', 'is_superuser')
    search_fields = ('username', 'first_name', 'last_name', 'telegram_username', 'telegram_id')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Telegram Info'), {
            'fields': ('telegram_id', 'telegram_username', 'user_type', 'phone_number', 'is_active_telegram')
        }),
    )


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'code')
    list_editable = ('is_active',)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'models_count')
    list_filter = ('is_active',)
    search_fields = ('name',)
    list_editable = ('is_active',)
    
    def models_count(self, obj):
        return obj.models.count()
    models_count.short_description = _('عدد الموديلات')


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'is_active')
    list_filter = ('brand', 'is_active')
    search_fields = ('name', 'brand__name')
    list_editable = ('is_active',)


@admin.register(Junkyard)
class JunkyardAdmin(admin.ModelAdmin):
    list_display = ('user', 'city', 'phone', 'is_active', 'is_verified', 'rating_display', 'total_ratings')
    list_filter = ('city', 'is_active', 'is_verified')
    search_fields = ('user__first_name', 'user__last_name', 'phone')
    readonly_fields = ('total_ratings', 'average_rating', 'created_at')
    list_editable = ('is_active', 'is_verified')
    
    def rating_display(self, obj):
        if obj.total_ratings > 0:
            stars = '⭐' * int(obj.average_rating)
            return format_html(f'{stars} {obj.average_rating:.1f}')
        return _('لا توجد تقييمات')
    rating_display.short_description = _('التقييم')


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'user', 'city', 'brand', 'model', 'year', 'status', 'created_at', 'expires_at')
    list_filter = ('status', 'city', 'brand', 'created_at')
    search_fields = ('order_id', 'user__first_name', 'user__last_name', 'parts')
    readonly_fields = ('order_id', 'created_at', 'expires_at')
    date_hierarchy = 'created_at'
    list_editable = ('status',)


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('request', 'junkyard', 'price', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('request__order_id', 'junkyard__user__first_name')
    date_hierarchy = 'created_at'
    list_editable = ('status',)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('client', 'junkyard', 'request', 'is_active', 'started_at', 'ended_at')
    list_filter = ('is_active', 'started_at')
    search_fields = ('client__first_name', 'junkyard__first_name', 'request__order_id')
    readonly_fields = ('started_at',)


@admin.register(JunkyardRating)
class JunkyardRatingAdmin(admin.ModelAdmin):
    list_display = ('junkyard', 'client', 'request', 'rating', 'comment', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('junkyard__user__first_name', 'client__first_name')
    readonly_fields = ('created_at',)


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'description', 'updated_at')
    search_fields = ('key', 'description')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'message_type', 'telegram_message_id', 'created_at')
    list_filter = ('message_type', 'created_at')
    search_fields = ('user__first_name', 'message_type')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


# Customize admin site
admin.site.site_header = _('نظام قطع الغيار - لوحة التحكم')
admin.site.site_title = _('نظام قطع الغيار')
admin.site.index_title = _('مرحباً بك في لوحة تحكم نظام قطع الغيار')
