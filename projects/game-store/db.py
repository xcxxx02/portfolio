import sqlite3
from werkzeug.security import generate_password_hash
import datetime

DB_NAME = "store.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password_hash TEXT,
        role TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY,
        shipping_address TEXT,
        FOREIGN KEY(customer_id) REFERENCES users(user_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        admin_id INTEGER PRIMARY KEY,
        department TEXT, 
        FOREIGN KEY(admin_id) REFERENCES users(user_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        price REAL,
        image TEXT,
        is_digital BOOLEAN,
        description TEXT,
        product_type TEXT,
        discount INTEGER DEFAULT 0
    )""")

    try:
        cur.execute("SELECT discount FROM products LIMIT 1")
    except sqlite3.OperationalError:
        cur.execute("ALTER TABLE products ADD COLUMN discount INTEGER DEFAULT 0")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS games (
        game_id INTEGER PRIMARY KEY,
        publisher TEXT,
        release_date TEXT,
        FOREIGN KEY(game_id) REFERENCES products(product_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bundles (
        bundle_id INTEGER PRIMARY KEY,
        FOREIGN KEY(bundle_id) REFERENCES products(product_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bundle_items (
        bundle_id INTEGER,
        product_id INTEGER,
        FOREIGN KEY(bundle_id) REFERENCES bundles(bundle_id),
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        product_id INTEGER PRIMARY KEY,
        stock_level INTEGER,
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS shopping_carts (
        cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        created_at TEXT,
        status TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS cart_items (
        cart_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cart_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        unit_price REAL,
        FOREIGN KEY(cart_id) REFERENCES shopping_carts(cart_id),
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        order_date TEXT,
        status TEXT,
        total_amount REAL,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price_at_purchase REAL,
        game_keys TEXT,
        FOREIGN KEY(order_id) REFERENCES orders(order_id)
    )""")

    try:
        cur.execute("SELECT game_keys FROM order_items LIMIT 1")
    except sqlite3.OperationalError:
        cur.execute("ALTER TABLE order_items ADD COLUMN game_keys TEXT")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS wishlists (
        wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        created_at TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
    )""")
    
    cur.execute("""
    CREATE TABLE IF NOT EXISTS wishlist_items (
        wishlist_id INTEGER,
        product_id INTEGER,
        FOREIGN KEY(wishlist_id) REFERENCES wishlists(wishlist_id),
        FOREIGN KEY(product_id) REFERENCES products(product_id)
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        customer_id INTEGER,
        rating INTEGER,
        comment TEXT,
        review_date TEXT,
        FOREIGN KEY(product_id) REFERENCES products(product_id),
        FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
    )""")

    cur.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")

    cur.execute("SELECT count(*) FROM users")
    if cur.fetchone()[0] == 0:
        admin_pass = generate_password_hash("admin123")
        cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)", 
                    ("admin", "admin@example.com", admin_pass, "Admin"))
        admin_id = cur.lastrowid
        cur.execute("INSERT INTO admins (admin_id, department) VALUES (?, ?)", (admin_id, "IT"))

        user_pass = generate_password_hash("user123")
        cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)", 
                    ("user", "user@example.com", user_pass, "Customer"))
        main_user_id = cur.lastrowid
        cur.execute("INSERT INTO customers (customer_id, shipping_address) VALUES (?, ?)", (main_user_id, "Main Street 123"))

        cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)", ("GamerOne", "gamer1@test.com", user_pass, "Customer"))
        uid2 = cur.lastrowid
        cur.execute("INSERT INTO customers (customer_id) VALUES (?)", (uid2,))

        cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)", ("EldenLord", "elden@test.com", user_pass, "Customer"))
        uid3 = cur.lastrowid
        cur.execute("INSERT INTO customers (customer_id) VALUES (?)", (uid3,))

        cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)", ("CyberFan", "cyber@test.com", user_pass, "Customer"))
        uid4 = cur.lastrowid
        cur.execute("INSERT INTO customers (customer_id) VALUES (?)", (uid4,))
    else:
        conn.row_factory = None
        main_user_id = conn.execute("SELECT user_id FROM users WHERE name='user'").fetchone()[0]
        uid2 = conn.execute("SELECT user_id FROM users WHERE name='GamerOne'").fetchone()
        if not uid2: uid2 = main_user_id
        else: uid2 = uid2[0]
        
        uid3 = conn.execute("SELECT user_id FROM users WHERE name='EldenLord'").fetchone()
        if not uid3: uid3 = main_user_id
        else: uid3 = uid3[0]

        uid4 = conn.execute("SELECT user_id FROM users WHERE name='CyberFan'").fetchone()
        if not uid4: uid4 = main_user_id
        else: uid4 = uid4[0]
        conn.row_factory = sqlite3.Row

    cur.execute("SELECT count(*) FROM products")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO products (title, price, image, is_digital, description, product_type, discount) VALUES (?, ?, ?, 1, ?, 'Game', 0)", 
            ('Elden Ring', 59.99, 'https://upload.wikimedia.org/wikipedia/en/b/b9/Elden_Ring_Box_art.jpg', 
             'THE NEW FANTASY ACTION RPG. Rise, Tarnished, and be guided by grace to brandish the power of the Elden Ring and become an Elden Lord in the Lands Between.'))
        pid1 = cur.lastrowid
        cur.execute("INSERT INTO games (game_id, publisher, release_date) VALUES (?, ?, ?)", (pid1, 'FromSoftware', '2022-02-25'))
        cur.execute("INSERT INTO inventory (product_id, stock_level) VALUES (?, ?)", (pid1, 50))

        cur.execute("INSERT INTO products (title, price, image, is_digital, description, product_type, discount) VALUES (?, ?, ?, 1, ?, 'Game', 20)", 
            ('Cyberpunk 2077', 49.99, 'https://upload.wikimedia.org/wikipedia/en/9/9f/Cyberpunk_2077_box_art.jpg', 
             'Cyberpunk 2077 is an open-world, action-adventure RPG set in the dark future of Night City.'))
        pid2 = cur.lastrowid
        cur.execute("INSERT INTO games (game_id, publisher, release_date) VALUES (?, ?, ?)", (pid2, 'CD Projekt Red', '2020-12-10'))
        cur.execute("INSERT INTO inventory (product_id, stock_level) VALUES (?, ?)", (pid2, 20))

        cur.execute("INSERT INTO products (title, price, image, is_digital, description, product_type, discount) VALUES (?, ?, ?, 1, ?, 'Game', 0)", 
            ('God of War', 49.99, 'https://upload.wikimedia.org/wikipedia/en/a/a7/God_of_War_4_cover.jpg', 
             'His vengeance against the Gods of Olympus years behind him, Kratos now lives as a man in the realm of Norse Gods and monsters.'))
        pid3 = cur.lastrowid
        cur.execute("INSERT INTO games (game_id, publisher, release_date) VALUES (?, ?, ?)", (pid3, 'Santa Monica Studio', '2018-04-20'))
        cur.execute("INSERT INTO inventory (product_id, stock_level) VALUES (?, ?)", (pid3, 5))

        cur.execute("INSERT INTO products (title, price, image, is_digital, description, product_type, discount) VALUES (?, ?, ?, 1, ?, 'Game', 0)", 
            ('Black Myth: Wukong', 69.99, 'https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/2358720/header.jpg', 
             'Black Myth: Wukong is an action RPG rooted in Chinese mythology.'))
        pid4 = cur.lastrowid
        cur.execute("INSERT INTO games (game_id, publisher, release_date) VALUES (?, ?, ?)", (pid4, 'Game Science', '2024-08-20'))
        cur.execute("INSERT INTO inventory (product_id, stock_level) VALUES (?, ?)", (pid4, 100))
        
        cur.execute("INSERT INTO products (title, price, image, is_digital, description, product_type, discount) VALUES (?, ?, ?, 1, ?, 'Bundle', 10)", 
            ('RPG Legends Collection', 99.99, 'https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1245620/header.jpg', 
             'Experience two of the biggest open-world RPGs of the decade in one package.'))
        bid = cur.lastrowid
        cur.execute("INSERT INTO bundles (bundle_id) VALUES (?)", (bid,))
        cur.execute("INSERT INTO bundle_items (bundle_id, product_id) VALUES (?, ?)", (bid, pid1))
        cur.execute("INSERT INTO bundle_items (bundle_id, product_id) VALUES (?, ?)", (bid, pid2))
        cur.execute("INSERT INTO inventory (product_id, stock_level) VALUES (?, ?)", (bid, 3))

        cur.execute("SELECT count(*) FROM reviews")
        if cur.fetchone()[0] == 0:
            reviews = [
                (pid1, uid2, 5, "Masterpiece! One of the best open-world RPGs ever made.", "2023-01-15"),
                (pid1, uid3, 5, "Hard but fair. I love the atmosphere.", "2023-01-20"),
                (pid2, uid4, 4, "Night City is breathtaking. The story is gripping from start to finish.", "2023-03-10"),
                (pid3, uid2, 5, "Boy! What a journey. Combat is visceral and satisfying.", "2023-04-05"),
                (pid4, uid3, 5, "Absolutely stunning visuals and fluid combat. A must-play!", "2024-08-25"),
                (pid4, uid4, 4, "Great graphics, boss fights are intense.", "2024-08-28")
            ]
            cur.executemany("INSERT INTO reviews (product_id, customer_id, rating, comment, review_date) VALUES (?, ?, ?, ?, ?)", reviews)

        cur.execute("SELECT count(*) FROM wishlists WHERE customer_id=?", (main_user_id,))
        if cur.fetchone()[0] == 0:
            cur.execute("INSERT INTO wishlists (customer_id, created_at) VALUES (?, ?)", (main_user_id, "2024-01-01"))
            wid = cur.lastrowid
            cur.execute("INSERT INTO wishlist_items (wishlist_id, product_id) VALUES (?, ?)", (wid, pid4))
            cur.execute("INSERT INTO wishlist_items (wishlist_id, product_id) VALUES (?, ?)", (wid, pid3))

        cur.execute("SELECT count(*) FROM orders WHERE customer_id=?", (main_user_id,))
        if cur.fetchone()[0] == 0:
            date1 = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO orders (customer_id, order_date, status, total_amount) VALUES (?, ?, 'PAID', ?)", (main_user_id, date1, 59.99))
            oid1 = cur.lastrowid
            cur.execute("INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase, game_keys) VALUES (?, ?, 1, 59.99, ?)", 
                        (oid1, pid1, "ELDEN-RING-KEY1"))

            date2 = (datetime.datetime.now() - datetime.timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO orders (customer_id, order_date, status, total_amount) VALUES (?, ?, 'PAID', ?)", (main_user_id, date2, 39.99))
            oid2 = cur.lastrowid
            cur.execute("INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase, game_keys) VALUES (?, ?, 1, 39.99, ?)", 
                        (oid2, pid2, "CYBER-PUNK-2077"))

    conn.commit()
    conn.close()