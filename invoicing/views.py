# invoicing/views.py
from datetime import datetime
from functools import wraps
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.messages import get_messages
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .forms import ProfileForm, RegisterForm, LoginForm, CustomerForm, ProductForm
from db import (
    add_invoice_item, add_payment, create_invoice, get_all_products, get_all_users, create_user, get_payments_by_invoice, get_user_by_id, mark_product_sold, update_invoice, update_user, delete_user,
    get_user_by_email,
    add_billing_address, get_billing_by_user, update_billing_address, delete_billing_address,
    get_products_by_user, create_product as db_create_product, get_product_by_id, update_product as db_update_product, delete_product as db_delete_product,
    get_all_invoices, get_invoice_by_id, get_items_by_invoice, delete_invoice as db_delete_invoice
)
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
import weasyprint
import tempfile
import os
from pathlib import Path
from django.conf import settings
from django.utils import timezone


def ensure_admin(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.session.get('user_role') != 'admin':
            return redirect('invoicing:login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def login_view(request):
    form = LoginForm(request.POST or None)

    # If already logged in, send to the right dashboard
    if request.session.get('user_id'):
        role = request.session.get('user_role')
        if role == 'admin':
            return redirect('invoicing:dashboard')
        else:
            return redirect('invoicing:customer_dashboard')

    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        user = get_user_by_email(cd['email'])
        if user and user['password'] == cd['password']:
            # store session
            request.session['user_id'] = user['user_id']
            request.session['user_name'] = user['name']
            request.session['user_role'] = user['role']

            # immediately redirect by role
            if user['role'] == 'admin':
                return redirect('invoicing:dashboard')
            else:
                return redirect('invoicing:customer_dashboard')

        messages.error(request, "Invalid credentials")

    return render(request, "login.html", {"form": form})


def register(request):
    # Redirect logged‑in users
    if request.session.get('user_id'):
        return redirect('invoicing:dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        res = create_user(cd['name'], cd['email'],
                          cd['password'], cd['role'], cd['phone'])
        if res['status_code'] == 0:
            messages.success(
                request, "Registration successful. Please log in.")
            return redirect('invoicing:login')
        else:
            messages.error(request, res['status_msg'])

    return render(request, "register.html", {"form": form})


def logout_view(request):
    # consume (and discard) any pending messages
    storage = get_messages(request)
    for _ in storage:
        pass

    # now clear the session
    request.session.flush()

    # redirect to login (no old messages will remain)
    return redirect('invoicing:login')


def dashboard(request):
    if not request.session.get('user_id'):
        return redirect('invoicing:login')

    # Only admins see this page—guard with ensure_admin if you like
    # Fetch data for the summary cards
    u_res = get_all_users()
    i_res = get_all_invoices()
    if u_res['status_code'] != 0 or i_res['status_code'] != 0:
        messages.error(request, "Failed to load dashboard metrics.")
        # fallback to zeros
        total_customers = total_invoices = pending_invoices = 0
    else:
        users = u_res['data']
        invoices = i_res['data']
        total_customers = len([u for u in users if u['role'] == 'customer'])
        total_invoices = len(invoices)
        pending_invoices = len(
            [inv for inv in invoices if inv['payment_status'] == 'Pending'])

    return render(request, "dashboard.html", {
        "total_customers":   total_customers,
        "total_invoices":    total_invoices,
        "pending_invoices":  pending_invoices,
    })


# --- Customer CRUD ---

@ensure_admin
def list_customers(request):
    res = get_all_users()
    if res['status_code'] != 0:
        messages.error(request, res['status_msg'])
        customers = []
    else:
        customers = [u for u in res['data'] if u['role'] == 'customer']
    return render(request, "customers/list.html", {"customers": customers})


@ensure_admin
def create_customer(request):
    form = CustomerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        r = create_user(cd['name'], cd['email'],
                        cd['password'], 'customer', cd['phone'])
        if r['status_code'] == 0:
            # fetch user_id
            user = get_user_by_email(cd['email'])
            if user:
                addr_res = add_billing_address(
                    user['user_id'], cd['billing_address'])
                if addr_res['status_code'] == 0:
                    messages.success(request, "Customer created successfully.")
                else:
                    messages.warning(
                        request, "User created; billing address failed.")
            else:
                messages.warning(request, "User created; could not verify ID.")
            return redirect('invoicing:list_customers')
        else:
            messages.error(request, r['status_msg'])
    return render(request, "customers/create.html", {"form": form})


@ensure_admin
def edit_customer(request, user_id):
    user_res = get_user_by_id(user_id)
    addr_res = get_billing_by_user(user_id)
    if user_res['status_code'] != 0:
        messages.error(request, "Customer not found.")
        return redirect('invoicing:list_customers')

    initial = {
        'name': user_res['data']['name'],
        'email': user_res['data']['email'],
        'phone': user_res['data']['phone'],
        'password': user_res['data']['password'],
        'billing_address': addr_res['data'][0]['billing_address'] if addr_res['data'] else ''
    }

    form = CustomerForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        u = update_user(user_id, cd['name'], cd['email'],
                        cd['password'], 'customer', cd['phone'])
        if u['status_code'] == 0:
            if addr_res['data']:
                addr_id = addr_res['data'][0]['address_id']
                update_billing_address(addr_id, cd['billing_address'])
            else:
                add_billing_address(user_id, cd['billing_address'])
            messages.success(request, "Customer updated.")
            return redirect('invoicing:list_customers')
        else:
            messages.error(request, u['status_msg'])

    return render(request, "customers/edit.html", {"form": form, "user_id": user_id})


@ensure_admin
def delete_customer(request, user_id):
    addr_res = get_billing_by_user(user_id)
    for addr in addr_res.get('data', []):
        delete_billing_address(addr['address_id'])
    d = delete_user(user_id)
    if d['status_code'] == 0:
        messages.success(request, "Customer deleted.")
    else:
        messages.error(request, d['status_msg'])
    return redirect('invoicing:list_customers')


# --- Product CRUD ---

@ensure_admin
def list_products(request):
    res = get_products_by_user(request.session['user_id'])
    products = res['data'] if res['status_code'] == 0 else []
    return render(request, "products/list.html", {"products": products})


@ensure_admin
def create_product(request):
    form = ProductForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        db_create_product(
            request.session['user_id'], cd['name'], cd['description'], cd['unit_price'], cd['is_available'])
        messages.success(request, "Product created.")
        return redirect('invoicing:list_products')
    return render(request, "products/form.html", {"form": form, "is_edit": False})


@ensure_admin
def edit_product(request, product_id):
    res = get_product_by_id(product_id)
    if res['status_code'] != 0:
        messages.error(request, "Product not found.")
        return redirect('invoicing:list_products')

    initial = res['data'].copy()
    initial['is_available'] = bool(res['data'].get('is_available', 0))
    form = ProductForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        db_update_product(product_id, name=cd['name'], description=cd['description'],
                          unit_price=cd['unit_price'], is_available=cd['is_available'])
        messages.success(request, "Product updated.")
        return redirect('invoicing:list_products')
    return render(request, "products/form.html", {"form": form, "is_edit": True})


@ensure_admin
def delete_product(request, product_id):
    db_delete_product(product_id)
    messages.success(request, "Product deleted.")
    return redirect('invoicing:list_products')

# --- Invoice CRUD  ---


@ensure_admin
def list_invoices(request):
    res = get_all_invoices()
    invoices = res['data'] if res['status_code'] == 0 else []
    return render(request, "invoices/list.html", {"invoices": invoices})


@ensure_admin
def view_invoice(request, invoice_id):
    # 1) Fetch invoice header
    ires = get_invoice_by_id(invoice_id)
    if ires['status_code'] != 0:
        messages.error(request, "Invoice not found.")
        return redirect('invoicing:list_invoices')
    invoice = ires['data']

    # 2) Customer info
    cust = get_user_by_id(invoice['user_id'])
    customer = cust['data'] if cust['status_code'] == 0 else {}

    # 3) Billing address (first one)
    addr = get_billing_by_user(invoice['user_id'])
    customer['address'] = addr['data'][0]['billing_address'] if addr['data'] else ''

    # 4) Owner (the admin viewing the invoice)
    adm = get_user_by_id(request.session['user_id'])
    owner = adm['data'] if adm['status_code'] == 0 else {}

    # 5) Line items with product names
    items = get_items_by_invoice(invoice_id).get('data', [])

    # 6) Payment date if any
    pay = get_payments_by_invoice(invoice_id)
    payment_date = pay['data'][-1]['payment_date'] if pay['status_code'] == 0 and pay['data'] else None

    return render(request, "invoices/detail.html", {
        "invoice": invoice,
        "customer": customer,
        "owner": owner,
        "items": items,
        "payment_date": payment_date,
    })


@ensure_admin
def delete_invoice(request, invoice_id):
    db_delete_invoice(invoice_id)
    messages.success(request, "Invoice deleted.")
    return redirect('invoicing:list_invoices')


@ensure_admin
def send_invoice(request, invoice_id):
    # 1) Fetch invoice, customer, owner, items, payment_date (unchanged)…
    ires = get_invoice_by_id(invoice_id)
    if ires['status_code'] != 0:
        messages.error(request, "Invoice not found.")
        return redirect('invoicing:list_invoices')
    invoice = ires['data']

    cust_res = get_user_by_id(invoice['user_id'])
    customer = cust_res['data'] if cust_res['status_code'] == 0 else {}
    addr_res = get_billing_by_user(invoice['user_id'])
    customer['address'] = addr_res['data'][0]['billing_address'] if addr_res['data'] else ''

    owner_res = get_user_by_id(request.session['user_id'])
    owner = owner_res['data'] if owner_res['status_code'] == 0 else {}

    items = get_items_by_invoice(invoice_id).get('data', [])
    pay_res = get_payments_by_invoice(invoice_id)
    payment_date = pay_res['data'][-1]['payment_date'] if pay_res['status_code'] == 0 and pay_res['data'] else None

    # 2) Render the new PDF‑optimized template
    html_string = render_to_string(
        'invoices/invoice_pdf.html',
        {
            'invoice': invoice,
            'owner': owner,
            'customer': customer,
            'items': items,
            'payment_date': payment_date,
            'now': timezone.now(),
        }
    )

    # 3) Prepare project‑local temp folder
    temp_dir = Path(settings.BASE_DIR) / "temp_invoices"
    temp_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = temp_dir / f"invoice_{invoice_id}.pdf"

    try:
        # 4) Generate PDF to that path
        weasyprint.HTML(string=html_string).write_pdf(str(pdf_path))

        # 5) Compose email
        subject = f"Invoice #{invoice_id} from InvoiceSys"
        if invoice['payment_status'] == 'Paid':
            body = (
                f"Dear {customer.get('name')},\n\n"
                f"Thank you for your payment on {payment_date:%d-%m-%Y}. "
                "Attached is your paid invoice for your records.\n\n"
                f"Best,\n{owner.get('name')}"
            )
        else:
            days_left = (invoice['due_date'] - datetime.now()).days
            body = (
                f"Dear {customer.get('name')},\n\n"
                f"Your invoice #{invoice_id} is due on {invoice['due_date']:%d-%m-%Y} "
                f"({days_left} days remaining). Please find it attached.\n\n"
                f"Thank you,\n{owner.get('name')}"
            )

        msg = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.get('email')],
        )
        # attach the generated PDF
        with open(pdf_path, 'rb') as f:
            msg.attach(f"Invoice_{invoice_id}.pdf",
                       f.read(), 'application/pdf')

        msg.send()
        messages.success(
            request, f"Invoice #{invoice_id} emailed to {customer.get('email')}")

    except Exception as e:
        messages.error(request, f"Failed to generate/send invoice: {e}")

    return redirect('invoicing:list_invoices')

# Customer views starts here protect customer‑only views


def ensure_customer(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.session.get('user_role') != 'customer':
            return redirect('invoicing:login')
        return view_func(request, *args, **kwargs)
    return _wrapped


@ensure_customer
def customer_dashboard(request):
    # you can pass summary counts if desired
    return render(request, "customer/dashboard.html")


@ensure_customer
def customer_invoices(request):
    res = get_all_invoices()
    invoices = []
    if res['status_code'] == 0:
        uid = request.session['user_id']
        invoices = [inv for inv in res['data'] if inv['user_id'] == uid]
    return render(request, "customer/invoices.html", {"invoices": invoices})


@ensure_customer
def customer_invoice_detail(request, invoice_id):
    ires = get_invoice_by_id(invoice_id)
    if ires['status_code'] != 0 or ires['data']['user_id'] != request.session['user_id']:
        messages.error(request, "Invoice not found.")
        return redirect('invoicing:customer_invoices')
    invoice = ires['data']

    # Customer info (you)
    cust = get_user_by_id(request.session['user_id'])
    customer = cust['data'] if cust['status_code'] == 0 else {}
    addr = get_billing_by_user(request.session['user_id'])
    customer['address'] = addr['data'][0]['billing_address'] if addr['data'] else ''

    # Owner info: static “company” or first admin user (ID=1) – adjust as needed
    comp = get_user_by_id(1)
    owner = comp['data'] if comp and comp['status_code'] == 0 else {
        'name': 'Your Company', 'email': 'info@company.com', 'phone': '123‑456', 'address': 'Company Address'
    }

    items = get_items_by_invoice(invoice_id).get('data', [])
    pay = get_payments_by_invoice(invoice_id)
    payment_date = pay['data'][-1]['payment_date'] if pay['status_code'] == 0 and pay['data'] else None

    return render(request, "customer/invoice_detail.html", {
        "invoice": invoice,
        "customer": customer,
        "owner": owner,
        "items": items,
        "payment_date": payment_date,
    })


@ensure_customer
@require_http_methods(["GET", "POST"])
def pay_invoice(request, invoice_id):
    # Ensure invoice belongs to this user
    ires = get_invoice_by_id(invoice_id)
    if ires['status_code'] != 0 or ires['data']['user_id'] != request.session['user_id']:
        messages.error(request, "Invoice not found.")
        return redirect('invoicing:customer_invoices')

    if request.method == "POST":
        method = request.POST.get("method")
        # 1) Record the payment
        pay_res = add_payment(
            invoice_id,
            method,
            transaction_reference="",       # no gateway, so blank
            payment_date=datetime.now()
        )
        if pay_res['status_code'] != 0:
            messages.error(request, f"Payment failed: {pay_res['status_msg']}")
            return redirect('invoicing:customer_invoice_detail', invoice_id)

        # 2) Update the invoice status to Paid
        upd_res = update_invoice(
            invoice_id,
            payment_status="Paid"
        )
        if upd_res['status_code'] != 0:
            messages.error(
                request, f"Payment recorded but failed to update invoice: {upd_res['status_msg']}")
            return redirect('invoicing:customer_invoice_detail', invoice_id)

        messages.success(
            request, "Payment successful! Your invoice is now marked as Paid.")
        return redirect('invoicing:customer_invoices')

    # GET: render the payment form
    return render(request, "customer/pay_invoice.html", {
        "invoice": ires['data']
    })


@ensure_customer
def customer_profile(request):
    # fetch the user & billing address
    user = get_user_by_id(request.session['user_id'])['data']
    addr_r = get_billing_by_user(request.session['user_id'])
    address = addr_r['data'][0] if addr_r['data'] else {}
    return render(request, "customer/profile.html", {"user": user, "address": address})


@ensure_customer
@require_http_methods(["GET", "POST"])
def edit_profile(request):
    user_id = request.session['user_id']
    # fetch existing values
    u_res = get_user_by_id(user_id)
    addr_res = get_billing_by_user(user_id)
    initial = {}
    if u_res['status_code'] == 0:
        initial['name'] = u_res['data']['name']
        initial['phone'] = u_res['data']['phone']
    if addr_res['status_code'] == 0 and addr_res['data']:
        initial['billing_address'] = addr_res['data'][0]['billing_address']

    if request.method == 'POST':
        form = ProfileForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            # update user
            update_user(user_id, cd['name'], u_res['data']['email'],
                        u_res['data']['password'], 'customer', cd['phone'])
            # update billing
            if addr_res['data']:
                update_billing_address(
                    addr_res['data'][0]['address_id'], cd['billing_address'])
            else:
                add_billing_address(user_id, cd['billing_address'])
            messages.success(request, "Profile updated.")
            return redirect('invoicing:customer_profile')
    else:
        form = ProfileForm(initial=initial)

    return render(request, "customer/edit_profile.html", {"form": form})


@ensure_customer
def customer_products(request):
    res = get_all_products()
    products = []
    if res['status_code'] == 0:
        products = [p for p in res['data'] if p['is_available']]
    return render(request, "customer/products.html", {"products": products})


@ensure_customer
def buy_product(request, product_id):
    user_id = request.session['user_id']

    # 1) create invoice header
    inv_res = create_invoice(user_id)
    print(inv_res)
    if inv_res['status_code'] != 0:
        messages.error(request, inv_res['status_msg'])
        return redirect('invoicing:customer_products')
    invoice_id = inv_res['invoice_id']

    # 2) add the line item
    p_res = get_product_by_id(product_id)
    if p_res['status_code'] != 0:
        messages.error(request, "Product not found.")
        return redirect('invoicing:customer_products')

    unit_price = p_res['data']['unit_price']
    add_item_res = add_invoice_item(invoice_id, product_id, 1, unit_price)
    if add_item_res['status_code'] != 0:
        messages.error(request, add_item_res['status_msg'])
        return redirect('invoicing:customer_products')

    # 3) mark the product sold
    sold_res = mark_product_sold(product_id)
    if sold_res['status_code'] != 0:
        messages.warning(
            request, "Invoice created, but failed to mark product sold.")

    messages.success(
        request, f"Invoice #{invoice_id} created. Check your Invoices.")
    return redirect('invoicing:customer_invoices')
