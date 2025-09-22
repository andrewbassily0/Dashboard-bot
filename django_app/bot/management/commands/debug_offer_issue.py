"""
Management command to debug offer submission issues for junkyards
"""

from django.core.management.base import BaseCommand
from bot.models import Junkyard, User, Request
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Debug offer submission issues for a specific junkyard'

    def add_arguments(self, parser):
        parser.add_argument(
            '--telegram-id',
            type=int,
            help='Telegram ID of the junkyard user'
        )
        parser.add_argument(
            '--junkyard-id', 
            type=int,
            help='Junkyard ID from database'
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Username of the junkyard'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 تشخيص مشاكل تقديم العروض'))
        self.stdout.write('=' * 60)
        
        # Find the junkyard
        junkyard = None
        user = None
        
        if options['telegram_id']:
            try:
                user = User.objects.get(telegram_id=options['telegram_id'])
                self.stdout.write(f'✅ وُجد المستخدم بـ Telegram ID: {options["telegram_id"]}')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ لا يوجد مستخدم بـ Telegram ID: {options["telegram_id"]}'))
                return
        
        elif options['junkyard_id']:
            try:
                junkyard = Junkyard.objects.get(id=options['junkyard_id'])
                user = junkyard.user
                self.stdout.write(f'✅ وُجد التشليح بـ ID: {options["junkyard_id"]}')
            except Junkyard.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ لا يوجد تشليح بـ ID: {options["junkyard_id"]}'))
                return
        
        elif options['username']:
            try:
                user = User.objects.get(username=options['username'])
                self.stdout.write(f'✅ وُجد المستخدم بـ Username: {options["username"]}')
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ لا يوجد مستخدم بـ Username: {options["username"]}'))
                return
        
        else:
            self.stdout.write(self.style.ERROR('❌ يجب تحديد telegram-id أو junkyard-id أو username'))
            return
        
        # Get junkyard if not found yet
        if not junkyard and user:
            try:
                junkyard = Junkyard.objects.get(user=user)
            except Junkyard.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ المستخدم {user.username} ليس مرتبط بتشليح'))
                return
        
        # Display comprehensive info
        self.display_user_info(user)
        self.display_junkyard_info(junkyard)
        self.display_recent_activity(junkyard)
        self.display_system_checks(user, junkyard)
        self.display_recommendations(user, junkyard)

    def display_user_info(self, user):
        self.stdout.write('\n📊 معلومات المستخدم:')
        self.stdout.write('-' * 40)
        self.stdout.write(f'   الاسم: {user.first_name} {user.last_name}')
        self.stdout.write(f'   Username: {user.username}')
        self.stdout.write(f'   Telegram ID: {user.telegram_id}')
        self.stdout.write(f'   نوع المستخدم: {user.user_type}')
        self.stdout.write(f'   نشط: {user.is_active}')
        self.stdout.write(f'   تاريخ الإنشاء: {user.created_at}')

    def display_junkyard_info(self, junkyard):
        self.stdout.write('\n🏪 معلومات التشليح:')
        self.stdout.write('-' * 40)
        self.stdout.write(f'   ID: {junkyard.id}')
        self.stdout.write(f'   المدينة: {junkyard.city.name}')
        self.stdout.write(f'   الهاتف: {junkyard.phone}')
        self.stdout.write(f'   نشط: {junkyard.is_active}')
        self.stdout.write(f'   معتمد: {junkyard.is_verified}')
        self.stdout.write(f'   الموقع: {junkyard.location}')
        self.stdout.write(f'   تاريخ الإنشاء: {junkyard.created_at}')

    def display_recent_activity(self, junkyard):
        self.stdout.write('\n📈 النشاط الحديث:')
        self.stdout.write('-' * 40)
        
        # Offers in last 7 days
        last_week = timezone.now() - timedelta(days=7)
        recent_offers = junkyard.offers.filter(created_at__gte=last_week).count()
        total_offers = junkyard.offers.count()
        
        self.stdout.write(f'   إجمالي العروض: {total_offers}')
        self.stdout.write(f'   عروض الأسبوع الماضي: {recent_offers}')
        
        # Recent requests in same city
        recent_requests = Request.objects.filter(
            city=junkyard.city,
            created_at__gte=last_week,
            status__in=['new', 'active']
        ).count()
        
        self.stdout.write(f'   طلبات حديثة في {junkyard.city.name}: {recent_requests}')
        
        # Last offer
        last_offer = junkyard.offers.order_by('-created_at').first()
        if last_offer:
            self.stdout.write(f'   آخر عرض: {last_offer.created_at} (طلب {last_offer.request.order_id})')
        else:
            self.stdout.write(f'   آخر عرض: لم يقدم عروض بعد')

    def display_system_checks(self, user, junkyard):
        self.stdout.write('\n🔍 فحص النظام:')
        self.stdout.write('-' * 40)
        
        issues = []
        warnings = []
        success = []
        
        # Check telegram_id
        if not user.telegram_id:
            issues.append("❌ لا يوجد telegram_id")
        else:
            success.append(f"✅ telegram_id: {user.telegram_id}")
        
        # Check user type
        if user.user_type != 'junkyard':
            issues.append(f"❌ نوع المستخدم خاطئ: {user.user_type}")
        else:
            success.append("✅ نوع المستخدم صحيح")
        
        # Check junkyard active
        if not junkyard.is_active:
            issues.append("❌ التشليح غير مُفعل")
        else:
            success.append("✅ التشليح مُفعل")
        
        # Check city
        if not junkyard.city.is_active:
            issues.append(f"❌ المدينة {junkyard.city.name} غير مُفعلة")
        else:
            success.append(f"✅ المدينة {junkyard.city.name} مُفعلة")
        
        # Display results
        for item in success:
            self.stdout.write(f'   {item}')
        
        for item in warnings:
            self.stdout.write(self.style.WARNING(f'   {item}'))
        
        for item in issues:
            self.stdout.write(self.style.ERROR(f'   {item}'))

    def display_recommendations(self, user, junkyard):
        self.stdout.write('\n💡 التوصيات:')
        self.stdout.write('-' * 40)
        
        recommendations = []
        
        if not user.telegram_id:
            recommendations.append("1. إضافة telegram_id صحيح للمستخدم")
        
        if user.user_type != 'junkyard':
            recommendations.append(f"2. تغيير نوع المستخدم من '{user.user_type}' إلى 'junkyard'")
        
        if not junkyard.is_active:
            recommendations.append("3. تفعيل التشليح من الداشبورد")
        
        if not junkyard.city.is_active:
            recommendations.append(f"4. تفعيل المدينة {junkyard.city.name}")
        
        if user.telegram_id:
            recommendations.append("5. التأكد من أن التشليح أرسل /start للبوت")
            recommendations.append("6. اختبار الإشعارات من الداشبورد")
        
        if not recommendations:
            self.stdout.write(self.style.SUCCESS('   ✅ لا توجد مشاكل واضحة! المشكلة قد تكون مؤقتة.'))
            self.stdout.write('   💡 جرب إرسال /start للبوت مرة أخرى')
        else:
            for rec in recommendations:
                self.stdout.write(f'   {rec}')
        
        self.stdout.write(f'\n🔧 أوامر مفيدة:')
        self.stdout.write(f'   - اختبار إشعارات: python manage.py test_junkyard_notifications --junkyard-id {junkyard.id}')
        self.stdout.write(f'   - تشخيص من الداشبورد: /dashboard/junkyards/{junkyard.id}/diagnose/')
        self.stdout.write(f'   - اختبار رسالة: /dashboard/junkyards/{junkyard.id}/test-notification/')
