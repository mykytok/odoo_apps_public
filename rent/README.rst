===================
Odoo Rent Module
===================

Overview
========
The module allows you to organize accounting of rental objects. For each rental object, it is possible to add several contracts with monthly rental rates in different currencies. Based on the entered data, it is possible to generate an analytical report with the calculation of the rental amount.

Key Features
======
Storage of a list of Rental Object.
Printing summary information on the Rental Object.
Maintaining a list of Contracts.
Generating Rent Analysis Report.

Installation: Clone repository. Add the repository path to the config file. Update the app list. Install the module. Usage User manual To view the module description, you need to:
Go to Apps > Apps > Main Apps. Search the module by name. Open the module form. Notes: Don't forget to update Apps List by clicking on Update Apps List menu.

Models
======
* `rent.rental.object`: Main model for rental properties.
* `rent.rental.object.group`: Categories for rental objects.
* `rent.contract`: Details of rental agreements.
* `rent.cost.center`: Cost tracking associated with rental objects.
* `rent.planned.monthly.revenue`: (Associated with Cost Center)
* `rent.actual.monthly.revenue`: (Associated with Cost Center)
* `rent.analysis.report.line`: Transient Model for generating an analytical report.

Reports
=======
* **Rental Object Details**: A PDF report summarizing a rental object's main information, contracts, and cost centers.

Authors/Credits
=======
Mykyta Ohirchuk <i.nikita@i.ua>

License:
=======
OPL-1