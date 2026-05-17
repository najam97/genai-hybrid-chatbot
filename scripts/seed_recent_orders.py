import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_db.sqlite")

# Ensure database exists
if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}. Run scripts/init_db.py first.")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Insert a few recent orders (today and within last 7 days) for customers 1-3
now = datetime.now()
orders = []
for i in range(3):
    # one order today
    orders.append((i+1, f"Test Product {i+1}", 199.99 + i*10, now.strftime("%Y-%m-%d")))
    # one order 3 days ago
    d3 = (now - timedelta(days=3)).strftime("%Y-%m-%d")
    orders.append((i+1, f"Test Product {i+1}", 49.99 + i*5, d3))
    # one order 6 days ago
    d6 = (now - timedelta(days=6)).strftime("%Y-%m-%d")
    orders.append((i+1, f"Test Product {i+1}", 29.99 + i*2, d6))

# Insert without duplicating identical rows (naive check)
inserted = 0
for customer_id, product_name, amount, order_date in orders:
    cursor.execute(
        "SELECT 1 FROM orders WHERE customer_id=? AND product_name=? AND amount=? AND order_date=?",
        (customer_id, product_name, amount, order_date)
    )
    if cursor.fetchone():
        continue
    cursor.execute(
        "INSERT INTO orders (customer_id, product_name, amount, order_date) VALUES (?, ?, ?, ?)",
        (customer_id, product_name, amount, order_date)
    )
    inserted += 1

conn.commit()
conn.close()

print(f"Inserted {inserted} recent orders into {DB_PATH}")