from flask import Flask, render_template, request, redirect, session, url_for, flash
from db import init_db, get_connection
from services import CartService, InventoryService
from patterns import UserFactory, AdminFactory, CustomerFactory
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")

init_db()

def attach_bundle_images(conn, products):
    results = []
    for p in products:
        p_dict = dict(p)
        if p_dict['product_type'] == 'Bundle':
            imgs = conn.execute("""
                SELECT p.image 
                FROM bundle_items bi 
                JOIN products p ON bi.product_id = p.product_id 
                WHERE bi.bundle_id = ?
                LIMIT 4
            """, (p_dict['product_id'],)).fetchall()
            p_dict['bundle_imgs'] = [i['image'] for i in imgs]
        else:
            p_dict['bundle_imgs'] = []
        results.append(p_dict)
    return results

@app.route("/")
def index():
    conn = get_connection()
    sql = """
    SELECT p.product_id, p.title, p.price, p.image, i.stock_level, p.description, p.product_type, p.discount
    FROM products p 
    LEFT JOIN inventory i ON p.product_id = i.product_id
    """
    products_rows = conn.execute(sql).fetchall()
    products = attach_bundle_images(conn, products_rows)
    conn.close()
    return render_template("index.html", games=products)

@app.route("/product/<int:pid>")
def product_detail(pid):
    conn = get_connection()
    product_row = conn.execute("""
        SELECT p.*, i.stock_level 
        FROM products p
        LEFT JOIN inventory i ON p.product_id = i.product_id
        WHERE p.product_id = ?
    """, (pid,)).fetchone()
    
    if not product_row:
        conn.close()
        return redirect("/")

    products_list = attach_bundle_images(conn, [product_row])
    product = products_list[0]
    
    bundle_contents = []
    if product['product_type'] == 'Bundle':
        bundle_contents = conn.execute("""
            SELECT p.* FROM bundle_items bi
            JOIN products p ON bi.product_id = p.product_id
            WHERE bi.bundle_id = ?
        """, (pid,)).fetchall()
        
    reviews = conn.execute("""
        SELECT r.*, u.name 
        FROM reviews r
        JOIN customers c ON r.customer_id = c.customer_id
        JOIN users u ON c.customer_id = u.user_id
        WHERE r.product_id = ?
        ORDER BY r.review_date DESC
    """, (pid,)).fetchall()
    
    conn.close()
    return render_template("product_detail.html", product=product, bundle_contents=bundle_contents, reviews=reviews)

@app.route("/add_review/<int:pid>", methods=['POST'])
def add_review(pid):
    if 'user_id' not in session or session.get('role') != 'Customer': return redirect(f"/product/{pid}")
    rating = int(request.form['rating'])
    comment = request.form['comment']
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    conn.execute("INSERT INTO reviews (product_id, customer_id, rating, comment, review_date) VALUES (?, ?, ?, ?, ?)",
                 (pid, session['user_id'], rating, comment, date_str))
    conn.commit()
    conn.close()
    return redirect(f"/product/{pid}")

@app.route("/login_page")
def login_page(): return render_template("login.html")

@app.route("/register_page")
def register_page(): return render_template("register.html")

@app.route("/login", methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    email = username + "@example.com"
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        session['user'] = user['name']
        session['user_id'] = user['user_id']
        session['role'] = user['role']
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect("/")
    else:
        return render_template("login.html", error="Invalid Username or Password")

@app.route("/register", methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    # Public registration creates customer accounts only.
    role = 'Customer'
    email = username + "@example.com"
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user:
        conn.close()
        return render_template("register.html", error="User already exists! Please Login.")
    pw_hash = generate_password_hash(password)
    try:
        cur = conn.execute("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)", 
                     (username, email, pw_hash, role))
        user_id = cur.lastrowid
        if role == 'Customer':
            conn.execute("INSERT INTO customers (customer_id, shipping_address) VALUES (?, ?)", (user_id, "Default Address"))
        elif role == 'Admin':
            conn.execute("INSERT INTO admins (admin_id, department) VALUES (?, ?)", (user_id, "IT"))
        conn.commit()
        if role == 'Customer': factory = CustomerFactory()
        else: factory = AdminFactory()
        user_obj = factory.create_user(user_id, username, email)
        conn.close()
        flash("Account created successfully! Please login.", "success")
        return redirect("/login_page")
    except Exception as e:
        conn.close()
        return f"Error: {e}"

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect("/")

@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if 'user_id' not in session or session.get('role') != 'Customer':
        return {"status": "error", "message": "Please login first"}, 401
    
    result = CartService.add_item(session['user_id'], product_id)
    
    if result == "Out of Stock":
        return {"status": "error", "message": "⚠️ Cannot add item. Not enough stock!"}, 400
    else:
        return {"status": "success", "message": "✅ Item added to cart successfully!"}

@app.route("/cart/update/<int:pid>/<string:action>")
def update_cart_quantity(pid, action):
    if 'user_id' not in session: return redirect("/")
    change = 1 if action == 'plus' else -1
    result = CartService.update_quantity(session['user_id'], pid, change)
    if result == "Out of Stock": flash("⚠️ Max stock limit reached!", "error")
    return redirect("/cart")

@app.route("/cart/remove/<int:pid>")
def remove_from_cart(pid):
    if 'user_id' not in session: return redirect("/")
    CartService.remove_item(session['user_id'], pid)
    flash("Item removed from cart.", "info")
    return redirect("/cart")

@app.route("/cart")
def view_cart():
    if 'user_id' not in session: return redirect("/")
    items, _, total = CartService.get_cart_details(session['user_id'])
    conn = get_connection()
    items = attach_bundle_images(conn, items)
    conn.close()
    return render_template("cart.html", items=items, total=total)

@app.route("/checkout")
def checkout():
    if 'user_id' not in session: return redirect("/")
    msg, total = CartService.checkout(session['user_id'])
    if "Error" in msg: 
        flash(msg, "error")
        return redirect("/cart")
    return render_template("success.html", msg=msg, amount=round(total, 2))

@app.route("/add_to_wishlist/<int:product_id>")
def add_to_wishlist(product_id):
    if 'user_id' not in session or session.get('role') != 'Customer':
        return {"status": "error", "message": "Please login first"}, 401
    
    conn = get_connection()
    wishlist = conn.execute("SELECT wishlist_id FROM wishlists WHERE customer_id = ?", (session['user_id'],)).fetchone()
    
    if not wishlist:
        cur = conn.execute("INSERT INTO wishlists (customer_id, created_at) VALUES (?, ?)", 
                           (session['user_id'], datetime.datetime.now().strftime("%Y-%m-%d")))
        wishlist_id = cur.lastrowid
    else:
        wishlist_id = wishlist['wishlist_id']
    
    exists = conn.execute("SELECT 1 FROM wishlist_items WHERE wishlist_id = ? AND product_id = ?", (wishlist_id, product_id)).fetchone()
    
    if not exists:
        conn.execute("INSERT INTO wishlist_items (wishlist_id, product_id) VALUES (?, ?)", (wishlist_id, product_id))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "❤️ Added to Wishlist!"}
    else:
        conn.close()
        return {"status": "info", "message": "Item already in Wishlist."}

@app.route("/wishlist")
def view_wishlist():
    if 'user_id' not in session: return redirect("/")
    conn = get_connection()
    items_rows = conn.execute("""
        SELECT p.product_id, p.title, p.price, p.image, i.stock_level, p.discount, p.product_type
        FROM wishlist_items wi 
        JOIN wishlists w ON wi.wishlist_id = w.wishlist_id
        JOIN products p ON wi.product_id = p.product_id
        LEFT JOIN inventory i ON p.product_id = i.product_id
        WHERE w.customer_id = ?""", (session['user_id'],)).fetchall()
    items = attach_bundle_images(conn, items_rows)
    conn.close()
    return render_template("wishlist.html", items=items)

@app.route("/history")
def history():
    if 'user_id' not in session: return redirect("/")
    conn = get_connection()
    
    orders_rows = conn.execute("SELECT * FROM orders WHERE customer_id = ? ORDER BY order_date DESC", (session['user_id'],)).fetchall()
    
    orders = []
    for o_row in orders_rows:
        order = dict(o_row)
        
        items_rows = conn.execute("""
            SELECT oi.*, p.title, p.image, p.product_type, p.discount
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            WHERE oi.order_id = ?
        """, (order['order_id'],)).fetchall()
        
        order['items'] = attach_bundle_images(conn, items_rows)
        
        for item in order['items']:
            if item['game_keys']:
                item['keys_list'] = item['game_keys'].split('\n')
            else:
                item['keys_list'] = []
                
        orders.append(order)
        
    conn.close()
    return render_template("history.html", orders=orders)

@app.route("/admin_dashboard")
def admin_dashboard():
    if session.get('role') != 'Admin': return "Access Denied"
    conn = get_connection()

    inventory_rows = conn.execute("""
        SELECT p.product_id, p.title, p.price, p.image, i.stock_level, p.product_type, p.discount
        FROM products p 
        LEFT JOIN inventory i ON p.product_id = i.product_id
        ORDER BY p.product_id DESC
    """).fetchall()
    
    inventory = attach_bundle_images(conn, inventory_rows)
    
    conn.close()
    return render_template("admin.html", inventory=inventory)

@app.route("/admin/add_game", methods=['GET', 'POST'])
def add_game():
    if session.get('role') != 'Admin': return redirect("/")
    
    if request.method == 'POST':
        title = request.form['title']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        discount = int(request.form.get('discount', 0))
        image = request.form['image']
        description = request.form['description']
        publisher = request.form['publisher']
        date = request.form['date']
        
        conn = get_connection()
        cur = conn.execute("INSERT INTO products (title, price, image, is_digital, product_type, description, discount) VALUES (?, ?, ?, 1, 'Game', ?, ?)", 
                     (title, price, image, description, discount))
        pid = cur.lastrowid
        conn.execute("INSERT INTO inventory (product_id, stock_level) VALUES (?, ?)", (pid, stock))
        conn.execute("INSERT INTO games (game_id, publisher, release_date) VALUES (?, ?, ?)", (pid, publisher, date))
        conn.commit()
        conn.close()
        flash("New game added successfully!", "success")
        return redirect("/admin_dashboard")
    return render_template("add_game.html")

@app.route("/admin/create_bundle", methods=['GET', 'POST'])
def create_bundle():
    if session.get('role') != 'Admin': return redirect("/")
    conn = get_connection()
    
    if request.method == 'POST':
        title = request.form['title']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        discount = int(request.form.get('discount', 0))
        image = request.form['image']
        description = request.form['description']
        selected_games = request.form.getlist('games')
        
        cur = conn.execute("INSERT INTO products (title, price, image, is_digital, product_type, description, discount) VALUES (?, ?, ?, 1, 'Bundle', ?, ?)", 
                     (title, price, image, description, discount))
        bundle_id = cur.lastrowid
        
        conn.execute("INSERT INTO inventory (product_id, stock_level) VALUES (?, ?)", (bundle_id, stock))
        conn.execute("INSERT INTO bundles (bundle_id) VALUES (?)", (bundle_id,))
        
        for game_id in selected_games:
            conn.execute("INSERT INTO bundle_items (bundle_id, product_id) VALUES (?, ?)", (bundle_id, game_id))
            
        conn.commit()
        conn.close()
        flash("Bundle created successfully!", "success")
        return redirect("/admin_dashboard")
    
    available_games = conn.execute("SELECT * FROM products WHERE product_type = 'Game'").fetchall()
    conn.close()
    return render_template("create_bundle.html", games=available_games)

@app.route("/edit_game/<int:pid>", methods=['GET', 'POST'])
def edit_game(pid):
    if session.get('role') != 'Admin': return redirect("/")
    conn = get_connection()
    
    product_row = conn.execute("SELECT product_type FROM products WHERE product_id = ?", (pid,)).fetchone()
    if not product_row:
        conn.close()
        return redirect("/admin_dashboard")

    if request.method == 'POST':
        discount = int(request.form.get('discount', 0))
        conn.execute("UPDATE products SET title=?, price=?, image=?, description=?, discount=? WHERE product_id=?", 
                     (request.form['title'], float(request.form['price']), request.form['image'], request.form['description'], discount, pid))
        conn.execute("UPDATE inventory SET stock_level=? WHERE product_id=?", 
                     (int(request.form['stock']), pid))
        
        if product_row['product_type'] == 'Game':
            conn.execute("UPDATE games SET publisher=?, release_date=? WHERE game_id=?", 
                        (request.form['publisher'], request.form['date'], pid))
        else:
            conn.execute("DELETE FROM bundle_items WHERE bundle_id = ?", (pid,))
            selected_games = request.form.getlist('games')
            for g_id in selected_games:
                conn.execute("INSERT INTO bundle_items (bundle_id, product_id) VALUES (?, ?)", (pid, g_id))
                        
        conn.commit()
        conn.close()
        flash("Product updated successfully!", "success")
        return redirect("/admin_dashboard")
    
    game = conn.execute("""
        SELECT p.*, i.stock_level, g.publisher, g.release_date
        FROM products p
        LEFT JOIN inventory i ON p.product_id = i.product_id
        LEFT JOIN games g ON p.product_id = g.game_id
        WHERE p.product_id = ?
    """, (pid,)).fetchone()

    if product_row['product_type'] == 'Bundle':
        available_games = conn.execute("SELECT * FROM products WHERE product_type = 'Game'").fetchall()
        current_items = conn.execute("SELECT product_id FROM bundle_items WHERE bundle_id = ?", (pid,)).fetchall()
        current_ids = [item['product_id'] for item in current_items]
        conn.close()
        return render_template("edit_bundle.html", game=game, games=available_games, current_ids=current_ids)
    
    conn.close()
    return render_template("edit_game.html", game=game)

@app.route("/delete_game/<int:pid>")
def delete_game(pid):
    if session.get('role') == 'Admin':
        conn = get_connection()
        conn.execute("DELETE FROM inventory WHERE product_id = ?", (pid,))
        conn.execute("DELETE FROM games WHERE game_id = ?", (pid,))
        conn.execute("DELETE FROM bundles WHERE bundle_id = ?", (pid,))
        conn.execute("DELETE FROM bundle_items WHERE bundle_id = ?", (pid,))
        conn.execute("DELETE FROM reviews WHERE product_id = ?", (pid,))
        conn.execute("DELETE FROM wishlist_items WHERE product_id = ?", (pid,))
        conn.execute("DELETE FROM cart_items WHERE product_id = ?", (pid,))
        conn.execute("DELETE FROM products WHERE product_id = ?", (pid,))
        conn.commit()
        conn.close()
        flash("Product deleted.", "info")
    return redirect("/admin_dashboard")

@app.route("/wishlist/remove/<int:product_id>")
def remove_from_wishlist(product_id):
    if 'user_id' not in session or session.get('role') != 'Customer':
        return {"status": "error", "message": "Please login first"}, 401
    
    conn = get_connection()
    wishlist = conn.execute("SELECT wishlist_id FROM wishlists WHERE customer_id = ?", (session['user_id'],)).fetchone()
    
    if wishlist:
        conn.execute("DELETE FROM wishlist_items WHERE wishlist_id = ? AND product_id = ?", 
                     (wishlist['wishlist_id'], product_id))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "Removed from wishlist."}
    
    conn.close()
    return {"status": "error", "message": "Wishlist not found."}, 404

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=5000)