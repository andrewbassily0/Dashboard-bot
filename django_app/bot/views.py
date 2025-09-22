import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from telegram import Update
from .telegram_bot import TelegramBot
from .models import User, Request, Offer, Junkyard, City, Brand, Model
import asyncio

logger = logging.getLogger(__name__)

# Simple decorator to replace api_view
def api_view(methods):
    def decorator(func):
        func.allowed_methods = methods
        return func
    return decorator

def permission_classes(classes):
    def decorator(func):
        return func
    return decorator

class AllowAny:
    pass

def health_check(request):
    """Health check endpoint for Docker"""
    return JsonResponse({"status": "healthy", "service": "auto_parts_bot"})

@api_view(['GET'])
@permission_classes([AllowAny])
def health_queue(request):
    """Health check for queue/worker status"""
    try:
        # Check if we can access the database
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        # Check if workflow service is available
        from .services import workflow_service
        service_status = "available" if workflow_service else "unavailable"
        
        return JsonResponse({
            "status": "healthy",
            "database": "connected",
            "workflow_service": service_status,
            "timestamp": timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": timezone.now().isoformat()
        }, status=500)

@api_view(['GET'])
@permission_classes([AllowAny])
def health_notifications(request):
    """Health check for notification system"""
    try:
        from django.conf import settings
        
        # Check Telegram bot token
        bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        token_status = "configured" if bot_token else "missing"
        
        # Check if we can create a test message
        test_message = "🧪 Test notification from health check"
        
        return JsonResponse({
            "status": "healthy",
            "telegram_token": token_status,
            "test_message": test_message,
            "timestamp": timezone.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": timezone.now().isoformat()
        }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    """Handle Telegram webhook updates - حل جذري لمشكلة التضارب"""
    
    def post(self, request):
        try:
            logger.info("📡 Webhook received update")
            
            # Parse the update
            update_data = json.loads(request.body.decode('utf-8'))
            logger.info(f"📊 Update data: {update_data}")
            
            # Create bot instance
            bot = TelegramBot()
            app = bot.setup_bot()
            
            if not app:
                logger.error("❌ Failed to setup bot application")
                return HttpResponse("Bot Error", status=500)
            
            # Create update object with proper bot instance
            from telegram import Bot
            bot_instance = Bot(token=app.bot.token)
            
            # Handle CallbackQuery creation properly
            if 'callback_query' in update_data:
                # Create a proper CallbackQuery object
                from telegram import CallbackQuery, Message, User, Chat
                
                callback_data = update_data['callback_query']
                from_data = callback_data['from']
                message_data = callback_data['message']
                chat_data = message_data['chat']
                
                # Create User objects
                from_user = User(
                    id=from_data['id'],
                    is_bot=from_data['is_bot'],
                    first_name=from_data['first_name'],
                    last_name=from_data.get('last_name'),
                    username=from_data.get('username')
                )
                
                # Create Chat object
                chat = Chat(
                    id=chat_data['id'],
                    type=chat_data['type'],
                    first_name=chat_data.get('first_name'),
                    last_name=chat_data.get('last_name'),
                    username=chat_data.get('username')
                )
                
                # Create Message object
                message = Message(
                    message_id=message_data['message_id'],
                    from_user=from_user,
                    date=message_data['date'],
                    chat=chat,
                    text=message_data.get('text', '')
                )
                
                # Create CallbackQuery object
                callback_query = CallbackQuery(
                    id=callback_data['id'],
                    from_user=from_user,
                    message=message,
                    data=callback_data.get('data'),
                    chat_instance=callback_data.get('chat_instance', '')
                )
                
                # Create Update object
                update = Update(
                    update_id=update_data['update_id'],
                    callback_query=callback_query
                )
            else:
                # Regular message update
                update = Update.de_json(update_data, bot_instance)
            
            # Process the update synchronously to avoid conflicts
            import asyncio
            
            async def process_update():
                try:
                    await app.initialize()
                    await app.process_update(update)
                    logger.info("✅ Update processed successfully")
                except Exception as e:
                    logger.error(f"❌ Error processing update: {e}")
            
            # Run in new event loop to avoid conflicts
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(process_update())
                loop.close()
            except Exception as e:
                logger.error(f"❌ Event loop error: {e}")
                # Fallback to direct processing
                asyncio.create_task(process_update())
            
            return HttpResponse("OK")
            
        except Exception as e:
            logger.error(f"❌ Error processing webhook: {e}")
            return HttpResponse("Error", status=500)
    
    def get(self, request):
        """Health check للـ webhook"""
        return HttpResponse("Telegram Webhook is ready! 🤖", status=200)

# n8n webhooks removed - using direct workflow service instead

# @api_view(['POST'])
# @permission_classes([AllowAny])
# def n8n_webhook_new_request(request):
#     """DEPRECATED: Webhook for n8n to handle new requests - now handled directly by workflow service"""
#     return JsonResponse({'error': 'This endpoint is deprecated. Use workflow service instead.'}, status=410)

# @api_view(['POST'])
# @permission_classes([AllowAny])
# def n8n_webhook_new_offer(request):
#     """DEPRECATED: Webhook for n8n to handle new offers - now handled directly by workflow service"""
#     return JsonResponse({'error': 'This endpoint is deprecated. Use workflow service instead.'}, status=410)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_active_requests(request):
    """Get active requests for n8n processing"""
    try:
        city_id = request.GET.get('city_id')
        
        requests_query = Request.objects.filter(status='new')
        if city_id:
            requests_query = requests_query.filter(city_id=city_id)
        
        requests_data = []
        for req in requests_query:
            requests_data.append({
                'id': req.id,
                'order_id': req.order_id,
                'user_telegram_id': req.user.telegram_id,
                'city': req.city.name,
                'brand': req.brand.name,
                'model': req.model.name,
                'year': req.year,
                'parts': req.parts,
                'media_files': req.media_files,
                'created_at': req.created_at.isoformat(),
                'expires_at': req.expires_at.isoformat()
            })
        
        return JsonResponse({
            'success': True,
            'requests': requests_data
        })
        
    except Exception as e:
        logger.error(f"Error getting active requests: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_junkyards_by_city(request):
    """Get active junkyards by city for n8n"""
    try:
        city_id = request.GET.get('city_id')
        
        junkyards_query = Junkyard.objects.filter(is_active=True)
        if city_id:
            junkyards_query = junkyards_query.filter(city_id=city_id)
        
        junkyards_data = []
        for junkyard in junkyards_query:
            junkyards_data.append({
                'id': junkyard.id,
                'user_telegram_id': junkyard.user.telegram_id,
                'name': junkyard.user.first_name,
                'phone': junkyard.phone,
                'city': junkyard.city.name,
                'location': junkyard.location,
                'is_verified': junkyard.is_verified,
                'average_rating': float(junkyard.average_rating),
                'total_ratings': junkyard.total_ratings
            })
        
        return JsonResponse({
            'success': True,
            'junkyards': junkyards_data
        })
        
    except Exception as e:
        logger.error(f"Error getting junkyards: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

# @api_view(['POST'])
# @permission_classes([AllowAny])
# def send_telegram_message(request):
#     """DEPRECATED: Send message via Telegram for n8n - now handled directly by workflow service"""
#     return JsonResponse({'error': 'This endpoint is deprecated. Use workflow service instead.'}, status=410)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_system_stats(request):
    """Get system statistics for dashboard"""
    try:
        from django.db.models import Count, Avg
        from datetime import datetime, timedelta
        
        # Get date ranges
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        stats = {
            'total_users': User.objects.count(),
            'total_clients': User.objects.filter(user_type='client').count(),
            'total_junkyards': User.objects.filter(user_type='junkyard').count(),
            'total_requests': Request.objects.count(),
            'active_requests': Request.objects.filter(status='new').count(),
            'total_offers': Offer.objects.count(),
            'requests_today': Request.objects.filter(created_at__date=today).count(),
            'requests_this_week': Request.objects.filter(created_at__date__gte=week_ago).count(),
            'requests_this_month': Request.objects.filter(created_at__date__gte=month_ago).count(),
            'average_offers_per_request': Offer.objects.aggregate(
                avg=Avg('request__offers__id')
            )['avg'] or 0,
            'top_cities': list(Request.objects.values('city__name').annotate(
                count=Count('id')
            ).order_by('-count')[:5]),
            'top_brands': list(Request.objects.values('brand__name').annotate(
                count=Count('id')
            ).order_by('-count')[:5])
        }
        
        return JsonResponse({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

# Async helper functions
# DEPRECATED: This function is now handled by the workflow service
# async def notify_customer_new_offer(offer):
#     """DEPRECATED: Notify customer about new offer - now handled by workflow service"""
#     pass

async def send_message_async(telegram_id, message, keyboard=None):
    """Send message asynchronously"""
    try:
        reply_markup = None
        if keyboard:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            buttons = []
            for row in keyboard:
                button_row = []
                for button in row:
                    button_row.append(InlineKeyboardButton(
                        button['text'], 
                        callback_data=button['callback_data']
                    ))
                buttons.append(button_row)
            reply_markup = InlineKeyboardMarkup(buttons)
        
        bot = TelegramBot()
        app = bot.setup_bot()
        if app:
            await app.bot.send_message(
                chat_id=telegram_id,
                text=message,
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Error sending async message: {e}")


# DEPRECATED: This function is now handled by the workflow service
async def notify_junkyards_async(request):
    """DEPRECATED: إرسال إشعارات للتشاليح عن طلب جديد - now handled by workflow service"""
    logger.warning(f"🚨 DEPRECATED: notify_junkyards_async called for request {request.order_id}. This should now be handled by workflow service.")
    
    # Fallback to workflow service if called
    try:
        from .services import workflow_service
        from .telegram_bot import TelegramBot
        
        bot = TelegramBot()
        workflow_service.set_telegram_bot(bot)
        await workflow_service.notify_all_junkyards(request)
        
    except Exception as e:
        logger.error(f"❌ Error in deprecated notify_junkyards_async fallback: {e}")

# Old implementation completely removed - replaced by workflow service


@api_view(['GET'])
@permission_classes([AllowAny])
def debug_junkyards_in_city(request):
    """تشخيص التشاليح في مدينة معينة"""
    try:
        city_id = request.GET.get('city_id')
        if not city_id:
            return JsonResponse({'error': 'city_id parameter required'}, status=400)
        
        from .models import Junkyard, City, JunkyardStaff
        
        city = City.objects.get(id=city_id)
        junkyards = Junkyard.objects.filter(city=city).select_related('user')
        
        debug_info = {
            'city_name': city.name,
            'total_junkyards': junkyards.count(),
            'active_junkyards': junkyards.filter(is_active=True).count(),
            'verified_junkyards': junkyards.filter(is_verified=True).count(),
            'junkyards_with_telegram': junkyards.filter(user__telegram_id__isnull=False).count(),
            'details': []
        }
        
        for junkyard in junkyards:
            staff_count = JunkyardStaff.objects.filter(
                junkyard=junkyard, 
                is_active=True,
                user__telegram_id__isnull=False
            ).count()
            
            junkyard_info = {
                'id': junkyard.id,
                'name': junkyard.user.first_name,
                'is_active': junkyard.is_active,
                'is_verified': junkyard.is_verified,
                'has_telegram_id': bool(junkyard.user.telegram_id),
                'telegram_id': junkyard.user.telegram_id,
                'staff_with_telegram': staff_count,
                'phone': junkyard.phone,
                'created_at': junkyard.created_at.strftime('%Y-%m-%d')
            }
            debug_info['details'].append(junkyard_info)
        
        return JsonResponse({
            'success': True,
            'debug_info': debug_info
        })
        
    except City.DoesNotExist:
        return JsonResponse({'error': 'City not found'}, status=404)
    except Exception as e:
        logger.error(f"Error in debug_junkyards_in_city: {e}")
        return JsonResponse({'error': str(e)}, status=500)
