{
    'name': 'Smart Radar',
    'version': '1.0',
    'category': 'Administration',
    'summary': 'AI SaaS Platform Management & Dashboard',
    'description': """
    Smart Radar - Zero-Touch AI SaaS Platform.
    Manage API keys and view real-time SaaS operations in a bespoke OWL Dashboard.
    """,
    'author': 'Alpha Plus IT',
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/demo_data.xml',
        'views/target_views.xml',
        'views/post_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'smart_radar/static/src/scss/backend_views.scss',
            'smart_radar/static/src/components/dashboard/**/*.js',
            'smart_radar/static/src/components/dashboard/**/*.xml',
            'smart_radar/static/src/components/dashboard/**/*.scss',
            'smart_radar/static/src/components/posts/**/*.js',
            'smart_radar/static/src/components/posts/**/*.xml',
            'smart_radar/static/src/components/posts/**/*.scss',
        ],
    },
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
