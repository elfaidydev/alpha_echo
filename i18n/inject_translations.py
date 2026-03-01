import os

TRANSLATIONS = {
    "Dashboard": "لوحة التحكم",
    "Central interface for tracking, reformulating, and publishing content": "الواجهة المركزية للتتبع والصياغة والنشر",
    "monitored sources": "مصادر رصد",
    "Welcome to": "مرحباً بك في",
    "Automate content harvesting, formulation, and publishing with AI. Follow these steps to begin.": "أتمتة جلب المحتوى وصياغته ونشره بالذكاء الاصطناعي. اتبع الخطوات التالية للبدء.",
    "Link X (Twitter)": "ربط حساب X (تويتر)",
    "Authorize the system to publish via your account.": "تفويض النظام للنشر عبر حسابك.",
    "Linked": "متصل",
    "Connect": "اتصال",
    "AI Prompt": "توجيه الذكاء الاصطناعي",
    "Define the tone and instructions for the AI engine.": "تحديد نبرة وتعليمات محرك الذكاء الاصطناعي.",
    "Set": "تم الإعداد",
    "Configure": "تخصيص",
    "Search Keywords": "كلمات البحث",
    "Set primary filters for discovered content.": "تعيين الفلاتر الأساسية للمحتوى المكتشف.",
    "Defined": "محددة",
    "Add Filters": "إضافة فلاتر",
    "Monitored Sources": "مصادر الرصد",
    "Add the accounts the radar will track.": "إضافة الحسابات التي سيتابعها الرادار.",
    "Added": "مضافة",
    "Add Targets": "إضافة مصادر",
    "Resource Management": "إدارة المصادر",
    "Live monitoring network for approved sources and accounts.": "شبكة رصد حية للمصادر والحسابات المعتمدة.",
    "Search sources...": "ابحث في المصادر...",
    "Add Source": "إضافة مصدر",
    "All": "الكل",
    "General Content": "محتوى عام",
    "Health & Medicine": "صحة وطب",
    "Education & Research": "تعليم وأبحاث",
    "Tech & Innovation": "تقنية وابتكار",
    "Content & Publications": "المحتوى والمنشورات",
    "Review AI reformulations and approve them with one click for automated publishing.": "مراجعة صياغات الذكاء الاصطناعي واعتمادها للنشر التلقائي بضغطة واحدة.",
    "Search content or sources...": "ابحث في المحتوى أو المصادر...",
    "Pending Drafts": "مسودات معلقة",
    "Published": "تم النشر",
    "Rejected": "مرفوضة",
    "Pause Monitoring": "إيقاف الرصد مؤقتاً",
    "Start Exploration": "بدء الاستكشاف",
    "System Readiness": "جاهزية النظام",
    "Exploration engine and AI formulation unit are in real-time activation mode. Connection is active and stable.": "محرك الاستكشاف ووحدة صياغة الذكاء الاصطناعي في وضع التنشيط الفوري. الاتصال نشط ومستقر.",
}

def inject_translations(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_entries = []
    for msgid, msgstr in TRANSLATIONS.items():
        # Check if already exists (case sensitive)
        search_str = f'msgid "{msgid}"'
        if search_str not in content:
            entry = f'''
#. odoo-javascript
msgid "{msgid}"
msgstr "{msgstr}"
'''
            new_entries.append(entry)
    
    if new_entries:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write("".join(new_entries))
        print(f'Injected {len(new_entries)} new translations into {filepath}')
    else:
        print(f'All translations already exist in {filepath}')

inject_translations('/Users/abdelazim.dev/Projects/odoo-projects/odoo-v17/custom_addons/MANZOR/addons/alpha_echo/i18n/ar_EG.po')
inject_translations('/Users/abdelazim.dev/Projects/odoo-projects/odoo-v17/custom_addons/MANZOR/addons/alpha_echo/i18n/ar.po')
