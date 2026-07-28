from flask import session
from db import get_connection
import datetime
import random
import string
from patterns import StripeAdapter
from patterns import PercentageDiscount, NoDiscount

# =====================================================
# 📦 INVENTORY SERVICE
# =====================================================
class InventoryService:
    @staticmethod
    def reserve_stock(product_id, quantity, conn=None):
        should_close = False
        if conn is None:
            conn = get_connection()
            should_close = True
        try:
            item = conn.execute("SELECT stock_level FROM inventory WHERE product_id = ?", (product_id,)).fetchone()
            if not item: return False
            if item['stock_level'] < quantity: return False
            return True
        finally:
            if should_close: conn.close()

    @staticmethod
    def update_stock(product_id, quantity_change, conn=None):
        should_close = False
        if conn is None:
            conn = get_connection()
            should_close = True
        try:
            conn.execute("UPDATE inventory SET stock_level = stock_level + ? WHERE product_id = ?", (quantity_change, product_id))
            if should_close: conn.commit()
        finally:
            if should_close: conn.close()

# =====================================================
# 🛒 CART SERVICE
# =====================================================
class CartService:
    @staticmethod
    def generate_key():
        parts = []
        for _ in range(3):
            part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            parts.append(part)
        return '-'.join(parts)

    @staticmethod
    def get_active_cart(customer_id):
        conn = get_connection()
        cart = conn.execute("SELECT * FROM shopping_carts WHERE customer_id = ? AND status = 'ACTIVE'", (customer_id,)).fetchone()
        if not cart:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            cur = conn.execute("INSERT INTO shopping_carts (customer_id, created_at, status) VALUES (?, ?, 'ACTIVE')", (customer_id, date_str))
            cart_id = cur.lastrowid
            conn.commit()
            cart = conn.execute("SELECT * FROM shopping_carts WHERE cart_id = ?", (cart_id,)).fetchone()
        conn.close()
        return cart

    @staticmethod
    def add_item(customer_id, product_id):
        conn = get_connection()
        try:
            cart_row = conn.execute("SELECT cart_id FROM shopping_carts WHERE customer_id = ? AND status='ACTIVE'", (customer_id,)).fetchone()
            if not cart_row:
                conn.close()
                CartService.get_active_cart(customer_id) 
                return CartService.add_item(customer_id, product_id)
            
            cart_id = cart_row['cart_id']
            existing = conn.execute("SELECT quantity, cart_item_id FROM cart_items WHERE cart_id = ? AND product_id = ?", (cart_id, product_id)).fetchone()
            current_qty = existing['quantity'] if existing else 0
            new_qty = current_qty + 1
            
            if not InventoryService.reserve_stock(product_id, new_qty, conn):
                return "Out of Stock"
            
            prod = conn.execute("SELECT price FROM products WHERE product_id = ?", (product_id,)).fetchone()
            
            if existing:
                conn.execute("UPDATE cart_items SET quantity = ? WHERE cart_item_id = ?", (new_qty, existing['cart_item_id']))
            else:
                conn.execute("INSERT INTO cart_items (cart_id, product_id, quantity, unit_price) VALUES (?, ?, 1, ?)", 
                             (cart_id, product_id, prod['price']))
            conn.commit()
            return "Added"
        finally:
            conn.close()

    @staticmethod
    def update_quantity(customer_id, product_id, change):
        conn = get_connection()
        try:
            cart = conn.execute("SELECT cart_id FROM shopping_carts WHERE customer_id = ? AND status='ACTIVE'", (customer_id,)).fetchone()
            if not cart: return
            item = conn.execute("SELECT * FROM cart_items WHERE cart_id = ? AND product_id = ?", (cart['cart_id'], product_id)).fetchone()
            if not item: return
            new_qty = item['quantity'] + change
            if new_qty <= 0:
                conn.execute("DELETE FROM cart_items WHERE cart_item_id = ?", (item['cart_item_id'],))
            else:
                if change > 0:
                    if not InventoryService.reserve_stock(product_id, new_qty, conn): return "Out of Stock"
                conn.execute("UPDATE cart_items SET quantity = ? WHERE cart_item_id = ?", (new_qty, item['cart_item_id']))
            conn.commit()
            return "Updated"
        finally:
            conn.close()

    @staticmethod
    def remove_item(customer_id, product_id):
        conn = get_connection()
        try:
            cart = conn.execute("SELECT cart_id FROM shopping_carts WHERE customer_id = ? AND status='ACTIVE'", (customer_id,)).fetchone()
            if cart:
                conn.execute("DELETE FROM cart_items WHERE cart_id = ? AND product_id = ?", (cart['cart_id'], product_id))
                conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_cart_details(customer_id):
        cart_row = CartService.get_active_cart(customer_id)
        conn = get_connection()
        
        sql = """
        SELECT ci.product_id, p.title, p.price, p.image, p.discount, p.product_type, ci.quantity, ci.unit_price, i.stock_level
        FROM cart_items ci
        JOIN products p ON ci.product_id = p.product_id
        LEFT JOIN inventory i ON p.product_id = i.product_id
        WHERE ci.cart_id = ?
        """
        items = conn.execute(sql, (cart_row['cart_id'],)).fetchall()
        conn.close()
        
        final_total = 0
        cart_items = []
        
        for item in items:
            discount = item['discount'] if item['discount'] else 0
            if discount > 0:
                strategy = PercentageDiscount(discount) 
                discounted_price = strategy.apply(item['price'])
            else:
                strategy = NoDiscount()
                discounted_price = strategy.apply(item['price'])
            
            item_dict = dict(item)
            item_dict['final_price'] = discounted_price
            item_dict['discount'] = discount
            
            cart_items.append(item_dict)
            final_total += discounted_price * item['quantity']
            
        return cart_items, final_total, final_total

    @staticmethod
    def checkout(customer_id):
        items, _, total = CartService.get_cart_details(customer_id)
        if not items: return "Cart Empty", 0

        for item in items:
            if not InventoryService.reserve_stock(item['product_id'], item['quantity']):
                return f"Error: Not enough stock for {item['title']}", 0
        try:
            payment_adapter = StripeAdapter()
            payment_msg = payment_adapter.process_payment(total) 
            print(f"[LOG] {payment_msg}") 
        except Exception as e:
            return f"Payment Error: {str(e)}", 0

        conn = get_connection()
        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur = conn.execute("INSERT INTO orders (customer_id, order_date, status, total_amount) VALUES (?, ?, 'PAID', ?)",
                               (customer_id, date_str, total))
            order_id = cur.lastrowid
            
            for item in items:
         
                keys_text = ""
                qty = item['quantity']
                
                if item['product_type'] == 'Bundle':
    
                    bundle_games = conn.execute("""
                        SELECT p.title FROM bundle_items bi
                        JOIN products p ON bi.product_id = p.product_id
                        WHERE bi.bundle_id = ?
                    """, (item['product_id'],)).fetchall()
                    
                
                    all_keys = []
                    for q in range(qty):
                        group_keys = []
                        for bg in bundle_games:
                            group_keys.append(f"{bg['title']}: {CartService.generate_key()}")
                        all_keys.append(" | ".join(group_keys))
                    keys_text = "\n".join(all_keys)
                    
                else:
            
                    keys_list = [CartService.generate_key() for _ in range(qty)]
                    keys_text = "\n".join(keys_list)

                conn.execute("INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase, game_keys) VALUES (?, ?, ?, ?, ?)",
                             (order_id, item['product_id'], item['quantity'], item['final_price'], keys_text))
                
                InventoryService.update_stock(item['product_id'], -item['quantity'], conn=conn)

            cart = CartService.get_active_cart(customer_id)
            conn.execute("UPDATE shopping_carts SET status = 'COMPLETED' WHERE cart_id = ?", (cart['cart_id'],))
            conn.commit()
            return "Payment Successful!", total
        except Exception as e:
            conn.rollback()
            return f"Error: {str(e)}", 0
        finally:
            conn.close()