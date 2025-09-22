from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from bot.models import User, Request, Offer, Junkyard, City, Brand, Model, JunkyardRating, SystemSetting, JunkyardStaff
from .telegram_service import telegram_service
import logging

logger = logging.getLogger(__name__)

def is_admin(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_admin)
def dashboard_home(request):
    """Admin dashboard view with comprehensive statistics"""
    # Get statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Basic stats
    total_users = User.objects.count()
    total_clients = User.objects.filter(user_type='client').count()
    total_junkyards = User.objects.filter(user_type='junkyard').count()
    total_requests = Request.objects.count()
    total_offers = Offer.objects.count()
    
    # Advanced admin stats
    stats = {
        'total_users': total_users,
        'total_clients': total_clients,
        'total_junkyards': total_junkyards,
        'total_requests': total_requests,
        'active_requests': Request.objects.filter(status='new').count(),
        'total_offers': total_offers,
        'requests_today': Request.objects.filter(created_at__date=today).count(),
        'requests_this_week': Request.objects.filter(created_at__date__gte=week_ago).count(),
        'requests_this_month': Request.objects.filter(created_at__date__gte=month_ago).count(),
        
        # New admin-specific stats
        'new_users_today': User.objects.filter(date_joined__date=today).count(),
        'new_users_week': User.objects.filter(date_joined__date__gte=week_ago).count(),
        'new_requests_today': Request.objects.filter(created_at__date=today).count(),
        'new_offers_today': Offer.objects.filter(created_at__date=today).count(),
        'active_clients': User.objects.filter(user_type='client', is_active=True).count(),
        'verified_junkyards': Junkyard.objects.filter(is_verified=True).count(),
        'new_requests': Request.objects.filter(status='new').count(),
        'completed_requests': Request.objects.filter(status='completed').count(),
    }
    
    # Recent requests
    recent_requests = Request.objects.select_related('user', 'city', 'brand', 'model').order_by('-created_at')[:10]
    
    # Top cities
    top_cities = Request.objects.values('city__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Top brands
    top_brands = Request.objects.values('brand__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'stats': stats,
        'recent_requests': recent_requests,
        'top_cities': top_cities,
        'top_brands': top_brands,
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)

def public_dashboard(request):
    """Public dashboard view for general users"""
    # Get basic statistics for public view
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    stats = {
        'total_users': User.objects.count(),
        'total_clients': User.objects.filter(user_type='client').count(),
        'total_junkyards': User.objects.filter(user_type='junkyard').count(),
        'total_requests': Request.objects.count(),
        'active_requests': Request.objects.filter(status='new').count(),
        'total_offers': Offer.objects.count(),
        'requests_this_week': Request.objects.filter(created_at__date__gte=week_ago).count(),
    }
    
    # Recent requests (limited for public view)
    recent_requests = Request.objects.select_related('user', 'city', 'brand', 'model').order_by('-created_at')[:5]
    
    # Top cities
    top_cities = Request.objects.values('city__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Top brands
    top_brands = Request.objects.values('brand__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'stats': stats,
        'recent_requests': recent_requests,
        'top_cities': top_cities,
        'top_brands': top_brands,
    }
    
    return render(request, 'dashboard/home.html', context)

@staff_member_required
def requests_list(request):
    """List all requests with filtering"""
    requests = Request.objects.select_related('user', 'city', 'brand', 'model').prefetch_related('items').order_by('-created_at')
    
    # Filtering
    status_filter = request.GET.get('status')
    city_filter = request.GET.get('city')
    brand_filter = request.GET.get('brand')
    expired_filter = request.GET.get('expired')
    
    if status_filter:
        requests = requests.filter(status=status_filter)
    if city_filter:
        requests = requests.filter(city_id=city_filter)
    if brand_filter:
        requests = requests.filter(brand_id=brand_filter)
    if expired_filter == 'true':
        requests = requests.filter(expires_at__lt=timezone.now())
    elif expired_filter == 'false':
        requests = requests.filter(expires_at__gte=timezone.now())
    
    # Get filter options
    cities = City.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    
    # Calculate statistics
    all_requests = Request.objects.all()
    stats = {
        'total_requests': all_requests.count(),
        'active_requests': all_requests.filter(status='new').count(),
        'completed_requests': all_requests.filter(status='completed').count(),
        'expired_requests': all_requests.filter(expires_at__lt=timezone.now()).count(),
    }
    
    context = {
        'requests': requests,
        'cities': cities,
        'brands': brands,
        'stats': stats,
        'current_status': status_filter,
        'current_city': city_filter,
        'current_brand': brand_filter,
        'current_expired': expired_filter,
    }
    
    return render(request, 'dashboard/requests_list.html', context)

@staff_member_required
def request_detail(request, request_id):
    """Request detail view"""
    req = get_object_or_404(Request.objects.prefetch_related('items'), id=request_id)
    offers = req.offers.select_related('junkyard__user').order_by('-created_at')
    
    context = {
        'request': req,
        'offers': offers,
    }
    
    return render(request, 'dashboard/request_detail.html', context)

@staff_member_required
def junkyards_list(request):
    """List all junkyards"""
    junkyards = Junkyard.objects.select_related('user', 'city').order_by('-created_at')
    
    # Filtering
    city_filter = request.GET.get('city')
    verified_filter = request.GET.get('verified')
    active_filter = request.GET.get('active')
    
    if city_filter:
        junkyards = junkyards.filter(city_id=city_filter)
    if verified_filter == 'true':
        junkyards = junkyards.filter(is_verified=True)
    elif verified_filter == 'false':
        junkyards = junkyards.filter(is_verified=False)
    if active_filter == 'true':
        junkyards = junkyards.filter(is_active=True)
    elif active_filter == 'false':
        junkyards = junkyards.filter(is_active=False)
    
    cities = City.objects.filter(is_active=True)
    
    # Calculate statistics
    all_junkyards = Junkyard.objects.all()
    stats = {
        'total_junkyards': all_junkyards.count(),
        'verified_junkyards': all_junkyards.filter(is_verified=True).count(),
        'active_junkyards': all_junkyards.filter(is_active=True).count(),
        'avg_rating': all_junkyards.aggregate(avg=Avg('average_rating'))['avg'] or 0,
    }
    
    context = {
        'junkyards': junkyards,
        'cities': cities,
        'stats': stats,
        'current_city': city_filter,
        'current_verified': verified_filter,
        'current_active': active_filter,
    }
    
    return render(request, 'dashboard/junkyards_list.html', context)

@staff_member_required
def junkyard_detail(request, junkyard_id):
    """Junkyard detail view"""
    junkyard = get_object_or_404(Junkyard, id=junkyard_id)
    offers = junkyard.offers.select_related('request').order_by('-created_at')[:20]
    ratings = junkyard.ratings.select_related('client', 'request').order_by('-created_at')[:20]
    
    context = {
        'junkyard': junkyard,
        'offers': offers,
        'ratings': ratings,
    }
    
    return render(request, 'dashboard/junkyard_detail.html', context)

@staff_member_required
def test_junkyard_notification(request, junkyard_id):
    """Send test notification to junkyard"""
    junkyard = get_object_or_404(Junkyard, id=junkyard_id)
    
    if request.method == 'POST':
        try:
            from bot.telegram_bot import TelegramBot
            import asyncio
            from django.utils import timezone
            
            # Check if junkyard has telegram_id
            if not junkyard.user.telegram_id:
                messages.error(request, 'التشليح ليس لديه معرف تليجرام')
                return redirect('dashboard:junkyard_detail', junkyard_id=junkyard_id)
            
            # Setup bot
            bot = TelegramBot()
            app = bot.setup_bot()
            
            if not app:
                messages.error(request, 'فشل في إعداد البوت')
                return redirect('dashboard:junkyard_detail', junkyard_id=junkyard_id)
            
            # Test message
            test_message = f"""
🧪 رسالة اختبار من لوحة التحكم

مرحباً {junkyard.user.first_name}!

هذه رسالة اختبار للتأكد من وصول الإشعارات لحسابك.

✅ إذا وصلتك هذه الرسالة، فإن نظام الإشعارات يعمل بشكل صحيح!

تم الإرسال في: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

🔔 ستبدأ في استقبال إشعارات الطلبات الجديدة من الآن.
            """
            
            # Send test message
            async def send_test():
                await app.bot.send_message(
                    chat_id=junkyard.user.telegram_id,
                    text=test_message.strip()
                )
            
            asyncio.run(send_test())
            
            messages.success(request, f'تم إرسال رسالة اختبار بنجاح للتشليح {junkyard.user.first_name}')
            
        except Exception as e:
            error_msg = str(e)
            
            if "Forbidden" in error_msg:
                messages.error(request, f'لا يمكن إرسال الرسالة للتشليح. السبب: التشليح لم يبدأ محادثة مع البوت. يجب على {junkyard.user.first_name} إرسال /start للبوت أولاً.')
            elif "chat not found" in error_msg.lower():
                messages.error(request, 'معرف التليجرام غير صحيح')
            else:
                messages.error(request, f'فشل في إرسال الرسالة: {error_msg}')
    
    return redirect('dashboard:junkyard_detail', junkyard_id=junkyard_id)

@staff_member_required
def diagnose_junkyard_issues(request, junkyard_id):
    """Diagnose common junkyard issues"""
    junkyard = get_object_or_404(Junkyard, id=junkyard_id)
    
    issues = []
    warnings = []
    success_items = []
    
    # Check basic junkyard setup
    if not junkyard.user.telegram_id:
        issues.append("❌ لا يوجد معرف تليجرام للتشليح")
    else:
        success_items.append(f"✅ معرف التليجرام: {junkyard.user.telegram_id}")
    
    if not junkyard.is_active:
        issues.append("❌ التشليح غير مُفعل في النظام")
    else:
        success_items.append("✅ التشليح مُفعل")
        
    if junkyard.user.user_type != 'junkyard':
        issues.append(f"❌ نوع المستخدم خاطئ: {junkyard.user.user_type}")
    else:
        success_items.append("✅ نوع المستخدم صحيح (junkyard)")
    
    # Check city setup
    if not junkyard.city or not junkyard.city.is_active:
        issues.append("❌ المدينة غير مُفعلة أو غير موجودة")
    else:
        success_items.append(f"✅ المدينة: {junkyard.city.name}")
    
    # Check offers history
    offers_count = junkyard.offers.count()
    if offers_count == 0:
        warnings.append(f"⚠️ لم يُقدم أي عروض بعد")
    else:
        success_items.append(f"✅ قدم {offers_count} عرض سابق")
    
    # Check recent activity
    from django.utils import timezone
    from datetime import timedelta
    last_week = timezone.now() - timedelta(days=7)
    recent_offers = junkyard.offers.filter(created_at__gte=last_week).count()
    
    if recent_offers == 0:
        warnings.append("⚠️ لا توجد عروض في الأسبوع الماضي")
    else:
        success_items.append(f"✅ {recent_offers} عرض في الأسبوع الماضي")
    
    # Check if junkyard is in same city as recent requests
    if junkyard.city:
        recent_requests = Request.objects.filter(
            city=junkyard.city,
            created_at__gte=last_week,
            status__in=['new', 'active']
        ).count()
        
        if recent_requests == 0:
            warnings.append(f"⚠️ لا توجد طلبات حديثة في مدينة {junkyard.city.name}")
        else:
            success_items.append(f"✅ {recent_requests} طلب حديث في مدينة {junkyard.city.name}")
    
    # Determine overall status
    if issues:
        overall_status = "critical"
        status_message = "❌ يوجد مشاكل تحتاج إصلاح"
        status_class = "bg-red-100 text-red-800 border-red-200"
    elif warnings:
        overall_status = "warning"
        status_message = "⚠️ تحتاج متابعة"
        status_class = "bg-yellow-100 text-yellow-800 border-yellow-200"
    else:
        overall_status = "good"
        status_message = "✅ كل شيء يعمل بشكل جيد"
        status_class = "bg-green-100 text-green-800 border-green-200"
    
    context = {
        'junkyard': junkyard,
        'issues': issues,
        'warnings': warnings,
        'success_items': success_items,
        'overall_status': overall_status,
        'status_message': status_message,
        'status_class': status_class,
    }
    
    return render(request, 'dashboard/diagnose_junkyard.html', context)

@staff_member_required
def test_order_workflow(request):
    """Test the complete order workflow"""
    from bot.models import Request, City, Brand, Model, User
    from bot.services import workflow_service
    from bot.telegram_bot import TelegramBot
    import asyncio
    from django.utils import timezone
    from datetime import timedelta
    
    if request.method == 'POST':
        try:
            # Get test parameters
            city_id = request.POST.get('city_id')
            
            if not city_id:
                messages.error(request, 'يرجى اختيار مدينة للاختبار')
                return redirect('dashboard:test_order_workflow')
            
            city = get_object_or_404(City, id=city_id)
            
            # Check if there are active junkyards in this city
            from bot.models import Junkyard
            active_junkyards = Junkyard.objects.filter(city=city, is_active=True).count()
            
            if active_junkyards == 0:
                messages.warning(request, f'لا توجد تشاليح نشطة في مدينة {city.name}')
            
            # Get first brand and model for testing
            first_brand = Brand.objects.filter(is_active=True).first()
            first_model = Model.objects.filter(brand=first_brand, is_active=True).first() if first_brand else None
            
            if not first_brand or not first_model:
                messages.error(request, 'لا توجد وكالات أو أسماء سيارات نشطة للاختبار')
                return redirect('dashboard:test_order_workflow')
            
            # Create a test user if doesn't exist
            test_user, created = User.objects.get_or_create(
                username='test_customer',
                defaults={
                    'first_name': 'عميل تجريبي',
                    'user_type': 'client',
                    'telegram_id': 123456789,  # Fake telegram ID for testing
                    'is_active': True
                }
            )
            
            # Create a test request
            test_request = Request.objects.create(
                user=test_user,
                city=city,
                brand=first_brand,
                model=first_model,
                year=2020,
                parts="قطع اختبار - مصد أمامي، فانوس",
                status='new'
            )
            
            # Create RequestItems
            from bot.models import RequestItem
            RequestItem.objects.create(
                request=test_request,
                name="مصد أمامي",
                description="مصد أمامي أصلي",
                quantity=1
            )
            RequestItem.objects.create(
                request=test_request,
                name="فانوس يمين",
                description="فانوس أمامي يمين",
                quantity=1
            )
            
            # Test the workflow
            try:
                # Setup bot and workflow service
                bot = TelegramBot()
                workflow_service.set_telegram_bot(bot)
                
                # Process the order
                async def test_workflow():
                    await workflow_service.process_confirmed_order(test_request)
                
                # Run the async function
                asyncio.run(test_workflow())
                
                messages.success(request, f'تم إنشاء طلب اختبار بنجاح! رقم الطلب: {test_request.order_id} في مدينة {city.name}. تم إرسال الإشعارات للتشاليح ({active_junkyards} تشليح).')
                
            except Exception as workflow_error:
                messages.warning(request, f'تم إنشاء الطلب لكن فشل في إرسال الإشعارات: {str(workflow_error)}')
            
            # Redirect to request detail
            return redirect('dashboard:request_detail', request_id=test_request.id)
            
        except Exception as e:
            messages.error(request, f'فشل في إنشاء طلب الاختبار: {str(e)}')
    
    # GET request - show form
    cities = City.objects.filter(is_active=True).order_by('name')
    
    # Get junkyard counts per city
    from bot.models import Junkyard
    for city in cities:
        city.junkyard_count = Junkyard.objects.filter(city=city, is_active=True).count()
    
    context = {
        'cities': cities,
    }
    
    return render(request, 'dashboard/test_order_workflow.html', context)

@staff_member_required
def quick_fix_junkyard(request, junkyard_id):
    """Quick fix for junkyard offer submission issues"""
    junkyard = get_object_or_404(Junkyard, id=junkyard_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'activate_junkyard':
            junkyard.is_active = True
            junkyard.save()
            messages.success(request, f'تم تفعيل التشليح {junkyard.user.first_name}')
        
        elif action == 'fix_user_type':
            junkyard.user.user_type = 'junkyard'
            junkyard.user.save()
            messages.success(request, f'تم تصحيح نوع المستخدم لـ {junkyard.user.first_name}')
        
        elif action == 'activate_city':
            junkyard.city.is_active = True
            junkyard.city.save()
            messages.success(request, f'تم تفعيل المدينة {junkyard.city.name}')
            
        elif action == 'test_telegram':
            # Test sending a message
            try:
                from bot.telegram_bot import TelegramBot
                import asyncio
                from django.utils import timezone
                
                if not junkyard.user.telegram_id:
                    messages.error(request, 'التشليح ليس لديه معرف تليجرام')
                    return redirect('dashboard:quick_fix_junkyard', junkyard_id=junkyard_id)
                
                bot = TelegramBot()
                app = bot.setup_bot()
                
                if not app:
                    messages.error(request, 'فشل في إعداد البوت')
                    return redirect('dashboard:quick_fix_junkyard', junkyard_id=junkyard_id)
                
                test_message = f"""
🔧 اختبار سريع للنظام

مرحباً {junkyard.user.first_name}!

هذه رسالة اختبار سريع للتأكد من أن النظام يعمل بشكل صحيح.

✅ إذا وصلتك هذه الرسالة، فالنظام يعمل بشكل طبيعي.

🔄 جرب الآن الضغط على "إضافة عرض" في أي طلب جديد.

الوقت: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
                """
                
                async def send_test():
                    await app.bot.send_message(
                        chat_id=junkyard.user.telegram_id,
                        text=test_message.strip()
                    )
                
                asyncio.run(send_test())
                messages.success(request, f'تم إرسال رسالة اختبار بنجاح للتشليح {junkyard.user.first_name}')
                
            except Exception as e:
                error_msg = str(e)
                if "Forbidden" in error_msg:
                    messages.error(request, f'لا يمكن إرسال الرسالة. السبب: التشليح لم يبدأ محادثة مع البوت. يجب على {junkyard.user.first_name} إرسال /start للبوت أولاً.')
                else:
                    messages.error(request, f'فشل في إرسال الرسالة: {error_msg}')
        
        return redirect('dashboard:quick_fix_junkyard', junkyard_id=junkyard_id)
    
    # GET request - analyze issues
    issues = []
    fixes = []
    warnings = []
    
    # Check common issues
    if not junkyard.user.telegram_id:
        issues.append({
            'type': 'critical',
            'message': '❌ لا يوجد معرف تليجرام',
            'fix': 'يجب إضافة telegram_id للمستخدم'
        })
    
    if junkyard.user.user_type != 'junkyard':
        issues.append({
            'type': 'critical', 
            'message': f'❌ نوع المستخدم خاطئ: {junkyard.user.user_type}',
            'fix': 'fix_user_type',
            'fix_label': 'تصحيح نوع المستخدم'
        })
    
    if not junkyard.is_active:
        issues.append({
            'type': 'critical',
            'message': '❌ التشليح غير مُفعل',
            'fix': 'activate_junkyard',
            'fix_label': 'تفعيل التشليح'
        })
    
    if not junkyard.city.is_active:
        issues.append({
            'type': 'warning',
            'message': f'⚠️ المدينة {junkyard.city.name} غير مُفعلة',
            'fix': 'activate_city',
            'fix_label': 'تفعيل المدينة'
        })
    
    # Check recent activity
    from django.utils import timezone
    from datetime import timedelta
    
    last_week = timezone.now() - timedelta(days=7)
    recent_offers = junkyard.offers.filter(created_at__gte=last_week).count()
    total_offers = junkyard.offers.count()
    
    if total_offers == 0:
        warnings.append('⚠️ لم يقدم أي عروض بعد')
    
    # Check if bot can send messages
    can_test_telegram = junkyard.user.telegram_id is not None
    
    context = {
        'junkyard': junkyard,
        'issues': issues,
        'fixes': fixes,
        'warnings': warnings,
        'can_test_telegram': can_test_telegram,
        'recent_offers': recent_offers,
        'total_offers': total_offers,
    }
    
    return render(request, 'dashboard/quick_fix_junkyard.html', context)

@staff_member_required
def edit_junkyard(request, junkyard_id):
    """Edit existing junkyard"""
    try:
        junkyard = get_object_or_404(Junkyard, id=junkyard_id)
        print(f"🔍 EDIT DEBUG: Starting edit for junkyard {junkyard_id} - {junkyard.user.first_name}")
    except Junkyard.DoesNotExist:
        messages.error(request, f'التشليح رقم {junkyard_id} غير موجود')
        return redirect('dashboard:junkyards_list')
    
    if request.method == 'POST':
        # Debug: Print all POST data
        print(f"🔍 EDIT DEBUG: POST data for junkyard {junkyard_id}: {request.POST}")
        
        # Store original values for comparison
        original_junkyard_id = junkyard.id
        original_user_id = junkyard.user.id
        original_telegram_id = junkyard.user.telegram_id
        print(f"🔍 EDIT DEBUG: Original IDs - Junkyard: {original_junkyard_id}, User: {original_user_id}, Telegram: {original_telegram_id}")
        
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        phone = request.POST.get('phone', '').strip()
        city_id = request.POST.get('city')
        location = request.POST.get('location', '').strip()
        telegram_id = request.POST.get('telegram_id', '').strip()
        is_active = request.POST.get('is_active') == 'on'
        is_verified = request.POST.get('is_verified') == 'on'
        
        # Debug: Print extracted values
        print(f"🔍 EDIT DEBUG: Form data - first_name={first_name}, username={username}, phone={phone}, city_id={city_id}, telegram_id={telegram_id}")
        
        # Validate required fields
        if not all([first_name, username, phone, city_id, location]):
            print(f"DEBUG: Validation failed - missing required fields")
            messages.error(request, 'جميع الحقول مطلوبة عدا telegram_id')
            return redirect('dashboard:edit_junkyard', junkyard_id=junkyard_id)
        
        # Validate telegram_id if provided
        telegram_id_int = None
        if telegram_id:
            try:
                telegram_id_int = int(telegram_id)
                if telegram_id_int <= 0 or len(telegram_id) < 8:
                    print(f"🔍 EDIT DEBUG: Invalid telegram_id format: {telegram_id}")
                    messages.error(request, 'معرف التليجرام يجب أن يكون رقماً صحيحاً مكوناً من 8 أرقام على الأقل')
                    return redirect('dashboard:edit_junkyard', junkyard_id=original_junkyard_id)
            except (ValueError, TypeError):
                print(f"🔍 EDIT DEBUG: telegram_id is not a valid number: {telegram_id}")
                messages.error(request, 'معرف التليجرام يجب أن يكون رقماً صحيحاً')
                return redirect('dashboard:edit_junkyard', junkyard_id=original_junkyard_id)
        
        print(f"🔍 EDIT DEBUG: Validated telegram_id: {telegram_id_int} (original: {original_telegram_id})")
        
        try:
            # Refresh junkyard from database to ensure we have the latest data
            junkyard.refresh_from_db()
            print(f"🔍 EDIT DEBUG: After refresh - Junkyard ID: {junkyard.id}, User ID: {junkyard.user.id}")
            
            # Check if username already exists (excluding current user)
            existing_username = User.objects.filter(username=username).exclude(id=junkyard.user.id).first()
            if existing_username:
                print(f"🔍 EDIT DEBUG: Username '{username}' already exists for user ID {existing_username.id}")
                messages.error(request, f'اسم المستخدم "{username}" مستخدم بالفعل من قبل مستخدم آخر')
                return redirect('dashboard:edit_junkyard', junkyard_id=original_junkyard_id)
            
            # Check if telegram_id already exists (excluding current user)
            if telegram_id_int:
                existing_telegram = User.objects.filter(telegram_id=telegram_id_int).exclude(id=junkyard.user.id).first()
                if existing_telegram:
                    print(f"🔍 EDIT DEBUG: Telegram ID {telegram_id_int} already exists for user ID {existing_telegram.id} ({existing_telegram.first_name})")
                    messages.error(request, f'معرف التليجرام {telegram_id_int} مستخدم بالفعل من قبل "{existing_telegram.first_name}"')
                    return redirect('dashboard:edit_junkyard', junkyard_id=original_junkyard_id)
            
            # Get city
            print(f"DEBUG: Getting city with id {city_id}")
            city = get_object_or_404(City, id=city_id)
            print(f"DEBUG: Found city: {city.name}")
            
            # Update user
            print(f"🔍 EDIT DEBUG: Starting user update - User ID: {junkyard.user.id}")
            print(f"🔍 EDIT DEBUG: Before update - telegram_id: {junkyard.user.telegram_id}")
            
            junkyard.user.username = username
            junkyard.user.first_name = first_name
            junkyard.user.last_name = last_name
            junkyard.user.telegram_id = telegram_id_int
            # Ensure user type is always 'junkyard' for junkyards
            junkyard.user.user_type = 'junkyard'
            junkyard.user.save()
            
            print(f"🔍 EDIT DEBUG: After user save - User ID: {junkyard.user.id}, telegram_id: {junkyard.user.telegram_id}")
            
            # Update junkyard
            print(f"🔍 EDIT DEBUG: Starting junkyard update - Junkyard ID: {junkyard.id}")
            junkyard.phone = phone
            junkyard.city = city
            junkyard.location = location
            junkyard.is_active = is_active
            junkyard.is_verified = is_verified
            junkyard.save()
            
            print(f"🔍 EDIT DEBUG: After junkyard save - Junkyard ID: {junkyard.id}")
            
            # Final verification that IDs haven't changed
            if junkyard.id != original_junkyard_id:
                print(f"🚨 ALERT: Junkyard ID changed from {original_junkyard_id} to {junkyard.id}!")
                messages.warning(request, f'تحذير: معرف التشليح تغير من {original_junkyard_id} إلى {junkyard.id}')
            
            if junkyard.user.id != original_user_id:
                print(f"🚨 ALERT: User ID changed from {original_user_id} to {junkyard.user.id}!")
                messages.warning(request, f'تحذير: معرف المستخدم تغير من {original_user_id} إلى {junkyard.user.id}')
            
            messages.success(request, f'تم تحديث بيانات التشليح "{first_name}" بنجاح (ID: {junkyard.id})')
            print(f"🔍 EDIT DEBUG: Success! Redirecting to junkyard detail {junkyard.id}")
            return redirect('dashboard:junkyard_detail', junkyard_id=junkyard.id)
            
        except Exception as e:
            print(f"🚨 EDIT ERROR: Exception occurred while updating junkyard {original_junkyard_id}: {str(e)}")
            print(f"🚨 EDIT ERROR: Exception type: {type(e)}")
            import traceback
            print(f"🚨 EDIT ERROR: Traceback: {traceback.format_exc()}")
            messages.error(request, f'حدث خطأ أثناء تحديث التشليح: {str(e)}')
            return redirect('dashboard:edit_junkyard', junkyard_id=original_junkyard_id)
    
    # GET request - show form with current data
    cities = City.objects.filter(is_active=True).order_by('name')
    
    context = {
        'junkyard': junkyard,
        'cities': cities,
        'is_edit': True,
    }
    
    return render(request, 'dashboard/edit_junkyard.html', context)

@staff_member_required
def fix_junkyard_user_types(request):
    """Fix incorrect user types for junkyards"""
    
    if request.method == 'POST':
        # Get all junkyards with wrong user types
        wrong_type_junkyards = Junkyard.objects.filter(
            user__user_type__in=['junkyard_owner', 'owner', 'manager', 'admin', 'staff']
        ).exclude(user__user_type='junkyard')
        
        fixed_count = 0
        errors = []
        
        try:
            for junkyard in wrong_type_junkyards:
                old_type = junkyard.user.user_type
                junkyard.user.user_type = 'junkyard'
                junkyard.user.save()
                fixed_count += 1
                print(f"✅ Fixed junkyard {junkyard.id}: {junkyard.user.first_name} - {old_type} → junkyard")
            
            if fixed_count > 0:
                messages.success(request, f'تم إصلاح {fixed_count} تشليح بنجاح! جميع التشاليح الآن لها نوع المستخدم الصحيح.')
            else:
                messages.info(request, 'جميع التشاليح لها نوع المستخدم الصحيح بالفعل.')
                
        except Exception as e:
            messages.error(request, f'حدث خطأ أثناء الإصلاح: {str(e)}')
            print(f"❌ Error fixing user types: {e}")
        
        return redirect('dashboard:fix_junkyard_user_types')
    
    # GET request - show current status
    try:
        # Get all junkyards and their user types
        all_junkyards = Junkyard.objects.select_related('user', 'city').all()
        
        # Categorize by user type
        correct_junkyards = []
        wrong_type_junkyards = []
        
        for junkyard in all_junkyards:
            if junkyard.user.user_type == 'junkyard':
                correct_junkyards.append(junkyard)
            else:
                wrong_type_junkyards.append(junkyard)
        
        # Get statistics
        stats = {
            'total_junkyards': all_junkyards.count(),
            'correct_type': len(correct_junkyards),
            'wrong_type': len(wrong_type_junkyards),
            'needs_fix': len(wrong_type_junkyards) > 0,
        }
        
        context = {
            'stats': stats,
            'correct_junkyards': correct_junkyards,
            'wrong_type_junkyards': wrong_type_junkyards,
        }
        
    except Exception as e:
        messages.error(request, f'حدث خطأ في تحميل البيانات: {str(e)}')
        context = {
            'stats': {'total_junkyards': 0, 'correct_type': 0, 'wrong_type': 0, 'needs_fix': False},
            'correct_junkyards': [],
            'wrong_type_junkyards': [],
        }
    
    return render(request, 'dashboard/fix_user_types.html', context)

@staff_member_required
def debug_junkyard_edit_issue(request):
    """Debug tool for junkyard edit issues"""
    
    context = {
        'junkyards': [],
        'debug_info': '',
        'search_performed': False,
    }
    
    if request.method == 'POST':
        search_name = request.POST.get('search_name', '').strip()
        
        if search_name:
            # Search for junkyards by name
            junkyards = Junkyard.objects.filter(
                user__first_name__icontains=search_name
            ).select_related('user', 'city').order_by('id')
            
            debug_info = []
            debug_info.append(f"🔍 البحث عن التشاليح باسم: '{search_name}'")
            debug_info.append(f"📊 عدد النتائج: {junkyards.count()}")
            debug_info.append("")
            
            for idx, junkyard in enumerate(junkyards, 1):
                debug_info.append(f"--- التشليح رقم {idx} ---")
                debug_info.append(f"🆔 معرف التشليح: {junkyard.id}")
                debug_info.append(f"👤 معرف المستخدم: {junkyard.user.id}")
                debug_info.append(f"📝 الاسم: {junkyard.user.first_name} {junkyard.user.last_name}")
                debug_info.append(f"🏷️ اسم المستخدم: {junkyard.user.username}")
                debug_info.append(f"📱 معرف التليجرام: {junkyard.user.telegram_id or 'غير محدد'}")
                debug_info.append(f"🏙️ المدينة: {junkyard.city.name}")
                debug_info.append(f"📞 الهاتف: {junkyard.phone}")
                debug_info.append(f"🔧 نوع المستخدم: {junkyard.user.user_type}")
                debug_info.append(f"✅ نشط: {'نعم' if junkyard.is_active else 'لا'}")
                debug_info.append(f"🔐 معتمد: {'نعم' if junkyard.is_verified else 'لا'}")
                debug_info.append(f"📅 تاريخ الإنشاء: {junkyard.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                debug_info.append("")
            
            # Check for duplicates
            user_ids = [j.user.id for j in junkyards]
            telegram_ids = [j.user.telegram_id for j in junkyards if j.user.telegram_id]
            usernames = [j.user.username for j in junkyards]
            
            duplicate_users = [uid for uid in set(user_ids) if user_ids.count(uid) > 1]
            duplicate_telegrams = [tid for tid in set(telegram_ids) if telegram_ids.count(tid) > 1]
            duplicate_usernames = [uname for uname in set(usernames) if usernames.count(uname) > 1]
            
            if duplicate_users or duplicate_telegrams or duplicate_usernames:
                debug_info.append("⚠️ تم العثور على تضارب في البيانات:")
                if duplicate_users:
                    debug_info.append(f"   - معرفات مستخدمين مكررة: {duplicate_users}")
                if duplicate_telegrams:
                    debug_info.append(f"   - معرفات تليجرام مكررة: {duplicate_telegrams}")
                if duplicate_usernames:
                    debug_info.append(f"   - أسماء مستخدمين مكررة: {duplicate_usernames}")
            else:
                debug_info.append("✅ لا توجد تضارب في البيانات")
            
            context.update({
                'junkyards': junkyards,
                'debug_info': '\n'.join(debug_info),
                'search_performed': True,
                'search_name': search_name,
            })
    
    return render(request, 'dashboard/debug_junkyard_edit.html', context)

@staff_member_required
def add_junkyard(request):
    """Add new junkyard from dashboard"""
    if request.method == 'POST':
        # Debug: Print all POST data
        print(f"DEBUG: POST data: {request.POST}")
        
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name', '')
        username = request.POST.get('username')
        phone = request.POST.get('phone')
        city_id = request.POST.get('city')
        location = request.POST.get('location')
        telegram_id = request.POST.get('telegram_id')
        
        # Debug: Print extracted values
        print(f"DEBUG: first_name={first_name}, username={username}, phone={phone}, city_id={city_id}, location={location}, telegram_id={telegram_id}")
        
        # Validate required fields
        if not all([first_name, username, phone, city_id, location, telegram_id]):
            print(f"DEBUG: Validation failed - missing required fields")
            messages.error(request, 'جميع الحقول مطلوبة')
            return redirect('dashboard:add_junkyard')
        
        # Validate telegram_id
        try:
            telegram_id_int = int(telegram_id)
            if telegram_id_int <= 0 or len(telegram_id) < 8:
                print(f"DEBUG: Invalid telegram_id: {telegram_id}")
                messages.error(request, 'معرف التليجرام يجب أن يكون رقماً صحيحاً مكوناً من 8 أرقام على الأقل')
                return redirect('dashboard:add_junkyard')
        except (ValueError, TypeError):
            print(f"DEBUG: telegram_id is not a valid number: {telegram_id}")
            messages.error(request, 'معرف التليجرام يجب أن يكون رقماً صحيحاً')
            return redirect('dashboard:add_junkyard')
        
        try:
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                print(f"DEBUG: Username {username} already exists")
                messages.error(request, 'اسم المستخدم موجود بالفعل')
                return redirect('dashboard:add_junkyard')
            
            # Check if telegram_id already exists
            if User.objects.filter(telegram_id=telegram_id_int).exists():
                print(f"DEBUG: Telegram ID {telegram_id_int} already exists")
                messages.error(request, 'معرف التليجرام مستخدم بالفعل')
                return redirect('dashboard:add_junkyard')
            
            # Get city
            print(f"DEBUG: Getting city with id {city_id}")
            city = get_object_or_404(City, id=city_id)
            print(f"DEBUG: Found city: {city.name}")
            
            # Create user
            print(f"DEBUG: Creating user {username} with telegram_id {telegram_id_int}")
            user = User.objects.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                user_type='junkyard',
                telegram_id=telegram_id_int
            )
            print(f"DEBUG: User created with id {user.id} and telegram_id {user.telegram_id}")
            
            # Create junkyard
            print(f"DEBUG: Creating junkyard for user {user.id}")
            junkyard = Junkyard.objects.create(
                user=user,
                phone=phone,
                city=city,
                location=location,
                is_active=True,
                is_verified=False
            )
            print(f"DEBUG: Junkyard created with id {junkyard.id}")
            
            messages.success(request, f'تم إضافة التشليح "{first_name}" بنجاح')
            print(f"DEBUG: Redirecting to junkyard detail {junkyard.id}")
            return redirect('dashboard:junkyard_detail', junkyard_id=junkyard.id)
            
        except Exception as e:
            print(f"DEBUG: Exception occurred: {str(e)}")
            print(f"DEBUG: Exception type: {type(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            messages.error(request, f'حدث خطأ أثناء إضافة التشليح: {str(e)}')
            return redirect('dashboard:add_junkyard')
    
    # GET request - show form
    cities = City.objects.filter(is_active=True).order_by('name')
    
    context = {
        'cities': cities,
    }
    
    return render(request, 'dashboard/add_junkyard.html', context)

@staff_member_required
def users_list(request):
    """List all users with their junkyard relationships"""
    users = User.objects.select_related('junkyard_profile').prefetch_related('junkyard_roles__junkyard').order_by('-date_joined')
    
    # Filtering
    user_type_filter = request.GET.get('type')
    active_filter = request.GET.get('active')
    
    if user_type_filter:
        users = users.filter(user_type=user_type_filter)
    
    if active_filter == 'true':
        users = users.filter(is_active=True)
    elif active_filter == 'false':
        users = users.filter(is_active=False)
    
    # Calculate statistics
    all_users = User.objects.all()
    stats = {
        'total_users': all_users.count(),
        'total_clients': all_users.filter(user_type='client').count(),
        'total_junkyards': all_users.filter(user_type='junkyard').count(),
        'active_users': all_users.filter(is_active=True).count(),
        'blocked_users': all_users.filter(is_active=False).count(),
    }
    
    context = {
        'users': users,
        'stats': stats,
        'current_type': user_type_filter,
        'current_active': active_filter,
    }
    
    return render(request, 'dashboard/users_list.html', context)

@staff_member_required
def settings_view(request):
    """System settings view"""
    if request.method == 'POST':
        # Update settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_key = key.replace('setting_', '')
                try:
                    # Try to parse as JSON for complex values
                    import json
                    parsed_value = json.loads(value)
                except:
                    # Keep as string if not valid JSON
                    parsed_value = value
                
                SystemSetting.set_setting(setting_key, parsed_value)
        
        return redirect('dashboard:settings')
    
    # Get current settings
    settings_data = {}
    default_settings = {
        'commission_percentage': 2.0,
        'payment_url': 'https://your-payment-gateway.com',
        'request_expiry_hours': 6,
        'welcome_message': 'مرحباً بك في بوت قطع غيار السيارات!',
        'support_contact': '@support_username',
    }
    
    for key, default_value in default_settings.items():
        settings_data[key] = SystemSetting.get_setting(key, default_value)
    
    context = {
        'settings': settings_data,
    }
    
    return render(request, 'dashboard/settings.html', context)

@staff_member_required
def analytics_view(request):
    """Analytics and reports view"""
    # Date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Requests over time
    requests_over_time = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        count = Request.objects.filter(created_at__date=date).count()
        requests_over_time.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # Offers over time
    offers_over_time = []
    for i in range(days):
        date = start_date + timedelta(days=i)
        count = Offer.objects.filter(created_at__date=date).count()
        offers_over_time.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # City distribution
    city_stats = Request.objects.filter(
        created_at__date__gte=start_date
    ).values('city__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Brand distribution
    brand_stats = Request.objects.filter(
        created_at__date__gte=start_date
    ).values('brand__name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Average response time (offers per request)
    avg_offers_per_request = Offer.objects.filter(
        created_at__date__gte=start_date
    ).count() / max(Request.objects.filter(created_at__date__gte=start_date).count(), 1)
    
    context = {
        'days': days,
        'requests_over_time': requests_over_time,
        'offers_over_time': offers_over_time,
        'city_stats': city_stats,
        'brand_stats': brand_stats,
        'avg_offers_per_request': round(avg_offers_per_request, 2),
    }
    
    return render(request, 'dashboard/analytics.html', context)

# Telegram Media Views
@staff_member_required
def telegram_image(request, file_id):
    """Proxy Telegram image to dashboard"""
    import requests
    from django.http import HttpResponse
    from django.conf import settings
    
    try:
        # Get file path from Telegram
        bot_token = settings.TELEGRAM_BOT_TOKEN
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile"
        response = requests.get(get_file_url, params={'file_id': file_id})
        
        if response.status_code == 200:
            file_info = response.json()
            if file_info.get('ok'):
                file_path = file_info['result']['file_path']
                # Download the actual file
                file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
                file_response = requests.get(file_url)
                
                if file_response.status_code == 200:
                    # Determine content type
                    content_type = 'image/jpeg'
                    if file_path.lower().endswith('.png'):
                        content_type = 'image/png'
                    elif file_path.lower().endswith('.gif'):
                        content_type = 'image/gif'
                    elif file_path.lower().endswith('.webp'):
                        content_type = 'image/webp'
                    
                    response = HttpResponse(file_response.content, content_type=content_type)
                    response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
                    return response
        
        # If we get here, something went wrong
        return HttpResponse("Image not found", status=404)
        
    except Exception as e:
        logger.error(f"Error fetching Telegram image {file_id}: {e}")
        return HttpResponse("Error loading image", status=500)

@staff_member_required
def telegram_video(request, file_id):
    """Proxy Telegram video to dashboard"""
    import requests
    from django.http import HttpResponse
    from django.conf import settings
    
    try:
        # Get file path from Telegram
        bot_token = settings.TELEGRAM_BOT_TOKEN
        get_file_url = f"https://api.telegram.org/bot{bot_token}/getFile"
        response = requests.get(get_file_url, params={'file_id': file_id})
        
        if response.status_code == 200:
            file_info = response.json()
            if file_info.get('ok'):
                file_path = file_info['result']['file_path']
                # Download the actual file
                file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
                file_response = requests.get(file_url)
                
                if file_response.status_code == 200:
                    # Determine content type
                    content_type = 'video/mp4'
                    if file_path.lower().endswith('.webm'):
                        content_type = 'video/webm'
                    elif file_path.lower().endswith('.avi'):
                        content_type = 'video/avi'
                    elif file_path.lower().endswith('.mov'):
                        content_type = 'video/quicktime'
                    
                    response = HttpResponse(file_response.content, content_type=content_type)
                    response['Cache-Control'] = 'public, max-age=3600'  # Cache for 1 hour
                    return response
        
        # If we get here, something went wrong
        return HttpResponse("Video not found", status=404)
        
    except Exception as e:
        logger.error(f"Error fetching Telegram video {file_id}: {e}")
        return HttpResponse("Error loading video", status=500)

# API endpoints for AJAX requests
@staff_member_required
def api_stats(request):
    """API endpoint for dashboard stats"""
    today = timezone.now().date()
    
    stats = {
        'total_users': User.objects.count(),
        'active_requests': Request.objects.filter(status='new').count(),
        'total_offers': Offer.objects.count(),
        'requests_today': Request.objects.filter(created_at__date=today).count(),
    }
    
    return JsonResponse(stats)

def public_dashboard(request):
    """Public dashboard view (no login required)"""
    # Basic stats only
    stats = {
        'total_requests': Request.objects.count(),
        'total_junkyards': Junkyard.objects.filter(is_active=True).count(),
        'total_cities': City.objects.filter(is_active=True).count(),
        'average_rating': JunkyardRating.objects.aggregate(avg=Avg('rating'))['avg'] or 0,
    }
    
    context = {
        'stats': stats,
    }
    
    return render(request, 'dashboard/public_dashboard.html', context)

@staff_member_required
def add_user(request):
    """Add new user and link to junkyard"""
    if request.method == 'POST':
        # Debug: Print all POST data
        print(f"DEBUG: POST data: {request.POST}")
        
        # Get form data
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email', '')
        password = request.POST.get('password')
        phone = request.POST.get('phone')
        telegram_id = request.POST.get('telegram_id')
        junkyard_id = request.POST.get('junkyard')
        role = request.POST.get('role')
        
        # Debug: Print extracted values
        print(f"DEBUG: first_name={first_name}, username={username}, junkyard_id={junkyard_id}, role={role}")
        
        # Validate required fields
        if not all([first_name, last_name, username, password, phone, telegram_id, junkyard_id, role]):
            print(f"DEBUG: Validation failed - missing required fields")
            messages.error(request, 'جميع الحقول مطلوبة')
            return redirect('dashboard:add_user')
        
        # Validate telegram_id
        try:
            telegram_id_int = int(telegram_id)
            if telegram_id_int <= 0 or len(telegram_id) < 8:
                print(f"DEBUG: Invalid telegram_id: {telegram_id}")
                messages.error(request, 'معرف التليجرام يجب أن يكون رقماً صحيحاً مكوناً من 8 أرقام على الأقل')
                return redirect('dashboard:add_user')
        except (ValueError, TypeError):
            print(f"DEBUG: telegram_id is not a valid number: {telegram_id}")
            messages.error(request, 'معرف التليجرام يجب أن يكون رقماً صحيحاً')
            return redirect('dashboard:add_user')
        
        # Validate password length
        if len(password) < 8:
            print(f"DEBUG: Password too short: {len(password)} characters")
            messages.error(request, 'كلمة المرور يجب أن تكون مكونة من 8 أحرف على الأقل')
            return redirect('dashboard:add_user')
        
        try:
            # Check if username already exists
            if User.objects.filter(username=username).exists():
                print(f"DEBUG: Username {username} already exists")
                messages.error(request, 'اسم المستخدم موجود بالفعل')
                return redirect('dashboard:add_user')
            
            # Check if telegram_id already exists
            if User.objects.filter(telegram_id=telegram_id_int).exists():
                print(f"DEBUG: Telegram ID {telegram_id_int} already exists")
                messages.error(request, 'معرف التليجرام مستخدم بالفعل')
                return redirect('dashboard:add_user')
            
            # Get junkyard
            print(f"DEBUG: Getting junkyard with id {junkyard_id}")
            junkyard = get_object_or_404(Junkyard, id=junkyard_id)
            print(f"DEBUG: Found junkyard: {junkyard.user.first_name}")
            
            # Create user
            print(f"DEBUG: Creating user {username} with telegram_id {telegram_id_int}")
            user = User.objects.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=make_password(password),  # Hash the password
                phone_number=phone,
                telegram_id=telegram_id_int,
                user_type='junkyard',
                is_active=True
            )
            print(f"DEBUG: User created with id {user.id} and telegram_id {user.telegram_id}")
            
            # Create JunkyardStaff relationship
            staff_member = JunkyardStaff.objects.create(
                user=user,
                junkyard=junkyard,
                role=role,
                is_active=True
            )
            print(f"DEBUG: Staff relationship created with id {staff_member.id} and role {role}")
            
            messages.success(request, f'تم إضافة المستخدم "{first_name} {last_name}" بنجاح وربطه بالتشليح "{junkyard.user.first_name}" كـ {staff_member.get_role_display()}')
            print(f"DEBUG: Redirecting to users list")
            return redirect('dashboard:users_list')
            
        except Exception as e:
            print(f"DEBUG: Exception occurred: {str(e)}")
            print(f"DEBUG: Exception type: {type(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            messages.error(request, f'حدث خطأ أثناء إضافة المستخدم: {str(e)}')
            return redirect('dashboard:add_user')
    
    # GET request - show form
    junkyards = Junkyard.objects.filter(is_active=True).select_related('user', 'city').order_by('user__first_name')
    
    context = {
        'junkyards': junkyards,
    }
    
    return render(request, 'dashboard/add_user.html', context)

@staff_member_required
def toggle_user_status(request, user_id):
    """Toggle user active/inactive status"""
    if request.method != 'POST':
        messages.error(request, 'طريقة غير صحيحة')
        return redirect('dashboard:users_list')
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Prevent admins from deactivating themselves
        if user == request.user:
            messages.error(request, 'لا يمكنك حجب حسابك الشخصي')
            return redirect('dashboard:users_list')
        
        # Store original status before change
        was_inactive = not user.is_active
        
        # Toggle status
        user.is_active = not user.is_active
        user.save()
        
        status = "تم إلغاء حجب" if user.is_active else "تم حجب"
        
        # Send Telegram notification if user was unblocked
        if was_inactive and user.is_active:
            print(f"DEBUG: Sending unban notification to user {user.telegram_id}")
            try:
                result = telegram_service.send_unban_notification(user)
                if result["success"]:
                    messages.success(request, f'{status} المستخدم "{user.first_name} {user.last_name}" بنجاح وتم إرسال إشعار التفعيل')
                    print(f"DEBUG: Unban notification sent successfully to {user.telegram_id}")
                else:
                    messages.success(request, f'{status} المستخدم "{user.first_name} {user.last_name}" بنجاح')
                    messages.warning(request, f'تعذر إرسال إشعار التفعيل: {result.get("error", "خطأ غير معروف")}')
                    print(f"DEBUG: Failed to send unban notification: {result.get('error')}")
            except Exception as e:
                messages.success(request, f'{status} المستخدم "{user.first_name} {user.last_name}" بنجاح')
                messages.warning(request, f'تعذر إرسال إشعار التفعيل: {str(e)}')
                print(f"DEBUG: Exception sending unban notification: {e}")
        else:
            messages.success(request, f'{status} المستخدم "{user.first_name} {user.last_name}" بنجاح')
        
        print(f"DEBUG: User {user.username} status changed to active={user.is_active}")
        
    except Exception as e:
        print(f"DEBUG: Error toggling user status: {e}")
        messages.error(request, f'حدث خطأ أثناء تغيير حالة المستخدم: {str(e)}')
    
    return redirect('dashboard:users_list')

@staff_member_required
def delete_user(request, user_id):
    """Delete a user permanently"""
    if request.method != 'POST':
        messages.error(request, 'طريقة غير صحيحة')
        return redirect('dashboard:users_list')
    
    try:
        user = get_object_or_404(User, id=user_id)
        
        # Prevent admins from deleting themselves
        if user == request.user:
            messages.error(request, 'لا يمكنك حذف حسابك الشخصي')
            return redirect('dashboard:users_list')
        
        # Prevent deletion of superusers by non-superusers
        if user.is_superuser and not request.user.is_superuser:
            messages.error(request, 'ليس لديك صلاحية حذف هذا المستخدم')
            return redirect('dashboard:users_list')
        
        # Store info for message
        user_name = f"{user.first_name} {user.last_name}"
        user_username = user.username
        
        # Check if user owns a junkyard
        if hasattr(user, 'junkyard_profile'):
            messages.warning(request, f'تحذير: المستخدم "{user_name}" يملك تشليح. حذف المستخدم سيؤثر على التشليح المرتبط.')
        
        # Check if user has staff roles
        staff_roles = user.junkyard_roles.count()
        if staff_roles > 0:
            messages.warning(request, f'تحذير: المستخدم "{user_name}" مرتبط بـ {staff_roles} تشليح كموظف.')
        
        # Delete user
        user.delete()
        
        messages.success(request, f'تم حذف المستخدم "{user_name}" ({user_username}) نهائياً من النظام')
        print(f"DEBUG: User {user_username} deleted permanently")
        
    except Exception as e:
        print(f"DEBUG: Error deleting user: {e}")
        messages.error(request, f'حدث خطأ أثناء حذف المستخدم: {str(e)}')
    
    return redirect('dashboard:users_list')
