from flask import current_app, Blueprint, render_template, request, redirect, url_for, flash
from .extensions import db
from sqlalchemy import text
from werkzeug.utils import secure_filename
import os
import sqlite3
from collections import defaultdict
from sqlalchemy.exc import IntegrityError
from flask_login import UserMixin, logout_user, login_required, login_user, current_user
from app import login_manager
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

main = Blueprint('main', __name__)
DB_PATH = "instance/inventory.db"

class User(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash


@login_manager.user_loader
def load_user(user_id):
    result = db.session.execute(
        text("SELECT id, username, email, password_hash FROM user WHERE id = :id"),
        {"id": user_id}
    ).fetchone()

    if result:
        return User(result.id, result.username, result.email, result.password_hash)
    return None

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        print("Register POST received")  # debug
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not username or not email or not password or not confirm_password:
            flash('Please fill out all fields.', 'danger')
            return redirect(url_for('main.register'))

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('main.register'))

        user_exists = db.session.execute(
            text("SELECT id FROM user WHERE username = :username OR email = :email"),
            {"username": username, "email": email}
        ).fetchone()

        if user_exists:
            flash('Username or email already registered.', 'danger')
            return redirect(url_for('main.register'))

        password_hash = generate_password_hash(password)

        try:
            db.session.execute(
                text("INSERT INTO user (username, email, password_hash) VALUES (:username, :email, :password_hash)"),
                {"username": username, "email": email, "password_hash": password_hash}
            )
            db.session.commit()
        except Exception as e:
            print("DB Insert Error:", e)
            flash('An error occurred. Please try again.', 'danger')
            return redirect(url_for('main.register'))

        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('main.login'))

    return render_template('register.html')

@main.route('/')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('main.login'))
    return render_template('home.html')

@main.route('/inventory')
@login_required
def inventory():
    query = text("""
                WITH ranked_deliveries AS (
                    SELECT 
                        a.item_id,
                        a.unit_id,
                        a.price,
                        a.quantity,
                        a.date,
                        ROW_NUMBER() OVER (PARTITION BY a.item_id, a.unit_id ORDER BY a.date DESC) AS rn
                    FROM actions a
                    WHERE a.action_type = 'delivery'
                ),
                latest_delivery AS (
                    SELECT 
                        item_id,
                        unit_id,
                        price,
                        quantity
                    FROM ranked_deliveries
                    WHERE rn = 1
                ),
                inventory_summary AS (
                    SELECT 
                        item_id,
                        unit_id,
                        MAX(date) AS latest_date,
                        SUM(CASE 
                                WHEN action_type = 'delivery' THEN quantity
                                WHEN action_type IN ('sales', 'consumption', 'waste') THEN -quantity
                                ELSE 0 
                            END) AS net_quantity
                    FROM actions
                    GROUP BY item_id, unit_id
                )
                SELECT 
                    i.name AS item_name,
                    u.name AS unit_name,
                    s.latest_date,
                    ROUND(s.net_quantity, 1) AS net_quantity,
                    ROUND(s.net_quantity * (ld.price * 1.0 / NULLIF(ld.quantity, 0)), 2) AS total_price
                FROM inventory_summary s
                LEFT JOIN latest_delivery ld
                    ON s.item_id = ld.item_id AND s.unit_id = ld.unit_id
                JOIN item i ON s.item_id = i.id
                JOIN unit u ON s.unit_id = u.id
                ORDER BY s.latest_date DESC;

    """)

    inventory = db.session.execute(query).fetchall()
    total_inventory_price = sum(row.total_price for row in inventory if row.total_price)
    formatted_total_inventory = f"${total_inventory_price:,.2f}"
    return render_template('inventory.html', inventory=inventory, total_inventory_price=total_inventory_price, formatted_total_inventory=formatted_total_inventory)

@main.route('/action', methods=['GET', 'POST'])
@login_required
def action():
    if request.method == 'POST':
        date = request.form['date']
        action_type = request.form['action_type']
        category_ids = request.form.getlist('category_id[]')
        item_ids = request.form.getlist('item_id[]')
        unit_ids = request.form.getlist('unit_id[]')
        quantities = request.form.getlist('quantity[]')
        prices = request.form.getlist('price[]')
        photo = request.files.get('photo')

        photo_path = None
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo_dir = os.path.join(current_app.root_path, 'static/uploads')
            os.makedirs(photo_dir, exist_ok=True)
            photo.save(os.path.join(photo_dir, filename))
            photo_path = f'static/uploads/{filename}'

        for category_id, item_id, unit_id, quantity, price in zip(category_ids, item_ids, unit_ids, quantities, prices):
            try:
                if float(quantity) <= 0:  
                    flash("Quantity must be greater than 0.", "danger")
                    return redirect(url_for('main.action'))
                if price and float(price) <= 0:
                    flash("Price must be greater than 0.", "danger")
                    return redirect(url_for('main.action')) 
            except ValueError:
                flash("Please enter valid numeric value for qunatity and pricec", "danger")
                return redirect(url_for('main.action')) 
                             
            db.session.execute(text("""
                INSERT INTO actions (date, action_type, category_id, item_id, unit_id, quantity, price, photo_path)
                VALUES (:date, :action_type, :category_id, :item_id, :unit_id, :quantity, :price, :photo_path)
            """), {
                'date': date,
                'action_type': action_type,
                'category_id': category_id,
                'item_id': item_id,
                'unit_id': unit_id,
                'quantity': quantity,
                'price': price,
                'photo_path': photo_path
            })

        db.session.commit()
        return redirect(url_for('main.action'))
    categories = db.session.execute(text("SELECT id, name FROM category ORDER BY name")).fetchall()
    items = db.session.execute(text("SELECT id, name FROM item ORDER BY name")).fetchall()
    units = db.session.execute(text("SELECT id, name FROM unit ORDER by name")).fetchall()

    actions = db.session.execute(text("""
        SELECT a.id, a.date, a.action_type, c.name as category_name, i.name AS item_name, u.name AS unit_name, a.quantity, a.price, a.photo_path
        FROM actions a
        JOIN category c ON a.category_id = c.id
        JOIN item i ON a.item_id = i.id
        JOIN unit u ON a.unit_id = u.id
        ORDER BY a.date DESC
    """)).fetchall()

    return render_template('action.html', categories=categories, items=items, units=units, actions=actions)

@main.route('/action/delete', methods=['POST'])
@login_required
def delete_action():
    action_id = request.form.get('action_id')
    if not action_id:
        flash('No action selected to delete.', 'danger')
        return redirect(url_for('main.action'))

    db.session.execute(
        text("DELETE FROM actions WHERE id = :id"),
        {"id": action_id}
    )
    db.session.commit()
    return redirect(url_for('main.action'))




@main.route("/inventory_setup", methods=["GET", "POST"])
@login_required
def inventory_setup():
    if request.method == "POST":
        action = request.form.get("action")

        if action == "add_item":
            name = request.form.get("item_name")
            if name:
                try:
                    db.session.execute(
                        text("INSERT INTO item (name) VALUES (:name)"), {"name": name}
                    )
                    db.session.commit()
                    flash("Item added successfully!", "success")
                except IntegrityError:
                    db.session.rollback()
                    flash("Item already exists!", "danger")

        elif action == "add_category":
            name = request.form.get("category_name")
            if name:
                try:
                    db.session.execute(
                        text("INSERT INTO category (name) VALUES (:name)"), {"name": name}
                    )
                    db.session.commit()
                    flash("Category added successfully!", "success")
                except IntegrityError:
                    db.session.rollback()
                    flash("Category already exists!", "danger")

        elif action == "add_unit":
            name = request.form.get("unit_name")
            if name:
                try:
                    db.session.execute(
                        text("INSERT INTO unit (name) VALUES (:name)"), {"name": name}
                    )
                    db.session.commit()
                    flash("Unit added successfully!", "success")
                except IntegrityError:
                    db.session.rollback()
                    flash("Unit already exists!", "danger")

        return redirect(url_for("main.inventory_setup"))
    
    categories = db.session.execute(text("SELECT * FROM category ORDER BY name")).fetchall()
    items = db.session.execute(text("SELECT * FROM item ORDER BY name")).fetchall()
    units = db.session.execute(text("SELECT * FROM unit ORDER BY name")).fetchall()

    return render_template("inventory_setup.html", categories=categories, items=items, units=units)



@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        result = db.session.execute(
            text("SELECT id, username, email, password_hash FROM user WHERE username = :username"),
            {"username": username}
        ).fetchone()

        if result and check_password_hash(result.password_hash, password):
            user = User(result.id, result.username, result.email, result.password_hash)
            login_user(user)
            print(f"DEBUG: User logged in: {user.username}") 
            # flash("Logged in successfully.", "success")
            return redirect(url_for('main.home'))
        else:
            flash("Invalid username or password", "danger")

    return render_template('login.html')

@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))


@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    import os

    db_path = os.path.join(current_app.instance_path, 'inventory.db')

    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # 1. Get stored password hash from DB
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT password_hash FROM user WHERE id = ?", (current_user.id,))
        stored_hash = c.fetchone()[0]
        conn.close()

        # 2. Verify current password
        if not check_password_hash(stored_hash, current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('main.profile'))

        # 3. Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('main.profile'))

        # 4. Update password
        new_hash = generate_password_hash(new_password)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("UPDATE user SET password_hash = ? WHERE id = ?", (new_hash, current_user.id))
        conn.commit()
        conn.close()

        flash('Password updated successfully.', 'success')
        return redirect(url_for('main.profile'))

    return render_template('profile.html')

@main.route('/items/<int:id>/edit', methods=['GET', 'POST'])
def edit_item(id):
    item = db.session.execute(
        text("SELECT * FROM item WHERE id = :id"),
        {"id": id}
    ).fetchone()

    if not item:
        flash("Item not found.", "danger")
        return redirect(url_for("main.inventory_setup"))

    if request.method == 'POST':
        new_name = request.form['name']
        db.session.execute(
            text("UPDATE item SET name = :name WHERE id = :id"),
            {"name": new_name, "id": id}
        )
        db.session.commit()
        return redirect(url_for('main.inventory_setup'))

    return render_template('edit_item.html', item=item)


@main.route('/items/<int:id>/delete', methods=['POST'])
def delete_item(id):
    db.session.execute(
        text("DELETE FROM item WHERE id = :id"),
        {"id": id}
    )
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('main.inventory_setup'))


@main.route('/categories/<int:id>/edit', methods=['GET', 'POST'])
def edit_category(id):
    category = db.session.execute(
        text("SELECT * FROM category WHERE id = :id"),
        {"id": id}
    ).fetchone()

    if not category:
        flash("Category not found.", "danger")
        return redirect(url_for("main.inventory_setup"))

    if request.method == 'POST':
        new_name = request.form['name']
        db.session.execute(
            text("UPDATE category SET name = :name WHERE id = :id"),
            {"name": new_name, "id": id}
        )
        db.session.commit()
        return redirect(url_for('main.inventory_setup'))

    return render_template('edit_category.html', category=category)


@main.route('/categories/<int:id>/delete', methods=['POST'])
def delete_category(id):
    db.session.execute(
        text("DELETE FROM category WHERE id = :id"),
        {"id": id}
    )
    db.session.commit()
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('main.inventory_setup'))

@main.route('/units/<int:id>/edit', methods=['GET', 'POST'])
def edit_unit(id):
    unit = db.session.execute(
        text("SELECT * FROM unit WHERE id = :id"),
        {"id": id}
    ).fetchone()

    if not unit:
        flash("Unit not found.", "danger")
        return redirect(url_for("main.inventory_setup"))

    if request.method == 'POST':
        new_name = request.form['name']
        db.session.execute(
            text("UPDATE unit SET name = :name WHERE id = :id"),
            {"name": new_name, "id": id}
        )
        db.session.commit()
        return redirect(url_for('main.inventory_setup'))

    return render_template('edit_unit.html', unit=unit)


@main.route('/units/<int:id>/delete', methods=['POST'])
def delete_unit(id):
    db.session.execute(
        text("DELETE FROM unit WHERE id = :id"),
        {"id": id}
    )
    db.session.commit()
    flash('Unit deleted successfully!', 'success')
    return redirect(url_for('main.inventory_setup'))


@main.route("/reports", methods=["GET", "POST"])
def reports():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get list of items
    cur.execute("SELECT id, name FROM item ORDER BY name")
    items = cur.fetchall()

    if not items:
        return render_template(
            "reports.html",
            items=[],
            selected_item_id=None,
            start_date="",
            end_date="",
            dates=[],
            action_types=[],
            chart_data={},
            balance_data=[],
            total_spend=0
        )

    # Default: first item if none selected
    selected_item_id = request.form.get("item_id", items[0]["id"])
    start_date = request.form.get("start_date", "")
    end_date = request.form.get("end_date", "")

    # Build WHERE clause with date filter
    where_clauses = ["item_id = ?"]
    params = [selected_item_id]

    if start_date:
        where_clauses.append("date >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("date <= ?")
        params.append(end_date)

    where_sql = " AND ".join(where_clauses)

    # Query inventory actions for selected item with optional date range
    cur.execute(
        f"""
        SELECT date, action_type, quantity, price
        FROM actions
        WHERE {where_sql}
        ORDER BY date
        """,
        params
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return render_template(
            "reports.html",
            items=items,
            selected_item_id=int(selected_item_id),
            start_date=start_date,
            end_date=end_date,
            dates=[],
            action_types=[],
            chart_data={},
            balance_data=[],
            total_spend=0
        )

    # Process data for charts
    dates = sorted(set([row["date"] for row in rows]))
    action_types = sorted(set([row["action_type"] for row in rows]))
    chart_data = {atype: [] for atype in action_types}
    balance_data = []

    # Running totals per action type for cumulative chart
    running = {atype: 0 for atype in action_types}
    cumulative_balance = 0
    total_spend = 0

    for d in dates:
        daily_rows = [r for r in rows if r["date"] == d]

        # Cumulative quantity per action type
        for atype in action_types:
            qty = sum(float(r["quantity"]) for r in daily_rows if r["action_type"] == atype)
            running[atype] += qty
            chart_data[atype].append(running[atype])

        # Update cumulative balance
        in_qty = sum(float(r["quantity"]) for r in daily_rows if r["action_type"].lower() == "delivery")
        out_qty = sum(float(r["quantity"]) for r in daily_rows if r["action_type"].lower() in ("sales", "consumption", "waste"))
        cumulative_balance += in_qty - out_qty
        balance_data.append(cumulative_balance)

        # Update total spend on deliveries
        total_spend += sum(float(r["price"]) for r in daily_rows if r["action_type"].lower() == "delivery")

    formatted_total_spend = f"${total_spend:,.2f}"

    # Latest delivery price per unit
    delivery_rows = [r for r in rows if r["action_type"].lower() == "delivery"]
    if delivery_rows:
        latest_delivery = delivery_rows[-1]  # last delivery by order in rows
        latest_price_per_unit = float(latest_delivery["price"]) / float(latest_delivery["quantity"])
    else:
        latest_price_per_unit = 0

    formatted_latest_price = f"${latest_price_per_unit:,.2f}"

    # Total Quantity Sold/Consumed/Wasted
    total_sold_consumed_wasted = sum(
        float(r["quantity"]) for r in rows if r["action_type"].lower() in ("sales", "consumption", "waste")
    )

    return render_template(
        "reports.html",
        items=items,
        selected_item_id=int(selected_item_id),
        start_date=start_date,
        end_date=end_date,
        dates=dates,
        action_types=action_types,
        chart_data=chart_data,
        balance_data=balance_data,
        formatted_total_spend=formatted_total_spend,
        formatted_latest_price=formatted_latest_price,
        total_sold_consumed_wasted=total_sold_consumed_wasted
    )