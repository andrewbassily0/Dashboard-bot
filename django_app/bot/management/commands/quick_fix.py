"""
Quick fix command for common junkyard issues
"""

from django.core.management.base import BaseCommand
from bot.models import Junkyard, User
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Quick fix for common junkyard offer submission issues'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-all',
            action='store_true',
            help='Fix all common issues for all junkyards'
        )
        parser.add_argument(
            '--telegram-id',
            type=int,
            help='Fix issues for specific telegram ID'
        )
        parser.add_argument(
            '--junkyard-name',
            type=str,
            help='Fix issues for junkyard by name'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 أداة الإصلاح السريع'))
        self.stdout.write('=' * 50)
        
        if options['fix_all']:
            self.fix_all_junkyards(options['dry_run'])
        elif options['telegram_id']:
            self.fix_by_telegram_id(options['telegram_id'], options['dry_run'])
        elif options['junkyard_name']:
            self.fix_by_name(options['junkyard_name'], options['dry_run'])
        else:
            self.show_help()

    def fix_all_junkyards(self, dry_run=True):
        """Fix issues for all junkyards"""
        self.stdout.write('\n🔧 فحص جميع التشاليح...')
        
        junkyards = Junkyard.objects.all().select_related('user', 'city')
        fixed_count = 0
        
        for junkyard in junkyards:
            if self.fix_junkyard_issues(junkyard, dry_run):
                fixed_count += 1
        
        if dry_run:
            self.stdout.write(f'\n📊 يمكن إصلاح {fixed_count} تشليح')
            self.stdout.write('🔄 أعد تشغيل الأمر بدون --dry-run لتطبيق الإصلاحات')
        else:
            self.stdout.write(f'\n✅ تم إصلاح {fixed_count} تشليح')

    def fix_by_telegram_id(self, telegram_id, dry_run=True):
        """Fix issues for specific telegram ID"""
        try:
            user = User.objects.get(telegram_id=telegram_id)
            junkyard = Junkyard.objects.get(user=user)
            
            self.stdout.write(f'\n🔧 فحص التشليح: {junkyard.user.first_name}')
            
            if self.fix_junkyard_issues(junkyard, dry_run):
                if not dry_run:
                    self.stdout.write(self.style.SUCCESS('✅ تم الإصلاح بنجاح'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ لا توجد مشاكل'))
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ لا يوجد مستخدم بـ telegram_id: {telegram_id}'))
        except Junkyard.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ المستخدم ليس تشليح'))

    def fix_by_name(self, name, dry_run=True):
        """Fix issues for junkyard by name"""
        junkyards = Junkyard.objects.filter(
            user__first_name__icontains=name
        ).select_related('user', 'city')
        
        if not junkyards:
            self.stdout.write(self.style.ERROR(f'❌ لا يوجد تشليح باسم: {name}'))
            return
        
        for junkyard in junkyards:
            self.stdout.write(f'\n🔧 فحص التشليح: {junkyard.user.first_name}')
            
            if self.fix_junkyard_issues(junkyard, dry_run):
                if not dry_run:
                    self.stdout.write(self.style.SUCCESS('✅ تم الإصلاح'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ لا توجد مشاكل'))

    def fix_junkyard_issues(self, junkyard, dry_run=True):
        """Fix common issues for a junkyard"""
        issues_found = []
        fixes_applied = []
        
        # Check telegram_id
        if not junkyard.user.telegram_id:
            issues_found.append("❌ لا يوجد telegram_id")
        
        # Check user type
        if junkyard.user.user_type != 'junkyard':
            issues_found.append(f"❌ نوع المستخدم خاطئ: {junkyard.user.user_type}")
            if not dry_run:
                with transaction.atomic():
                    junkyard.user.user_type = 'junkyard'
                    junkyard.user.save()
                fixes_applied.append("✅ تم تصحيح نوع المستخدم")
        
        # Check junkyard active status
        if not junkyard.is_active:
            issues_found.append("❌ التشليح غير مُفعل")
            if not dry_run:
                with transaction.atomic():
                    junkyard.is_active = True
                    junkyard.save()
                fixes_applied.append("✅ تم تفعيل التشليح")
        
        # Check city active status
        if not junkyard.city.is_active:
            issues_found.append(f"⚠️ المدينة {junkyard.city.name} غير مُفعلة")
            if not dry_run:
                with transaction.atomic():
                    junkyard.city.is_active = True
                    junkyard.city.save()
                fixes_applied.append(f"✅ تم تفعيل المدينة {junkyard.city.name}")
        
        # Display results
        if issues_found or fixes_applied:
            self.stdout.write(f'   التشليح: {junkyard.user.first_name} ({junkyard.city.name})')
            
            for issue in issues_found:
                if dry_run:
                    self.stdout.write(f'   {issue}')
                else:
                    # Don't show issues that were fixed
                    if ("نوع المستخدم" in issue and "✅ تم تصحيح نوع المستخدم" in fixes_applied):
                        continue
                    if ("غير مُفعل" in issue and "✅ تم تفعيل التشليح" in fixes_applied):
                        continue
                    if ("المدينة" in issue and "تم تفعيل المدينة" in str(fixes_applied)):
                        continue
                    self.stdout.write(f'   {issue}')
            
            for fix in fixes_applied:
                self.stdout.write(self.style.SUCCESS(f'   {fix}'))
            
            return True
        
        return False

    def show_help(self):
        """Show usage help"""
        self.stdout.write('''
🔧 استخدام أداة الإصلاح السريع:

# إصلاح جميع التشاليح (فحص فقط)
python manage.py quick_fix --fix-all --dry-run

# إصلاح جميع التشاليح (تطبيق فعلي)
python manage.py quick_fix --fix-all

# إصلاح تشليح محدد بـ telegram_id
python manage.py quick_fix --telegram-id 123456789

# إصلاح تشليح محدد بالاسم
python manage.py quick_fix --junkyard-name "أحمد"

🎯 الإصلاحات التلقائية:
✅ تصحيح نوع المستخدم إلى 'junkyard'
✅ تفعيل التشليح إذا كان غير مُفعل
✅ تفعيل المدينة إذا كانت غير مُفعلة

❌ لا يمكن إصلاح:
- telegram_id مفقود (يجب إضافته يدوياً)
- حساب غير موجود (يجب إنشاؤه يدوياً)
        ''')
