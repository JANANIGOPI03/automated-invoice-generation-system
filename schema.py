import os
import pyodbc

# Path to the Access DB file (must exist and be empty initially)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "invoices.accdb")

CONN_STR = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    fr"DBQ={DB_PATH};"
)


def get_conn():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database file not found: {DB_PATH}")
    return pyodbc.connect(CONN_STR, autocommit=True)


def main():
    conn = get_conn()
    cursor = conn.cursor()

    # 1) Drop the unique index on Users.email, if present
    try:
        cursor.execute("DROP INDEX idxUsersEmail ON Users")
        print("Dropped index idxUsersEmail")
    except pyodbc.Error:
        pass  # index didn’t exist

    # 2) Drop tables in reverse‑dependency order
    for tbl in (
        "Payments",
        "Invoice_Items",
        "Invoices",
        "Products",
        "BillingAddresses",
        "Users"
    ):
        try:
            cursor.execute(f"DROP TABLE {tbl}")
            print(f"Dropped table {tbl}")
        except pyodbc.Error:
            pass

    # 3) Recreate tables and constraints

    # Users
    cursor.execute("""
        CREATE TABLE Users (
            user_id   COUNTER       PRIMARY KEY,
            name      TEXT(255)     NOT NULL,
            email     TEXT(255)     NOT NULL,
            password  TEXT(255)     NOT NULL,
            role      TEXT(50)      NOT NULL,
            phone     TEXT(50)
        )
    """
                   )
    cursor.execute("CREATE UNIQUE INDEX idxUsersEmail ON Users (email)")
    print("Created Users + idxUsersEmail")

    # BillingAddresses
    cursor.execute("""
        CREATE TABLE BillingAddresses (
            address_id      COUNTER PRIMARY KEY,
            user_id         LONG    NOT NULL,
            billing_address MEMO    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """
                   )
    print("Created BillingAddresses")

    # Products (now linked to Users)
    cursor.execute("""
        CREATE TABLE Products (
            product_id  COUNTER    PRIMARY KEY,
            user_id     LONG       NOT NULL,
            name        TEXT(255)  NOT NULL,
            description MEMO,
            unit_price  CURRENCY   NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """
                   )
    print("Created Products")

    # Invoices
    cursor.execute("""
        CREATE TABLE Invoices (
            invoice_id     COUNTER   PRIMARY KEY,
            user_id        LONG      NOT NULL,
            invoice_date   DATETIME  NOT NULL,
            due_date       DATETIME  NOT NULL,
            total_amount   CURRENCY  NOT NULL,
            payment_status TEXT(50)  NOT NULL,
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """
                   )
    print("Created Invoices")

    # Invoice_Items
    cursor.execute("""
        CREATE TABLE Invoice_Items (
            item_id    COUNTER    PRIMARY KEY,
            invoice_id LONG       NOT NULL,
            product_id LONG       NOT NULL,
            quantity   LONG       NOT NULL,
            subtotal   CURRENCY   NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES Invoices(invoice_id),
            FOREIGN KEY (product_id) REFERENCES Products(product_id)
        )
    """
                   )
    print("Created Invoice_Items")

    # Payments
    cursor.execute("""
        CREATE TABLE Payments (
            payment_id            COUNTER    PRIMARY KEY,
            invoice_id            LONG       NOT NULL,
            payment_method        TEXT(50)   NOT NULL,
            transaction_reference TEXT(255),
            payment_date          DATETIME   NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES Invoices(invoice_id)
        )
    """
                   )
    print("Created Payments")

    cursor.close()
    conn.close()
    print("✅ Schema creation complete.")


if __name__ == "__main__":
    main()
