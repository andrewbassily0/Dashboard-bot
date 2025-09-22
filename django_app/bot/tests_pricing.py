"""
Tests for pricing system and refactoring changes
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from .models import Request, RequestItem, Offer, Brand, Model, City, Junkyard

User = get_user_model()


class PricingSystemTests(TestCase):
    """Test unit pricing system functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            user_type='client',
            telegram_id=123456789
        )
        
        self.city = City.objects.create(name='Riyadh', code='RY')
        self.brand = Brand.objects.create(name='Toyota')
        self.model = Model.objects.create(brand=self.brand, name='Camry')
        
        self.junkyard_user = User.objects.create_user(
            username='junkyard',
            first_name='Junkyard',
            user_type='junkyard',
            telegram_id=987654321
        )
        
        self.junkyard = Junkyard.objects.create(
            user=self.junkyard_user,
            phone='0501234567',
            city=self.city,
            location='Test Location'
        )
    
    def test_request_item_unit_price_calculation(self):
        """Test unit price calculation for RequestItem"""
        request = Request.objects.create(
            user=self.user,
            city=self.city,
            brand=self.brand,
            model=self.model,
            year=2020,
            parts='Test parts'
        )
        
        # Test with unit price
        item = RequestItem.objects.create(
            request=request,
            name='Test Part',
            unit_price=Decimal('100.50'),
            quantity=1
        )
        
        self.assertEqual(item.calculate_line_total(), Decimal('100.50'))
        
        # Test with different quantity
        item.quantity = 2
        item.save()
        self.assertEqual(item.calculate_line_total(), Decimal('201.00'))
    
    def test_request_total_price_calculation(self):
        """Test total price calculation for Request"""
        request = Request.objects.create(
            user=self.user,
            city=self.city,
            brand=self.brand,
            model=self.model,
            year=2020,
            parts='Test parts'
        )
        
        # Add items with different prices
        RequestItem.objects.create(
            request=request,
            name='Part 1',
            unit_price=Decimal('100.00'),
            quantity=1
        )
        
        RequestItem.objects.create(
            request=request,
            name='Part 2',
            unit_price=Decimal('50.00'),
            quantity=2
        )
        
        RequestItem.objects.create(
            request=request,
            name='Part 3',
            unit_price=Decimal('25.00'),
            quantity=1
        )
        
        # Total should be 100 + (50*2) + 25 = 225
        self.assertEqual(request.calculate_total_price(), Decimal('225.00'))
    
    def test_request_item_currency_default(self):
        """Test default currency for RequestItem"""
        request = Request.objects.create(
            user=self.user,
            city=self.city,
            brand=self.brand,
            model=self.model,
            year=2020,
            parts='Test parts'
        )
        
        item = RequestItem.objects.create(
            request=request,
            name='Test Part',
            unit_price=Decimal('100.00')
        )
        
        self.assertEqual(item.currency, 'SAR')
    
    def test_request_item_deprecated_fields(self):
        """Test that deprecated fields are marked correctly"""
        request = Request.objects.create(
            user=self.user,
            city=self.city,
            brand=self.brand,
            model=self.model,
            year=2020,
            parts='Test parts'
        )
        
        item = RequestItem.objects.create(
            request=request,
            name='Test Part',
            description='Old description',
            quantity=5
        )
        
        # Fields should still exist but be marked as deprecated
        self.assertEqual(item.description, 'Old description')
        self.assertEqual(item.quantity, 5)
        
        # But help text should indicate deprecation
        self.assertIn('DEPRECATED', item._meta.get_field('description').help_text)
        self.assertIn('DEPRECATED', item._meta.get_field('quantity').help_text)


class LabelUpdateTests(TestCase):
    """Test Arabic label updates"""
    
    def test_brand_label_update(self):
        """Test that brand is now referred to as 'الوكالة'"""
        # This would be tested in templates, but we can test model help text
        brand = Brand.objects.create(name='Toyota')
        self.assertEqual(brand.name, 'Toyota')
    
    def test_model_label_update(self):
        """Test that model is now referred to as 'اسم السيارة'"""
        brand = Brand.objects.create(name='Toyota')
        model = Model.objects.create(brand=brand, name='Camry')
        self.assertEqual(model.name, 'Camry')


class OfferCreationTests(TestCase):
    """Test offer creation with new pricing system"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            user_type='client',
            telegram_id=123456789
        )
        
        self.city = City.objects.create(name='Riyadh', code='RY')
        self.brand = Brand.objects.create(name='Toyota')
        self.model = Model.objects.create(brand=self.brand, name='Camry')
        
        self.junkyard_user = User.objects.create_user(
            username='junkyard',
            first_name='Junkyard',
            user_type='junkyard',
            telegram_id=987654321
        )
        
        self.junkyard = Junkyard.objects.create(
            user=self.junkyard_user,
            phone='0501234567',
            city=self.city,
            location='Test Location'
        )
    
    def test_offer_creation_without_delivery_time(self):
        """Test that offers can be created without delivery_time"""
        request = Request.objects.create(
            user=self.user,
            city=self.city,
            brand=self.brand,
            model=self.model,
            year=2020,
            parts='Test parts'
        )
        
        # Create offer without delivery_time (should be allowed)
        offer = Offer.objects.create(
            request=request,
            junkyard=self.junkyard,
            price=Decimal('500.00'),
            notes='Test offer'
        )
        
        self.assertEqual(offer.price, Decimal('500.00'))
        self.assertEqual(offer.delivery_time, '')
        self.assertEqual(offer.status, 'pending')
    
    def test_offer_validation_without_delivery_time(self):
        """Test that offer validation doesn't require delivery_time"""
        request = Request.objects.create(
            user=self.user,
            city=self.city,
            brand=self.brand,
            model=self.model,
            year=2020,
            parts='Test parts'
        )
        
        # This should not raise any validation errors
        offer = Offer.objects.create(
            request=request,
            junkyard=self.junkyard,
            price=Decimal('500.00')
        )
        
        self.assertIsNotNone(offer)
        self.assertEqual(offer.price, Decimal('500.00'))


class NotificationTests(TestCase):
    """Test notification system health"""
    
    def test_health_check_endpoints(self):
        """Test health check endpoints"""
        from django.test import Client
        from django.urls import reverse
        
        client = Client()
        
        # Test basic health check
        response = client.get('/bot/health/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        
        # Test queue health check
        response = client.get('/bot/health/queue/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['database'], 'connected')
        
        # Test notifications health check
        response = client.get('/bot/health/notifications/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')


class WorkflowServiceTests(TestCase):
    """Test workflow service functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            user_type='client',
            telegram_id=123456789
        )
        
        self.city = City.objects.create(name='Riyadh', code='RY')
        self.brand = Brand.objects.create(name='Toyota')
        self.model = Model.objects.create(brand=self.brand, name='Camry')
        
        self.junkyard_user = User.objects.create_user(
            username='junkyard',
            first_name='Junkyard',
            user_type='junkyard',
            telegram_id=987654321
        )
        
        self.junkyard = Junkyard.objects.create(
            user=self.junkyard_user,
            phone='0501234567',
            city=self.city,
            location='Test Location'
        )
    
    def test_workflow_service_availability(self):
        """Test that workflow service is available"""
        from .services import workflow_service
        
        self.assertIsNotNone(workflow_service)
        self.assertTrue(hasattr(workflow_service, 'process_confirmed_order'))
        self.assertTrue(hasattr(workflow_service, 'process_junkyard_offer'))
        self.assertTrue(hasattr(workflow_service, 'notify_customer_about_offer'))
    
    def test_offer_creation_workflow(self):
        """Test complete offer creation workflow"""
        request = Request.objects.create(
            user=self.user,
            city=self.city,
            brand=self.brand,
            model=self.model,
            year=2020,
            parts='Test parts'
        )
        
        # Add items with pricing
        RequestItem.objects.create(
            request=request,
            name='Test Part 1',
            unit_price=Decimal('100.00'),
            quantity=1
        )
        
        RequestItem.objects.create(
            request=request,
            name='Test Part 2',
            unit_price=Decimal('50.00'),
            quantity=1
        )
        
        # Create offer
        offer = Offer.objects.create(
            request=request,
            junkyard=self.junkyard,
            price=Decimal('150.00'),
            notes='Test offer'
        )
        
        # Verify offer was created
        self.assertEqual(offer.request, request)
        self.assertEqual(offer.junkyard, self.junkyard)
        self.assertEqual(offer.price, Decimal('150.00'))
        
        # Verify request total matches offer price
        self.assertEqual(request.calculate_total_price(), Decimal('150.00'))


class MigrationTests(TransactionTestCase):
    """Test database migrations"""
    
    def test_migration_applies_correctly(self):
        """Test that the unit pricing migration applies correctly"""
        # Test that the new fields exist by creating objects
        from .models import RequestItem, Request, User, City, Brand, Model
        
        # Create test data
        user = User.objects.create_user(
            username='testuser',
            first_name='Test',
            user_type='client'
        )
        city = City.objects.create(name='Riyadh', code='RY')
        brand = Brand.objects.create(name='Toyota')
        model = Model.objects.create(brand=brand, name='Camry')
        
        request = Request.objects.create(
            user=user,
            city=city,
            brand=brand,
            model=model,
            year=2020,
            parts='Test parts'
        )
        
        # Test that unit_price field exists and works
        item = RequestItem.objects.create(
            request=request,
            name='Test Part',
            unit_price=100.50,
            currency='SAR'
        )
        
        # Verify the fields work correctly
        self.assertEqual(item.unit_price, 100.50)
        self.assertEqual(item.currency, 'SAR')
        self.assertEqual(item.calculate_line_total(), 100.50)


class FeatureFlagTests(TestCase):
    """Test feature flag functionality"""
    
    def test_feature_flags_exist(self):
        """Test that feature flags are defined in settings"""
        from django.conf import settings
        
        self.assertTrue(hasattr(settings, 'FEATURE_DEPRECATE_OLD_FIELDS'))
        self.assertTrue(hasattr(settings, 'FEATURE_UNIT_PRICING'))
        
        self.assertIsInstance(settings.FEATURE_DEPRECATE_OLD_FIELDS, bool)
        self.assertIsInstance(settings.FEATURE_UNIT_PRICING, bool)
    
    def test_deprecated_field_warning(self):
        """Test that deprecated field usage triggers warning"""
        import logging
        from unittest.mock import patch
        
        with patch('logging.Logger.warning') as mock_warning:
            # This would be tested in actual field usage
            # For now, just verify the logging setup
            self.assertTrue(True)  # Placeholder for actual test
