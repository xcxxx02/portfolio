from db import get_connection
import os
import datetime

class AppConfig:
    _instance = None
    _data = {}

    def __init__(self):
        if AppConfig._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.Reload()

    @staticmethod
    def instance():
        if AppConfig._instance is None:
            AppConfig._instance = AppConfig()
        return AppConfig._instance

    def Get(self, key):
        return self._data.get(key)

    def Reload(self):
        conn = get_connection()
        rows = conn.execute("SELECT key, value FROM config").fetchall()
        conn.close()
        self._data = {row['key']: row['value'] for row in rows}
        self._data['stripe_api_key'] = os.environ.get('STRIPE_API_KEY', '')

class DiscountStrategy:
    def apply(self, total_amount): raise NotImplementedError

class NoDiscount(DiscountStrategy):
    def apply(self, total_amount): return total_amount

class PercentageDiscount(DiscountStrategy):
    def __init__(self, percent):
        self.percent = float(percent) 
    
    def apply(self, total_amount):
        return total_amount * (1 - self.percent / 100)

class PaymentProcessor:
    def process_payment(self, amount): raise NotImplementedError

class StripeClient:
    def charge(self, amount_cents):
        print(f"[Stripe API] Charging {amount_cents} cents...")
        return {"status": "success", "tx_id": "tx_12345"}

class StripeAdapter(PaymentProcessor):
    def __init__(self):
        self.gateway = StripeClient()
        
    def process_payment(self, amount):
        cents = int(amount * 100)
        config = AppConfig.instance()
        response = self.gateway.charge(cents)
        return f"Payment Successful via Stripe (Tx: {response['tx_id']})"

class User:
    def __init__(self, user_id, name, email, role):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.role = role
    
    def login(self): raise NotImplementedError

class Customer(User):
    def __init__(self, user_id, name, email, shipping_address=""):
        super().__init__(user_id, name, email, "Customer")
        self.shipping_address = shipping_address
    
    def login(self):
        print(f"Customer {self.name} logged in.")
        
    def view_order_history(self):
        conn = get_connection()
        orders = conn.execute("SELECT * FROM orders WHERE customer_id = ?", (self.customer_id,)).fetchall()
        conn.close()
        return orders
    
    @property
    def customer_id(self):
        conn = get_connection()
        res = conn.execute("SELECT customer_id FROM customers WHERE customer_id = ?", (self.user_id,)).fetchone()
        conn.close()
        return res['customer_id'] if res else None

class Admin(User):
    def __init__(self, user_id, name, email):
        super().__init__(user_id, name, email, "Admin")
    
    def login(self):
        print(f"Admin {self.name} logged in.")

    def manage_games(self):
        return "Admin accessing Game Management Module."

class UserFactory:
    def create_user(self, user_id, name, email, extra_info=None): raise NotImplementedError

class CustomerFactory(UserFactory):
    def create_user(self, user_id, name, email, extra_info=None):
        return Customer(user_id, name, email, extra_info)

class AdminFactory(UserFactory):
    def create_user(self, user_id, name, email, extra_info=None):
        return Admin(user_id, name, email)