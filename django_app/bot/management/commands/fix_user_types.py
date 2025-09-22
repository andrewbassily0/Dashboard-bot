#!/usr/bin/env python3
"""
Django Management Command to fix incorrect user types for junkyards

Usage:
    python manage.py fix_user_types           # Show current status and prompt for confirmation
    python manage.py fix_user_types --fix     # Fix all wrong user types automatically
    python manage.py fix_user_types --dry-run # Show what would be fixed without making changes
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from bot.models import Junkyard, User


class Command(BaseCommand):
    help = 'Fix incorrect user types for junkyards (e.g., junkyard_owner → junkyard)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Actually fix the user types (without this, just shows status)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without making changes',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 فحص أنواع المستخدمين للتشاليح...')
        self.stdout.write('=' * 50)
        
        try:
            # Get all junkyards and categorize by user type
            all_junkyards = Junkyard.objects.select_related('user', 'city').all()
            
            correct_junkyards = []
            wrong_type_junkyards = []
            
            for junkyard in all_junkyards:
                if junkyard.user.user_type == 'junkyard':
                    correct_junkyards.append(junkyard)
                else:
                    wrong_type_junkyards.append(junkyard)
            
            # Show summary
            self.stdout.write(f'📊 إجمالي التشاليح: {all_junkyards.count()}')
            self.stdout.write(f'✅ بنوع صحيح: {len(correct_junkyards)}')
            self.stdout.write(f'❌ بنوع خاطئ: {len(wrong_type_junkyards)}')
            self.stdout.write('')
            
            if len(wrong_type_junkyards) == 0:
                self.stdout.write(self.style.SUCCESS('🎉 جميع التشاليح لها نوع المستخدم الصحيح!'))
                return
            
            # Show problematic junkyards
            self.stdout.write('❌ التشاليح ذات الأنواع الخاطئة:')
            for junkyard in wrong_type_junkyards:
                self.stdout.write(
                    f'   - ID: {junkyard.id}, الاسم: {junkyard.user.first_name}, '
                    f'المدينة: {junkyard.city.name}, النوع الحالي: {junkyard.user.user_type}'
                )
            self.stdout.write('')
            
            # Handle different modes
            if options['dry_run']:
                self.stdout.write(self.style.WARNING('🔍 وضع المعاينة - لن يتم تغيير أي شيء:'))
                for junkyard in wrong_type_junkyards:
                    self.stdout.write(
                        f'   سيتم تغيير: {junkyard.user.first_name} من "{junkyard.user.user_type}" إلى "junkyard"'
                    )
                self.stdout.write('')
                self.stdout.write('لتطبيق التغييرات، استخدم: python manage.py fix_user_types --fix')
                
            elif options['fix']:
                self.stdout.write(self.style.WARNING('🔧 بدء إصلاح أنواع المستخدمين...'))
                fixed_count = 0
                
                for junkyard in wrong_type_junkyards:
                    old_type = junkyard.user.user_type
                    junkyard.user.user_type = 'junkyard'
                    junkyard.user.save()
                    fixed_count += 1
                    
                    self.stdout.write(
                        f'   ✅ تم إصلاح: {junkyard.user.first_name} - {old_type} → junkyard'
                    )
                
                self.stdout.write('')
                self.stdout.write(
                    self.style.SUCCESS(f'🎉 تم إصلاح {fixed_count} تشليح بنجاح!')
                )
                
            else:
                # Interactive mode - ask for confirmation
                self.stdout.write(self.style.WARNING(f'هل تريد إصلاح {len(wrong_type_junkyards)} تشليح؟'))
                self.stdout.write('سيتم تغيير نوع المستخدم لجميع التشاليح إلى "junkyard"')
                self.stdout.write('')
                
                confirm = input('اكتب "نعم" أو "yes" للتأكيد: ').lower().strip()
                
                if confirm in ['نعم', 'yes', 'y']:
                    self.stdout.write(self.style.WARNING('🔧 بدء الإصلاح...'))
                    fixed_count = 0
                    
                    for junkyard in wrong_type_junkyards:
                        old_type = junkyard.user.user_type
                        junkyard.user.user_type = 'junkyard'
                        junkyard.user.save()
                        fixed_count += 1
                        
                        self.stdout.write(
                            f'   ✅ تم إصلاح: {junkyard.user.first_name} - {old_type} → junkyard'
                        )
                    
                    self.stdout.write('')
                    self.stdout.write(
                        self.style.SUCCESS(f'🎉 تم إصلاح {fixed_count} تشليح بنجاح!')
                    )
                else:
                    self.stdout.write(self.style.WARNING('❌ تم إلغاء العملية'))
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ حدث خطأ: {str(e)}')
            )
            import traceback
            self.stdout.write(traceback.format_exc())
        
        self.stdout.write('')
        self.stdout.write('=' * 50)
        self.stdout.write('💡 نصائح:')
        self.stdout.write('• استخدم --dry-run لمعاينة التغييرات قبل التطبيق')
        self.stdout.write('• استخدم --fix للإصلاح التلقائي دون تأكيد')
        self.stdout.write('• النوع الصحيح للتشاليح هو "junkyard"')
        self.stdout.write('• الأنواع الخاطئة الشائعة: junkyard_owner, owner, manager')
