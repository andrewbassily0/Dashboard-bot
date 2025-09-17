#!/usr/bin/env python3
"""
سكريبت للبحث عن المصطلحات المطلوب تغييرها في المشروع
"""

import os
import re
from pathlib import Path
from collections import defaultdict

# المصطلحات المطلوب البحث عنها
TERMS_TO_FIND = {
    'arabic': [
        'الموثوقة',
        'موثوقة',
        'ماركة',
        'الماركة',
        'موديل',
        'الموديل',
        'سنة الصنع',
        'سنوات الصنع',
        'الوصف',
        'وصف القطعة',
        'الكمية',
        'عدد الكمية',
        'مدة التوريد',
        'وقت التوريد'
    ],
    'english': [
        'trusted',
        'brand',
        'Brand',
        'model',
        'Model',
        'year',
        'Year',
        'manufacture',
        'description',
        'Description',
        'quantity',
        'Quantity',
        'delivery_time',
        'delivery time',
        'Delivery Time'
    ]
}

# المجلدات المستهدفة
TARGET_DIRS = [
    '/project/Dashboard-bot/django_app',
    '/project/Dashboard-bot/templates',
    '/project/Dashboard-bot/n8n'
]

# امتدادات الملفات المستهدفة
FILE_EXTENSIONS = ['.py', '.html', '.js', '.css', '.json', '.md', '.txt', '.yml', '.yaml']

def find_files_with_extensions(directory, extensions):
    """البحث عن الملفات بامتدادات معينة"""
    files = []
    for root, dirs, filenames in os.walk(directory):
        # تجاهل المجلدات غير المرغوبة
        if '__pycache__' in root or '.git' in root or 'migrations' in root:
            continue
        
        for filename in filenames:
            if any(filename.endswith(ext) for ext in extensions):
                files.append(os.path.join(root, filename))
    return files

def search_terms_in_file(file_path, terms):
    """البحث عن المصطلحات في ملف"""
    found_terms = defaultdict(list)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            for term in terms:
                # البحث بشكل غير حساس لحالة الأحرف
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                
                for line_num, line in enumerate(lines, 1):
                    if pattern.search(line):
                        found_terms[term].append({
                            'line': line_num,
                            'content': line.strip()[:100]  # أول 100 حرف من السطر
                        })
    except Exception as e:
        print(f"خطأ في قراءة الملف {file_path}: {e}")
    
    return found_terms

def main():
    """الدالة الرئيسية"""
    print("🔍 بدء البحث عن المصطلحات المطلوب تغييرها...")
    print("=" * 60)
    
    all_results = {}
    
    # البحث في كل مجلد
    for directory in TARGET_DIRS:
        if not os.path.exists(directory):
            print(f"⚠️  المجلد غير موجود: {directory}")
            continue
        
        print(f"\n📁 البحث في: {directory}")
        files = find_files_with_extensions(directory, FILE_EXTENSIONS)
        print(f"   عدد الملفات: {len(files)}")
        
        # البحث عن المصطلحات في كل ملف
        for file_path in files:
            all_terms = TERMS_TO_FIND['arabic'] + TERMS_TO_FIND['english']
            found_terms = search_terms_in_file(file_path, all_terms)
            
            if found_terms:
                relative_path = file_path.replace('/project/Dashboard-bot/', '')
                all_results[relative_path] = found_terms
    
    # عرض النتائج
    print("\n" + "=" * 60)
    print("📊 ملخص النتائج:")
    print("=" * 60)
    
    if not all_results:
        print("✅ لم يتم العثور على أي من المصطلحات المطلوبة!")
        return
    
    # إحصائيات عامة
    term_counts = defaultdict(int)
    for file_path, terms in all_results.items():
        for term, occurrences in terms.items():
            term_counts[term] += len(occurrences)
    
    print("\n📈 إحصائيات المصطلحات:")
    for term, count in sorted(term_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {term}: {count} مرة")
    
    print(f"\n📁 عدد الملفات المتأثرة: {len(all_results)}")
    
    # تفاصيل كل ملف
    print("\n" + "=" * 60)
    print("📋 التفاصيل:")
    print("=" * 60)
    
    for file_path, terms in sorted(all_results.items()):
        print(f"\n📄 {file_path}")
        for term, occurrences in terms.items():
            print(f"   🔸 '{term}' ({len(occurrences)} مرة):")
            for occ in occurrences[:3]:  # عرض أول 3 مواضع فقط
                print(f"      السطر {occ['line']}: {occ['content']}")
            if len(occurrences) > 3:
                print(f"      ... و {len(occurrences) - 3} مواضع أخرى")
    
    # حفظ النتائج في ملف
    output_file = '/project/Dashboard-bot/webapp/terms_search_results.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("نتائج البحث عن المصطلحات المطلوب تغييرها\n")
        f.write("=" * 60 + "\n\n")
        
        for file_path, terms in sorted(all_results.items()):
            f.write(f"\n📄 {file_path}\n")
            for term, occurrences in terms.items():
                f.write(f"   • '{term}' ({len(occurrences)} مرة)\n")
                for occ in occurrences:
                    f.write(f"      السطر {occ['line']}: {occ['content']}\n")
    
    print(f"\n💾 تم حفظ النتائج في: {output_file}")

if __name__ == "__main__":
    main()