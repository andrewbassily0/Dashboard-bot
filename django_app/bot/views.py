import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
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

@method_decorator(csrf_exempt, name='dispatch')
class TelegramWebhookView(View):
    """Handle Telegram webhook updates"""
    
    def post(self, request):
        try:
            # Parse the update
            update_data = json.loads(request.body.decode('utf-8'))
            
            # Create bot instance
            bot = TelegramBot()
            app = bot.setup_bot()
            
            if not app:
                logger.error("Failed to setup bot application")
                return HttpResponse("Bot Error", status=500)
            
            update = Update.de_json(update_data, app.bot)
            
            # Process the update asynchronously
            asyncio.create_task(app.process_update(update))
            
            return HttpResponse("OK")
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return HttpResponse("Error", status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def n8n_webhook_new_request(request):
    """Webhook for n8n to handle new requests"""
    try:
        data = request.data
        
        # Create new request from n8n data
        user = User.objects.get(telegram_id=data['user_telegram_id'])
        city = City.objects.get(id=data['city_id'])
        brand = Brand.objects.get(id=data['brand_id'])
        model = Model.objects.get(id=data['model_id'])
        
        new_request = Request.objects.create(
            user=user,
            city=city,
            brand=brand,
            model=model,
            year=data['year'],
            parts=data['parts'],
            media_files=data.get('media_files', [])
        )
        
        return JsonResponse({
            'success': True,
            'request_id': new_request.id,
            'order_id': new_request.order_id
        }, status=201)
        
    except Exception as e:
        logger.error(f"Error in n8n webhook: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def n8n_webhook_new_offer(request):
    """Webhook for n8n to handle new offers"""
    try:
        data = request.data
        
        request_obj = Request.objects.get(id=data['request_id'])
        junkyard = Junkyard.objects.get(user__telegram_id=data['junkyard_telegram_id'])
        
        offer = Offer.objects.create(
            request=request_obj,
            junkyard=junkyard,
            price=data['price'],
            notes=data.get('notes', '')
        )
        
        # Notify customer about new offer
        asyncio.create_task(notify_customer_new_offer(offer))
        
        return JsonResponse({
            'success': True,
            'offer_id': offer.id
        }, status=201)
        
    except Exception as e:
        logger.error(f"Error in n8n offer webhook: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

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

@api_view(['POST'])
@permission_classes([AllowAny])
def send_telegram_message(request):
    """Send message via Telegram for n8n"""
    try:
        data = request.data
        
        telegram_id = data['telegram_id']
        message = data['message']
        keyboard = data.get('keyboard', None)
        
        # Send message asynchronously
        asyncio.create_task(send_message_async(telegram_id, message, keyboard))
        
        return JsonResponse({
            'success': True,
            'message': 'Message sent'
        })
        
    except Exception as e:
        logger.error(f"Error sending telegram message: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)

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
async def notify_customer_new_offer(offer):
    """Notify customer about new offer"""
    try:
        message = f"""
💰 عرض جديد لطلبك!

🆔 رقم الطلب: {offer.request.order_id}
🏪 المخزن: {offer.junkyard.user.first_name}
💵 السعر: {offer.price} ريال
⭐ التقييم: {offer.junkyard.average_rating:.1f} ({offer.junkyard.total_ratings} تقييم)
📍 الموقع: {offer.junkyard.location}

هل تريد قبول هذا العرض؟
        """
        
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("✅ قبول العرض", callback_data=f"offer_accept_{offer.id}")],
            [InlineKeyboardButton("❌ رفض العرض", callback_data=f"offer_reject_{offer.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        bot = TelegramBot()
        app = bot.setup_bot()
        if app:
            await app.bot.send_message(
                chat_id=offer.request.user.telegram_id,
                text=message,
                reply_markup=reply_markup
            )
        
    except Exception as e:
        logger.error(f"Error notifying customer: {e}")

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
