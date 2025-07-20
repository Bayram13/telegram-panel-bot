import sqlite3

DATABASE_NAME = "bot_data.db"

def init_db():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0
        )
    """)

    # Services table (for prices)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS services (
            service_name TEXT PRIMARY KEY,
            price_per_k REAL
        )
    """)

    # Orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            service_type TEXT,
            amount REAL,
            link TEXT,
            status TEXT DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # Admin Messages table (adminə göndərilən user mesajlarını izləmək üçün)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_messages (
            message_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            admin_message_id INTEGER, -- Adminin botdan aldığı mesajın ID-si
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add default service prices if not exist
    services_to_add = [
        ("tiktok_like", 1.50),
        ("tiktok_follower", 3.00),
        ("tiktok_view", 0.50),
        ("instagram_like", 1.20),
        ("instagram_follower", 2.50),
        ("instagram_view", 0.40),
        ("telegram_subscriber", 4.00),
        ("telegram_view", 0.30),
    ]

    for service_name, price in services_to_add:
        cursor.execute("INSERT OR IGNORE INTO services (service_name, price_per_k) VALUES (?, ?)",
                       (service_name, price))

    conn.commit()
    conn.close()

def get_user_balance(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0.0

def update_user_balance(user_id, amount):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0.0)", (user_id,))
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_service_price(service_name):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT price_per_k FROM services WHERE service_name = ?", (service_name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def get_all_services():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT service_name, price_per_k FROM services")
    results = cursor.fetchall()
    conn.close()
    return results

def update_service_price(service_name, new_price):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE services SET price_per_k = ? WHERE service_name = ?", (new_price, service_name))
    conn.commit()
    conn.close()

def add_order(user_id, service_type, amount, link):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO orders (user_id, service_type, amount, link) VALUES (?, ?, ?, ?)",
                   (user_id, service_type, amount, link))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def update_order_status(order_id, status):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))
    conn.commit()
    conn.close()

def get_order_details(order_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, service_type, amount, link, status, timestamp FROM orders WHERE order_id = ?", (order_id,))
    result = cursor.fetchone()
    conn.close()
    return result

def get_all_orders():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT order_id, user_id, service_type, amount, link, status, timestamp FROM orders ORDER BY timestamp DESC")
    results = cursor.fetchall()
    conn.close()
    return results

def save_admin_message_mapping(user_telegram_id, admin_message_telegram_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO admin_messages (user_id, admin_message_id) VALUES (?, ?)",
                   (user_telegram_id, admin_message_telegram_id))
    conn.commit()
    conn.close()

def get_user_id_from_admin_message_id(admin_message_telegram_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admin_messages WHERE admin_message_id = ?", (admin_message_telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
