import time
import datetime
import asyncio
import subprocess
import os
import sys
import sqlite3
from database import get_watchlist, save_products, DB_PATH
from scraper import run_all_parsers

def send_windows_toast(title: str, message: str):
    """
    Отправка нативного всплывающего уведомления Windows 10/11
    через Windows.UI.Notifications (работает без сторонних утилит).
    """
    title_escaped = title.replace("'", "''").replace('"', '`"')
    message_escaped = message.replace("'", "''").replace('"', '`"')
    
    ps_cmd = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $textNodes = $template.GetElementsByTagName('text')
    $textNodes.Item(0).AppendChild($template.CreateTextNode('{title_escaped}')) | Out-Null
    $textNodes.Item(1).AppendChild($template.CreateTextNode('{message_escaped}')) | Out-Null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Стиральные машины Георгиевск').Show($toast)
    """
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd], capture_output=True)
        return True
    except Exception as e:
        print(f"[Toast Error]: {e}")
        return False

async def check_watchlist_prices(refresh_catalog: bool = False):
    """
    Проверяет цены товаров из списка отслеживания.
    Если refresh_catalog=True, сначала опрашивает магазины на свежие цены.
    """
    items = get_watchlist()
    if not items:
        print("[Мониторинг] Список отслеживания пуст. Добавьте товары кнопкой 'Отслеживать цену' в приложении.")
        return 0

    print(f"[Мониторинг] Проверка {len(items)} моделей в отслеживании...")

    if refresh_catalog:
        try:
            print("[Мониторинг] Опрос магазинов для обновления цен...")
            await run_all_parsers(pages_per_store=1)
        except Exception as e:
            print(f"[Мониторинг] Ошибка обновления магазинов: {e}")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    notifications_sent = 0

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

        # Если задана целевая цена и текущая цена упала до неё или ниже
        if target_price and current_price <= target_price:
            p_curr = f"{current_price:,} руб".replace(',', ' ')
            p_targ = f"{target_price:,} руб".replace(',', ' ')
            
            toast_title = "🔥 Цена снизилась! (Георгиевск)"
            toast_msg = f"{store}: {title[:35]}...\nСейчас: {p_curr} (цель была: {p_targ})"
            
            try:
                print(f"[СКИДКА]: {title} в {store} -> {p_curr}")
            except Exception:
                pass
            send_windows_toast(toast_title, toast_msg)
            notifications_sent += 1

    conn.close()
    return notifications_sent

def run_monitoring_loop(interval_minutes: int = 30):
    """
    Непрерывный фоновый мониторинг с периодическим опросом
    """
    print(f"[Мониторинг] Служба запущена. Интервал проверки: {interval_minutes} мин.")
    send_windows_toast(
        "🧺 Мониторинг запущен",
        f"Отслеживание цен стиральных машин в Георгиевске активно (проверка каждые {interval_minutes} мин)"
    )

    while True:
        try:
            asyncio.run(check_watchlist_prices(refresh_catalog=True))
        except Exception as e:
            print(f"[Ошибка мониторинга]: {e}")
            
        time.sleep(interval_minutes * 60)

if __name__ == '__main__':
    # При запуске из start_monitor.bat запускаем непрерывный цикл
    run_monitoring_loop(interval_minutes=30)
