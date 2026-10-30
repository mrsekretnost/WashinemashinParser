import sqlite3
import datetime
from typing import List, Dict, Any, Optional

DB_PATH = "washers.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Таблица товаров
    cur.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        store TEXT,
        title TEXT,
        brand TEXT,
        model TEXT,
        price INTEGER,
        old_price INTEGER,
        rating REAL,
        reviews_count INTEGER,
        url TEXT,
        image_url TEXT,
        load_type TEXT,
        load_capacity REAL,
        spin_speed INTEGER,
        depth REAL,
        width REAL,
        height REAL,
        inverter BOOLEAN,
        steam BOOLEAN,
        drying BOOLEAN,
        delivery_available BOOLEAN,
        delivery_info TEXT,
        city TEXT DEFAULT 'Георгиевск',
        updated_at TIMESTAMP
    )
    ''')

    # Таблица истории цен для мониторинга
    cur.execute('''
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT,
        price INTEGER,
        recorded_at TIMESTAMP,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    ''')

    # Таблица отслеживаемых товаров (мониторинг цены)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS watchlist (
        product_id TEXT PRIMARY KEY,
        target_price INTEGER,
        notify_on_drop BOOLEAN DEFAULT 1,
        added_at TIMESTAMP,
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    ''')

    conn.commit()
    conn.close()

def save_products(products: List[Dict[str, Any]]):
    if not products:
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.datetime.now().isoformat()

    for p in products:
        # Сначала проверяем текущую цену
        cur.execute("SELECT price FROM products WHERE id = ?", (p['id'],))
        row = cur.fetchone()

        cur.execute('''
        INSERT INTO products (
            id, store, title, brand, model, price, old_price, rating, reviews_count,
            url, image_url, load_type, load_capacity, spin_speed, depth, width, height,
            inverter, steam, drying, delivery_available, delivery_info, city, updated_at
        ) VALUES (
            :id, :store, :title, :brand, :model, :price, :old_price, :rating, :reviews_count,
            :url, :image_url, :load_type, :load_capacity, :spin_speed, :depth, :width, :height,
            :inverter, :steam, :drying, :delivery_available, :delivery_info, :city, :updated_at
        )
        ON CONFLICT(id) DO UPDATE SET
            price = excluded.price,
            old_price = excluded.old_price,
            delivery_available = excluded.delivery_available,
            delivery_info = excluded.delivery_info,
            rating = excluded.rating,
            reviews_count = excluded.reviews_count,
            updated_at = excluded.updated_at
        ''', {
            'id': p['id'],
            'store': p.get('store', ''),
            'title': p.get('title', ''),
            'brand': p.get('brand', ''),
            'model': p.get('model', ''),
            'price': p.get('price', 0),
            'old_price': p.get('old_price', 0),
            'rating': p.get('rating', 0.0),
            'reviews_count': p.get('reviews_count', 0),
            'url': p.get('url', ''),
            'image_url': p.get('image_url', ''),
            'load_type': p.get('load_type', 'Фронтальная'),
            'load_capacity': p.get('load_capacity', 0.0),
            'spin_speed': p.get('spin_speed', 0),
            'depth': p.get('depth', 0.0),
            'width': p.get('width', 0.0),
            'height': p.get('height', 0.0),
            'inverter': 1 if p.get('inverter') else 0,
            'steam': 1 if p.get('steam') else 0,
            'drying': 1 if p.get('drying') else 0,
            'delivery_available': 1 if p.get('delivery_available', True) else 0,
            'delivery_info': p.get('delivery_info', 'Доставка в Георгиевск'),
            'city': 'Георгиевск',
            'updated_at': now
        })

        # Если цены не было или изменилась - пишем в историю
        if not row or row[0] != p.get('price', 0):
            cur.execute('''
            INSERT INTO price_history (product_id, price, recorded_at)
            VALUES (?, ?, ?)
            ''', (p['id'], p.get('price', 0), now))

    conn.commit()
    conn.close()

def get_filtered_products(
    stores: Optional[List[str]] = None,
    brands: Optional[List[str]] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    min_load: Optional[float] = None,
    max_depth: Optional[float] = None,
    load_type: Optional[str] = None,
    inverter_only: bool = False,
    drying_only: bool = False,
    delivery_only: bool = True
) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = "SELECT * FROM products WHERE 1=1"
    params = []

    if stores:
        query += f" AND store IN ({','.join(['?']*len(stores))})"
        params.extend(stores)

    if brands:
        query += f" AND brand IN ({','.join(['?']*len(brands))})"
        params.extend(brands)

    if min_price is not None:
        query += " AND price >= ?"
        params.append(min_price)

    if max_price is not None:
        query += " AND price <= ?"
        params.append(max_price)

    if min_load is not None:
        query += " AND load_capacity >= ?"
        params.append(min_load)

    if max_depth is not None:
        query += " AND depth <= ?"
        params.append(max_depth)

    if load_type and load_type != "Все":
        query += " AND load_type = ?"
        params.append(load_type)

    if inverter_only:
        query += " AND inverter = 1"

    if drying_only:
        query += " AND drying = 1"

    if delivery_only:
        query += " AND delivery_available = 1"

    query += " ORDER BY price ASC"

    cur.execute(query, params)
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def add_to_watchlist(product_id: str, target_price: Optional[int] = None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.datetime.now().isoformat()
    cur.execute('''
    INSERT INTO watchlist (product_id, target_price, notify_on_drop, added_at)
    VALUES (?, ?, 1, ?)
    ON CONFLICT(product_id) DO UPDATE SET target_price = excluded.target_price
    ''', (product_id, target_price, now))
    conn.commit()
    conn.close()

def remove_from_watchlist(product_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM watchlist WHERE product_id = ?", (product_id,))
    conn.commit()
    conn.close()

def get_watchlist() -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('''
    SELECT w.product_id, w.target_price, w.notify_on_drop, w.added_at,
           p.title, p.store, p.price, p.url, p.image_url, p.delivery_info
    FROM watchlist w
    JOIN products p ON w.product_id = p.id
    ORDER BY w.added_at DESC
    ''')
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

def get_price_history(product_id: str) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('''
    SELECT price, recorded_at FROM price_history
    WHERE product_id = ?
    ORDER BY recorded_at ASC
    ''', (product_id,))
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
