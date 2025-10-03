#!/usr/bin/env python
"""
Script to populate the database with essential data for the bot to work
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auto_parts_bot.settings')
django.setup()

from bot.models import City, Brand, Model, User, Junkyard

def populate_cities():
    """Add essential cities"""
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
    
    created_count = 0
    for city_data in cities_data:
        city, created = City.objects.get_or_create(
            code=city_data['code'],
            defaults={'name': city_data['name'], 'is_active': True}
        )
        if created:
            created_count += 1
            print(f"✅ Created city: {city.name}")
    
    print(f"Cities: {created_count} created, {City.objects.count()} total")

def populate_brands_and_models():
    """Add car brands and their models"""
    brands_data = {
        'تويوتا': ['كامري', 'كورولا', 'لاندكروزر', 'برادو', 'هايلكس', 'يارس', 'أفالون', 'راف فور'],
        'هوندا': ['أكورد', 'سيفيك', 'سي آر في', 'بايلوت', 'أوديسي', 'ريدج لاين'],
        'نيسان': ['التيما', 'سنترا', 'باترول', 'اكس تريل', 'مورانو', 'تيتان', 'ماكسيما'],
        'هيونداي': ['النترا', 'سوناتا', 'توسان', 'سانتا في', 'أكسنت', 'جينيسيس'],
        'كيا': ['أوبتيما', 'سيراتو', 'سورينتو', 'سبورتاج', 'ريو', 'كادينزا'],
        'شيفروليه': ['كابتيفا', 'تاهو', 'سيلفرادو', 'كروز', 'ماليبو', 'تريل بليزر'],
        'فورد': ['اكسبلورر', 'ايدج', 'اف 150', 'فيوجن', 'اسكيب', 'موستانج'],
        'جي ام سي': ['يوكون', 'سييرا', 'أكاديا', 'تيرين', 'سافانا'],
        'مرسيدس': ['الفئة سي', 'الفئة إي', 'الفئة إس', 'جي إل إس', 'جي إل سي', 'الفئة أي'],
        'بي ام دبليو': ['الفئة الثالثة', 'الفئة الخامسة', 'الفئة السابعة', 'اكس 3', 'اكس 5', 'اكس 6'],
        'أودي': ['أي 4', 'أي 6', 'أي 8', 'كيو 5', 'كيو 7', 'كيو 8'],
        'لكزس': ['إي إس', 'آي إس', 'إل إس', 'جي إكس', 'إل إكس', 'آر إكس'],
        'انفينيتي': ['كيو 50', 'كيو 60', 'كيو اكس 50', 'كيو اكس 60', 'كيو اكس 80'],
        'أكورا': ['تي إل إكس', 'آر دي إكس', 'إم دي إكس', 'آي إل إكس'],
        'جاكوار': ['إكس إي', 'إكس إف', 'إكس جي', 'إف بيس', 'إي بيس'],
        'لاند روفر': ['رينج روفر', 'ديسكفري', 'إيفوك', 'فيلار', 'ديفندر'],
        'بورش': ['كايين', 'ماكان', '911', 'بانامرا', 'تايكان'],
        'فولكس واجن': ['جيتا', 'باسات', 'تيجوان', 'توارق', 'جولف'],
        'مازدا': ['مازدا 3', 'مازدا 6', 'سي اكس 5', 'سي اكس 9', 'ام اكس 5'],
        'سوبارو': ['امبريزا', 'ليجاسي', 'اوت باك', 'فورستر', 'اسنت'],
    }
    
    created_brands = 0
    created_models = 0
    
    for brand_name, models_list in brands_data.items():
        # Create or get brand
        brand, brand_created = Brand.objects.get_or_create(
            name=brand_name,
            defaults={'is_active': True}
        )
        if brand_created:
            created_brands += 1
            print(f"✅ Created brand: {brand.name}")
        
        # Create models for this brand
        for model_name in models_list:
            model, model_created = Model.objects.get_or_create(
                brand=brand,
                name=model_name,
                defaults={'is_active': True}
            )
            if model_created:
                created_models += 1
    
    print(f"Brands: {created_brands} created, {Brand.objects.count()} total")
    print(f"Models: {created_models} created, {Model.objects.count()} total")

def create_sample_junkyard():
    """Create a sample junkyard for testing"""
    try:
        # Create a sample junkyard user
        junkyard_user, created = User.objects.get_or_create(
            username='sample_junkyard',
            defaults={
                'first_name': 'تشليح النموذجي',
                'user_type': 'junkyard',
                'telegram_id': 123456789,  # Sample telegram ID
                'is_active': True
            }
        )
        
        if created:
            print(f"✅ Created sample junkyard user: {junkyard_user.first_name}")
        
        # Create junkyard profile
        junkyard, junkyard_created = Junkyard.objects.get_or_create(
            user=junkyard_user,
            defaults={
                'city': City.objects.first(),
                'phone': '0501234567',
                'location': 'الرياض - حي الصناعية',
                'is_active': True
            }
        )
        
        if junkyard_created:
            print(f"✅ Created sample junkyard: {junkyard.user.first_name}")
        
    except Exception as e:
        print(f"⚠️ Could not create sample junkyard: {e}")

def main():
    """Main function to populate all data"""
    print("🔄 Populating database with essential data...")
    print("=" * 50)
    
    try:
        populate_cities()
        print()
        
        populate_brands_and_models()
        print()
        
        create_sample_junkyard()
        print()
        
        print("✅ Database population completed successfully!")
        print("\n📊 Final Statistics:")
        print(f"Cities: {City.objects.count()}")
        print(f"Brands: {Brand.objects.count()}")
        print(f"Models: {Model.objects.count()}")
        print(f"Users: {User.objects.count()}")
        print(f"Junkyards: {Junkyard.objects.count()}")
        
    except Exception as e:
        print(f"❌ Error during database population: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
