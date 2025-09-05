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
    requests = Request.objects.select_related('user', 'city', 'brand', 'model').order_by('-created_at')
    
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
    req = get_object_or_404(Request, id=request_id)
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
