#!/bin/bash

# Script لاستيراد workflows في n8n تلقائياً
# Auto Parts Bot Project

set -e

# الألوان للطباعة
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# إعدادات n8n
N8N_URL="http://localhost:5678"
N8N_USERNAME="admin"
N8N_PASSWORD="admin123"
WORKFLOWS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/workflows"

echo -e "${BLUE}🚀 بدء استيراد workflows في n8n...${NC}"
echo -e "${BLUE}📍 n8n URL: ${N8N_URL}${NC}"
echo -e "${BLUE}📁 مجلد Workflows: ${WORKFLOWS_DIR}${NC}"

# التحقق من تشغيل n8n
echo -e "${YELLOW}🔍 التحقق من تشغيل n8n...${NC}"
if ! curl -s "${N8N_URL}/healthz" > /dev/null; then
    echo -e "${RED}❌ n8n غير متاح على ${N8N_URL}${NC}"
    echo -e "${YELLOW}💡 تأكد من تشغيل n8n: docker-compose up -d n8n${NC}"
    exit 1
fi
echo -e "${GREEN}✅ n8n يعمل بشكل صحيح${NC}"

# الحصول على token المصادقة
echo -e "${YELLOW}🔐 الحصول على token المصادقة...${NC}"
AUTH_TOKEN=$(curl -s -X POST "${N8N_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${N8N_USERNAME}\",\"password\":\"${N8N_USERNAME}\"}" | \
    jq -r '.data.token' 2>/dev/null || echo "")

if [ -z "$AUTH_TOKEN" ] || [ "$AUTH_TOKEN" = "null" ]; then
    echo -e "${RED}❌ فشل في الحصول على token المصادقة${NC}"
    echo -e "${YELLOW}💡 تأكد من صحة اسم المستخدم وكلمة المرور${NC}"
    exit 1
fi
echo -e "${GREEN}✅ تم الحصول على token المصادقة${NC}"

# دالة لاستيراد workflow
import_workflow() {
    local workflow_file="$1"
    local workflow_name=$(basename "$workflow_file" .json)
    
    echo -e "${YELLOW}📥 استيراد ${workflow_name}...${NC}"
    
    # التحقق من وجود الملف
    if [ ! -f "$workflow_file" ]; then
        echo -e "${RED}❌ الملف غير موجود: ${workflow_file}${NC}"
        return 1
    fi
    
    # استيراد workflow
    local response=$(curl -s -X POST "${N8N_URL}/api/v1/workflows" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${AUTH_TOKEN}" \
        -d "@${workflow_file}")
    
    local workflow_id=$(echo "$response" | jq -r '.data.id' 2>/dev/null || echo "")
    
    if [ -n "$workflow_id" ] && [ "$workflow_id" != "null" ]; then
        echo -e "${GREEN}✅ تم استيراد ${workflow_name} بنجاح (ID: ${workflow_id})${NC}"
        
        # تفعيل workflow
        local activate_response=$(curl -s -X POST "${N8N_URL}/api/v1/workflows/${workflow_id}/activate" \
            -H "Authorization: Bearer ${AUTH_TOKEN}")
        
        if echo "$activate_response" | jq -e '.success' > /dev/null 2>&1; then
            echo -e "${GREEN}✅ تم تفعيل ${workflow_name}${NC}"
        else
            echo -e "${YELLOW}⚠️  فشل في تفعيل ${workflow_name}${NC}"
        fi
        
        return 0
    else
        echo -e "${RED}❌ فشل في استيراد ${workflow_name}${NC}"
        echo -e "${YELLOW}📋 الاستجابة: ${response}${NC}"
        return 1
    fi
}

# استيراد جميع workflows
echo -e "${BLUE}📋 بدء استيراد workflows...${NC}"

# التحقق من وجود مجلد workflows
if [ ! -d "$WORKFLOWS_DIR" ]; then
    echo -e "${RED}❌ مجلد workflows غير موجود: ${WORKFLOWS_DIR}${NC}"
    exit 1
fi

# البحث عن ملفات workflows
workflow_files=($(find "$WORKFLOWS_DIR" -name "*.json" -type f))

if [ ${#workflow_files[@]} -eq 0 ]; then
    echo -e "${RED}❌ لم يتم العثور على ملفات workflows${NC}"
    exit 1
fi

echo -e "${BLUE}📁 تم العثور على ${#workflow_files[@]} workflow(s)${NC}"

# استيراد كل workflow
success_count=0
total_count=${#workflow_files[@]}

for workflow_file in "${workflow_files[@]}"; do
    if import_workflow "$workflow_file"; then
        ((success_count++))
    fi
    echo ""
done

# ملخص النتائج
echo -e "${BLUE}📊 ملخص الاستيراد:${NC}"
echo -e "${GREEN}✅ نجح: ${success_count}/${total_count}${NC}"
echo -e "${RED}❌ فشل: $((total_count - success_count))/${total_count}${NC}"

if [ $success_count -eq $total_count ]; then
    echo -e "${GREEN}🎉 تم استيراد جميع workflows بنجاح!${NC}"
else
    echo -e "${YELLOW}⚠️  بعض workflows فشل في الاستيراد${NC}"
fi

echo ""
echo -e "${BLUE}🔗 روابط مفيدة:${NC}"
echo -e "${GREEN}📱 n8n Dashboard: ${N8N_URL}${NC}"
echo -e "${GREEN}📋 Workflows: ${N8N_URL}/workflows${NC}"
echo -e "${GREEN}🔧 Executions: ${N8N_URL}/executions${NC}"
echo -e "${GREEN}⚙️  Settings: ${N8N_URL}/settings${NC}"

echo ""
echo -e "${BLUE}💡 نصائح:${NC}"
echo -e "${YELLOW}1. تحقق من حالة workflows في n8n dashboard${NC}"
echo -e "${YELLOW}2. اختبر webhooks للتأكد من عملها${NC}"
echo -e "${YELLOW}3. راقب executions للأخطاء${NC}"
echo -e "${YELLOW}4. تأكد من إعداد المتغيرات البيئية${NC}"

echo ""
echo -e "${GREEN}✨ تم الانتهاء من استيراد workflows!${NC}" 