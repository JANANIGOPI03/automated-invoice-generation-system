from django.urls import path
from . import views

app_name = "invoicing"

urlpatterns = [
    # Auth...
    path("register/", views.register,   name="register"),
    path("login/",    views.login_view, name="login"),
    path("logout/",   views.logout_view, name="logout"),

    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # Customers
    path("customers/",             views.list_customers,   name="list_customers"),
    path("customers/new/",         views.create_customer, name="create_customer"),
    path("customers/<int:user_id>/edit/",
         views.edit_customer,   name="edit_customer"),
    path("customers/<int:user_id>/delete/",
         views.delete_customer, name="delete_customer"),

    # Products
    path("products/",             views.list_products,   name="list_products"),
    path("products/new/",         views.create_product, name="create_product"),
    path("products/<int:product_id>/edit/",
         views.edit_product,   name="edit_product"),
    path("products/<int:product_id>/delete/",
         views.delete_product, name="delete_product"),

    # Invoices
    path("invoices/",             views.list_invoices,   name="list_invoices"),
    path("invoices/<int:invoice_id>/view/",
         views.view_invoice,   name="view_invoice"),
    path("invoices/<int:invoice_id>/delete/",
         views.delete_invoice, name="delete_invoice"),
    path('invoices/<int:invoice_id>/send/',
         views.send_invoice, name='send_invoice'),

    # Customer‑specific:
    path('customer/dashboard/',
         views.customer_dashboard,     name='customer_dashboard'),
    path('customer/invoices/',
         views.customer_invoices,      name='customer_invoices'),
    path('customer/invoices/<int:invoice_id>/',
         views.customer_invoice_detail, name='customer_invoice_detail'),
    path('customer/invoices/<int:invoice_id>/pay/',
         views.pay_invoice,        name='pay_invoice'),
    path('customer/profile/',
         views.customer_profile,       name='customer_profile'),
    path('customer/profile/edit/',
         views.edit_profile,           name='edit_profile'),
    # Customer product catalog
    path('customer/products/', views.customer_products, name='customer_products'),
    path('customer/products/<int:product_id>/buy/',
         views.buy_product, name='buy_product'),

]
