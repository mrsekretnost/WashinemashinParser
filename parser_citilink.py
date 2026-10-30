import asyncio
import json
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

def parse_specs_from_citilink(item: Dict[str, Any]) -> Dict[str, Any]:
    name = item.get('name') or item.get('shortName') or ''
    props = item.get('propertiesShort', [])
    
    brand = item.get('brand', {}).get('name', '')
    if not brand:
        # Попробуем извлечь из названия
        for b in ['LG', 'Samsung', 'Bosch', 'Haier', 'Beko', 'Indesit', 'Candy', 'Gorenje', 'Hisense', 'TCL', 'Midea', 'Centek', 'Weissgauff']:
            if b.lower() in name.lower():
                brand = b
                break

    load_capacity = 0.0
    spin_speed = 0
    load_type = 'Фронтальная'
    depth = 0.0
    inverter = False
    steam = False
    drying = False

    name_lower = name.lower()
    if 'вертикальн' in name_lower:
        load_type = 'Вертикальная'

    if any(k in name_lower for k in ['инвертор', 'inverter', 'direct drive']):
        inverter = True
    if any(k in name_lower for k in ['пар', 'steam']):
        steam = True
    if any(k in name_lower for k in ['сушк', 'сушкой', 'wd']):
        drying = True

    for p in props:
        p_name = p.get('name', '').lower()
        p_val = p.get('value', '')
        # Загрузка и отжим: "6 кг, 1200 об/мин"
        load_m = re.search(r'(\d+[\.,]?\d*)\s*кг', p_val, re.IGNORECASE)
        if load_m:
            try:
                load_capacity = float(load_m.group(1).replace(',', '.'))
            except ValueError:
                pass

        spin_m = re.search(r'(\d{3,4})\s*об', p_val, re.IGNORECASE)
        if spin_m:
            try:
                spin_speed = int(spin_m.group(1))
            except ValueError:
                pass

        # Габариты: "59.5×84.5×42 см"
        dim_m = re.findall(r'(\d+[\.,]?\d*)', p_val)
        if 'габариты' in p_name or 'размеры' in p_name or len(dim_m) >= 3:
            try:
                # Обычно: ширина x высота x глубина
                if len(dim_m) >= 3:
                    depth = float(dim_m[2].replace(',', '.'))
            except (IndexError, ValueError):
                pass

    # Если не нашли в свойствах, ищем в заголовке
    if load_capacity == 0.0:
        lm = re.search(r'(\d+[\.,]?\d*)\s*кг', name_lower)
        if lm:
            try:
                load_capacity = float(lm.group(1).replace(',', '.'))
            except ValueError:
                pass

    if spin_speed == 0:
        sm = re.search(r'(\d{3,4})\s*об', name_lower)
        if sm:
            try:
                spin_speed = int(sm.group(1))
            except ValueError:
                pass

    return {
        'brand': brand or 'Другой',
        'load_capacity': load_capacity,
        'spin_speed': spin_speed,
        'load_type': load_type,
        'depth': depth,
        'inverter': inverter,
        'steam': steam,
        'drying': drying
    }

async def parse_citilink(max_pages: int = 2) -> List[Dict[str, Any]]:
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale='ru-RU',
            viewport={'width': 1920, 'height': 1080}
        )
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        for page_num in range(1, max_pages + 1):
            url = f"https://www.citilink.ru/catalog/stiralnye-mashiny/?p={page_num}"
            print(f"[Ситилинк] Загрузка страницы {page_num}: {url}")
            
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
                await page.goto(url, wait_until='domcontentloaded', timeout=25000)
                await page.wait_for_timeout(4000)
            except Exception as e:
                print(f"[Ситилинк] Ошибка загрузки страницы {page_num}: {e}")
                break

            if not captured_products:
                print(f"[Ситилинк] На странице {page_num} нет товаров GraphQL.")
                break

            for item in captured_products:
                prod_id = f"citilink_{item.get('id')}"
                name = item.get('name') or item.get('shortName') or ''
                slug = item.get('slug', '')
                prod_url = f"https://www.citilink.ru/product/{slug}-{item.get('id')}/"
                
                # Цена
                price_obj = item.get('price', {})
                current_price = 0
                old_price = 0
                if isinstance(price_obj, dict):
                    cp = price_obj.get('current', '0')
                    op = price_obj.get('old', '0')
                    try:
                        current_price = int(re.sub(r'[^\d]', '', str(cp)))
                    except ValueError:
                        pass
                    try:
                        old_price = int(re.sub(r'[^\d]', '', str(op)))
                    except ValueError:
                        pass

                # Картинка
                image_url = ''
                images = item.get('images', {}).get('citilink', [])
                if images and isinstance(images, list):
                    sources = images[0].get('sources', [])
                    for s in sources:
                        if s.get('size') in ['ML', 'MD', 'XL']:
                            image_url = s.get('url', '')
                            break
                    if not image_url and sources:
                        image_url = sources[0].get('url', '')

                specs = parse_specs_from_citilink(item)

                results.append({
                    'id': prod_id,
                    'store': 'Ситилинк',
                    'title': name,
                    'brand': specs['brand'],
                    'model': '',
                    'price': current_price,
                    'old_price': old_price,
                    'rating': float(item.get('rating') or 4.8),
                    'reviews_count': int(item.get('counters', {}).get('reviews', 0)),
                    'url': prod_url,
                    'image_url': image_url,
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
                    'delivery_info': 'Доставка на дом / пункт выдачи (Георгиевск)',
                    'city': 'Георгиевск'
                })

            print(f"[Ситилинк] Собрано {len(captured_products)} товаров со страницы {page_num}")

        await browser.close()

    print(f"[Ситилинк] Всего успешно спарсено: {len(results)} товаров.")
    return results

if __name__ == '__main__':
    items = asyncio.run(parse_citilink(1))
    print(f"Sample: {items[0] if items else 'None'}")
