from flask import Flask, render_template, jsonify, request, redirect
import mysql.connector

app = Flask(__name__)

# MySQL Database Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="cherry1810",
    database="inventory_db",
    autocommit=True,
    connect_timeout=10
)

cursor = db.cursor(dictionary=True)


# =========================
# DASHBOARD
# =========================

@app.route("/")
def home():
    return render_template("dashboard.html")


# =========================
# DASHBOARD STATISTICS
# =========================

@app.route("/dashboard-stats")
def dashboard_stats():
    db.ping(reconnect=True, attempts=3, delay=1)

    # Total products
    cursor.execute("SELECT COUNT(*) AS total FROM products")
    total_products = cursor.fetchone()["total"]

    # Total categories
    cursor.execute("SELECT COUNT(*) AS total FROM categories")
    total_categories = cursor.fetchone()["total"]

    # Total suppliers
    cursor.execute("SELECT COUNT(*) AS total FROM suppliers")
    total_suppliers = cursor.fetchone()["total"]

    # Total customers
    cursor.execute("SELECT COUNT(*) AS total FROM customers")
    total_customers = cursor.fetchone()["total"]

    # Low stock products
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM products
        WHERE quantity <= reorder_level
    """)
    low_stock = cursor.fetchone()["total"]

    # Total stock quantity
    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total
        FROM products
    """)
    total_stock = cursor.fetchone()["total"]
    # Total inventory value
    cursor.execute("""
    SELECT COALESCE(SUM(price * quantity), 0) AS total
    FROM products""")
    inventory_value = cursor.fetchone()["total"]

    return jsonify({
        "total_products": total_products,
        "total_categories": total_categories,
        "total_suppliers": total_suppliers,
        "total_customers": total_customers,
        "low_stock": low_stock,
        "total_stock": total_stock,
        "inventory_value": float(inventory_value)
    })


# =========================
# PRODUCTS API
# =========================

@app.route("/products")
def get_products():
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return jsonify(products)


# =========================
# PRODUCTS PAGE
# =========================

@app.route("/products-page")
def products_page():
    return render_template("products.html")
# =========================
# CATEGORIES
# =========================

@app.route("/categories-page")
def categories_page():

    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()

    return render_template("categories.html", categories=categories)


@app.route("/add-category", methods=["POST"])
def add_category():

    category_name = request.form["category_name"]
    description = request.form["description"]

    sql = """
    INSERT INTO categories
    (category_name, description)
    VALUES (%s, %s)
    """

    values = (
        category_name,
        description
    )

    cursor.execute(sql, values)
    db.commit()

    return redirect("/categories-page")
# =========================
# SUPPLIERS
# =========================

@app.route("/suppliers-page")
def suppliers_page():

    cursor.execute("SELECT * FROM suppliers")
    suppliers = cursor.fetchall()

    return render_template("suppliers.html", suppliers=suppliers)


@app.route("/add-supplier", methods=["POST"])
def add_supplier():

    supplier_name = request.form["supplier_name"]
    phone = request.form["phone"]
    email = request.form["email"]
    address = request.form["address"]

    sql = """
    INSERT INTO suppliers
    (supplier_name, phone, email, address)
    VALUES (%s, %s, %s, %s)
    """

    values = (
        supplier_name,
        phone,
        email,
        address
    )

    cursor.execute(sql, values)
    db.commit()

    return redirect("/suppliers-page")
# =========================
# CUSTOMERS
# =========================

@app.route("/customers-page")
def customers_page():

    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()

    return render_template("customers.html", customers=customers)


@app.route("/add-customer", methods=["POST"])
def add_customer():

    customer_name = request.form["customer_name"]
    phone = request.form["phone"]
    email = request.form["email"]
    address = request.form["address"]

    sql = """
    INSERT INTO customers
    (customer_name, phone, email, address)
    VALUES (%s, %s, %s, %s)
    """

    values = (
        customer_name,
        phone,
        email,
        address
    )

    cursor.execute(sql, values)
    db.commit()

    return redirect("/customers-page")
# =========================
# STOCK IN
# =========================

@app.route("/stock-in-page")
def stock_in_page():

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    return render_template("stock_in.html", products=products)


@app.route("/stock-in", methods=["POST"])
def stock_in():

    product_id = request.form["product_id"]
    quantity = int(request.form["quantity"])

    # Increase product quantity
    cursor.execute(
        """
        UPDATE products
        SET quantity = quantity + %s
        WHERE product_id = %s
        """,
        (quantity, product_id)
    )

    # Record transaction
    cursor.execute(
        """
        INSERT INTO stock_transactions
        (product_id, transaction_type, quantity)
        VALUES (%s, 'IN', %s)
        """,
        (product_id, quantity)
    )

    db.commit()

    return redirect("/stock-in-page")
# =========================
# STOCK OUT
# =========================

@app.route("/stock-out-page")
def stock_out_page():

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    return render_template("stock_out.html", products=products)


@app.route("/stock-out", methods=["POST"])
def stock_out():

    product_id = request.form["product_id"]
    quantity = int(request.form["quantity"])

    cursor.execute(
        "SELECT quantity FROM products WHERE product_id = %s",
        (product_id,)
    )

    product = cursor.fetchone()

    if product is None:
        return "Product not found"

    if quantity > product["quantity"]:
        return "Not enough stock available!"

    cursor.execute(
        """
        UPDATE products
        SET quantity = quantity - %s
        WHERE product_id = %s
        """,
        (quantity, product_id)
    )

    cursor.execute(
        """
        INSERT INTO stock_transactions
        (product_id, transaction_type, quantity)
        VALUES (%s, 'OUT', %s)
        """,
        (product_id, quantity)
    )

    db.commit()

    return redirect("/stock-out-page")
# =========================
# PURCHASES
# =========================

@app.route("/purchases-page")
def purchases_page():

    cursor.execute("SELECT * FROM suppliers")
    suppliers = cursor.fetchall()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    cursor.execute("""
        SELECT
            purchases.purchase_id,
            suppliers.supplier_name,
            products.product_name,
            purchases.quantity,
            purchases.purchase_price,
            purchases.purchase_date
        FROM purchases
        JOIN suppliers
            ON purchases.supplier_id = suppliers.supplier_id
        JOIN products
            ON purchases.product_id = products.product_id
        ORDER BY purchases.purchase_id DESC
    """)

    purchases = cursor.fetchall()

    return render_template(
        "purchase.html",
        suppliers=suppliers,
        products=products,
        purchases=purchases
    )


@app.route("/add-purchase", methods=["POST"])
def add_purchase():

    supplier_id = request.form["supplier_id"]
    product_id = request.form["product_id"]
    quantity = int(request.form["quantity"])
    purchase_price = request.form["purchase_price"]

    # Add purchase record
    cursor.execute(
        """
        INSERT INTO purchases
        (supplier_id, product_id, quantity, purchase_price)
        VALUES (%s, %s, %s, %s)
        """,
        (supplier_id, product_id, quantity, purchase_price)
    )

    # Increase product stock
    cursor.execute(
        """
        UPDATE products
        SET quantity = quantity + %s
        WHERE product_id = %s
        """,
        (quantity, product_id)
    )

    # Record stock transaction
    cursor.execute(
        """
        INSERT INTO stock_transactions
        (product_id, transaction_type, quantity)
        VALUES (%s, 'IN', %s)
        """,
        (product_id, quantity)
    )

    db.commit()

    return redirect("/purchases-page")
# =========================
# SALES
# =========================

@app.route("/sales-page")
def sales_page():

    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()

    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()

    cursor.execute("""
        SELECT
            sales.sale_id,
            customers.customer_name,
            products.product_name,
            sales.quantity,
            sales.selling_price,
            sales.sale_date
        FROM sales
        JOIN customers
            ON sales.customer_id = customers.customer_id
        JOIN products
            ON sales.product_id = products.product_id
        ORDER BY sales.sale_id DESC
    """)

    sales = cursor.fetchall()

    return render_template(
        "sales.html",
        customers=customers,
        products=products,
        sales=sales
    )


@app.route("/add-sale", methods=["POST"])
def add_sale():

    customer_id = request.form["customer_id"]
    product_id = request.form["product_id"]
    quantity = int(request.form["quantity"])
    selling_price = request.form["selling_price"]

    # Check available stock
    cursor.execute(
        "SELECT quantity FROM products WHERE product_id = %s",
        (product_id,)
    )

    product = cursor.fetchone()

    if product is None:
        return "Product not found"

    if quantity > product["quantity"]:
        return "Not enough stock available!"

    # Add sale record
    cursor.execute(
        """
        INSERT INTO sales
        (customer_id, product_id, quantity, selling_price)
        VALUES (%s, %s, %s, %s)
        """,
        (customer_id, product_id, quantity, selling_price)
    )

    # Decrease product stock
    cursor.execute(
        """
        UPDATE products
        SET quantity = quantity - %s
        WHERE product_id = %s
        """,
        (quantity, product_id)
    )

    # Record stock transaction
    cursor.execute(
        """
        INSERT INTO stock_transactions
        (product_id, transaction_type, quantity)
        VALUES (%s, 'OUT', %s)
        """,
        (product_id, quantity)
    )

    db.commit()

    return redirect("/sales-page")
# =========================
# TRANSACTIONS
# =========================

@app.route("/transactions-page")
def transactions_page():

    cursor.execute("""
        SELECT
            stock_transactions.transaction_id,
            products.product_name,
            stock_transactions.transaction_type,
            stock_transactions.quantity,
            stock_transactions.transaction_date
        FROM stock_transactions
        JOIN products
            ON stock_transactions.product_id = products.product_id
        ORDER BY stock_transactions.transaction_id DESC
    """)

    transactions = cursor.fetchall()

    return render_template(
        "transactions.html",
        transactions=transactions
    )

# =========================
# ADD PRODUCT
# =========================

@app.route("/add-product", methods=["GET", "POST"])
def add_product():

    if request.method == "POST":

        product_name = request.form["product_name"]
        category_id = request.form["category_id"]
        supplier_id = request.form["supplier_id"]
        price = request.form["price"]
        quantity = request.form["quantity"]
        reorder_level = request.form["reorder_level"]

        sql = """
        INSERT INTO products
        (product_name, category_id, supplier_id, price, quantity, reorder_level)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        values = (
            product_name,
            category_id,
            supplier_id,
            price,
            quantity,
            reorder_level
        )

        cursor.execute(sql, values)
        db.commit()

        return redirect("/products-page")

    return render_template("add_product.html")


# =========================
# EDIT PRODUCT
# =========================

@app.route("/edit-product/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):

    if request.method == "POST":

        product_name = request.form["product_name"]
        category_id = request.form["category_id"]
        supplier_id = request.form["supplier_id"]
        price = request.form["price"]
        quantity = request.form["quantity"]
        reorder_level = request.form["reorder_level"]

        sql = """
        UPDATE products
        SET product_name = %s,
            category_id = %s,
            supplier_id = %s,
            price = %s,
            quantity = %s,
            reorder_level = %s
        WHERE product_id = %s
        """

        values = (
            product_name,
            category_id,
            supplier_id,
            price,
            quantity,
            reorder_level,
            product_id
        )

        cursor.execute(sql, values)
        db.commit()

        return redirect("/products-page")

    cursor.execute(
        "SELECT * FROM products WHERE product_id = %s",
        (product_id,)
    )

    product = cursor.fetchone()

    return render_template("edit_product.html", product=product)


# =========================
# RUN FLASK
# =========================
# =========================
# DELETE PRODUCT
# =========================

@app.route("/delete-product/<int:product_id>")
def delete_product(product_id):

    cursor.execute(
        "DELETE FROM products WHERE product_id = %s",
        (product_id,)
    )

    db.commit()

    return redirect("/products-page")
if __name__ == "__main__":
    app.run(debug=True)