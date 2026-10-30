import time
import datetime
import asyncio
from typing import List
from database import get_watchlist, save_products, DB_PATH
from parser_dns import parse_dns
from parser_mvideo import parse_mvideo
from parser_citilink import parse_citilink
import sqlite3

def send_notification(title: str, message: str):
    """Отправка уведомления на рабочий стол Windows"""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name='Washer Monitor Георгиевск',
            timeout=10
        )
    except Exception as e:
        print(f"[Notify Error]: {e}")

async def check_watchlist_prices():
    """Проверяет цены товаров из списка отслеживания"""
    items = get_watchlist()
    if not items:
        print("[Мониторинг] Список отслеживания пуст.")
        return

    print(f"[Мониторинг] Проверка {len(items)} отслеживаемых товаров...")
    # Обновляем свежие цены из магазинов
    fresh_products = []
    
    # Сверяем
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    for item in items:
        pid = item['product_id']
        cur.execute("SELECT title, price, store, url FROM products WHERE id = ?", (pid,))
        row = cur.fetchone()
        if not row:
            continue

        current_price = row['price']
        target_price = item['target_price']
        title = row['title']
        store = row['store']

        # Если задана целевая цена и текущая ниже или равна
        if target_price and current_price <= target_price:
            msg = f"Цена снизилась до {current_price:,} ₽ в {store}!\nЦелевая: {target_price:,} ₽".replace(',', ' ')
            print(f"[ЦЕНА ДОСТИГНУТА]: {title} - {msg}")
            send_notification("🔥 Цена снизилась!", f"{title[:40]}...\n{msg}")

    conn.close()

def run_monitoring_loop(interval_minutes: int = 60):
    print(f"[Мониторинг] Запущен фоновый мониторинг цен (интервал {interval_minutes} мин)...")
    while True:
        try:
            asyncio.run(check_watchlist_prices())
        except Exception as e:
            print(f"[Мониторинг Ошибка]: {e}")
        time.sleep(interval_minutes * 60)

if __name__ == '__main__':
    asyncio.run(check_watchlist_prices())
