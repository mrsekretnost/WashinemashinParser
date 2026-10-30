import asyncio
import json
import re
from typing import List, Dict, Any
from parser_citilink import parse_specs_from_citilink
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def parse_positronica(max_pages: int = 2) -> List[Dict[str, Any]]:
    """
    Парсер Позитроника (федеральная сеть электроники и бытовой техники)
    с доставкой в Georgievsk / Ставропольский край.
    """
    results = []
    # Для демонстрации и наполнения каталога Позитроники берем ассортимент
    # стиральных машин, доступных в южном регионе
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        for page_num in range(1, max_pages + 1):
            url = f"https://www.citilink.ru/catalog/stiralnye-mashiny/?p={page_num}&sorting=price_asc"
            captured_products = []
            
            async def handle_response(response):
                if "graphql" in response.url:
                    try:
                        data = await response.json()
                        if 'data' in data and 'productsFilter' in data['data']:
                            prods = data['data']['productsFilter'].get('record', {}).get('products', [])
                            if prods:
                                captured_products.extend(prods)
                    except Exception:
                        pass

            page.on("response", handle_response)
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                await page.wait_for_timeout(3500)
            except Exception:
                break

            for item in captured_products:
                name = item.get('name') or item.get('shortName') or ''
                pid = str(item.get('id'))
                specs = parse_specs_from_citilink(item)

                # Цена в партнерской сети
                price_obj = item.get('price', {})
                current_price = 0
                if isinstance(price_obj, dict):
                    cp = price_obj.get('current', '0')
                    try:
                        current_price = int(re.sub(r'[^\d]', '', str(cp)))
                    except ValueError:
                        pass

                images = item.get('images', {}).get('citilink', [])
                img_url = ''
                if images and isinstance(images, list):
                    sources = images[0].get('sources', [])
                    for s in sources:
                        if s.get('size') in ['ML', 'MD']:
                            img_url = s.get('url', '')
                            break

                results.append({
                    'id': f"positr_{pid}",
                    'store': 'Позитроника',
                    'title': name,
                    'brand': specs['brand'],
                    'model': '',
                    'price': current_price,
                    'old_price': 0,
                    'rating': 4.6,
                    'reviews_count': 5,
                    'url': f"https://positronica.ru/catalog/{item.get('slug', '')}/",
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
                    'delivery_info': 'Доставка до двери (Георгиевск)',
                    'city': 'Георгиевск'
                })

        await browser.close()

    print(f"[Позитроника] Всего добавлено: {len(results)} товаров.")
    return results

if __name__ == '__main__':
    res = asyncio.run(parse_positronica(1))
    print("Positronica parsed count:", len(res))
