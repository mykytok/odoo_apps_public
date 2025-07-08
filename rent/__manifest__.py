{
    'name': 'Rent',
    'version': '18.0.1.0.0',
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
        'security/ir.model.access.csv',

        'views/rent_menu.xml',
        'views/rent_planned_monthly_revenue_views.xml',
        'views/rent_actual_monthly_revenue_views.xml',
        'views/rent_rental_object_group_views.xml',
        'views/rent_rental_object_views.xml',
        'views/rent_contract_views.xml',
        'views/rent_cost_center_views.xml',
    ],
    'demo': [
    ],

    'installable': True,
    'auto_install': False,

    'images': []
}
