{
    'name': 'Alpha Echo',
    'version': '1.0',
    'category': 'Administration',
    'summary': 'Alpha Echo: The Autonomous AI Social Presence Engine',
    'description': """
Alpha Echo: المحرك الذكي للحضور الاجتماعي المستقل

يعد موديول Alpha Echo الحل المبتكر والأكثر تطوراً لإدارة المحتوى الرقمي عبر منصة (X)، حيث تم تصميمه لتمكين المؤسسات من السيطرة على حضورها الرقمي بذكاء واحترافية. يقوم النظام بدور "الصدى الذكي" لعلامتك التجارية، حيث يراقب، يعالج، وينشر المحتوى بطريقة تجعل العميل دائماً في قلب الحدث وبأقل مجهود.

🚀 المميزات الرئيسية:
- رادار الرصد الشامل: مراقبة لحظية لعدد غير محدود من الحسابات المستهدفة (يحدده العميل)، لضمان عدم تفويت أي محتوى رائج أو ذو صلة بمجال العمل.
- المعالج الذكي (AI Core): استخدام تقنيات OpenAI (GPT-4o-mini) لإعادة صياغة التغريدات بأسلوب إبداعي يطابق نبرة صوت العميل، مما يضمن ظهور المحتوى وكأنه كُتب يدوياً.
- النشر الآلي المباشر: التكامل الكامل مع (X API v2) للنشر الفوري والمباشر على حساب العميل دون الحاجة لأي تدخل يدوي.
- نظام الفلترة الذكي: تقنيات متطورة لتصفية المحتوى بناءً على الكلمات المفتاحية لضمان دقة البيانات وتحسين جودة المنشورات.
- لوحة تحكم مركزية: داشبورد تفاعلية توفر تحليلات دقيقة لعمليات الرصد، حالات النشر، ومعدلات الأداء العام.

Alpha Echo: The Autonomous AI Social Presence Engine

Alpha Echo is a high-end Odoo 17 module developed by Alpha Plus Information Technology to revolutionize how businesses manage their digital footprint on X (Twitter). Designed as a SaaS-ready solution, it acts as a "Smart Echo" for your brand—monitoring, transforming, and publishing content with absolute precision.

🚀 Key Features:
- Comprehensive Radar: Real-time monitoring of a flexible number of target accounts (fully determined by the client), ensuring complete coverage of industry updates and trends.
- AI Transformation Core: Leverages OpenAI’s GPT-4o-mini to rephrase raw data into professional, engaging posts that perfectly mirror the client’s unique brand voice.
- Direct X Integration: Full synchronization with X API v2 for seamless, direct-to-profile publishing, making every post look authentically handcrafted.
- Precision Filtering: Advanced keyword-based filtering logic to ensure content relevance and maintain a high-quality feed.
- Executive Dashboard: A centralized, interactive UI providing deep insights into monitoring activities, publishing status, and engagement metrics.
    """,
    'author': 'Alpha Plus',
    'website': 'https://alpha.com.se/',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/demo_data.xml',
        'data/ir_cron_data.xml',
        'views/target_views.xml',
        'views/post_views.xml',
        'views/client_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'alpha_echo/static/src/core/scss/_variables.scss',
            'alpha_echo/static/src/core/scss/_animations.scss',
            'alpha_echo/static/src/core/scss/design_system.scss',
            'alpha_echo/static/src/scss/backend_views.scss',
            'alpha_echo/static/src/components/dashboard/dashboard.scss',
            'alpha_echo/static/src/components/posts/posts_page.scss',
            'alpha_echo/static/src/components/targets/targets_page.scss',
            'alpha_echo/static/src/components/config/config_page.scss',
            'alpha_echo/static/src/services/radar_service.js',
            'alpha_echo/static/src/components/dashboard/**/*.js',
            'alpha_echo/static/src/components/dashboard/**/*.xml',
            'alpha_echo/static/src/components/posts/**/*.js',
            'alpha_echo/static/src/components/posts/**/*.xml',
            'alpha_echo/static/src/components/targets/**/*.js',
            'alpha_echo/static/src/components/targets/**/*.xml',
            'alpha_echo/static/src/components/config/**/*.js',
            'alpha_echo/static/src/components/config/**/*.xml',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
