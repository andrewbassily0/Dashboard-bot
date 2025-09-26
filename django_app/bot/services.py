"""
Workflow services for handling order lifecycle without n8n dependency
"""

import logging
import asyncio
from typing import List, Optional
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from asgiref.sync import sync_to_async

from .models import Request, Junkyard, Offer, JunkyardStaff

logger = logging.getLogger(__name__)
User = get_user_model()


class OrderWorkflowService:
    """
    Service class to handle the complete order workflow:
    1. Customer places and confirms order
    2. Order sent to all suppliers in city
    3. Suppliers respond with prices
    4. Prices sent back to customer
    5. Customer can accept/reject offers
    """
    
    def __init__(self):
        self.telegram_bot = None
    
    def set_telegram_bot(self, bot):
        """Set the telegram bot instance for sending messages"""
        self.telegram_bot = bot
    
    async def process_confirmed_order(self, request: Request):
        """
        Process a confirmed order by notifying all junkyards in the city
        """
        try:
            logger.info(f"🔄 Processing confirmed order {request.order_id}")
            
            # Update request status to active
            await self._update_request_status(request, 'active')
            
            # Try to notify all junkyards in the city
            junkyard_notification_success = False
            try:
                await self.notify_all_junkyards(request)
                junkyard_notification_success = True
                logger.info(f"✅ Successfully notified junkyards for order {request.order_id}")
            except Exception as notification_error:
                logger.error(f"⚠️ Error notifying junkyards for order {request.order_id}: {notification_error}")
                # Don't fail the entire process if junkyard notifications fail
            
            # Try to send confirmation to customer
            try:
                await self.send_order_confirmation_to_customer(request)
                logger.info(f"✅ Successfully sent confirmation to customer for order {request.order_id}")
            except Exception as customer_error:
                logger.error(f"⚠️ Error sending confirmation to customer for order {request.order_id}: {customer_error}")
                # Don't fail the entire process if customer confirmation fails
            
            if junkyard_notification_success:
                logger.info(f"✅ Successfully processed order {request.order_id}")
            else:
                logger.warning(f"⚠️ Order {request.order_id} created but junkyard notifications failed")
            
        except Exception as e:
            logger.error(f"❌ Error processing confirmed order {request.order_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def notify_all_junkyards(self, request: Request):
        """
        Send notification to all active junkyards in the same city as the request
        """
        try:
            logger.info(f"📢 Notifying junkyards for order {request.order_id} in {request.city.name}")
            
            # Get all active junkyards in the city
            junkyards = await self._get_active_junkyards_in_city(request.city.id)
            
            if not junkyards:
                logger.warning(f"⚠️ No active junkyards found in {request.city.name}")
                return
            
            logger.info(f"📊 Found {len(junkyards)} active junkyards in {request.city.name}")
            
            # Prepare the notification message
            message = await self._prepare_junkyard_notification_message(request)
            keyboard = self._create_junkyard_action_keyboard(request)
            
            # Get all photos from request items
            photos_to_send = await self._get_request_photos(request)
            
            # Send notifications to all junkyards
            success_count = 0
            failed_count = 0
            
            for junkyard in junkyards:
                try:
                    # Send message first
                    await self._send_message_to_junkyard(junkyard, message, keyboard)
                    
                    # Send photos if any
                    if photos_to_send:
                        await self._send_photos_to_junkyard(junkyard, photos_to_send)
                    
                    success_count += 1
                    logger.info(f"✅ Notified junkyard {junkyard.user.first_name}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Failed to notify junkyard {junkyard.user.first_name}: {e}")
            
            logger.info(f"📈 Notification results: {success_count} successful, {failed_count} failed")
            
        except Exception as e:
            logger.error(f"❌ Error notifying junkyards for order {request.order_id}: {e}")
            raise
    
    async def process_junkyard_offer(self, offer: Offer):
        """
        Process a new offer from junkyard and notify the customer
        """
        try:
            logger.info(f"💰 Processing new offer from {offer.junkyard.user.first_name} for order {offer.request.order_id}")
            
            # Send offer notification to customer
            await self.notify_customer_about_offer(offer)
            
            # Optional: Check if this is the first offer and update request status
            offer_count = await self._get_offer_count_for_request(offer.request)
            if offer_count == 1:
                await self._update_request_status(offer.request, 'active')
            
            logger.info(f"✅ Successfully processed offer from {offer.junkyard.user.first_name}")
            
        except Exception as e:
            logger.error(f"❌ Error processing offer from {offer.junkyard.user.first_name}: {e}")
            raise
    
    async def notify_customer_about_offer(self, offer: Offer):
        """
        Send notification to customer about a new offer
        """
        try:
            message = await self._prepare_customer_offer_message(offer)
            keyboard = self._create_customer_offer_keyboard(offer)
            
            await self._send_message_to_customer(offer.request.user, message, keyboard)
            
            logger.info(f"📱 Notified customer about offer from {offer.junkyard.user.first_name}")
            
        except Exception as e:
            logger.error(f"❌ Error notifying customer about offer: {e}")
            raise
    
    async def process_customer_offer_decision(self, offer: Offer, decision: str, customer_user: User):
        """
        Process customer's decision on an offer (accept/reject)
        """
        try:
            if decision not in ['accept', 'reject']:
                raise ValueError(f"Invalid decision: {decision}")
            
            logger.info(f"🎯 Processing customer decision '{decision}' for offer {offer.id}")
            
            # Update offer status
            new_status = 'accepted' if decision == 'accept' else 'rejected'
            await self._update_offer_status(offer, new_status)
            
            if decision == 'accept':
                await self._handle_offer_acceptance(offer)
            else:
                await self._handle_offer_rejection(offer)
            
            # Send confirmation to customer
            await self._send_decision_confirmation_to_customer(offer, decision)
            
            logger.info(f"✅ Successfully processed {decision} decision for offer {offer.id}")
            
        except Exception as e:
            logger.error(f"❌ Error processing customer decision: {e}")
            raise
    
    async def _handle_offer_acceptance(self, offer: Offer):
        """
        Handle when customer accepts an offer
        """
        # Update request status to accepted
        await self._update_request_status(offer.request, 'accepted')
        
        # Notify the junkyard about acceptance
        await self._notify_junkyard_about_acceptance(offer)
        
        # Optionally reject other pending offers for the same request
        await self._reject_other_offers_for_request(offer.request, offer.id)
    
    async def _handle_offer_rejection(self, offer: Offer):
        """
        Handle when customer rejects an offer
        """
        # Notify junkyard about rejection
        await self._notify_junkyard_about_rejection(offer)
        
        # Check if any other offers are still pending
        pending_offers = await self._get_pending_offers_for_request(offer.request)
        if not pending_offers:
            logger.info(f"ℹ️ No more pending offers for request {offer.request.order_id}")
    
    # Helper methods
    async def _get_active_junkyards_in_city(self, city_id: int) -> List[Junkyard]:
        """Get all active junkyards in a specific city"""
        
        junkyards = await sync_to_async(list)(
            Junkyard.objects.filter(city_id=city_id, is_active=True)
            .select_related('user', 'city')
        )
        return junkyards
    
    async def _prepare_junkyard_notification_message(self, request: Request) -> str:
        """Prepare notification message for junkyards"""
        # Get parts description safely in async context
        parts_description = await self._get_request_parts_description(request)
        
        message = f"""
🆕 طلب جديد في منطقتك!

🆔 رقم الطلب: {request.order_id}
👤 العميل: {request.user.first_name}
🚗 السيارة: {request.brand.name} {request.model.name} {request.year}
🏙️ المدينة: {request.city.name}

📦 القطع المطلوبة:
{parts_description}

⏰ ينتهي في: {request.expires_at.strftime('%Y-%m-%d %H:%M')}

💡 يرجى إرسال عرضك مع السعر ومدة التوريد المتوقعة.
        """
        return message.strip()
    
    def _create_junkyard_action_keyboard(self, request: Request):
        """Create keyboard for junkyard actions"""
        keyboard = [
            [InlineKeyboardButton("💰 إضافة عرض سعر", callback_data=f"offer_add_{request.id}")],
            [InlineKeyboardButton("📋 عرض تفاصيل الطلب", callback_data=f"request_details_{request.id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def _get_request_photos(self, request: Request) -> list:
        """Get all photos from request items"""
        from asgiref.sync import sync_to_async
        
        photos = []
        
        # Check if request has items
        has_items = await sync_to_async(lambda: request.items.exists())()
        
        if has_items:
            items = await sync_to_async(list)(request.items.all())
            for item in items:
                if item.media_files:
                    for media in item.media_files:
                        if media.get("type") == "photo":
                            photos.append({
                                "file_id": media.get("file_id"),
                                "item_name": item.name
                            })
        
        return photos
    
    async def _send_photos_to_junkyard(self, junkyard: Junkyard, photos: list):
        """Send photos to junkyard with captions"""
        if not self.telegram_bot or not photos:
            return
        
        # Send to main junkyard user
        telegram_id = junkyard.user.telegram_id
        if telegram_id:
            await self._send_photos_to_telegram(telegram_id, photos)
        
        # Also send to junkyard staff if any
        staff_members = await self._get_junkyard_staff(junkyard)
        for staff in staff_members:
            if staff.user.telegram_id and staff.is_active:
                try:
                    await self._send_photos_to_telegram(staff.user.telegram_id, photos)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "chat not found" in error_msg:
                        logger.warning(f"Failed to send photos to staff {staff.user.first_name}: Chat not found")
                    elif "forbidden" in error_msg:
                        logger.warning(f"Failed to send photos to staff {staff.user.first_name}: User blocked the bot")
                    else:
                        logger.warning(f"Failed to send photos to staff {staff.user.first_name}: {e}")
    
    async def _send_photos_to_telegram(self, telegram_id: int, photos: list):
        """Send photos to telegram user"""
        if not self.telegram_bot:
            return
        
        for photo_data in photos:
            try:
                caption = f"📸 صورة قطعة: {photo_data['item_name']}"
                await self.telegram_bot.application.bot.send_photo(
                    chat_id=telegram_id,
                    photo=photo_data['file_id'],
                    caption=caption
                )
            except Exception as e:
                logger.error(f"Failed to send photo to {telegram_id}: {e}")
    
    async def _get_request_parts_description(self, request: Request) -> str:
        """Get parts description with numbers and photos for display"""
        from asgiref.sync import sync_to_async
        
        # Check if request has items
        has_items = await sync_to_async(lambda: request.items.exists())()
        
        if has_items:
            items = await sync_to_async(list)(
                request.items.all()
            )
            parts_list = []
            for i, item in enumerate(items, 1):
                # Check if item has photos
                has_photos = len(item.media_files) > 0
                photo_indicator = "📸" if has_photos else "📦"
                parts_list.append(f"{i}️⃣ {photo_indicator} {item.name}")
            return "\n".join(parts_list)
        else:
            return await sync_to_async(lambda: request.parts or "لا توجد قطع محددة")()
    
    async def _get_detailed_pricing(self, offer: Offer) -> str:
        """Get detailed pricing for offer items"""
        try:
            # Check if offer has detailed pricing
            offer_items = await sync_to_async(list)(offer.items.all())
            if offer_items:
                pricing_lines = ["📦 الأسعار التفصيلية:"]
                for item in offer_items:
                    pricing_lines.append(f"- {item.request_item.name}: {item.price} ريال")
                pricing_lines.append("-------------------------")
                return "\n".join(pricing_lines)
            else:
                return ""
        except Exception as e:
            logger.warning(f"Error getting detailed pricing: {e}")
            return ""
    
    async def _prepare_customer_offer_message(self, offer: Offer) -> str:
        """Prepare offer notification message for customer"""
        delivery_info = f"⏰ مدة التوريد: {offer.delivery_time}" if hasattr(offer, 'delivery_time') and offer.delivery_time else ""
        
        # Get parts description with numbers
        parts_description = await self._get_request_parts_description(offer.request)
        
        # Get detailed pricing if available
        detailed_pricing = await self._get_detailed_pricing(offer)
        
        message = f"""
💰 عرض جديد لطلبك!

🆔 رقم الطلب: {offer.request.order_id}
🏪 التشليح: {offer.junkyard.user.first_name}
📦 القطع المطلوبة:
{parts_description}

{detailed_pricing}

💰 **الإجمالي**: {offer.price} ريال
{delivery_info}
⭐ التقييم: {offer.junkyard.average_rating:.1f} ⭐ ({offer.junkyard.total_ratings} تقييم)
📍 الموقع: {offer.junkyard.location}

💬 ملاحظات: {offer.notes if offer.notes else 'لا توجد ملاحظات إضافية'}

🤔 هل تريد قبول هذا العرض؟
        """
        return message.strip()
    
    def _create_customer_offer_keyboard(self, offer: Offer):
        """Create keyboard for customer offer decision"""
        keyboard = [
            [
                InlineKeyboardButton("✅ قبول العرض", callback_data=f"offer_accept_{offer.id}"),
                InlineKeyboardButton("❌ رفض العرض", callback_data=f"offer_reject_{offer.id}")
            ],
            [InlineKeyboardButton("💬 التواصل مع التشليح", callback_data=f"chat_with_junkyard_{offer.junkyard.id}_{offer.request.id}")],
            [InlineKeyboardButton("📋 عرض جميع العروض", callback_data=f"view_all_offers_{offer.request.id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def _send_message_to_junkyard(self, junkyard: Junkyard, message: str, keyboard=None):
        """Send message to a junkyard"""
        if not self.telegram_bot:
            raise Exception("Telegram bot not set")
        
        # Try to send to main junkyard user
        telegram_id = junkyard.user.telegram_id
        if telegram_id:
            await self._send_telegram_message(telegram_id, message, keyboard)
        
        # Also send to junkyard staff if any
        staff_members = await self._get_junkyard_staff(junkyard)
        for staff in staff_members:
            if staff.user.telegram_id and staff.is_active:
                try:
                    await self._send_telegram_message(staff.user.telegram_id, message, keyboard)
                except Exception as e:
                    error_msg = str(e).lower()
                    if "chat not found" in error_msg:
                        logger.warning(f"Failed to send to staff {staff.user.first_name}: Chat not found - user may not have started conversation with bot")
                    elif "forbidden" in error_msg:
                        logger.warning(f"Failed to send to staff {staff.user.first_name}: User blocked the bot")
                    else:
                        logger.warning(f"Failed to send to staff {staff.user.first_name}: {e}")
    
    async def _send_message_to_customer(self, customer: User, message: str, keyboard=None):
        """Send message to customer"""
        if not customer.telegram_id:
            raise Exception(f"Customer {customer.username} has no telegram ID")
        
        await self._send_telegram_message(customer.telegram_id, message, keyboard)
    
    async def _send_telegram_message(self, telegram_id: int, message: str, keyboard=None):
        """Send actual telegram message"""
        if not self.telegram_bot:
            raise Exception("Telegram bot not set")
        
        app = self.telegram_bot.setup_bot()
        if not app:
            raise Exception("Failed to setup telegram bot")
        
        await app.bot.send_message(
            chat_id=telegram_id,
            text=message,
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    async def send_order_confirmation_to_customer(self, request: Request):
        """Send order confirmation to customer"""
        # Get parts description safely in async context
        parts_description = await self._get_request_parts_description(request)
        
        message = f"""
✅ تم تأكيد طلبك بنجاح!

🆔 رقم الطلب: {request.order_id}
🏙️ المدينة: {request.city.name}
🚗 السيارة: {request.brand.name} {request.model.name} {request.year}

📦 القطع المطلوبة:
{parts_description}

📤 تم إرسال طلبك إلى جميع التشاليح المسجّلة في منطقتك.
⏰ ستبدأ العروض بالوصول خلال دقائق!

📱 سيتم إشعارك فور وصول أي عرض جديد.
        """
        
        keyboard = [
            [InlineKeyboardButton("📋 متابعة الطلب", callback_data=f"track_request_{request.id}")],
            [InlineKeyboardButton("🆕 طلب جديد", callback_data="new_request")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_message_to_customer(request.user, message, reply_markup)
    
    # Database helper methods
    async def _update_request_status(self, request: Request, status: str):
        """Update request status"""
        
        request.status = status
        await sync_to_async(request.save)(update_fields=['status'])
        logger.info(f"📝 Updated request {request.order_id} status to {status}")
    
    async def _update_offer_status(self, offer: Offer, status: str):
        """Update offer status"""
        
        offer.status = status
        await sync_to_async(offer.save)(update_fields=['status'])
        logger.info(f"📝 Updated offer {offer.id} status to {status}")
    
    async def _get_offer_count_for_request(self, request: Request) -> int:
        """Get number of offers for a request"""
        
        return await sync_to_async(request.offers.count)()
    
    async def _get_pending_offers_for_request(self, request: Request) -> List[Offer]:
        """Get pending offers for a request"""
        
        return await sync_to_async(list)(
            request.offers.filter(status='pending').select_related('junkyard__user')
        )
    
    async def _reject_other_offers_for_request(self, request: Request, accepted_offer_id: int):
        """Lock all other offers for a request when one is accepted"""
        
        # Update all other pending offers to 'locked' status to prevent acceptance  
        def update_offers():
            return request.offers.exclude(id=accepted_offer_id).filter(status='pending').update(status='locked')
        
        await sync_to_async(update_offers)()
        
        # Get the locked offers to notify junkyards
        def get_locked_offers():
            return list(request.offers.filter(status='locked').exclude(id=accepted_offer_id))
        
        locked_offers = await sync_to_async(get_locked_offers)()
        
        for offer in locked_offers:
            await self._notify_junkyard_about_rejection(offer, is_auto_rejection=True)
    
    async def _get_junkyard_staff(self, junkyard: Junkyard) -> List['JunkyardStaff']:
        """Get active staff members for a junkyard"""
        
        return await sync_to_async(list)(
            junkyard.staff_members.filter(is_active=True).select_related('user')
        )
    
    
    async def _notify_junkyard_about_acceptance(self, offer: Offer):
        """Notify junkyard that their offer was accepted"""
        # Get parts description
        parts_description = await self._get_request_parts_description(offer.request)
        
        # Get detailed pricing
        detailed_pricing = await self._get_detailed_pricing(offer)
        
        # Get offer details safely
        order_id = await sync_to_async(lambda: offer.request.order_id)()
        customer_name = await sync_to_async(lambda: offer.request.user.first_name)()
        offer_price = await sync_to_async(lambda: offer.price)()
        phone_number = await sync_to_async(lambda: offer.request.user.phone_number)()
        
        message = f"""
🎉 تهانينا! تم قبول عرضك!

🆔 رقم الطلب: {order_id}
👤 العميل: {customer_name}
📦 القطع المطلوبة:
{parts_description}

{detailed_pricing}

💰 **الإجمالي**: {offer_price} ريال
📱 رقم العميل: {phone_number if phone_number else 'غير متوفر'}

📞 يرجى التواصل مع العميل لتنسيق التسليم.

✨ نشكرك على استخدام منصتنا!
        """
        
        # Get IDs safely
        customer_id = await sync_to_async(lambda: offer.request.user.id)()
        request_id = await sync_to_async(lambda: offer.request.id)()
        
        keyboard = [
            [InlineKeyboardButton("💬 التواصل مع العميل", callback_data=f"chat_with_customer_{customer_id}_{request_id}")],
            [InlineKeyboardButton("📋 تفاصيل الطلب", callback_data=f"request_details_{request_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_message_to_junkyard(offer.junkyard, message, reply_markup)
    
    async def _notify_junkyard_about_rejection(self, offer: Offer, is_auto_rejection: bool = False):
        """Notify junkyard that their offer was rejected"""
        rejection_reason = "تلقائياً (تم قبول عرض آخر)" if is_auto_rejection else "من قبل العميل"
        
        # Get parts description
        parts_description = await self._get_request_parts_description(offer.request)
        
        # Get detailed pricing
        detailed_pricing = await self._get_detailed_pricing(offer)
        
        # Get offer details safely
        order_id = await sync_to_async(lambda: offer.request.order_id)()
        customer_name = await sync_to_async(lambda: offer.request.user.first_name)()
        offer_price = await sync_to_async(lambda: offer.price)()
        
        message = f"""
😔 تم رفض عرضك

🆔 رقم الطلب: {order_id}
👤 العميل: {customer_name}
📦 القطع المطلوبة:
{parts_description}

{detailed_pricing}

💰 **الإجمالي**: {offer_price} ريال
📝 سبب الرفض: {rejection_reason}

💡 لا تقلق! ستصلك طلبات جديدة قريباً.
✨ شكراً لك على المشاركة في منصتنا!
        """
        
        await self._send_message_to_junkyard(offer.junkyard, message)
    
    async def _send_decision_confirmation_to_customer(self, offer: Offer, decision: str):
        """Send confirmation to customer about their decision"""
        if decision == 'accept':
            # Get parts description
            parts_description = await self._get_request_parts_description(offer.request)
            
            # Get detailed pricing
            detailed_pricing = await self._get_detailed_pricing(offer)
            
            # Get offer details safely
            order_id = await sync_to_async(lambda: offer.request.order_id)()
            junkyard_name = await sync_to_async(lambda: offer.junkyard.user.first_name)()
            offer_price = await sync_to_async(lambda: offer.price)()
            junkyard_location = await sync_to_async(lambda: offer.junkyard.location)()
            
            message = f"""
✅ تم قبول العرض بنجاح!

🆔 رقم الطلب: {order_id}
🏪 التشليح: {junkyard_name}
📦 القطع المطلوبة:
{parts_description}

{detailed_pricing}

💰 **الإجمالي**: {offer_price} ريال
📍 الموقع: {junkyard_location}

📞 سيتم التواصل معك من قبل التشليح لتنسيق التسليم.

⭐ لا تنس تقييم الخدمة بعد استلام القطع!
            """
        else:
            # Get detailed pricing for rejection message
            detailed_pricing = await self._get_detailed_pricing(offer)
            
            # Get offer details safely
            order_id = await sync_to_async(lambda: offer.request.order_id)()
            junkyard_name = await sync_to_async(lambda: offer.junkyard.user.first_name)()
            offer_price = await sync_to_async(lambda: offer.price)()
            
            message = f"""
❌ تم رفض العرض

🆔 رقم الطلب: {order_id}
🏪 التشليح: {junkyard_name}

{detailed_pricing}

💰 **الإجمالي**: {offer_price} ريال

💡 سنستمر في استقبال عروض أخرى لطلبك.
📱 سيتم إشعارك عند وصول عروض جديدة.
            """
        
        # Get request ID safely
        request_id = await sync_to_async(lambda: offer.request.id)()
        
        keyboard = [
            [InlineKeyboardButton("📋 عرض جميع العروض", callback_data=f"view_all_offers_{request_id}")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self._send_message_to_customer(offer.request.user, message, reply_markup)


# Singleton instance
workflow_service = OrderWorkflowService()
