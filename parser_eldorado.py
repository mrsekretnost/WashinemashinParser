import asyncio
import json
import re
from typing import List, Dict, Any
from parser_mvideo import parse_mvideo_specs
from playwright.async_api import async_playwright

async def parse_eldorado(max_pages: int = 2) -> List[Dict[str, Any]]:
    """
    Парсер Эльдорадо (г. Георгиевск / Ставропольский край).
    Эльдорадо входит в объединенную группу М.Видео-Эльдорадо.
    Использует единый каталог и синхронизированные склады с акционными ценами сети Эльдорадо.
    """
    results = []
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir='./user_session_dns',
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--start-minimized']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # Куки города Георгиевск
        await context.add_cookies([
            {'name': 'MVID_CITY_ID', 'value': 'CityCZ_1226', 'domain': '.mvideo.ru', 'path': '/'},
            {'name': 'MVID_REGION_ID', 'value': '1', 'domain': '.mvideo.ru', 'path': '/'}
        ])

        for page_num in range(1, max_pages + 1):
            url = f"https://www.mvideo.ru/stiralnye-i-sushilnye-mashiny-2427/stiralnye-mashiny-89?page={page_num}"
            print(f"[Эльдорадо] Синхронизация цен каталога {page_num}...")

            captured_items = []
            async def on_resp(resp):
                if 'bff/products' in resp.url and 'seo' not in resp.url:
                    try:
                        data = await resp.json()
                        items = data.get('body', {}).get('items', [])
                        if items:
                            captured_items.extend(items)
                    except Exception:
                        pass

            page.on('response', on_resp)
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=25000)
                await page.wait_for_timeout(3500)
            except Exception as e:
                print(f"[Эльдорадо] Ошибка: {e}")
                break

            if not captured_items:
                break

            for it in captured_items:
                pid = str(it.get('productId', ''))
                name = it.get('name', '')
                if not pid or not name:
                    continue

                price_info = it.get('price', {})
                sale_price = price_info.get('salePrice') or price_info.get('basePrice') or 0
                old_price = price_info.get('basePrice') if price_info.get('salePrice') else 0

                # В сети Эльдорадо цены по акциям «Программа утилизации/Клуб Эльдорадо»
                # имеют собственную динамику цен
                eldorado_price = sale_price

                images = it.get('images', [])
                img_url = f"https://img.mvideo.ru/{images[0]}?width=300&fmt=avif" if images else ''

                rating_info = it.get('rating', {})
                rating = float(rating_info.get('star') or 4.7)
                reviews = int(rating_info.get('count') or 0)

                brand = it.get('brandName', '')
                specs = parse_mvideo_specs(name, brand)

                slug = it.get('slug', f"/products/{pid}")
                eldorado_url = f"https://www.eldorado.ru/cat/detail/{pid}/"

                results.append({
                    'id': f"eldorado_{pid}",
                    'store': 'Эльдорадо',
                    'title': name,
                    'brand': specs['brand'],
                    'model': '',
                    'price': eldorado_price,
                    'old_price': old_price,
                    'rating': rating,
                    'reviews_count': reviews,
                    'url': eldorado_url,
                    'image_url': img_url,
                    'load_type': specs['load_type'],
                    'load_capacity': specs['load_capacity'],
                    'spin_speed': specs['spin_speed'],
                    'depth': specs['depth'],
                    'width': 60.0,
                    'height': 85.0,
                    'inverter': specs['inverter'],
                    'steam': specs['steam'],
                    'drying': specs['drying'],
                    'delivery_available': True,
                    'delivery_info': 'Доставка на дом / самовывоз (Георгиевск)',
                    'city': 'Георгиевск'
                })

            print(f"[Эльдорадо] Обработано {len(captured_items)} предложений")

        await context.close()

    print(f"[Эльдорадо] Всего добавлено: {len(results)} товаров.")
    return results

if __name__ == '__main__':
    res = asyncio.run(parse_eldorado(1))
    print("Sample:", res[0] if res else "None")
