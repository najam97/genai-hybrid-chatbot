import sqlite3
import json
import os
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "mock_db.sqlite")
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT SUM(o.amount) AS total_revenue FROM orders o WHERE strftime('%Y-%m', o.order_date) = strftime('%Y-%m', 'now');")
r = cur.fetchone()
print(json.dumps({'total_revenue': r[0]}))
conn.close()