{
    'name': "Timesheet of Completed Work",
    'summary': "Custom module for detailed timesheet-based invoicing with period selection.",
    'version': '17.0.1.0.0',
    'category': 'Invoicing/Customization',
    'author': 'Mykyta Ohirchuk',
    'website': "",
    'license': 'OPL-1',
    'depends': [
        'account',
        'hr_timesheet',
        'project',
        'sale_project',
    ],
    'data': [
        'security/ir.model.access.csv',

        'views/account_move_views.xml',
        'views/res_company_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}