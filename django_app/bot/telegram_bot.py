import os
import json
import logging
import uuid
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from django.conf import settings
from django.utils import timezone
from asgiref.sync import sync_to_async
from .models import User, City, Brand, Model, Request, Junkyard, Offer, Conversation, JunkyardRating

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.application = None
        self.user_states = {}  # تخزين حالات المحادثة والمسودات للمستخدمين
        self.MAX_DRAFTS = 5  # الحد الأقصى لعدد المسودات لكل مستخدم
    
    def setup_bot(self):
        """Initialize the bot application"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN not found in settings")
            return None
        
        try:
            self.application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
            
            # Add handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CallbackQueryHandler(self.button_callback))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            self.application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, self.handle_media))
            
            logger.info("Bot application setup successfully")
            return self.application
        except Exception as e:
            logger.error(f"Error setting up bot: {e}")
            return None
    
    @sync_to_async
    def get_or_create_user(self, telegram_user) -> User:
        """Get or create user from Telegram user data with connection handling"""
        from django.db import connection
        
        # Close any existing connections to force reconnection
        try:
            connection.close()
        except Exception:
            pass
            
        try:
            user, created = User.objects.get_or_create(
                telegram_id=telegram_user.id,
                defaults={
                    'username': telegram_user.username or f"user_{telegram_user.id}",
                    'first_name': telegram_user.first_name or '',
                    'last_name': telegram_user.last_name or '',
                    'telegram_username': telegram_user.username or '',
                    'user_type': 'client'  # Default to client
                }
            )
            return user
        except Exception as e:
            logger.error(f"Database error in get_or_create_user: {e}")
            # Try to reconnect and retry once
            try:
                connection.close()
                user, created = User.objects.get_or_create(
                    telegram_id=telegram_user.id,
                    defaults={
                        'username': telegram_user.username or f"user_{telegram_user.id}",
                        'first_name': telegram_user.first_name or '',
                        'last_name': telegram_user.last_name or '',
                        'telegram_username': telegram_user.username or '',
                        'user_type': 'client'  # Default to client
                    }
                )
                return user
            except Exception as retry_error:
                logger.error(f"Retry failed in get_or_create_user: {retry_error}")
                raise
    
    async def get_request_parts_description(self, request: Request) -> str:
        """Get parts description safely in async context"""
        # Check if request has items
        has_items = await sync_to_async(lambda: request.items.exists())()
        
        if has_items:
            items = await sync_to_async(list)(
                request.items.all()
            )
            parts_list = []
            for i, item in enumerate(items, 1):
                parts_list.append(f"{i}️⃣ {item.name}")
            return "\n".join(parts_list)
        else:
            return request.parts or "لا توجد قطع محددة"
    
    def _format_parts_for_pricing(self, parts_description):
        """Format parts description for pricing request"""
        lines = parts_description.split('\n')
        pricing_lines = []
        for line in lines:
            if line.strip():
                # Extract part name (remove emoji and number)
                part_name = line.split(' ', 1)[-1] if ' ' in line else line
                pricing_lines.append(f"- {part_name}: ___ ريال")
        return '\n'.join(pricing_lines)
    
    async def check_user_status(self, update: Update) -> bool:
        """Check if user is banned/inactive and send appropriate message"""
        user = await self.get_or_create_user(update.effective_user)
        
        # التحقق من حالة المستخدم
        if not user.is_active:
            # رسالة الحجب
            ban_message = """
🚫 عذراً، حسابك محظور من استخدام تشاليح

⚠️ لقد تم تعطيل حسابك من قبل إدارة النظام ولا يمكنك استخدام البوت حالياً.

🔍 أسباب محتملة للحظر:
• مخالفة شروط الاستخدام
• تقديم معلومات غير صحيحة
• سلوك غير لائق في التعامل

📞 للاستفسار والاستعلام:
• راجع شروط الاستخدام
• تواصل مع خدمة العملاء
• ارسل استفساراً لإدارة النظام

❌ لا يمكنك استخدام أي من خدمات البوت حتى يتم إلغاء الحظر من قبل الإدارة.
            """
            
            try:
                if hasattr(update, 'message') and update.message:
                    await update.message.reply_text(ban_message)
                elif hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.message.reply_text(ban_message)
                
                logger.warning(f"Blocked user {user.telegram_id} ({user.first_name}) attempted to use bot")
            except Exception as e:
                logger.error(f"Error sending ban message to user {user.telegram_id}: {e}")
            
            # مسح حالة المستخدم المحجوب
            await self.clear_banned_user_state(user.telegram_id)
            
            return False  # المستخدم محجوب
        
        return True  # المستخدم نشط ويمكنه الاستخدام
    
    async def clear_banned_user_state(self, telegram_id: int):
        """Clear user state when user gets banned"""
        if telegram_id in self.user_states:
            del self.user_states[telegram_id]
            logger.info(f"Cleared state for banned user {telegram_id}")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command - show initial start button"""
        # التحقق من حالة المستخدم أولاً
        if not await self.check_user_status(update):
            return  # المستخدم محجوب، تم إرسال رسالة الحجب
        
        user = await self.get_or_create_user(update.effective_user)
        
        # الترحيب الشخصي - تفضيل @username، البديل هو الاسم الأول
        telegram_user = update.effective_user
        if telegram_user.username:
            user_greeting = f"@{telegram_user.username}"
        else:
            user_greeting = telegram_user.first_name or "عزيزي المستخدم"
        
        # رسالة ترحيب أولية مع زر البداية
        initial_message = f"""
🔧 مرحباً {user_greeting}!

أهلاً بك في بوت قطع غيار السيارات 🚗

اضغط على الزر أدناه لبدء استخدام البوت:
        """
        
        # زر "ابدأ ✅" للبدء
        keyboard = [
            [InlineKeyboardButton("ابدأ ✅", callback_data="start_bot")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(initial_message, reply_markup=reply_markup)
    
    async def show_main_welcome(self, query, user):
        """Show main welcome message with new design"""
        # الترحيب الشخصي - تفضيل @username، البديل هو الاسم الأول
        telegram_user = query.from_user
        if telegram_user.username:
            user_greeting = f"@{telegram_user.username}"
        else:
            user_greeting = telegram_user.first_name or "عزيزي المستخدم"
        
        # رسالة الترحيب الجديدة
        welcome_message = f"""
🔧 مرحباً {user_greeting}!

أهلاً بك في **تشاليح** - منصتك  للعثور على قطع غيار السيارات 🚗

نحن نربطك بأفضل التشاليح المسجلة في منطقتك لتحصل على أفضل العروض والأسعار.

اختَر إجراءً:
        """
        
        # الأزرار الجديدة
        keyboard = [
            [InlineKeyboardButton("🛒 بدء الطلبات", callback_data="start_ordering")],
            [InlineKeyboardButton("❓ ما هو تشاليح", callback_data="about_tashaleeh")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(welcome_message, reply_markup=reply_markup)
    
    async def show_about_tashaleeh(self, query, user):
        """Show 'About Tashaleeh' screen"""
        about_message = """
❓ **ما هو تشاليح؟**

🔧 **تشاليح** هي منصة وسيطة ذكية لطلبات قطع غيار السيارات.

✨ **كيف نعمل:**
• نجمع طلبك بكل التفاصيل المطلوبة
• نرسله لجميع التشاليح المسجلة في منطقتك
• نستقبل العروض بالأسعار ومدد التوريد
• نعرضها عليك لاختيار الأنسب

🎯 **هدفنا:** توفير الوقت والجهد وضمان أفضل الأسعار!
        """
        
        keyboard = [
            [InlineKeyboardButton("🌐 الموقع", url="https://tashaleeh.com")],
            [InlineKeyboardButton("📜 طريقة الاستخدام وسياسة الاستخدام", callback_data="usage_policy")],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")],
            [InlineKeyboardButton("🛒 بدء الطلبات", callback_data="start_ordering")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(about_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def show_usage_policy(self, query, user):
        """Show usage instructions and policy screen"""
        policy_message = """
📜 **طريقة الاستخدام وسياسة الاستخدام**

🛠️ **كيف تستخدم الخدمة:**
• إنشاء طلب واحد يحتوي على عدة قطع غيار
• رفع صور اختيارية للقطع المطلوبة  
• تأكيد الطلب وإرساله للتشاليح
• استقبال عروض بأسعار ومدد توريد محددة
• قبول عرض واحد يؤدي لإغلاق بقية العروض تلقائياً

🔒 **سياسة الاستخدام والخصوصية:**
• مشاركة بيانات الطلب مع التشاليح المسجلة فقط لتقديم العروض
• جميع الأسعار تقديرية حتى التأكيد النهائي مع التشليح
• لا يتم تبادل بيانات الدفع داخل البوت
• الضغط على "بدء الطلبات" يُعتبر موافقة على هذه الشروط

✅ **بالمتابعة، أنت توافق على شروط الاستخدام**
        """
        
        keyboard = [
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_main")],
            [InlineKeyboardButton("🛒 بدء الطلبات", callback_data="start_ordering")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(policy_message, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard button callbacks"""
        query = update.callback_query
        await query.answer()
        
        try:
            # التحقق من حالة المستخدم أولاً
            if not await self.check_user_status(update):
                return  # المستخدم محجوب، تم إرسال رسالة الحجب
            
            user = await self.get_or_create_user(update.effective_user)
            data = query.data
            
            logger.info(f"Button callback: user {user.telegram_id} clicked '{data}'")
            
            # معالج زر "ابدأ ✅" - يقوم بتشغيل البوت وإظهار خيارات نوع الحساب
            if data == "start_bot":
                await self.show_main_welcome(query, user)
            elif data == "start_ordering":
                # بدء الطلبات - يذهب للقائمة الرئيسية للعملاء
                await self.show_client_menu(query, user)
            elif data == "about_tashaleeh":
                # شاشة "ما هو تشاليح"
                await self.show_about_tashaleeh(query, user)
            elif data == "usage_policy":
                # شاشة طريقة الاستخدام وسياسة الاستخدام
                await self.show_usage_policy(query, user)
            elif data == "back_to_main":
                # العودة للرئيسية
                await self.show_main_welcome(query, user)
            elif data == "user_type_client":
                # Direct to client menu since we removed junkyard option
                await self.show_client_menu(query, user)
            elif data.startswith("city_"):
                await self.handle_city_selection(query, user, data)
            elif data.startswith("brand_"):
                await self.handle_brand_selection(query, user, data)
            elif data.startswith("model_"):
                await self.handle_model_selection(query, user, data)
            elif data.startswith("year_range_"):
                await self.handle_year_range_selection(query, user, data)
            elif data.startswith("year_"):
                await self.handle_year_selection(query, user, data)
            elif data.startswith("offer_"):
                await self.handle_offer_action(query, user, data)
            elif data.startswith("rating_"):
                await self.handle_rating_selection(query, user, data)
            elif data == "new_request":
                await self.start_new_request(query, user)
            elif data == "my_requests":
                await self.show_user_requests(query, user)
            elif data.startswith("confirm_request_"):
                await self.confirm_request(query, user, data)
            elif data == "select_brand_again":
                await self.show_brand_selection(query, user)
            elif data == "show_more_brands":
                await self.show_all_brands(query, user)
            elif data.startswith("view_request_"):
                await self.show_request_details(query, user, data)
            elif data.startswith("request_action_"):
                await self.handle_request_action(query, user, data)
            elif data.startswith("draft_"):
                await self.handle_draft_action(query, user, data)
            elif data.startswith("switch_draft_"):
                await self.switch_to_draft(query, user, data)
            elif data.startswith("delete_draft_"):
                await self.delete_draft(query, user, data)
            elif data.startswith("offer_details_"):
                await self.show_offer_details(query, user, data)
            elif data.startswith("add_item_"):
                await self.handle_add_item(query, user, data)
            elif data.startswith("manage_items_"):
                await self.handle_manage_items(query, user, data)
            elif data.startswith("view_items_"):
                await self.handle_view_items(query, user, data)
            elif data.startswith("skip_description_"):
                await self.handle_skip_description(query, user, data)
            elif data.startswith("set_quantity_"):
                await self.handle_set_quantity(query, user, data)
            elif data.startswith("edit_item_menu_"):
                await self.handle_edit_item_menu(query, user, data)
            elif data.startswith("delete_item_menu_"):
                await self.handle_delete_item_menu(query, user, data)
            elif data.startswith("edit_item_"):
                await self.handle_edit_item(query, user, data)
            elif data.startswith("delete_item_"):
                await self.handle_delete_item(query, user, data)
            elif data.startswith("add_media_"):
                await self.handle_add_media_callback(query, user, data)
            elif data.startswith("chat_with_customer_"):
                await self.handle_chat_with_customer(query, user, data)
            elif data.startswith("view_all_offers_"):
                await self.handle_view_all_offers(query, user, data)
            elif data == "main_menu":
                await self.show_client_menu(query, user)
            else:
                # Handle unknown button clicks
                logger.warning(f"Unknown button callback: '{data}' from user {user.telegram_id}")
                await self.handle_unknown_button(query, user, data)
                
        except Exception as e:
            logger.error(f"Error in button_callback: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            try:
                await query.edit_message_text("""
❌ حدث خطأ مؤقت في النظام

🔧 يرجى المحاولة مرة أخرى، وإذا استمرت المشكلة:
• اضغط /start لإعادة تشغيل البوت
• تواصل مع الدعم الفني

نعتذر عن هذا الإزعاج المؤقت.""")
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")
                # Try to answer the callback at least
                try:
                    await query.answer("حدث خطأ، يرجى المحاولة مرة أخرى أو استخدم /start", show_alert=True)
                except:
                    pass

    async def handle_unknown_button(self, query, user, data):
        """Handle unknown or expired button clicks"""
        try:
            # Check if it might be an expired or old button
            expired_button_message = """
❓ هذا الزر غير متاح الآن

قد يكون هذا الزر منتهي الصلاحية أو من رسالة قديمة.

🔄 لاستخدام البوت، يرجى:
• اضغط /start للعودة للقائمة الرئيسية
• أو استخدم الأزرار من أحدث رسالة

🆔 إذا كنت تواجه مشاكل، تواصل مع الدعم مع ذكر الكود: {data}
            """.format(data=data[:20])  # Show only first 20 chars for privacy
            
            keyboard = [
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="start_bot")],
                [InlineKeyboardButton("🛒 بدء الطلبات", callback_data="start_ordering")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(expired_button_message, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in handle_unknown_button: {e}")
            try:
                await query.answer("هذا الزر غير متاح. استخدم /start للعودة للقائمة الرئيسية", show_alert=True)
            except:
                pass
    
    async def show_request_details(self, query, user, data):
        """Show detailed view of a specific request"""
        try:
            request_id = int(data.split("_")[2])
            request = await sync_to_async(Request.objects.select_related('brand', 'model', 'city').get)(id=request_id, user=user)
            
            # Get offers for this request (with related objects)
            offers = await sync_to_async(list)(
                request.offers.select_related('junkyard__user').order_by('-created_at')
            )
            
            # Build status message
            status_map = {
                'new': '🟡 جديد',
                'active': '🟢 نشط',
                'accepted': '✅ مقبول',
                'expired': '🔴 منتهي',
                'cancelled': '❌ ملغي'
            }
            
            # Get parts description
            parts_description = await self.get_request_parts_description(request)
            
            message = f"""
📋 تفاصيل الطلب

🆔 رقم الطلب: {request.order_id}
📊 الحالة: {status_map.get(request.status, request.status)}
🏙️ المدينة: {request.city.name}
🚗 السيارة: {request.brand.name} {request.model.name} {request.year}
📦 القطع المطلوبة:
{parts_description}
📅 تاريخ الإنشاء: {request.created_at.strftime('%Y-%m-%d %H:%M')}
⏰ ينتهي في: {request.expires_at.strftime('%Y-%m-%d %H:%M')}

💰 العروض المستلمة ({len(offers)}):
            """
            
            keyboard = []
            
            if offers:
                for i, offer in enumerate(offers[:3], 1):  # Show max 3 offers
                    offer_status = "✅ مقبول" if offer.status == "accepted" else "⏳ في الانتظار" if offer.status == "pending" else "❌ مرفوض"
                    message += f"\n{i}. 🏪 {offer.junkyard.user.first_name}"
                    message += f"\n   💰 {offer.price} ريال"
                    message += f"\n   📊 {offer_status}"
                    if offer.notes:
                        message += f"\n   📝 {offer.notes[:30]}..."
                    
                    # Add action buttons for pending offers
                    if offer.status == "pending":
                        keyboard.append([
                            InlineKeyboardButton(f"✅ قبول العرض {i}", callback_data=f"offer_accept_{offer.id}"),
                            InlineKeyboardButton(f"❌ رفض العرض {i}", callback_data=f"offer_reject_{offer.id}")
                        ])
            else:
                message += "\nلا توجد عروض بعد..."
            
            # Add general action buttons
            if request.status in ['new', 'active']:
                keyboard.append([InlineKeyboardButton("🔄 تحديث الحالة", callback_data=f"request_action_refresh_{request.id}")])
                keyboard.append([InlineKeyboardButton("❌ إلغاء الطلب", callback_data=f"request_action_cancel_{request.id}")])
            
            keyboard.append([InlineKeyboardButton("🔙 العودة للطلبات", callback_data="my_requests")])
            keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="user_type_client")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        except Request.DoesNotExist:
            await query.edit_message_text("❌ الطلب غير موجود أو لا تملك الصلاحية للوصول إليه.")
        except Exception as e:
            logger.error(f"Error showing request details: {e}")
            await query.edit_message_text("حدث خطأ أثناء عرض تفاصيل الطلب.")

    async def handle_request_action(self, query, user, data):
        """Handle actions on requests (refresh, cancel, etc.)"""
        try:
            action_parts = data.split("_")
            action = action_parts[2]  # refresh, cancel, etc.
            request_id = int(action_parts[3])
            
            request = await sync_to_async(Request.objects.select_related('brand', 'model', 'city').get)(id=request_id, user=user)
            
            if action == "refresh":
                # Simply show updated details
                await self.show_request_details(query, user, f"view_request_{request_id}")
            elif action == "cancel":
                # Cancel the request
                request.status = 'cancelled'
                await sync_to_async(request.save)()
                
                message = f"""
❌ تم إلغاء الطلب {request.order_id}

يمكنك إنشاء طلب جديد في أي وقت.
                """
                
                keyboard = [
                    [InlineKeyboardButton("🆕 طلب جديد", callback_data="new_request")],
                    [InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")],
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="user_type_client")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
                
        except Request.DoesNotExist:
            await query.edit_message_text("❌ الطلب غير موجود.")
        except Exception as e:
            logger.error(f"Error handling request action: {e}")
            await query.edit_message_text("حدث خطأ أثناء تنفيذ الإجراء.")

    async def show_brand_selection(self, query, user):
        """Show brand selection again"""
        # Reset user state to brand selection
        if user.telegram_id in self.user_states:
            self.user_states[user.telegram_id]["step"] = "select_brand"
        
        brands = await sync_to_async(list)(Brand.objects.filter(is_active=True).order_by('name'))
        
        # تسجيل عدد الماركات
        logger.info(f"Found {len(brands)} active brands for brand selection")
        
        # الماركات الأكثر شيوعاً أولاً
        popular_brands = ['تويوتا', 'هوندا', 'نيسان', 'هيونداي', 'كيا', 'مازدا', 'فورد', 'شيفروليه']
        sorted_brands = []
        
        # إضافة الماركات الشائعة أولاً
        for popular in popular_brands:
            for brand in brands:
                if brand.name == popular:
                    sorted_brands.append(brand)
                    break
        
        # إضافة باقي الماركات
        for brand in brands:
            if brand not in sorted_brands:
                sorted_brands.append(brand)
        
        # عرض أول 10 ماركات فقط
        display_brands = sorted_brands[:10]
        
        message = f"🚗 اختر وكالة السيارة (أشهر {len(display_brands)} وكالة):"
        keyboard = []
        
        # تجميع الماركات في صفوف من اثنين لتوفير مساحة
        for i in range(0, len(display_brands), 2):
            row = []
            row.append(InlineKeyboardButton(display_brands[i].name, callback_data=f"brand_{display_brands[i].id}"))
            if i + 1 < len(display_brands):
                row.append(InlineKeyboardButton(display_brands[i + 1].name, callback_data=f"brand_{display_brands[i + 1].id}"))
            keyboard.append(row)
        
        # إضافة زر "عرض المزيد" إذا كان هناك ماركات أخرى
        if len(brands) > 10:
            remaining = len(brands) - 10
            keyboard.append([InlineKeyboardButton(f"📄 عرض المزيد ({remaining} وكالة)", callback_data="show_more_brands")])
        
        # Add navigation button
        keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def show_all_brands(self, query, user):
        """Show all brands with pagination"""
        brands = await sync_to_async(list)(Brand.objects.filter(is_active=True).order_by('name'))
        
        # تسجيل عدد الماركات
        logger.info(f"Showing all {len(brands)} active brands")
        
        message = f"🚗 جميع الماركات المتاحة ({len(brands)} وكالة):\n\n"
        keyboard = []
        
        # تجميع الماركات في صفوف من اثنين
        for i in range(0, len(brands), 2):
            row = []
            row.append(InlineKeyboardButton(brands[i].name, callback_data=f"brand_{brands[i].id}"))
            if i + 1 < len(brands):
                row.append(InlineKeyboardButton(brands[i + 1].name, callback_data=f"brand_{brands[i + 1].id}"))
            keyboard.append(row)
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("🔙 الماركات الشائعة", callback_data="select_brand_again"),
            InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")
        ])
        keyboard.append([
            InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="user_type_client")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    
    async def show_client_menu(self, query, user):
        """Show main menu for clients"""
        # Personalized greeting
        telegram_user = query.from_user
        if telegram_user.username:
            user_greeting = f"@{telegram_user.username}"
        else:
            user_greeting = telegram_user.first_name or "عزيزي العميل"
        
        message = f"""
🛒 مرحباً {user_greeting}!

اختر ما تريد فعله:
        """
        
        keyboard = [
            [InlineKeyboardButton("🆕 طلب جديد", callback_data="new_request")],
            [InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def show_user_requests(self, query, user):
        """Show user's drafts and sent requests"""
        try:
            # Get user states for drafts
            user_drafts = self.user_states.get(user.telegram_id, {}).get("drafts", {})
            
            # Get sent requests from database
            requests = await sync_to_async(list)(
                Request.objects.filter(user=user)
                .select_related('brand', 'model', 'city')
                .order_by('-created_at')
            )
            
            # Build message and keyboard
            message = "📋 طلباتك:\n\n"
            keyboard = []
            
            # Show drafts section
            if user_drafts:
                message += "📝 **المسودات الجارية:**\n"
                draft_count = 0
                for draft_id, draft_data in user_drafts.items():
                    draft_count += 1
                    if draft_count > 3:  # Show max 3 drafts
                        break
                    
                    # Create draft summary
                    draft_name = draft_data.get("name", f"مسودة {draft_count}")
                    step = draft_data.get("step", "بداية")
                    
                    step_name = {
                        "select_city": "اختيار المدينة",
                        "select_brand": "اختيار الوكالة", 
                        "select_model": "اختيار الاسم السيارة",
                        "select_year_range": "اختيار العقد",
                        "select_year": "اختيار السنة",
                        "enter_parts": "وصف القطع",
                        "add_media": "إضافة صور"
                    }.get(step, step)
                    
                    button_text = f"📝 {draft_name} - {step_name}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f"switch_draft_{draft_id}")])
                
                if len(user_drafts) > 3:
                    message += f"و {len(user_drafts) - 3} مسودات أخرى...\n"
                message += "\n"
            
            # Show sent requests section
            if requests:
                message += "📤 **الطلبات المُرسلة:**\n"
                for req in requests[:3]:  # Show max 3 requests
                    status_map = {
                        'new': '🟡 بانتظار عروض',
                        'active': '🟢 يتم معالجته', 
                        'accepted': '✅ عرض مقبول',
                        'completed': '🎉 مكتمل',
                        'expired': '🔴 منتهي',
                        'cancelled': '❌ ملغي'
                    }
                    status_emoji = status_map.get(req.status, "❓")
                    button_text = f"{status_emoji} {req.order_id} - {req.brand.name} {req.model.name}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_request_{req.id}")])
                
                if len(requests) > 3:
                    message += f"و {len(requests) - 3} طلبات أخرى...\n"
            
            # If no drafts or requests
            if not user_drafts and not requests:
                message += "لا توجد لديك أي طلبات أو مسودات حتى الآن.\n\nيمكنك إنشاء طلبك الأول:"
            
            # Add action buttons
            keyboard.append([InlineKeyboardButton("🆕 طلب جديد", callback_data="new_request")])
            if user_drafts:
                keyboard.append([InlineKeyboardButton("🗑️ إدارة المسودات", callback_data="draft_manage")])
            keyboard.append([InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing user requests: {e}")
            await query.edit_message_text("حدث خطأ أثناء عرض الطلبات. يرجى المحاولة مرة أخرى.")
    
    
    
    async def start_command_from_callback(self, query, user):
        """Handle /start command from callback query - show main welcome directly"""
        # استخدام نفس دالة الترحيب الرئيسية
        await self.show_main_welcome(query, user)
    
    async def start_new_request(self, query, user):
        """Start new parts request process - create a new draft"""
        # Initialize user states if not exists
        if user.telegram_id not in self.user_states:
            self.user_states[user.telegram_id] = {"drafts": {}, "current_draft": None}
        
        user_state = self.user_states[user.telegram_id]
        
        # Check draft limit
        if len(user_state.get("drafts", {})) >= self.MAX_DRAFTS:
            message = f"""
⚠️ لديك العدد الأقصى من المسودات ({self.MAX_DRAFTS})

يرجى إكمال أو حذف بعض المسودات الموجودة قبل إنشاء مسودة جديدة.
            """
            
            keyboard = [
                [InlineKeyboardButton("📋 إدارة المسودات", callback_data="draft_manage")],
                [InlineKeyboardButton("🔙 العودة", callback_data="my_requests")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            return
        
        # Create new draft
        draft_id = str(uuid.uuid4())[:8]  # Short UUID
        current_time = timezone.now()
        draft_name = f"طلب {current_time.strftime('%m/%d %H:%M')}"
        
        # Initialize drafts dict if not exists
        if "drafts" not in user_state:
            user_state["drafts"] = {}
        
        user_state["drafts"][draft_id] = {
            "id": draft_id,
            "name": draft_name,
            "step": "select_city",
            "request_data": {},
            "created_at": current_time.isoformat()
        }
        user_state["current_draft"] = draft_id
        
        # Start city selection
        cities = await sync_to_async(list)(City.objects.filter(is_active=True))
        
        message = f"""
🆕 **مسودة جديدة:** {draft_name}

🏙️ اختر مدينتك:
        """
        keyboard = []
        
        for city in cities:
            keyboard.append([InlineKeyboardButton(city.name, callback_data=f"city_{city.id}")])
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("📋 طلباتي", callback_data="my_requests"),
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_city_selection(self, query, user, data):
        """Handle city selection"""
        city_id = int(data.split("_")[1])
        city = await sync_to_async(City.objects.get)(id=city_id)
        
        # Get current draft
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft_id = user_state.get("current_draft")
        
        if not current_draft_id or current_draft_id not in user_state.get("drafts", {}):
            await query.edit_message_text("❌ خطأ: لم يتم العثور على المسودة. يرجى بدء طلب جديد.")
            return
        
        current_draft = user_state["drafts"][current_draft_id]
        current_draft["request_data"]["city_id"] = city_id
        current_draft["step"] = "select_brand"
        
        brands = await sync_to_async(list)(Brand.objects.filter(is_active=True).order_by('name'))
        
        # تسجيل عدد الماركات
        logger.info(f"Found {len(brands)} active brands")
        
        # الماركات الأكثر شيوعاً أولاً (لتحسين تجربة المستخدم)
        popular_brands = ['تويوتا', 'هوندا', 'نيسان', 'هيونداي', 'كيا', 'مازدا', 'فورد', 'شيفروليه']
        sorted_brands = []
        
        # إضافة الماركات الشائعة أولاً
        for popular in popular_brands:
            for brand in brands:
                if brand.name == popular:
                    sorted_brands.append(brand)
                    break
        
        # إضافة باقي الماركات
        for brand in brands:
            if brand not in sorted_brands:
                sorted_brands.append(brand)
        
        # عرض أول 10 ماركات فقط مع زر "المزيد"
        display_brands = sorted_brands[:10]
        
        # Get city name safely
        city_name = await sync_to_async(lambda: city.name)()
        
        message = f"""
📝 **{current_draft['name']}**

✅ تم اختيار: {city_name}

🚗 اختر وكالة السيارة (أشهر {len(display_brands)} ماركات):
        """
        keyboard = []
        
        # تجميع الماركات في صفوف من اثنين لتوفير مساحة
        for i in range(0, len(display_brands), 2):
            row = []
            row.append(InlineKeyboardButton(display_brands[i].name, callback_data=f"brand_{display_brands[i].id}"))
            if i + 1 < len(display_brands):
                row.append(InlineKeyboardButton(display_brands[i + 1].name, callback_data=f"brand_{display_brands[i + 1].id}"))
            keyboard.append(row)
        
        # إضافة زر "عرض المزيد" إذا كان هناك ماركات أخرى
        if len(brands) > 10:
            remaining = len(brands) - 10
            keyboard.append([InlineKeyboardButton(f"📄 عرض المزيد ({remaining} وكالة)", callback_data="show_more_brands")])
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("📋 طلباتي", callback_data="my_requests"),
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_brand_selection(self, query, user, data):
        """Handle brand selection"""
        brand_id = int(data.split("_")[1])
        brand = await sync_to_async(Brand.objects.get)(id=brand_id)
        
        # Get current draft
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft_id = user_state.get("current_draft")
        
        if not current_draft_id or current_draft_id not in user_state.get("drafts", {}):
            await query.edit_message_text("❌ خطأ: لم يتم العثور على المسودة. يرجى بدء طلب جديد.")
            return
        
        current_draft = user_state["drafts"][current_draft_id]
        current_draft["request_data"]["brand_id"] = brand_id
        current_draft["step"] = "select_model"
        
        models = await sync_to_async(list)(brand.models.filter(is_active=True))
        
        # Check if brand has models
        if not models:
            # إذا لم تكن هناك اسم السيارةات محددة، انتقل مباشرة لاختيار نطاق السنوات
            current_draft["request_data"]["brand_id"] = brand_id
            current_draft["request_data"]["model_id"] = None  # لا يوجد اسم السيارة محدد
            current_draft["step"] = "select_year_range"
            
            # Get brand name safely
            brand_name = await sync_to_async(lambda: brand.name)()
            
            message = f"""
📝 **{current_draft['name']}**

✅ تم اختيار: {brand_name}
⚠️ لا توجد اسم السيارةات محددة لهذه الوكالة

📅 اختر نطاق سنة الصنع:
            """
            
            keyboard = [
                [InlineKeyboardButton("2020 - 2024", callback_data="year_range_2020_2024")],
                [InlineKeyboardButton("2015 - 2019", callback_data="year_range_2015_2019")],
                [InlineKeyboardButton("2010 - 2014", callback_data="year_range_2010_2014")],
                [InlineKeyboardButton("2005 - 2009", callback_data="year_range_2005_2009")],
                [InlineKeyboardButton("2000 - 2004", callback_data="year_range_2000_2004")],
                [InlineKeyboardButton("1995 - 1999", callback_data="year_range_1995_1999")],
                [InlineKeyboardButton("أقدم من 1995", callback_data="year_range_older")]
            ]
            
            # Add navigation buttons
            keyboard.append([
                InlineKeyboardButton("🔙 اختيار وكالة أخرى", callback_data="select_brand_again"),
                InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            return
        
        # Get brand name safely (reuse if already got)
        if 'brand_name' not in locals():
            brand_name = await sync_to_async(lambda: brand.name)()
        
        message = f"""
📝 **{current_draft['name']}**

✅ تم اختيار: {brand_name}

🚙 اختر اسم السيارة السيارة:
        """
        keyboard = []
        
        for model in models:
            keyboard.append([InlineKeyboardButton(model.name, callback_data=f"model_{model.id}")])
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("📋 طلباتي", callback_data="my_requests"),
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_model_selection(self, query, user, data):
        """Handle model selection"""
        model_id = int(data.split("_")[1])
        model = await sync_to_async(Model.objects.get)(id=model_id)
        
        # Get current draft
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft_id = user_state.get("current_draft")
        
        if not current_draft_id or current_draft_id not in user_state.get("drafts", {}):
            await query.edit_message_text("❌ خطأ: لم يتم العثور على المسودة. يرجى بدء طلب جديد.")
            return
        
        current_draft = user_state["drafts"][current_draft_id]
        current_draft["request_data"]["model_id"] = model_id
        current_draft["step"] = "select_year_range"
        
        # Generate year range options (decades)
        current_year = timezone.now().year
        year_ranges = []
        
        # Create decade ranges
        for start_year in range(current_year - (current_year % 10), current_year - 40, -10):
            end_year = start_year + 9
            if end_year > current_year:
                end_year = current_year
            year_ranges.append((start_year, end_year))
        
        # Get model name safely
        model_name = await sync_to_async(lambda: model.name)()
        
        message = f"""
📝 **{current_draft['name']}**

✅ تم اختيار: {model_name}

📅 اختر نطاق الموديل:
        """
        keyboard = []
        
        for start_year, end_year in year_ranges:
            range_text = f"{start_year} - {end_year}"
            keyboard.append([InlineKeyboardButton(range_text, callback_data=f"year_range_{start_year}_{end_year}")])
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("📋 طلباتي", callback_data="my_requests"),
            InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_year_range_selection(self, query, user, data):
        """Handle year range selection"""
        parts = data.split("_")
        start_year = int(parts[2])
        end_year = int(parts[3])
        
        # Get current draft
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft_id = user_state.get("current_draft")
        
        if not current_draft_id or current_draft_id not in user_state.get("drafts", {}):
            await query.edit_message_text("❌ خطأ: لم يتم العثور على المسودة. يرجى بدء طلب جديد.")
            return
        
        current_draft = user_state["drafts"][current_draft_id]
        current_draft["step"] = "select_year"
        
        # Generate specific years in the range
        years = list(range(end_year, start_year - 1, -1))
        
        message = f"""
📝 **{current_draft['name']}**

✅ تم اختيار نطاق: {start_year} - {end_year}

📅 اختر السنة المحددة:
        """
        keyboard = []
        
        # Show years in rows of 5
        for i in range(0, len(years), 5):
            row = []
            for year in years[i:i+5]:
                row.append(InlineKeyboardButton(str(year), callback_data=f"year_{year}"))
            keyboard.append(row)
        
        # Add navigation buttons
        keyboard.append([
            InlineKeyboardButton("🔙 اختيار نطاق آخر", callback_data="select_brand_again"),
            InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_year_selection(self, query, user, data):
        """Handle year selection"""
        year = int(data.split("_")[1])
        
        # Get current draft
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft_id = user_state.get("current_draft")
        
        if not current_draft_id or current_draft_id not in user_state.get("drafts", {}):
            await query.edit_message_text("❌ خطأ: لم يتم العثور على المسودة. يرجى بدء طلب جديد.")
            return
        
        current_draft = user_state["drafts"][current_draft_id]
        current_draft["request_data"]["year"] = year
        current_draft["step"] = "enter_parts"
        
        message = f"""
📝 **{current_draft['name']}**

✅ تم اختيار: {year}

🔧 الآن اكتب وصف قطع الغيار التي تحتاجها:

مثال: "مصد أمامي، مرآة جانبية يمين، فانوس خلفي"

يمكنك أيضاً التنقل إلى مسودة أخرى أو العودة للقائمة الرئيسية.
        """
        
        keyboard = [
            [InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")],
            [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        # التحقق من حالة المستخدم أولاً
        if not await self.check_user_status(update):
            return  # المستخدم محجوب، تم إرسال رسالة الحجب
        
        user = await self.get_or_create_user(update.effective_user)
        
        if user.telegram_id not in self.user_states:
            await update.message.reply_text("يرجى استخدام /start لبدء المحادثة")
            return
        
        user_state = self.user_states[user.telegram_id]
        
        # Check if user is working on a draft
        current_draft_id = user_state.get("current_draft")
        if current_draft_id and current_draft_id in user_state.get("drafts", {}):
            current_draft = user_state["drafts"][current_draft_id]
            step = current_draft.get("step")
            
            if step == "enter_parts":
                await self.handle_parts_input(update, user, update.message.text)
                return
            elif step == "enter_item_name":
                await self.handle_item_name_input(update, user, update.message.text)
                return
            elif step == "enter_item_unit_price":
                await self.handle_item_name_input(update, user, update.message.text)
                return
        
        # Handle user input steps
        step = user_state.get("step")
        if step == "enter_offer_price":
            await self.handle_offer_price_input(update, user, update.message.text)
        elif step == "enter_offer_delivery_time":
            await self.handle_offer_delivery_time_input(update, user, update.message.text)
        else:
            await update.message.reply_text("لم أفهم. يرجى استخدام الأزرار المتاحة أو العودة إلى القائمة الرئيسية.")
    
    async def handle_parts_input(self, update, user, parts_text):
        """Handle parts description input - now follows the same flow as adding new items"""
        # Get current draft
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft_id = user_state.get("current_draft")
        
        if not current_draft_id or current_draft_id not in user_state.get("drafts", {}):
            await update.message.reply_text("❌ خطأ: لم يتم العثور على المسودة. يرجى بدء طلب جديد.")
            return
        
        current_draft = user_state["drafts"][current_draft_id]
        
        # Initialize items list if not exists
        if "items" not in current_draft["request_data"]:
            current_draft["request_data"]["items"] = []
        
        current_draft["request_data"]["items"].append({
            "name": parts_text,
            "description": "",
            "quantity": 1,  # Fixed to 1
            "unit_price": 0,  # No price from customer
            "currency": "SAR",
            "media_files": []
        })
        
        current_draft["step"] = "manage_items"
        
        message = f"""
✅ تم إضافة القطعة بنجاح!

📝 **{current_draft['name']}**

✅ اسم القطعة: {parts_text}
        """
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قطعة أخرى", callback_data=f"add_item_{current_draft_id}")],
            [InlineKeyboardButton("📋 عرض القطع", callback_data=f"view_items_{current_draft_id}")],
            [InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"confirm_request_{current_draft_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_items_{current_draft_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def show_items_management(self, update, user, draft_id):
        """Show current items and management options"""
        user_state = self.user_states.get(user.telegram_id, {})
        
        # Check if drafts exist
        if "drafts" not in user_state or draft_id not in user_state["drafts"]:
            error_msg = "❌ خطأ: انتهت الجلسة. يرجى بدء طلب جديد بالضغط على /start"
            if hasattr(update, 'callback_query') and update.callback_query:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return
        
        current_draft = user_state["drafts"][draft_id]
        items = current_draft["request_data"].get("items", [])
        
        message = f"📝 **{current_draft['name']}**\n\n"
        
        if items:
            message += "📦 **القطع المطلوبة:**\n"
            for i, item in enumerate(items, 1):
                message += f"{i}️⃣ {item['name']}\n"
            message += "\n"
        else:
            message += "❌ لا توجد قطع مضافة بعد\n\n"
        
        message += "اختر ما تريد فعله:"
        
        keyboard = []
        keyboard.append([InlineKeyboardButton("➕ إضافة قطعة جديدة", callback_data=f"add_item_{draft_id}")])
        
        if items:
            keyboard.append([InlineKeyboardButton("✏️ تعديل قطعة", callback_data=f"edit_item_menu_{draft_id}")])
            keyboard.append([InlineKeyboardButton("🗑️ حذف قطعة", callback_data=f"delete_item_menu_{draft_id}")])
            keyboard.append([InlineKeyboardButton("📸 إضافة صور/فيديو", callback_data=f"add_media_{draft_id}")])
            keyboard.append([InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"confirm_request_{draft_id}")])
        
        keyboard.append([InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def handle_item_name_input(self, update, user, item_name):
        """Handle item name input"""
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft_id = user_state.get("current_draft")
        
        if not current_draft_id or current_draft_id not in user_state.get("drafts", {}):
            await update.message.reply_text("❌ خطأ: لم يتم العثور على المسودة.")
            return
        
        current_draft = user_state["drafts"][current_draft_id]
        
        # Initialize items list if not exists
        if "items" not in current_draft["request_data"]:
            current_draft["request_data"]["items"] = []
        
        current_draft["request_data"]["items"].append({
            "name": item_name,
            "description": "",
            "quantity": 1,  # Fixed to 1
            "unit_price": 0,  # No price from customer
            "currency": "SAR",
            "media_files": []
        })
        
        current_draft["step"] = "manage_items"
        
        message = f"""
✅ تم إضافة القطعة بنجاح!

📝 **{current_draft['name']}**

✅ اسم القطعة: {item_name}
        """
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قطعة أخرى", callback_data=f"add_item_{current_draft_id}")],
            [InlineKeyboardButton("📋 عرض القطع", callback_data=f"view_items_{current_draft_id}")],
            [InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"confirm_request_{current_draft_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_items_{current_draft_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    
    async def handle_item_unit_price_input(self, update, user, price_text):
        """Handle item name input - now directly adds item without price"""
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft_id = user_state.get("current_draft")
        
        if not current_draft_id or current_draft_id not in user_state.get("drafts", {}):
            await update.message.reply_text("❌ خطأ: لم يتم العثور على المسودة.")
            return
        
        current_draft = user_state["drafts"][current_draft_id]
        
        # Add the item to the list without price
        if "items" not in current_draft["request_data"]:
            current_draft["request_data"]["items"] = []
        
        current_draft["request_data"]["items"].append({
            "name": current_draft["temp_item"]["name"],
            "description": current_draft["temp_item"].get("description", ""),
            "quantity": 1,  # Fixed to 1
            "unit_price": 0,  # No price from customer
            "currency": "SAR",
            "media_files": []
        })
        
        # Clear temp item
        current_draft["temp_item"] = {}
        current_draft["step"] = "manage_items"
        
        message = f"""
        ✅ تم إضافة القطعة بنجاح!
        
        📝 **{current_draft['name']}**
        
        ✅ اسم القطعة: {current_draft["request_data"]["items"][-1]["name"]}
        """
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قطعة أخرى", callback_data=f"add_item_{current_draft_id}")],
            [InlineKeyboardButton("📋 عرض القطع", callback_data=f"view_items_{current_draft_id}")],
            [InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"confirm_request_{current_draft_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    
    async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo/video uploads"""
        # التحقق من حالة المستخدم أولاً
        if not await self.check_user_status(update):
            return  # المستخدم محجوب، تم إرسال رسالة الحجب
        
        user = await self.get_or_create_user(update.effective_user)
        
        if user.telegram_id not in self.user_states:
            await update.message.reply_text("يرجى بدء طلب جديد أولاً")
            return
        
        # Get current draft
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft_id = user_state.get("current_draft")
        
        if not current_draft_id or current_draft_id not in user_state.get("drafts", {}):
            await update.message.reply_text("❌ خطأ: لم يتم العثور على المسودة. يرجى بدء طلب جديد.")
            return
        
        current_draft = user_state["drafts"][current_draft_id]
        if current_draft.get("step") != "add_media":
            return
        
        # Store file ID
        if "media_files" not in current_draft["request_data"]:
            current_draft["request_data"]["media_files"] = []
        
        if update.message.photo:
            file_id = update.message.photo[-1].file_id  # Get highest resolution
            current_draft["request_data"]["media_files"].append({"type": "photo", "file_id": file_id})
        elif update.message.video:
            file_id = update.message.video.file_id
            current_draft["request_data"]["media_files"].append({"type": "video", "file_id": file_id})
        
        message = f"""
📝 **{current_draft['name']}**

✅ تم إضافة الملف ({len(current_draft["request_data"]["media_files"])} ملف)

يمكنك:
• ➕ إضافة قطعة جديدة
• 📸 إضافة المزيد من الصور/الفيديو
• 📤 تأكيد الطلب
        """
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قطعة جديدة", callback_data=f"add_item_{current_draft_id}")],
            [InlineKeyboardButton("📸 إضافة المزيد من الصور/الفيديو", callback_data=f"add_media_{current_draft_id}")],
            [InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"confirm_request_{current_draft_id}")],
            [InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    async def confirm_request(self, query, user, data):
        """Confirm and create the request from draft"""
        # Extract draft ID from callback data
        draft_id = data.split("_")[2] if "_" in data else None
        
        user_state = self.user_states.get(user.telegram_id, {})
        
        if not draft_id or draft_id not in user_state.get("drafts", {}):
            await query.edit_message_text("❌ خطأ: لم يتم العثور على المسودة.")
            return
        
        current_draft = user_state["drafts"][draft_id]
        request_data = current_draft["request_data"]
        
        # Validate required fields
        required_fields = ["city_id", "brand_id", "model_id", "year"]
        for field in required_fields:
            if field not in request_data:
                await query.edit_message_text(f"❌ خطأ: حقل {field} مفقود. يرجى إكمال جميع البيانات المطلوبة.")
                return
        
        # Validate that there are items
        items = request_data.get("items", [])
        if not items:
            await query.edit_message_text("❌ خطأ: يجب إضافة قطعة واحدة على الأقل.")
            return
        
        # Create the request
        try:
            # Validate that the referenced objects exist before creating the request
            try:
                city = await sync_to_async(City.objects.get)(id=request_data["city_id"])
            except City.DoesNotExist:
                await query.edit_message_text("""
❌ خطأ في بيانات المدينة

المدينة المحددة غير موجودة في النظام.
يرجى بدء طلب جديد واختيار مدينة صحيحة.
                """)
                return
            
            try:
                brand = await sync_to_async(Brand.objects.get)(id=request_data["brand_id"])
            except Brand.DoesNotExist:
                await query.edit_message_text("""
❌ خطأ في بيانات الوكالة

الوكالة المحددة غير موجودة في النظام.
يرجى بدء طلب جديد واختيار وكالة صحيحة.
                """)
                return
            
            try:
                model = await sync_to_async(Model.objects.get)(id=request_data["model_id"])
            except Model.DoesNotExist:
                await query.edit_message_text("""
❌ خطأ في بيانات اسم السيارة

اسم السيارة المحدد غير موجود في النظام.
يرجى بدء طلب جديد واختيار اسم سيارة صحيح.
                """)
                return
            
            # Create request with empty parts field (legacy)
            request = await sync_to_async(Request.objects.create)(
                user=user,
                city=city,
                brand=brand,
                model=model,
                year=request_data["year"],
                parts="",  # Will be populated by items
                media_files=request_data.get("media_files", [])
            )
            
            # Create individual RequestItem objects
            from .models import RequestItem
            for item_data in items:
                await sync_to_async(RequestItem.objects.create)(
                    request=request,
                    name=item_data["name"],
                    description=item_data.get("description", ""),
                    quantity=item_data.get("quantity", 1),
                    media_files=item_data.get("media_files", [])
                )
            
            # Remove the draft from user states (it's now a real request)
            del user_state["drafts"][draft_id]
            if user_state.get("current_draft") == draft_id:
                user_state["current_draft"] = None
            
            # Build items list for display
            items_text = ""
            for i, item in enumerate(items, 1):
                items_text += f"{i}️⃣ {item['name']}\n"
            
            # Send confirmation to user
            message = f"""
✅ تم إنشاء طلبك بنجاح!

🆔 رقم الطلب: {request.order_id}
🏙️ المدينة: {city.name}  
🚗 السيارة: {brand.name} {model.name} {request_data["year"]}

📦 القطع المطلوبة:
{items_text}
⏰ ينتهي الطلب في: {request.expires_at.strftime('%Y-%m-%d %H:%M')}

📤 تم إرسال طلبك إلى التشاليح المسجّلة في منطقتك.
ستصلك العروض قريباً!

🤔 هل تريد إضافة طلب آخر؟
            """
            
            keyboard = [
                [InlineKeyboardButton("🆕 طلب جديد آخر", callback_data="new_request")],
                [InlineKeyboardButton("📋 مراجعة طلباتي", callback_data="my_requests")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="user_type_client")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup)
            
            # Use workflow service to process confirmed order
            try:
                from .services import workflow_service
                workflow_service.set_telegram_bot(self)
                await workflow_service.process_confirmed_order(request)
                logger.info(f"✅ Successfully processed workflow for request {request.order_id}")
                
            except Exception as workflow_error:
                # Log the workflow error but don't fail the request creation
                logger.error(f"⚠️ Error in workflow processing for request {request.order_id}: {workflow_error}")
                
                # Send additional message to user about potential notification issues
                notification_message = f"""
ℹ️ تنبيه: تم إنشاء طلبك بنجاح برقم {request.order_id}

⚠️ لكن قد تكون هناك مشكلة في إرسال الإشعارات للتشاليح.

📞 يرجى التواصل مع الدعم إذا لم تصل عروض خلال ساعة.

🔄 يمكنك مراجعة حالة طلبك من "📋 طلباتي"
                """
                
                try:
                    await query.message.reply_text(notification_message.strip())
                except:
                    pass  # Don't fail if we can't send this notification
            
        except Exception as e:
            logger.error(f"❌ Error creating request: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # More specific error messages
            error_msg = str(e).lower()
            
            if "city" in error_msg and "does not exist" in error_msg:
                await query.edit_message_text("""
❌ خطأ في بيانات المدينة

المدينة المحددة غير موجودة في النظام.
يرجى بدء طلب جديد واختيار مدينة صحيحة.
                """)
            elif "brand" in error_msg and "does not exist" in error_msg:
                await query.edit_message_text("""
❌ خطأ في بيانات الوكالة

الوكالة المحددة غير موجودة في النظام.
يرجى بدء طلب جديد واختيار وكالة صحيحة.
                """)
            elif "model" in error_msg and "does not exist" in error_msg:
                await query.edit_message_text("""
❌ خطأ في بيانات الاسم السيارة

الاسم السيارة المحدد غير موجود في النظام.
يرجى بدء طلب جديد واختيار اسم السيارة صحيح.
                """)
            elif "database" in error_msg or "connection" in error_msg:
                await query.edit_message_text("""
❌ مشكلة في قاعدة البيانات

يرجى المحاولة مرة أخرى بعد دقائق قليلة.
إذا استمرت المشكلة، يرجى التواصل مع الدعم الفني.
                """)
            else:
                await query.edit_message_text(f"""
❌ حدث خطأ أثناء إنشاء الطلب

تفاصيل الخطأ: خطأ في النظام

يرجى المحاولة مرة أخرى، وإذا استمرت المشكلة، يرجى التواصل مع الدعم الفني.
                """)
    
    async def notify_junkyards(self, request):
        """DEPRECATED: Notify junkyards about new request - now handled by workflow service"""
        logger.warning(f"🚨 DEPRECATED: notify_junkyards called for request {request.order_id}. This should now be handled by workflow service.")
        return  # Don't execute the old logic
        from bot.models import JunkyardStaff
        
        logger.info(f"Starting to notify junkyards for request {request.order_id} in city {request.city.name}")
        
        junkyards = await sync_to_async(list)(
            Junkyard.objects.filter(city=request.city, is_active=True)
        )
        
        logger.info(f"Found {len(junkyards)} active junkyards in {request.city.name}")
        
        if not junkyards:
            logger.warning(f"No active junkyards found in city {request.city.name} for request {request.order_id}")
            return
        
        notifications_sent = 0
        notifications_failed = 0
        
        for junkyard in junkyards:
            try:
                logger.info(f"Processing junkyard: {junkyard.user.first_name} (ID: {junkyard.id})")
                # Get parts description safely in async context
                parts_description = await self.get_request_parts_description(request)
                
                message = f"""
🆕 طلب جديد في منطقتك!

🆔 رقم الطلب: {request.order_id}
👤 العميل: {request.user.first_name}
🚗 السيارة: {request.brand.name} {request.model.name} {request.year}

📦 القطع المطلوبة:
{parts_description}

⏰ ينتهي في: {request.expires_at.strftime('%Y-%m-%d %H:%M')}

💡 يرجى إرسال عرضك موضحًا سعر كل قطعة ومدة التوريد:
{self._format_parts_for_pricing(parts_description)}

⏱️ مدة التوريد المتوقعة: ___ يوم
                """
                
                keyboard = []
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Get all users associated with this junkyard (owner + staff)
                users_to_notify = []
                
                # Add junkyard owner
                if junkyard.user.telegram_id:
                    users_to_notify.append({
                        'user': junkyard.user,
                        'role': 'owner'
                    })
                
                # Add junkyard staff members
                staff_members = await sync_to_async(list)(
                    JunkyardStaff.objects.filter(
                        junkyard=junkyard, 
                        is_active=True,
                        user__telegram_id__isnull=False
                    ).select_related('user')
                )
                
                for staff in staff_members:
                    users_to_notify.append({
                        'user': staff.user,
                        'role': staff.get_role_display()
                    })
                
                # Send notifications to all relevant users
                if not users_to_notify:
                    logger.warning(f"Junkyard {junkyard.id} ({junkyard.user.first_name}) has no users with telegram_id - skipping notification")
                    continue
                
                logger.info(f"Found {len(users_to_notify)} users to notify for junkyard {junkyard.id}")
                
                for user_info in users_to_notify:
                    user = user_info['user']
                    role = user_info['role']
                    
                    try:
                        logger.info(f"Sending notification to {role} {user.first_name} (telegram_id: {user.telegram_id}) for junkyard {junkyard.id}")
                        await self.application.bot.send_message(
                            chat_id=user.telegram_id,
                            text=message,
                            reply_markup=reply_markup
                        )
                        notifications_sent += 1
                        logger.info(f"✅ Successfully sent notification to {user.first_name}")
                    except Exception as e:
                        notifications_failed += 1
                        logger.error(f"❌ Failed to send notification to {user.first_name} (telegram_id: {user.telegram_id}): {e}")
                
                # Send media files to all users if any
                for media in request.media_files:
                    for user_info in users_to_notify:
                        user = user_info['user']
                        try:
                            if media["type"] == "photo":
                                await self.application.bot.send_photo(
                                    chat_id=user.telegram_id,
                                    photo=media["file_id"]
                                )
                            elif media["type"] == "video":
                                await self.application.bot.send_video(
                                    chat_id=user.telegram_id,
                                    video=media["file_id"]
                                )
                        except Exception as e:
                            logger.error(f"Error sending media to {user.first_name}: {e}")
                
            except Exception as e:
                notifications_failed += 1
                logger.error(f"Error notifying junkyard {junkyard.id} ({junkyard.user.first_name}): {e}")
        
        logger.info(f"Notification summary for request {request.order_id}: {notifications_sent} sent, {notifications_failed} failed")
    
    async def handle_draft_action(self, query, user, data):
        """Handle draft management actions"""
        action = data.split("_")[1] if len(data.split("_")) > 1 else ""
        
        if action == "manage":
            await self.show_draft_management(query, user)
        else:
            await query.edit_message_text("❌ إجراء غير صحيح.")
    
    async def show_draft_management(self, query, user):
        """Show draft management interface"""
        user_state = self.user_states.get(user.telegram_id, {})
        user_drafts = user_state.get("drafts", {})
        
        if not user_drafts:
            message = "📝 لا توجد لديك مسودات حالياً."
            keyboard = [
                [InlineKeyboardButton("🆕 طلب جديد", callback_data="new_request")],
                [InlineKeyboardButton("🔙 العودة", callback_data="my_requests")]
            ]
        else:
            message = "📝 **إدارة المسودات:**\n\n"
            keyboard = []
            
            for draft_id, draft_data in user_drafts.items():
                draft_name = draft_data.get("name", "مسودة بدون اسم")
                step = draft_data.get("step", "غير محدد")
                button_text = f"🗑️ حذف: {draft_name}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"delete_draft_{draft_id}")])
            
            keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="my_requests")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def switch_to_draft(self, query, user, data):
        """Switch to a specific draft"""
        draft_id = data.split("_")[2]
        user_state = self.user_states.get(user.telegram_id, {})
        
        if draft_id not in user_state.get("drafts", {}):
            await query.edit_message_text("❌ المسودة غير موجودة.")
            return
        
        # Set as current draft
        user_state["current_draft"] = draft_id
        current_draft = user_state["drafts"][draft_id]
        
        # Resume from current step
        step = current_draft.get("step", "select_city")
        if step == "select_city":
            await self.start_new_request(query, user)
        elif step == "select_brand":
            await self.show_brand_selection(query, user)
        elif step == "enter_parts":
            message = f"""
📝 **{current_draft['name']}**

🔧 اكتب وصف قطع الغيار التي تحتاجها:

مثال: "مصد أمامي، مرآة جانبية يمين، فانوس خلفي"
            """
            keyboard = [
                [InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(f"📝 تم التبديل إلى مسودة: {current_draft['name']}")
    
    async def delete_draft(self, query, user, data):
        """Delete a specific draft"""
        draft_id = data.split("_")[2]
        user_state = self.user_states.get(user.telegram_id, {})
        
        if draft_id not in user_state.get("drafts", {}):
            await query.edit_message_text("❌ المسودة غير موجودة.")
            return
        
        draft_name = user_state["drafts"][draft_id].get("name", "مسودة")
        del user_state["drafts"][draft_id]
        
        # Clear current draft if it was deleted
        if user_state.get("current_draft") == draft_id:
            user_state["current_draft"] = None
        
        message = f"✅ تم حذف المسودة: {draft_name}"
        keyboard = [
            [InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")],
            [InlineKeyboardButton("🗑️ إدارة المسودات", callback_data="draft_manage")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_rating_selection(self, query, user, data):
        """Handle rating selection for junkyard"""
        try:
            rating_parts = data.split("_")
            rating = int(rating_parts[1])
            junkyard_id = int(rating_parts[2])
            
            # Get or create rating
            junkyard = await sync_to_async(Junkyard.objects.get)(id=junkyard_id)
            rating_obj, created = await sync_to_async(JunkyardRating.objects.get_or_create)(
                user=user,
                junkyard=junkyard,
                defaults={'rating': rating}
            )
            
            if not created:
                rating_obj.rating = rating
                await sync_to_async(rating_obj.save)()
            
            message = f"""
⭐ شكراً لك على التقييم!

تم تقييم {junkyard.name} بـ {rating} نجوم
            """
            
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="user_type_client")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error handling rating: {e}")
            await query.edit_message_text("حدث خطأ أثناء التقييم. يرجى المحاولة مرة أخرى.")
    
    async def accept_offer(self, query, user, offer_id):
        """Accept an offer from junkyard with locking mechanism"""
        try:
            offer = await sync_to_async(Offer.objects.select_related('request', 'junkyard__user').get)(
                id=offer_id, request__user=user
            )
            
            # Check if request already has an accepted offer (locking mechanism)
            request = offer.request
            existing_accepted = await sync_to_async(
                request.offers.filter(status='accepted').exists
            )()
            
            if existing_accepted:
                message = """
❌ عذراً، تم قبول عرض آخر لهذا الطلب مسبقاً.

لا يمكن قبول أكثر من عرض واحد للطلب الواحد.
                """
                keyboard = [
                    [InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
                return
            
            # Validate offer has mandatory fields
            if not offer.price:
                message = """
❌ هذا العرض غير مكتمل (يفتقر للسعر).

يرجى التواصل مع التشليح لتحديث العرض.
                """
                keyboard = [
                    [InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(message, reply_markup=reply_markup)
                return
            
            # Use workflow service to process the decision
            from .services import workflow_service
            workflow_service.set_telegram_bot(self)
            await workflow_service.process_customer_offer_decision(offer, 'accept', user)
            
            # Show acceptance confirmation with offer details
            message = f"""
✅ تم قبول العرض!

💰 السعر: {offer.price} ريال
⏰ مدة التوريد: {offer.delivery_time}
🏪 التشليح: {offer.junkyard.user.first_name}
📞 الهاتف: {offer.junkyard.phone}
📍 الموقع: {offer.junkyard.location}

🔒 تم قفل باقي العروض لهذا الطلب.
📱 سيتم التواصل معك قريباً لترتيب التسليم!
            """
            
            keyboard = [
                [InlineKeyboardButton("📋 طلباتي", callback_data="my_requests")],
                [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="user_type_client")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error accepting offer: {e}")
            await query.edit_message_text("حدث خطأ أثناء قبول العرض. يرجى المحاولة مرة أخرى.")
    
    async def reject_offer(self, query, user, offer_id):
        """Reject an offer from junkyard"""
        try:
            offer = await sync_to_async(Offer.objects.get)(id=offer_id, request__user=user)
            
            # Use workflow service to process the decision
            from .services import workflow_service
            workflow_service.set_telegram_bot(self)
            await workflow_service.process_customer_offer_decision(offer, 'reject', user)
            
            # Edit the message to show rejection confirmation
            await query.edit_message_text("❌ تم رفض العرض. سيتم إشعار التشليح.")
            
        except Exception as e:
            logger.error(f"Error rejecting offer: {e}")
            await query.edit_message_text("حدث خطأ أثناء رفض العرض. يرجى المحاولة مرة أخرى.")
    
    async def handle_offer_action(self, query, user, data):
        """Handle offer-related actions"""
        action_parts = data.split("_")
        action = action_parts[1]  # add, accept, reject
        
        if action == "add":
            request_id = int(action_parts[2])
            await self.start_offer_process(query, user, request_id)
        elif action == "accept":
            offer_id = int(action_parts[2])
            await self.accept_offer(query, user, offer_id)
        elif action == "reject":
            offer_id = int(action_parts[2])
            await self.reject_offer(query, user, offer_id)
    
    async def start_offer_process(self, query, user, request_id):
        """Start the offer creation process with mandatory price and delivery time"""
        try:
            # Check if request exists - load related fields to avoid async issues
            try:
                request = await sync_to_async(
                    Request.objects.select_related('brand', 'model', 'city', 'user').get
                )(id=request_id)
            except Request.DoesNotExist:
                logger.error(f"Request {request_id} not found for user {user.telegram_id}")
                await query.edit_message_text("❌ الطلب غير موجود أو انتهت صلاحيته.")
                return
            
            # Check if user is a junkyard
            try:
                junkyard = await sync_to_async(Junkyard.objects.get)(user=user)
            except Junkyard.DoesNotExist:
                logger.error(f"User {user.telegram_id} ({user.first_name}) is not a junkyard but trying to add offer")
                await query.edit_message_text("""
❌ عذراً، لا يمكنك تقديم عروض.

هذا الحساب غير مُسجل كتشليح في النظام.

للحصول على حساب تشليح، يرجى التواصل مع الإدارة.
                """)
                return
            
            # Check if junkyard is active
            if not junkyard.is_active:
                logger.warning(f"Inactive junkyard {junkyard.id} trying to add offer")
                await query.edit_message_text("""
❌ حسابك غير مُفعل حالياً.

يرجى التواصل مع الإدارة لتفعيل حسابك.
                """)
                return
            
            # Check if request is still accepting offers
            if request.status == 'accepted':
                message = """
❌ هذا الطلب تم قبول عرض له مسبقاً.

لا يمكن إضافة عروض جديدة للطلبات المقبولة.
                """
                await query.edit_message_text(message)
                return
            
            # Check if junkyard already has an offer for this request
            existing_offer = await sync_to_async(
                lambda: Offer.objects.filter(request=request, junkyard=junkyard).exists()
            )()
            
            if existing_offer:
                await query.edit_message_text("""
❌ لديك عرض مُسبق لهذا الطلب.

لا يمكن إضافة أكثر من عرض واحد للطلب الواحد.
                """)
                return
            
            self.user_states[user.telegram_id] = {
                "step": "enter_offer_price",
                "request_id": request_id,
                "offer_data": {}
            }
            
            # Get parts description safely in async context
            parts_description = await self.get_request_parts_description(request)
            
            message = f"""
💰 إضافة عرض سعر للطلب: {request.order_id}

🚗 السيارة: {request.brand.name} {request.model.name} {request.year}
📦 القطع المطلوبة:
{parts_description}

📝 **خطوة 1 من 2:**
أرسل السعر المطلوب (بالريال السعودي فقط):

مثال: 150
            """
            
            await query.edit_message_text(message)
            logger.info(f"✅ Started offer process for junkyard {junkyard.id} on request {request_id}")
            
        except Exception as e:
            logger.error(f"❌ Error starting offer process for user {user.telegram_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # More specific error handling
            error_str = str(e).lower()
            
            if "does not exist" in error_str and "junkyard" in error_str:
                error_message = """
❌ حسابك غير مُسجل كتشليح في النظام

يرجى التواصل مع الإدارة لتسجيل حسابك.

📞 خدمة العملاء متاحة لمساعدتك.
                """
            elif "not active" in error_str or "inactive" in error_str:
                error_message = """
⚠️ حسابك غير مُفعل حالياً

يرجى التواصل مع الإدارة لتفعيل حسابك.

📞 سيتم تفعيلك خلال دقائق قليلة.
                """
            elif "telegram_id" in error_str or "chat" in error_str:
                error_message = """
🔧 مشكلة في إعدادات حسابك

الحل السريع:
1. اضغط /start مرة أخرى
2. جرب الضغط على "إضافة عرض" مرة أخرى

إذا لم يعمل، يرجى التواصل مع الدعم.
                """
            else:
                error_message = f"""
⚠️ حدث خطأ مؤقت في النظام

الحل السريع:
1. اضغط /start 
2. جرب مرة أخرى

إذا استمر الخطأ، يرجى التواصل مع الدعم الفني.

🔧 كود الخطأ: {str(e)[:50]}...
                """
            
            # Only edit message if it's different from current content
            try:
                await query.edit_message_text(error_message.strip())
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    # Message is already the same, just answer the callback
                    await query.answer("حدث خطأ، يرجى المحاولة مرة أخرى")
                else:
                    # Different error, re-raise it
                    raise edit_error
    
    async def handle_offer_price_input(self, update, user, price_text):
        """Handle offer price input"""
        try:
            # Validate price is numeric
            price = float(price_text.strip())
            if price <= 0:
                await update.message.reply_text("❌ يرجى إدخال سعر صحيح أكبر من صفر.")
                return
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال سعر صحيح بالأرقام فقط.")
            return
        
        user_state = self.user_states[user.telegram_id]
        user_state["offer_data"]["price"] = price
        user_state["step"] = "enter_offer_delivery_time"
        
        request_id = user_state["request_id"]
        request = await sync_to_async(Request.objects.get)(id=request_id)
        
        message = f"""
💰 عرض سعر للطلب: {request.order_id}

✅ السعر: {price} ريال

📝 **خطوة 2 من 2:**
أرسل ملاحظات إضافية (اختياري):

        مثال: القطعة في حالة ممتازة
        مثال: متوفر فوراً
        مثال: يحتاج إصلاح بسيط
        """
        
        await update.message.reply_text(message)
    
    async def handle_offer_delivery_time_input(self, update, user, delivery_time_text):
        """Handle offer delivery time input and create offer"""
        delivery_time = delivery_time_text.strip()
        
        if len(delivery_time) < 2:
            await update.message.reply_text("❌ يرجى إدخال مدة توريد واضحة.")
            return
        
        user_state = self.user_states[user.telegram_id]
        request_id = user_state["request_id"]
        offer_data = user_state["offer_data"]
        offer_data["delivery_time"] = delivery_time
        
        try:
            # Load related fields to avoid async issues
            request = await sync_to_async(
                Request.objects.select_related('brand', 'model', 'city', 'user').get
            )(id=request_id)
            junkyard = await sync_to_async(
                Junkyard.objects.select_related('user').get
            )(user=user)
            
            # Create the offer using a proper async function
            def create_offer():
                return Offer.objects.create(
                    request=request,
                    junkyard=junkyard,
                    price=offer_data["price"],
                    delivery_time=delivery_time,
                    status='pending'
                )
            
            offer = await sync_to_async(create_offer)()
            
            # Clear user state
            del self.user_states[user.telegram_id]
            
            message = f"""
✅ تم إرسال عرضك بنجاح!

💰 السعر: {offer_data["price"]} ريال
⏰ مدة التوريد: {delivery_time}
📋 رقم الطلب: {request.order_id}

📱 سيتم إشعار العميل بعرضك وسيتواصل معك في حالة الموافقة.
            """
            
            await update.message.reply_text(message)
            
            # Use workflow service to process new offer
            from .services import workflow_service
            workflow_service.set_telegram_bot(self)
            await workflow_service.process_junkyard_offer(offer)
            
        except Exception as e:
            logger.error(f"Error creating offer: {e}")
            await update.message.reply_text("حدث خطأ أثناء إنشاء العرض. يرجى المحاولة مرة أخرى.")
    
    async def notify_junkyard_acceptance(self, offer):
        """Notify junkyard about offer acceptance"""
        try:
            message = f"""
🎉 تهانينا! تم قبول عرضك!

🆔 رقم الطلب: {offer.request.order_id}
👤 العميل: {offer.request.user.first_name}
💰 السعر المتفق عليه: {offer.price} ريال
⏰ مدة التوريد: {offer.delivery_time}

📱 يرجى التواصل مع العميل لترتيب التسليم.
            """
            
            await self.application.bot.send_message(
                chat_id=offer.junkyard.user.telegram_id,
                text=message
            )
            
        except Exception as e:
            logger.error(f"Error notifying junkyard about acceptance: {e}")
    
    async def notify_customer_new_offer(self, offer):
        """Notify customer about new offer"""
        try:
            message = f"""
🆕 عرض جديد وصل لطلبك!

🆔 رقم الطلب: {offer.request.order_id}
🏪 التشليح: {offer.junkyard.user.first_name}
💰 السعر: {offer.price} ريال
⏰ مدة التوريد: {offer.delivery_time}

اضغط لعرض التفاصيل واتخاذ قرارك:
            """
            
            keyboard = [
                [InlineKeyboardButton("👀 عرض التفاصيل", callback_data=f"view_request_{offer.request.id}")],
                [InlineKeyboardButton("📋 جميع طلباتي", callback_data="my_requests")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.application.bot.send_message(
                chat_id=offer.request.user.telegram_id,
                text=message,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error notifying customer about new offer: {e}")
    
    async def show_offer_details(self, query, user, data):
        """Show detailed view of a specific offer"""
        try:
            offer_id = int(data.split("_")[2])
            offer = await sync_to_async(Offer.objects.select_related('request', 'junkyard__user').get)(
                id=offer_id, request__user=user
            )
            
            status_map = {
                'pending': '⏳ في الانتظار', 
                'accepted': '✅ مقبول', 
                'rejected': '❌ مرفوض', 
                'locked': '🔒 مقفل'
            }
            status_display = status_map.get(offer.status, offer.status)
            
            message = f"""
💰 **تفاصيل العرض**

🆔 رقم الطلب: {offer.request.order_id}
🏪 التشليح: {offer.junkyard.user.first_name}
💰 السعر: {offer.price} ريال
⏰ مدة التوريد: {offer.delivery_time}
📊 الحالة: {status_display}
📞 الهاتف: {offer.junkyard.phone}
📍 الموقع: {offer.junkyard.location}
            """
            
            if offer.notes:
                message += f"\n📝 ملاحظات: {offer.notes}"
            
            keyboard = []
            
            if offer.status == 'pending':
                keyboard.extend([
                    [InlineKeyboardButton("✅ قبول العرض", callback_data=f"offer_accept_{offer.id}")],
                    [InlineKeyboardButton("❌ رفض العرض", callback_data=f"offer_reject_{offer.id}")]
                ])
            
            keyboard.extend([
                [InlineKeyboardButton("🔙 العودة للطلب", callback_data=f"view_request_{offer.request.id}")],
                [InlineKeyboardButton("📋 جميع طلباتي", callback_data="my_requests")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error showing offer details: {e}")
            await query.edit_message_text("حدث خطأ أثناء عرض تفاصيل العرض.")

    async def handle_junkyard_name(self, update, user, name_text):
        """Handle junkyard name input"""
        if len(name_text.strip()) < 2:
            await update.message.reply_text("يرجى إدخال اسم صحيح للمخزن (أكثر من حرفين)")
            return
        
        # Save name to user_states
        if user.telegram_id not in self.user_states:
            self.user_states[user.telegram_id] = {}
        
        if "junkyard_data" not in self.user_states[user.telegram_id]:
            self.user_states[user.telegram_id]["junkyard_data"] = {}
        
        self.user_states[user.telegram_id]["junkyard_data"]["name"] = name_text.strip()
        self.user_states[user.telegram_id]["step"] = "junkyard_phone"
        
        message = f"""
✅ تم حفظ اسم المخزن: {name_text.strip()}

📱 الآن أرسل رقم هاتف المخزن:

مثال: 0501234567 أو +966501234567
        """
        
        await update.message.reply_text(message)

    async def handle_junkyard_phone(self, update, user, phone_text):
        """Handle junkyard phone input"""
        # Basic phone validation
        phone_clean = phone_text.strip().replace(' ', '').replace('-', '')
        
        if len(phone_clean) < 9 or not any(char.isdigit() for char in phone_clean):
            await update.message.reply_text("يرجى إدخال رقم هاتف صحيح")
            return
        
        # Save phone to user_states
        self.user_states[user.telegram_id]["junkyard_data"]["phone"] = phone_clean
        self.user_states[user.telegram_id]["step"] = "junkyard_city"
        
        message = f"""
✅ تم حفظ رقم الهاتف: {phone_clean}

🏙️ الآن اختر مدينة المخزن:
        """
        
        # Get cities and show as buttons
        cities = await sync_to_async(list)(City.objects.filter(is_active=True))
        keyboard = []
        
        for city in cities:
            keyboard.append([InlineKeyboardButton(city.name, callback_data=f"junkyard_city_{city.id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message, reply_markup=reply_markup)

    async def handle_junkyard_city(self, query, user, data):
        """Handle junkyard city selection"""
        city_id = int(data.split("_")[2])
        city = await sync_to_async(City.objects.get)(id=city_id)
        
        self.user_states[user.telegram_id]["junkyard_data"]["city_id"] = city_id
        self.user_states[user.telegram_id]["step"] = "junkyard_location"
        
        message = f"""
✅ تم اختيار مدينة المخزن: {city.name}

📍 ما هو عنوان المخزن أو رابط عنوان المخزن على الخريطة؟

يمكنك إرسال:
• العنوان التفصيلي: مثل "حي النهضة - شارع الملك فهد - بجانب محطة البنزين"
• رابط خرائط جوجل
• إحداثيات GPS
        """
        
        await query.edit_message_text(message)

    async def handle_junkyard_location(self, update, user, location_text):
        """Handle junkyard location input and complete registration"""
        if len(location_text.strip()) < 10:
            await update.message.reply_text("يرجى إدخال عنوان واضح ومفصل أكثر")
            return
        
        try:
            # Check if user already has a junkyard (double check)
            existing_junkyard = await sync_to_async(Junkyard.objects.filter(user=user).first)()
            if existing_junkyard:
                await update.message.reply_text("❌ لديك مخزن مسجل بالفعل! استخدم /start للعودة للقائمة الرئيسية.")
                # Clear user state
                if user.telegram_id in self.user_states:
                    del self.user_states[user.telegram_id]
                return
            
            # Get junkyard data from user_states
            junkyard_data = self.user_states[user.telegram_id]["junkyard_data"]
            
            # Update user type to junkyard
            user.user_type = 'junkyard'
            user.first_name = junkyard_data["name"]
            await sync_to_async(user.save)()
            
            # Get the selected city
            city = await sync_to_async(City.objects.get)(id=junkyard_data["city_id"])
            
            junkyard = await sync_to_async(Junkyard.objects.create)(
                user=user,
                phone=junkyard_data["phone"],
                city=city,
                location=location_text.strip()
            )
            
            # Clear user state
            if user.telegram_id in self.user_states:
                del self.user_states[user.telegram_id]
            
            message = f"""
🎉 تم تسجيل المخزن بنجاح!

📋 بيانات المخزن:
• الاسم: {junkyard_data["name"]}
• الهاتف: {junkyard_data["phone"]}
• المدينة: {city.name}
• العنوان: {location_text.strip()}

✅ يمكنك الآن استقبال طلبات العملاء والرد عليها بعروض أسعار.

🔄 للعودة للقائمة الرئيسية استخدم /start
            """
            
            await update.message.reply_text(message)
            
            logger.info(f"New junkyard registered: {junkyard_data['name']} - {user.telegram_id}")
            
        except Exception as e:
            logger.error(f"Error creating junkyard: {e}")
            # Clear user state on error
            if user.telegram_id in self.user_states:
                del self.user_states[user.telegram_id]
            
            if "duplicate key value violates unique constraint" in str(e):
                await update.message.reply_text("❌ لديك مخزن مسجل بالفعل! استخدم /start للعودة للقائمة الرئيسية.")
            else:
                await update.message.reply_text("حدث خطأ أثناء التسجيل. يرجى المحاولة مرة أخرى لاحقاً.")

    # New Item Management Callback Handlers
    async def handle_add_item(self, query, user, data):
        """Handle add item button"""
        draft_id = data.split("_")[2]
        user_state = self.user_states.get(user.telegram_id, {})
        
        if draft_id not in user_state.get("drafts", {}):
            await query.edit_message_text("❌ خطأ: لم يتم العثور على المسودة.")
            return
        
        current_draft = user_state["drafts"][draft_id]
        current_draft["step"] = "enter_item_name"
        
        message = f"""
📝 **{current_draft['name']}**

➕ إضافة قطعة جديدة

📝 أدخل اسم القطعة المطلوبة:
مثال: "مقص شباك الواصل", "فلتر زيت", "كفر شنطة"
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_items_{draft_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_manage_items(self, query, user, data):
        """Handle manage items callback"""
        draft_id = data.split("_")[2]
        await self.show_items_management(query, user, draft_id)
    
    async def handle_view_items(self, query, user, data):
        """Handle view items callback"""
        draft_id = data.split("_")[2]
        user_state = self.user_states.get(user.telegram_id, {})
        
        if draft_id not in user_state.get("drafts", {}):
            await query.edit_message_text("❌ خطأ: لم يتم العثور على المسودة.")
            return
        
        draft = user_state["drafts"][draft_id]
        items = draft.get("request_data", {}).get("items", [])
        
        if not items:
            message = """
            📋 **عرض القطع**
            
            لا توجد قطع مضافة بعد.
            """
            keyboard = [
                [InlineKeyboardButton("➕ إضافة قطعة", callback_data=f"add_item_{draft_id}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_items_{draft_id}")]
            ]
        else:
            message = f"""
            📋 **عرض القطع ({len(items)} قطعة)**
            
            """
            
            for i, item in enumerate(items, 1):
                message += f"""
            **{i}. {item['name']}**
            """
                if item.get("description"):
                    message += f"📝 الوصف: {item['description']}\n"
                message += "\n"
            
            
            keyboard = [
                [InlineKeyboardButton("➕ إضافة قطعة أخرى", callback_data=f"add_item_{draft_id}")],
                [InlineKeyboardButton("✏️ تعديل القطع", callback_data=f"manage_items_{draft_id}")],
                [InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"confirm_request_{draft_id}")],
                [InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_items_{draft_id}")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_skip_description(self, query, user, data):
        """Handle skip description callback"""
        draft_id = data.split("_")[2]
        user_state = self.user_states.get(user.telegram_id, {})
        
        # Check if drafts exist
        if "drafts" not in user_state or draft_id not in user_state["drafts"]:
            await query.edit_message_text("❌ خطأ: انتهت الجلسة. يرجى بدء طلب جديد بالضغط على /start")
            return
        
        current_draft = user_state["drafts"][draft_id]
        
        # Check if temp_item exists
        if "temp_item" not in current_draft:
            await query.edit_message_text("❌ خطأ: بيانات القطعة مفقودة. يرجى بدء إضافة قطعة جديدة.")
            return
        
        current_draft["temp_item"]["description"] = ""
        current_draft["step"] = "enter_item_quantity"
        
        message = f"""
📝 **{current_draft['name']}**

✅ اسم القطعة: {current_draft["temp_item"]["name"]}

🔢 الكمية محددة على 1 قطعة (لا يمكن تغييرها):
        """
        
        keyboard = [
            [InlineKeyboardButton("1️⃣", callback_data=f"set_quantity_1_{draft_id}")],
            [InlineKeyboardButton("2️⃣", callback_data=f"set_quantity_2_{draft_id}")],
            [InlineKeyboardButton("3️⃣", callback_data=f"set_quantity_3_{draft_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_items_{draft_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_set_quantity(self, query, user, data):
        """Handle quantity button callbacks"""
        parts = data.split("_")
        quantity = int(parts[2])
        draft_id = parts[3]
        
        user_state = self.user_states.get(user.telegram_id, {})
        
        # Check if drafts exist
        if "drafts" not in user_state or draft_id not in user_state["drafts"]:
            await query.edit_message_text("❌ خطأ: انتهت الجلسة. يرجى بدء طلب جديد بالضغط على /start")
            return
        
        current_draft = user_state["drafts"][draft_id]
        
        # Check if temp_item exists
        if "temp_item" not in current_draft:
            await query.edit_message_text("❌ خطأ: بيانات القطعة مفقودة. يرجى بدء إضافة قطعة جديدة.")
            return
        
        # Add the item to the list
        if "items" not in current_draft["request_data"]:
            current_draft["request_data"]["items"] = []
        
        current_draft["request_data"]["items"].append({
            "name": current_draft["temp_item"]["name"],
            "description": current_draft["temp_item"].get("description", ""),
            "quantity": quantity,
            "media_files": []
        })
        
        # Clean up temporary item data
        del current_draft["temp_item"]
        current_draft["step"] = "manage_items"
        
        await query.answer("✅ تم إضافة القطعة بنجاح!")
        await self.show_items_management(query, user, draft_id)
    
    async def handle_edit_item_menu(self, query, user, data):
        """Show edit item menu"""
        draft_id = data.split("_")[3]
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft = user_state["drafts"][draft_id]
        items = current_draft["request_data"].get("items", [])
        
        if not items:
            await query.answer("❌ لا توجد قطع لتعديلها")
            return
        
        message = f"📝 **{current_draft['name']}**\n\n"
        message += "✏️ **اختر القطعة المراد تعديلها:**\n\n"
        
        keyboard = []
        for i, item in enumerate(items):
            quantity_text = f" (x{item['quantity']})" if item.get('quantity', 1) > 1 else ""
            button_text = f"{i+1}. {item['name']}{quantity_text}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"edit_item_{draft_id}_{i}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_items_{draft_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_delete_item_menu(self, query, user, data):
        """Show delete item menu"""
        draft_id = data.split("_")[3]
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft = user_state["drafts"][draft_id]
        items = current_draft["request_data"].get("items", [])
        
        if not items:
            await query.answer("❌ لا توجد قطع لحذفها")
            return
        
        message = f"📝 **{current_draft['name']}**\n\n"
        message += "🗑️ **اختر القطعة المراد حذفها:**\n\n"
        
        keyboard = []
        for i, item in enumerate(items):
            quantity_text = f" (x{item['quantity']})" if item.get('quantity', 1) > 1 else ""
            button_text = f"❌ {i+1}. {item['name']}{quantity_text}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"delete_item_{draft_id}_{i}")])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_items_{draft_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_edit_item(self, query, user, data):
        """Handle edit specific item"""
        parts = data.split("_")
        draft_id = parts[2]
        item_index = int(parts[3])
        
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft = user_state["drafts"][draft_id]
        items = current_draft["request_data"].get("items", [])
        
        if item_index >= len(items):
            await query.answer("❌ القطعة غير موجودة")
            return
        
        item = items[item_index]
        
        message = f"""
📝 **{current_draft['name']}**

✏️ **تعديل القطعة:**
🔧 الاسم: {item['name']}
💭 الوصف: {item.get('description', 'لا يوجد')}
🔢 الكمية: {item.get('quantity', 1)}

ماذا تريد تعديل؟
        """
        
        keyboard = [
            [InlineKeyboardButton("📝 تعديل الاسم", callback_data=f"edit_name_{draft_id}_{item_index}")],
            [InlineKeyboardButton("💭 تعديل الوصف", callback_data=f"edit_desc_{draft_id}_{item_index}")],
            [InlineKeyboardButton("🔢 تعديل الكمية", callback_data=f"edit_qty_{draft_id}_{item_index}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"edit_item_menu_{draft_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)
    
    async def handle_delete_item(self, query, user, data):
        """Handle delete specific item"""
        parts = data.split("_")
        draft_id = parts[2]
        item_index = int(parts[3])
        
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft = user_state["drafts"][draft_id]
        items = current_draft["request_data"].get("items", [])
        
        if item_index >= len(items):
            await query.answer("❌ القطعة غير موجودة")
            return
        
        # Remove the item
        deleted_item = items.pop(item_index)
        
        await query.answer(f"✅ تم حذف '{deleted_item['name']}' بنجاح")
        await self.show_items_management(query, user, draft_id)
    
    async def handle_add_media_callback(self, query, user, data):
        """Handle add media callback"""
        draft_id = data.split("_")[2]
        user_state = self.user_states.get(user.telegram_id, {})
        current_draft = user_state["drafts"][draft_id]
        current_draft["step"] = "add_media"
        
        message = f"""
📝 **{current_draft['name']}**

📸 أرسل صور أو فيديو للقطع المطلوبة (اختياري)

يمكنك إرسال:
• صور للقطع المطلوبة
• فيديو يوضح القطع
• عدة صور/فيديوهات

عند الانتهاء، اختر:
• ➕ إضافة قطعة جديدة
• 📤 تأكيد الطلب
        """
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة قطعة جديدة", callback_data=f"add_item_{draft_id}")],
            [InlineKeyboardButton("📸 إضافة المزيد من الصور/الفيديو", callback_data=f"add_media_{draft_id}")],
            [InlineKeyboardButton("✅ تأكيد الطلب", callback_data=f"confirm_request_{draft_id}")],
            [InlineKeyboardButton("🔙 رجوع", callback_data=f"manage_items_{draft_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup)

    async def handle_chat_with_customer(self, query, user, data):
        """Handle chat with customer button for junkyards"""
        try:
            # Extract customer_id and request_id from callback data
            parts = data.split("_")
            customer_id = int(parts[3])
            request_id = int(parts[4])
            
            # Get customer and request details safely
            customer = await sync_to_async(User.objects.get)(id=customer_id)
            request = await sync_to_async(Request.objects.select_related('brand', 'model', 'city').get)(id=request_id)
            
            # Get customer details safely
            customer_name = await sync_to_async(lambda: customer.first_name)()
            customer_phone = await sync_to_async(lambda: customer.phone_number)()
            
            # Get request details safely
            order_id = await sync_to_async(lambda: request.order_id)()
            brand_name = await sync_to_async(lambda: request.brand.name)()
            model_name = await sync_to_async(lambda: request.model.name)()
            year = await sync_to_async(lambda: request.year)()
            city_name = await sync_to_async(lambda: request.city.name)()
            
            message = f"""
💬 **معلومات التواصل مع العميل**

👤 **اسم العميل**: {customer_name}
📱 **رقم الهاتف**: {customer_phone if customer_phone else 'غير متوفر'}
🆔 **رقم الطلب**: {order_id}
🚗 **السيارة**: {brand_name} {model_name} {year}
🏙️ **المدينة**: {city_name}

📞 **يمكنك التواصل مع العميل مباشرة عبر:**
• رقم الهاتف: {customer_phone if customer_phone else 'غير متوفر'}
• أو انتظار رسالة من العميل

💡 **نصيحة**: تأكد من التواصل مع العميل لتنسيق موعد التسليم
            """
            
            keyboard = [
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in handle_chat_with_customer: {e}")
            await query.edit_message_text("❌ حدث خطأ في عرض معلومات العميل")

    async def handle_view_all_offers(self, query, user, data):
        """Handle view all offers button for customers"""
        try:
            # Extract request_id from callback data
            request_id = int(data.split("_")[3])
            
            # Get request and all offers
            request = await sync_to_async(Request.objects.select_related('brand', 'model', 'city').get)(id=request_id, user=user)
            offers = await sync_to_async(list)(
                request.offers.select_related('junkyard__user').order_by('-created_at')
            )
            
            if not offers:
                message = "❌ لا توجد عروض متاحة لهذا الطلب"
                keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]]
            else:
                # Get request details safely
                order_id = await sync_to_async(lambda: request.order_id)()
                brand_name = await sync_to_async(lambda: request.brand.name)()
                model_name = await sync_to_async(lambda: request.model.name)()
                year = await sync_to_async(lambda: request.year)()
                
                message = f"💰 **جميع العروض لطلبك**\n\n"
                message += f"🆔 رقم الطلب: {order_id}\n"
                message += f"🚗 السيارة: {brand_name} {model_name} {year}\n\n"
                
                for i, offer in enumerate(offers, 1):
                    # Get offer details safely
                    offer_status = await sync_to_async(lambda: offer.status)()
                    junkyard_name = await sync_to_async(lambda: offer.junkyard.user.first_name)()
                    offer_price = await sync_to_async(lambda: offer.price)()
                    average_rating = await sync_to_async(lambda: offer.junkyard.average_rating)()
                    location = await sync_to_async(lambda: offer.junkyard.location)()
                    delivery_time = await sync_to_async(lambda: offer.delivery_time)()
                    created_at = await sync_to_async(lambda: offer.created_at)()
                    
                    status_emoji = "✅" if offer_status == "accepted" else "⏳" if offer_status == "pending" else "❌"
                    message += f"{status_emoji} **العرض {i}**\n"
                    message += f"🏪 التشليح: {junkyard_name}\n"
                    message += f"💰 السعر: {offer_price} ريال\n"
                    message += f"⭐ التقييم: {average_rating:.1f}/5\n"
                    message += f"📍 الموقع: {location}\n"
                    if delivery_time:
                        message += f"🚚 مدة التوريد: {delivery_time}\n"
                    message += f"📅 تاريخ العرض: {created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
                
                keyboard = [
                    [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in handle_view_all_offers: {e}")
            await query.edit_message_text("❌ حدث خطأ في عرض العروض")


# Initialize bot instance
telegram_bot = TelegramBot()

