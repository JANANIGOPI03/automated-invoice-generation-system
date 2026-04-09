# invoicing/db.py
import pyodbc
from django.conf import settings
from datetime import datetime, timedelta


def get_conn():
    """
    Connect to the MS Access database using pyodbc.
    Ensure ACCESS_DB_PATH is defined in Django settings.
    """
    conn_str = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        rf"DBQ={settings.ACCESS_DB_PATH};"
    )
    return pyodbc.connect(conn_str, autocommit=True)


def _execute(sql, params=()):
    """
    Helper for INSERT/UPDATE/DELETE.
    Returns dict with status_code (0=success, 1=error) and status_msg.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        conn.close()
        return {"status_code": 0, "status_msg": "Success"}
    except Exception as e:
        return {"status_code": 1, "status_msg": str(e)}


def _fetchall(sql, params=()):
    """
    Helper for SELECT queries.
    Returns dict with status_code, status_msg, and data (list of dicts).
    """
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
        data = [dict(zip(cols, row)) for row in rows]
        cur.close()
        conn.close()
        return {"status_code": 0, "status_msg": "Success", "data": data}
    except Exception as e:
        return {"status_code": 1, "status_msg": str(e), "data": []}


# -----------------------
# Users CRUD
# -----------------------

def create_user(name, email, password, role, phone=None):
    sql = """
        INSERT INTO Users (name, email, password, role, phone)
        VALUES (?, ?, ?, ?, ?)
    """
    return _execute(sql, (name, email, password, role, phone))


def get_user_by_id(user_id):
    res = _fetchall(
        "SELECT user_id, name, email, role, phone, password FROM Users WHERE user_id = ?",
        (user_id,)
    )
    if res["status_code"] == 0:
        if res["data"]:
            res["data"] = res["data"][0]
        else:
            res["status_code"] = 2
            res["status_msg"] = "User not found"
    return res


def get_all_users():
    return _fetchall(
        "SELECT user_id, name, email, role, phone FROM Users",
        ()
    )


def update_user(user_id, name=None, email=None, password=None, role=None, phone=None):
    fields = []
    params = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if email is not None:
        fields.append("email = ?")
        params.append(email)
    if password is not None:
        fields.append("password = ?")
        params.append(password)
    if role is not None:
        fields.append("role = ?")
        params.append(role)
    if phone is not None:
        fields.append("phone = ?")
        params.append(phone)
    if not fields:
        return {"status_code": 3, "status_msg": "No fields to update"}
    params.append(user_id)
    sql = f"UPDATE Users SET {', '.join(fields)} WHERE user_id = ?"
    return _execute(sql, params)


def delete_user(user_id):
    return _execute(
        "DELETE FROM Users WHERE user_id = ?",
        (user_id,)
    )


# -----------------------
# BillingAddresses CRUD
# -----------------------

def add_billing_address(user_id, billing_address):
    sql = """
        INSERT INTO BillingAddresses (user_id, billing_address)
        VALUES (?, ?)
    """
    return _execute(sql, (user_id, billing_address))


def get_billing_by_user(user_id):
    return _fetchall(
        "SELECT address_id, user_id, billing_address "
        "FROM BillingAddresses WHERE user_id = ?",
        (user_id,)
    )


def update_billing_address(address_id, billing_address):
    return _execute(
        "UPDATE BillingAddresses SET billing_address = ? WHERE address_id = ?",
        (billing_address, address_id)
    )


def delete_billing_address(address_id):
    return _execute(
        "DELETE FROM BillingAddresses WHERE address_id = ?",
        (address_id,)
    )


# -----------------------
# Products CRUD
# -----------------------

def create_product(user_id, name, description, unit_price, is_available=True):
    sql = """
        INSERT INTO Products (user_id, name, description, unit_price, is_available)
        VALUES (?, ?, ?, ?, ?)
    """
    return _execute(sql, (user_id, name, description, unit_price, int(is_available)))


def get_product_by_id(product_id):
    res = _fetchall(
        "SELECT product_id, user_id, name, description, unit_price "
        "FROM Products WHERE product_id = ?",
        (product_id,)
    )
    if res["status_code"] == 0:
        if res["data"]:
            res["data"] = res["data"][0]
        else:
            res["status_code"] = 2
            res["status_msg"] = "Product not found"
    return res


def get_products_by_user(user_id):
    return _fetchall(
        "SELECT product_id, user_id, name, description, unit_price, is_available "
        "FROM Products WHERE user_id = ?",
        (user_id,)
    )


def update_product(product_id, name=None, description=None, unit_price=None, is_available=None):
    fields = []
    params = []
    if name is not None:
        fields.append("name = ?")
        params.append(name)
    if description is not None:
        fields.append("description = ?")
        params.append(description)
    if unit_price is not None:
        fields.append("unit_price = ?")
        params.append(unit_price)
    if is_available is not None:
        fields.append("is_available = ?")
        params.append(int(is_available))
    if not fields:
        return {"status_code": 3, "status_msg": "No fields to update"}
    params.append(product_id)
    sql = f"UPDATE Products SET {', '.join(fields)} WHERE product_id = ?"
    return _execute(sql, params)


def delete_product(product_id):
    return _execute(
        "DELETE FROM Products WHERE product_id = ?",
        (product_id,)
    )


# -----------------------
# Invoices CRUD
# -----------------------

def create_invoice(user_id, invoice_date, due_date, total_amount, payment_status):
    sql = """
        INSERT INTO Invoices (
            user_id, invoice_date, due_date, total_amount, payment_status
        ) VALUES (?, ?, ?, ?, ?)
    """
    return _execute(sql, (user_id, invoice_date, due_date, total_amount, payment_status))


def get_invoice_by_id(invoice_id):
    res = _fetchall(
        "SELECT invoice_id, user_id, invoice_date, due_date, total_amount, payment_status "
        "FROM Invoices WHERE invoice_id = ?",
        (invoice_id,)
    )
    if res["status_code"] == 0:
        if res["data"]:
            res["data"] = res["data"][0]
        else:
            res["status_code"] = 2
            res["status_msg"] = "Invoice not found"
    return res


def get_invoices_by_user(user_id):
    return _fetchall(
        "SELECT invoice_id, user_id, invoice_date, due_date, total_amount, payment_status "
        "FROM Invoices WHERE user_id = ?",
        (user_id,)
    )


def get_all_invoices():
    """
    Returns all invoices, including the customers user_name.
    """
    sql = """
      SELECT 
        i.invoice_id,
        i.user_id,
        u.name   AS user_name,
        i.invoice_date,
        i.due_date,
        i.total_amount,
        i.payment_status
      FROM Invoices AS i
      INNER JOIN Users    AS u
        ON i.user_id = u.user_id
    """
    return _fetchall(sql, ())


def update_invoice(invoice_id, invoice_date=None, due_date=None, total_amount=None, payment_status=None):
    fields = []
    params = []
    if invoice_date is not None:
        fields.append("invoice_date = ?")
        params.append(invoice_date)
    if due_date is not None:
        fields.append("due_date = ?")
        params.append(due_date)
    if total_amount is not None:
        fields.append("total_amount = ?")
        params.append(total_amount)
    if payment_status is not None:
        fields.append("payment_status = ?")
        params.append(payment_status)
    if not fields:
        return {"status_code": 3, "status_msg": "No fields to update"}
    params.append(invoice_id)
    sql = f"UPDATE Invoices SET {', '.join(fields)} WHERE invoice_id = ?"
    return _execute(sql, params)


def delete_invoice(invoice_id):
    return _execute(
        "DELETE FROM Invoices WHERE invoice_id = ?",
        (invoice_id,)
    )


# -----------------------
# Invoice_Items CRUD
# -----------------------

def add_invoice_item(invoice_id, product_id, quantity, subtotal):
    sql = """
        INSERT INTO Invoice_Items (invoice_id, product_id, quantity, subtotal)
        VALUES (?, ?, ?, ?)
    """
    return _execute(sql, (invoice_id, product_id, quantity, subtotal))


def get_items_by_invoice(invoice_id):
    """
    Returns line items including the product name.
    """
    sql = """
      SELECT 
        ii.item_id,
        ii.invoice_id,
        ii.product_id,
        p.name AS product_name,
        p.unit_price AS unit_price,
        ii.quantity,
        ii.subtotal
      FROM Invoice_Items AS ii
      INNER JOIN Products AS p
        ON ii.product_id = p.product_id
      WHERE ii.invoice_id = ?
    """
    return _fetchall(sql, (invoice_id,))


def update_invoice_item(item_id, quantity=None, subtotal=None):
    fields = []
    params = []
    if quantity is not None:
        fields.append("quantity = ?")
        params.append(quantity)
    if subtotal is not None:
        fields.append("subtotal = ?")
        params.append(subtotal)
    if not fields:
        return {"status_code": 3, "status_msg": "No fields to update"}
    params.append(item_id)
    sql = f"UPDATE Invoice_Items SET {', '.join(fields)} WHERE item_id = ?"
    return _execute(sql, params)


def delete_invoice_item(item_id):
    return _execute(
        "DELETE FROM Invoice_Items WHERE item_id = ?",
        (item_id,)
    )


# -----------------------
# Payments CRUD
# -----------------------

def add_payment(invoice_id, payment_method, transaction_reference, payment_date):
    sql = """
        INSERT INTO Payments (invoice_id, payment_method, transaction_reference, payment_date)
        VALUES (?, ?, ?, ?)
    """
    return _execute(sql, (invoice_id, payment_method, transaction_reference, payment_date))


def get_payments_by_invoice(invoice_id):
    return _fetchall(
        "SELECT payment_id, invoice_id, payment_method, transaction_reference, payment_date "
        "FROM Payments WHERE invoice_id = ?",
        (invoice_id,)
    )


def update_payment(payment_id, payment_method=None, transaction_reference=None, payment_date=None):
    fields = []
    params = []
    if payment_method is not None:
        fields.append("payment_method = ?")
        params.append(payment_method)
    if transaction_reference is not None:
        fields.append("transaction_reference = ?")
        params.append(transaction_reference)
    if payment_date is not None:
        fields.append("payment_date = ?")
        params.append(payment_date)
    if not fields:
        return {"status_code": 3, "status_msg": "No fields to update"}
    params.append(payment_id)
    sql = f"UPDATE Payments SET {', '.join(fields)} WHERE payment_id = ?"
    return _execute(sql, params)


def delete_payment(payment_id):
    return _execute(
        "DELETE FROM Payments WHERE payment_id = ?",
        (payment_id,)
    )


def get_user_by_email(email):
    """
    Fetch a single user by email. Returns dict or None.
    """
    res = _fetchall(
        "SELECT user_id, name, email, password, role, phone "
        "FROM Users WHERE email = ?",
        (email,)
    )
    if res["status_code"] != 0 or not res["data"]:
        return None
    return res["data"][0]


def get_all_products():
    """
    Returns all products, including their availability.
    """
    return _fetchall("""
        SELECT 
            product_id,
            user_id,
            name,
            description,
            unit_price,
            is_available
        FROM Products
    """)


def create_invoice(user_id):
    """
    Creates a new invoice for the given customer_id (user_id).
    Due date = invoice_date + 30 days.
    Returns {'status_code':0,'invoice_id':<new id>} on success.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()

        now = datetime.now()
        due = now + timedelta(days=30)

        # Insert header
        cur.execute("""
            INSERT INTO Invoices
              (user_id, invoice_date, due_date, total_amount, payment_status)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, now, due, 0.0, 'Pending'))
        conn.commit()

        # Fetch new autonumber
        cur.execute("SELECT @@IDENTITY")
        new_id = int(cur.fetchone()[0])

        cur.close()
        conn.close()
        return {"status_code": 0, "invoice_id": new_id}
    except Exception as e:
        return {"status_code": 1, "status_msg": str(e)}


def add_invoice_item(invoice_id, product_id, quantity, unit_price):
    """
    Adds a line item to the invoice and updates the invoice total.
    """
    try:
        conn = get_conn()
        cur = conn.cursor()

        subtotal = quantity * unit_price

        # 1) Insert into line‐items table
        cur.execute("""
            INSERT INTO Invoice_Items
              (invoice_id, product_id, quantity, subtotal)
            VALUES (?, ?, ?, ?)
        """, (invoice_id, product_id, quantity, subtotal))

        # 2) Update the invoice_total
        cur.execute("""
            UPDATE Invoices
            SET total_amount = total_amount + ?
            WHERE invoice_id = ?
        """, (subtotal, invoice_id))

        conn.commit()
        cur.close()
        conn.close()
        return {"status_code": 0}
    except Exception as e:
        return {"status_code": 1, "status_msg": str(e)}


def mark_product_sold(product_id):
    """
    Marks the given product as no longer available.
    """
    return _execute(
        "UPDATE Products SET is_available = 0 WHERE product_id = ?",
        (product_id,)
    )
