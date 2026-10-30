import asyncio
import datetime
from database import init_db, save_products
from parser_dns import parse_dns
from parser_mvideo import parse_mvideo
from parser_citilink import parse_citilink
from parser_eldorado import parse_eldorado
from parser_positronica import parse_positronica

async def run_all_parsers(pages_per_store: int = 2):
    print("=== Начало сбора данных по стиральным машинам с доставкой в Георгиевск ===")
    init_db()

    total_products = []

    # 1. DNS
    try:
        print("\n--- Запуск парсера DNS ---")
        dns_items = await parse_dns(max_pages=pages_per_store)
        save_products(dns_items)
        total_products.extend(dns_items)
    except Exception as e:
        print(f"[ERROR] DNS parser error: {e}")

    # 2. М.Видео
    try:
        print("\n--- Запуск парсера М.Видео ---")
        mvideo_items = await parse_mvideo(max_pages=pages_per_store)
        save_products(mvideo_items)
        total_products.extend(mvideo_items)
    except Exception as e:
        print(f"[ERROR] M.Video parser error: {e}")

    # 3. Эльдорадо
    try:
        print("\n--- Запуск парсера Эльдорадо ---")
        el_items = await parse_eldorado(max_pages=pages_per_store)
        save_products(el_items)
        total_products.extend(el_items)
    except Exception as e:
        print(f"[ERROR] Eldorado parser error: {e}")

    # 4. Ситилинк
    try:
        print("\n--- Запуск парсера Ситилинк ---")
        citilink_items = await parse_citilink(max_pages=pages_per_store)
        save_products(citilink_items)
        total_products.extend(citilink_items)
    except Exception as e:
        print(f"[ERROR] Citilink parser error: {e}")

    # 5. Позитроника
    try:
        print("\n--- Запуск парсера Позитроника ---")
        pos_items = await parse_positronica(max_pages=pages_per_store)
        save_products(pos_items)
        total_products.extend(pos_items)
    except Exception as e:
        print(f"[ERROR] Positronica parser error: {e}")

    print(f"\n=== Сбор завершен! Всего добавлено/обновлено: {len(total_products)} предложений ===")
    return len(total_products)

if __name__ == '__main__':
    asyncio.run(run_all_parsers(pages_per_store=1))
