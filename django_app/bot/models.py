from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta
import json


class User(AbstractUser):
    """Extended user model for Telegram users"""
    USER_TYPES = (
        ('client', 'Client'),
        ('junkyard', 'Junkyard'),
        ('admin', 'Admin'),
    )
    
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    telegram_username = models.CharField(max_length=100, blank=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='client')
    phone_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active_telegram = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


class City(models.Model):
    """Cities where the service is available"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Cities"
    
    def __str__(self):
        return self.name


class Brand(models.Model):
    """Car brands"""
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name


class Model(models.Model):
    """Car models"""
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.brand.name} {self.name}"


class Junkyard(models.Model):
    """Junkyard information"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='junkyard_profile')
    phone = models.CharField(max_length=20)
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    location = models.TextField(help_text="Location description or Google Maps link")
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    payment_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Rating fields
    total_ratings = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    
    def update_rating(self):
        """Update average rating based on all ratings"""
        ratings = self.ratings.all()
        if ratings.exists():
            self.total_ratings = ratings.count()
            self.average_rating = ratings.aggregate(models.Avg('rating'))['rating__avg'] or 0
            # Auto-verify if conditions are met
            if self.average_rating >= 4.5 and self.total_ratings >= 10:
                self.is_verified = True
        else:
            self.total_ratings = 0
            self.average_rating = 0.00
        self.save()
    
    def __str__(self):
        return f"{self.user.first_name} - {self.city.name}"


class Request(models.Model):
    """Customer requests for auto parts"""
    STATUS_CHOICES = (
        ('new', 'New'),
        ('active', 'Active'),
        ('accepted', 'Accepted'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    )
    
    order_id = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requests')
    city = models.ForeignKey(City, on_delete=models.CASCADE)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    model = models.ForeignKey(Model, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    parts = models.TextField(help_text="Required parts description (legacy field)", blank=True)
    media_files = models.JSONField(default=list, blank=True, help_text="Telegram file IDs for photos/videos")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.conf import settings
            hours = getattr(settings, 'REQUEST_EXPIRY_HOURS', 6)
            self.expires_at = timezone.now() + timedelta(hours=hours)
        
        if not self.order_id:
            self.order_id = self.generate_order_id()
        
        super().save(*args, **kwargs)
    
    def generate_order_id(self):
        """Generate unique order ID based on city code and date"""
        from django.utils import timezone
        import random
        now = timezone.now()
        date_str = now.strftime('%y%m%d')
        city_code = self.city.code

        # Try to find a unique order ID
        max_attempts = 100
        for attempt in range(max_attempts):
            # Find the next sequential number for today
            today_requests = Request.objects.filter(
                created_at__date=now.date(),
                city=self.city
            ).count()

            # Add some randomness to avoid conflicts
            sequence = str(today_requests + 1 + attempt).zfill(3)
            order_id = f"{city_code}{date_str}{sequence}"

            # Check if this order_id already exists
            if not Request.objects.filter(order_id=order_id).exists():
                return order_id

        # Fallback: use random number if all attempts failed
        random_suffix = str(random.randint(1000, 9999))
        return f"{city_code}{date_str}{random_suffix}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def has_items(self):
        """Check if request has individual items"""
        return self.items.exists()
    
    @property
    def items_count(self):
        """Get count of individual items"""
        return self.items.count()
    
    @property
    def all_parts_description(self):
        """Get all parts as a combined description"""
        if self.has_items:
            items = self.items.all()
            parts_list = []
            for item in items:
                parts_list.append(f"• {item.name}" + (f" - {item.description}" if item.description else ""))
            return "\n".join(parts_list)
        return self.parts
    
    def add_item(self, name, description="", quantity=1, unit_price=0.00):
        """Add a new item to this request"""
        return RequestItem.objects.create(
            request=self,
            name=name,
            description=description,
            quantity=quantity,
            unit_price=unit_price
        )
    
    def calculate_total_price(self):
        """Calculate total price for all items in this request"""
        return sum(item.calculate_line_total() for item in self.items.all())
    
    def __str__(self):
        parts_preview = self.all_parts_description[:50] if self.all_parts_description else "No items"
        return f"{self.order_id} - {self.user.first_name} - {parts_preview}"


class RequestItem(models.Model):
    """Individual items/parts within a request"""
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=200, help_text="Name of the part/item")
    description = models.TextField(blank=True, help_text="Additional description of the item (DEPRECATED)")
    quantity = models.PositiveIntegerField(default=1, help_text="Quantity needed (DEPRECATED - fixed to 1)")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Unit price per item", null=True, blank=True)
    currency = models.CharField(max_length=3, default='SAR', blank=True, help_text="Currency code", null=True)
    media_files = models.JSONField(default=list, blank=True, help_text="Telegram file IDs for photos/videos of this specific item")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def calculate_line_total(self):
        """Calculate line total for this item (unit_price * quantity)"""
        unit_price = self.unit_price or 0
        return unit_price * self.quantity
    
    def __str__(self):
        return f"{self.request.order_id} - {self.name}" + (f" (x{self.quantity})" if self.quantity > 1 else "")


class Offer(models.Model):
    """Junkyard offers for requests"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='offers')
    junkyard = models.ForeignKey(Junkyard, on_delete=models.CASCADE, related_name='offers')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total offer price")
    delivery_time = models.CharField(max_length=100, blank=True, help_text="Expected delivery time (DEPRECATED)")
    notes = models.TextField(blank=True, help_text="Additional notes from junkyard")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('request', 'junkyard')
    
    def __str__(self):
        return f"{self.request.order_id} - {self.junkyard.user.first_name} - {self.price}"


class OfferItem(models.Model):
    """Individual item prices in an offer"""
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='items')
    request_item = models.ForeignKey(RequestItem, on_delete=models.CASCADE, related_name='offer_items')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price for this specific item")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('offer', 'request_item')
    
    def __str__(self):
        return f"{self.offer} - {self.request_item.name} - {self.price}"


class Conversation(models.Model):
    """Chat conversations between clients and junkyards"""
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='client_conversations')
    junkyard = models.ForeignKey(User, on_delete=models.CASCADE, related_name='junkyard_conversations')
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='conversations')
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.client.first_name} <-> {self.junkyard.first_name} ({self.request.order_id})"


class JunkyardRating(models.Model):
    """Customer ratings for junkyards"""
    junkyard = models.ForeignKey(Junkyard, on_delete=models.CASCADE, related_name='ratings')
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_ratings')
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('junkyard', 'client', 'request')
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update junkyard rating after saving
        self.junkyard.update_rating()
    
    def __str__(self):
        return f"{self.client.first_name} -> {self.junkyard.user.first_name}: {self.rating}★"


class JunkyardStaff(models.Model):
    """Staff members linked to junkyards with specific roles"""
    ROLE_CHOICES = (
        ('junkyard_manager', 'مدير التشليح'),
        ('junkyard_staff', 'موظف التشليح'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='junkyard_roles')
    junkyard = models.ForeignKey(Junkyard, on_delete=models.CASCADE, related_name='staff_members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='junkyard_staff')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'junkyard')
    
    def __str__(self):
        return f"{self.user.first_name} - {self.junkyard.user.first_name} ({self.get_role_display()})"


class SystemSetting(models.Model):
    """System-wide settings"""
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.key}: {self.value}"
    
    @classmethod
    def get_setting(cls, key, default=None):
        """Get a setting value"""
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default
    
    @classmethod
    def set_setting(cls, key, value, description=""):
        """Set a setting value"""
        setting, created = cls.objects.get_or_create(
            key=key,
            defaults={'value': value, 'description': description}
        )
        if not created:
            setting.value = value
            setting.description = description
            setting.save()
        return setting


class TelegramMessage(models.Model):
    """Log of Telegram messages for debugging and analytics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    telegram_message_id = models.BigIntegerField()
    message_type = models.CharField(max_length=50)
    content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user} - {self.message_type} - {self.created_at}"
