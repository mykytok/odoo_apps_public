{
    'name': 'Rent',
    'version': '18.0.1.0.1',
    'author': 'Mykyta Ohirchuk',
    'website': '',
    'category': 'Customizations',
    'license': 'OPL-1',

    'depends': [
        'base',
        'portal'
    ],

    'external_dependencies': {
        'python': [],
    },

    'data': [
        'security/rent_groups.xml',
        'security/rent_security.xml',
        'security/ir.model.access.csv',

        'views/rent_menu.xml',

        'views/rent_planned_monthly_revenue_views.xml',
        'views/rent_actual_monthly_revenue_views.xml',
        'views/rent_rental_object_group_views.xml',
        'views/rent_rental_object_views.xml',
        'views/rent_contract_views.xml',
        'views/rent_cost_center_views.xml',
        'views/res_partner_views.xml',
        'views/res_country_views.xml',

        'reports/rental_object_report.xml',

        'views/rent_analysis_report_views.xml',
        'wizards/rent_analysis_wizard_view.xml',

    ],
    'demo': [
        'demo/rent.rental.object.group.csv',
        'demo/rent.rental.object.csv',
        'demo/rent_contract.xml',
    ],

    'installable': True,
    'auto_install': False,

    'images': []
}
