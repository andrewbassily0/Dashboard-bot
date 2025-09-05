import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from bot.models import City, Brand, Model, SystemSetting

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with initial data'

    def handle(self, *args, **options):
        self.stdout.write('Populating database with initial data...')
        
        # Create superuser if not exists
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                first_name='مدير النظام'
            )
            self.stdout.write(self.style.SUCCESS('Created superuser: admin/admin123'))
        
        # Cities
        cities_data = [
            {'name': 'الرياض', 'code': 'RYD'},
            {'name': 'جدة', 'code': 'JED'},
            {'name': 'الدمام', 'code': 'DMM'},
            {'name': 'مكة المكرمة', 'code': 'MKK'},
            {'name': 'المدينة المنورة', 'code': 'MED'},
            {'name': 'الطائف', 'code': 'TAF'},
            {'name': 'تبوك', 'code': 'TBK'},
            {'name': 'بريدة', 'code': 'BRD'},
            {'name': 'خميس مشيط', 'code': 'KMS'},
            {'name': 'حائل', 'code': 'HAL'},
        ]
        
        for city_data in cities_data:
            city, created = City.objects.get_or_create(
                code=city_data['code'],
                defaults={'name': city_data['name']}
            )
            if created:
                self.stdout.write(f'Created city: {city.name}')
        
        # Brands
        brands_data = [
            'تويوتا', 'هوندا', 'نيسان', 'هيونداي', 'كيا', 'مازدا', 'ميتسوبيشي',
            'سوزوكي', 'فورد', 'شيفروليه', 'جي إم سي', 'دودج', 'كرايسلر',
            'مرسيدس بنز', 'بي إم دبليو', 'أودي', 'فولكس واجن', 'لكزس',
            'إنفينيتي', 'أكورا', 'جينيسيس', 'فولفو', 'لاند روفر', 'جاكوار'
        ]
        
        for brand_name in brands_data:
            brand, created = Brand.objects.get_or_create(name=brand_name)
            if created:
                self.stdout.write(f'Created brand: {brand.name}')
        
        # Models for Toyota (example)
        toyota = Brand.objects.get(name='تويوتا')
        toyota_models = [
            'كامري', 'كورولا', 'يارس', 'أفالون', 'راف 4', 'هايلاندر',
            'برادو', 'لاند كروزر', 'سيكويا', 'تاكوما', 'تندرا'
        ]
        
        for model_name in toyota_models:
            model, created = Model.objects.get_or_create(
                brand=toyota,
                name=model_name
            )
            if created:
                self.stdout.write(f'Created model: {toyota.name} {model.name}')
        
        # Models for Honda (example)
        honda = Brand.objects.get(name='هوندا')
        honda_models = [
            'سيفيك', 'أكورد', 'سي آر في', 'بايلوت', 'أوديسي', 'فيت', 'إنسايت'
        ]
        
        for model_name in honda_models:
            model, created = Model.objects.get_or_create(
                brand=honda,
                name=model_name
            )
            if created:
                self.stdout.write(f'Created model: {honda.name} {model.name}')
        
        # System Settings
        default_settings = {
            'commission_percentage': 2.0,
            'payment_url': 'https://your-payment-gateway.com',
            'request_expiry_hours': 6,
            'welcome_message': 'مرحباً بك في بوت قطع غيار السيارات! 🔧\n\nهذا البوت يساعدك في العثور على قطع الغيار التي تحتاجها من خلال ربطك بأفضل المخازن في منطقتك.',
            'support_contact': '@support_username',
            'max_offers_per_request': 10,
            'auto_verify_rating_threshold': 4.5,
            'auto_verify_min_ratings': 10,
        }
        
        for key, value in default_settings.items():
            setting, created = SystemSetting.objects.get_or_create(
                key=key,
                defaults={
                    'value': value,
                    'description': f'Default setting for {key}'
                }
            )
            if created:
                self.stdout.write(f'Created setting: {key} = {value}')
        
        self.stdout.write(self.style.SUCCESS('Database populated successfully!'))

