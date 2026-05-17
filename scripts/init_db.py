"""
Database Initialization Script
Creates SQLite database schema and populates with mock data.
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_db.sqlite")
DATA_DIR = os.path.dirname(DB_PATH)

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)


def create_schema(conn):
    """Create database schema with foreign key constraints."""
    cursor = conn.cursor()
    
    # Enable foreign key support
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create customers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        country TEXT NOT NULL,
        signup_date DATE NOT NULL
    )
    """)
    
    # Create products table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL
    )
    """)
    
    # Create orders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        amount REAL NOT NULL,
        order_date DATE NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)
    
    conn.commit()
    print("✓ Database schema created successfully")


def populate_customers(conn):
    """Populate customers table with mock data."""
    cursor = conn.cursor()
    
    customers = [
        ("John Smith", "john.smith@email.com", "USA", "2023-01-15"),
        ("Sarah Johnson", "sarah.j@email.com", "USA", "2023-02-20"),
        ("Michael Brown", "m.brown@email.com", "UK", "2023-03-10"),
        ("Emma Wilson", "emma.w@email.com", "Canada", "2023-04-05"),
        ("David Lee", "david.lee@email.com", "USA", "2023-05-12"),
        ("Lisa Garcia", "lisa.garcia@email.com", "Spain", "2023-06-18"),
        ("James Taylor", "j.taylor@email.com", "Australia", "2023-07-22"),
        ("Maria Rodriguez", "m.rodriguez@email.com", "Mexico", "2023-08-30"),
        ("Robert Martinez", "r.martinez@email.com", "USA", "2023-09-14"),
        ("Anna Anderson", "anna.a@email.com", "Germany", "2023-10-25"),
    ]
    
    cursor.executemany(
        "INSERT INTO customers (name, email, country, signup_date) VALUES (?, ?, ?, ?)",
        customers
    )
    
    conn.commit()
    print(f"✓ Populated customers table with {len(customers)} records")


def populate_products(conn):
    """Populate products table with mock data."""
    cursor = conn.cursor()
    
    products = [
        ("Premium Laptop", "Electronics", 1299.99, 45),
        ("Wireless Mouse", "Electronics", 29.99, 150),
        ("USB-C Cable", "Accessories", 9.99, 500),
        ("Monitor Stand", "Accessories", 39.99, 80),
        ("Mechanical Keyboard", "Electronics", 149.99, 60),
        ("Laptop Backpack", "Accessories", 59.99, 90),
        ("Webcam HD", "Electronics", 79.99, 110),
        ("Phone Charger", "Accessories", 19.99, 200),
        ("Desk Lamp", "Lighting", 44.99, 70),
        ("Monitor 4K", "Electronics", 499.99, 35),
    ]
    
    cursor.executemany(
        "INSERT INTO products (name, category, price, stock_quantity) VALUES (?, ?, ?, ?)",
        products
    )
    
    conn.commit()
    print(f"✓ Populated products table with {len(products)} records")


def populate_orders(conn):
    """Populate orders table with mock data."""
    cursor = conn.cursor()
    
    products = [
        "Premium Laptop", "Wireless Mouse", "USB-C Cable", "Monitor Stand",
        "Mechanical Keyboard", "Laptop Backpack", "Webcam HD", "Phone Charger",
        "Desk Lamp", "Monitor 4K"
    ]
    
    orders = []
    base_date = datetime(2024, 1, 1)
    
    for customer_id in range(1, 11):
        # Each customer has 3-7 orders
        num_orders = random.randint(3, 7)
        for _ in range(num_orders):
            product_name = random.choice(products)
            
            # Get product price
            cursor.execute("SELECT price FROM products WHERE name = ?", (product_name,))
            result = cursor.fetchone()
            price = result[0] if result else 100.0
            
            # Quantity ordered (1-3)
            quantity = random.randint(1, 3)
            amount = price * quantity
            
            # Random order date within 2024
            days_offset = random.randint(0, 365)
            order_date = (base_date + timedelta(days=days_offset)).strftime("%Y-%m-%d")
            
            orders.append((customer_id, product_name, amount, order_date))
    
    cursor.executemany(
        "INSERT INTO orders (customer_id, product_name, amount, order_date) VALUES (?, ?, ?, ?)",
        orders
    )
    
    conn.commit()
    print(f"✓ Populated orders table with {len(orders)} records")


def main():
    """Initialize the database."""
    # Check if database already exists
    db_exists = os.path.exists(DB_PATH)
    
    if db_exists:
        response = input(f"Database already exists at {DB_PATH}. Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("Cancelling database initialization.")
            return
        os.remove(DB_PATH)
        print("✓ Removed existing database")
    
    try:
        # Connect and create database
        conn = sqlite3.connect(DB_PATH)
        
        print("Initializing Hybrid Chatbot Database...")
        print("-" * 50)
        
        # Create schema and populate tables
        create_schema(conn)
        populate_customers(conn)
        populate_products(conn)
        populate_orders(conn)
        
        conn.close()
        
        print("-" * 50)
        print(f"✓ Database successfully initialized at {DB_PATH}")
        print("\nYou can now run the chatbot with: python main.py")
    
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        raise


if __name__ == "__main__":
    main()
