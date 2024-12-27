import sqlite3
import csv
import os
import json
import random
import logging
from typing import Dict, Any, List
from config import DATABASE_URL

logging.basicConfig(level=logging.INFO)

def init_db():
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, 
                  age TEXT, gender TEXT, preferred_fragrances TEXT, location TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (user_id INTEGER, score INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products
                 (id TEXT PRIMARY KEY, name TEXT, url TEXT, category TEXT, description TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS support_requests
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, photo_id TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS recommendations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, recommendation TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()
    logging.info("Database initialized")

def add_user(user_id: int, first_name: str, last_name: str):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (id, first_name, last_name) VALUES (?, ?, ?)",
              (user_id, first_name, last_name))
    conn.commit()
    conn.close()
    logging.info(f"User added/updated: {user_id}")

def update_user(user_id: int, field: str, value: Any):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
        logging.info(f"New user created: {user_id}")
    if isinstance(value, list):
        value = json.dumps(value)
    c.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
    conn.commit()
    conn.close()
    logging.info(f"User {user_id} updated: {field} = {value}")


def get_user(user_id: int) -> Dict[str, Any]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        user_dict = {
            'id': user[0],
            'first_name': user[1],
            'last_name': user[2],
            'age': user[3],
            'gender': user[4],
            'preferred_fragrances': json.loads(user[5]) if user[5] else [],
            'location': user[6]
        }
        return user_dict
    return None

def update_user(user_id: int, field: str, value: Any):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
    if isinstance(value, list):
        value = json.dumps(value)
    c.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
    conn.commit()

    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (id) VALUES (?)", (user_id,))
        logging.info(f"New user created: {user_id}")
    if isinstance(value, list):
        value = json.dumps(value)
    c.execute(f"UPDATE users SET {field} = ? WHERE id = ?", (value, user_id))
    conn.commit()
    conn.close()
    logging.info(f"User {user_id} updated: {field} = {value}")

from typing import Dict, Any



def get_all_users() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    conn.close()
    return [{
        'id': user[0],
        'first_name': user[1],
        'last_name': user[2],
        'age': user[3],
        'gender': user[4],
        'preferred_fragrances': json.loads(user[5]) if user[5] else [],
        'location': user[6]
    } for user in users]

def save_feedback(user_id: int, score: int):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("INSERT INTO feedback (user_id, score) VALUES (?, ?)", (user_id, score))
    conn.commit()
    conn.close()

def get_feedback_stats() -> Dict[str, Any]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT AVG(score) as avg_score, COUNT(*) as total_feedback FROM feedback")
    result = c.fetchone()
    conn.close()
    return {
        'average_score': result[0],
        'total_feedback': result[1]
    }

def import_products_from_csv(csv_file_path):
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file not found at {csv_file_path}")
        return

    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    
    with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
        csv_reader = csv.reader(csvfile)
        for row in csv_reader:
            if len(row) >= 4 and row[3].startswith('https://edp.by/shop/'):
                c.execute("INSERT OR REPLACE INTO products (id, name, url, category) VALUES (?, ?, ?, ?)",
                          (row[0], row[4] if len(row) > 4 else '', row[3], row[3].split('/')[4]))
    
    conn.commit()
    conn.close()
    print("Products imported successfully.")

def get_products_by_category(category: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE category = ?", (category,))
    products = c.fetchall()
    conn.close()
    return [{'id': p[0], 'name': p[1], 'url': p[2], 'category': p[3]} for p in products]

def get_all_products() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()
    return [{'id': p[0], 'name': p[1], 'url': p[2], 'category': p[3]} for p in products]

def get_support_requests() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT * FROM support_requests ORDER BY timestamp DESC LIMIT 10")
    requests = c.fetchall()
    conn.close()
    return [{'id': r[0], 'user_id': r[1], 'message': r[2], 'photo_id': r[3], 'timestamp': r[4]} for r in requests]

def get_support_request_count() -> int:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM support_requests")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_recommendation_count() -> int:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM recommendations")
    count = c.fetchone()[0]
    conn.close()
    return count

def add_support_request(user_id: int, message: str, photo_id: str = None):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("INSERT INTO support_requests (user_id, message, photo_id) VALUES (?, ?, ?)",
              (user_id, message, photo_id))
    conn.commit()
    conn.close()

def add_recommendation(user_id: int, recommendation: str):
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("INSERT INTO recommendations (user_id, recommendation) VALUES (?, ?)",
              (user_id, recommendation))
    conn.commit()
    conn.close()

def get_products_by_preferences(gender: str, fragrances: List[str], limit: int = 5) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DATABASE_URL)
    c = conn.cursor()
    
    # Создаем более гибкое условие для поиска
    fragrance_condition = " OR ".join(["name LIKE ? OR category LIKE ? OR description LIKE ?"] * len(fragrances))
    params = []
    for fragrance in fragrances:
        params.extend([f"%{fragrance}%", f"%{fragrance}%", f"%{fragrance}%"])
    
    # Добавляем поиск по полу, но делаем его необязательным
    gender_condition = "OR (name LIKE ? OR category LIKE ? OR description LIKE ?)"
    params.extend([f"%{gender}%", f"%{gender}%", f"%{gender}%"])
    
    query = f"""
        SELECT * FROM products 
        WHERE ({fragrance_condition}) {gender_condition}
        ORDER BY RANDOM()
        LIMIT ?
    """
    c.execute(query, params + [limit])
    
    products = c.fetchall()
    
    # Если продукты не найдены, выбираем случайные продукты
    if not products:
        c.execute("SELECT * FROM products ORDER BY RANDOM() LIMIT ?", [limit])
        products = c.fetchall()
    
    conn.close()
    
    result = [{'id': p[0], 'name': p[1], 'url': p[2], 'category': p[3], 'description': p[4] if len(p) > 4 else ''} for p in products]
    logging.info(f"Products found: {result}")
    return result
