import asyncio
import json
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright

def parse_mvideo_specs(name: str, brand: str = "") -> Dict[str, Any]:
    full_text = name.lower()
    load_capacity = 0.0
    spin_speed = 0
    load_type = 'Фронтальная'
    depth = 0.0
    inverter = False
    steam = False
    drying = False

    if not brand:
        brands = [
            'LG', 'Samsung', 'Bosch', 'Haier', 'Beko', 'Indesit', 'Candy', 'Gorenje',
            'Whirlpool', 'Electrolux', 'AEG', 'Siemens', 'Weissgauff', 'Midea',
            'TCL', 'Hisense', 'Hotpoint-Ariston', 'Grundig', 'Toshiba', 'Centek'
        ]
        for b in brands:
            if b.lower() in full_text:
                brand = b
                break

    # Загрузка
    load_match = re.search(r'(\d+[\.,]?\d*)\s*(?:кг|kg)', full_text)
    if load_match:
        try:
            load_capacity = float(load_match.group(1).replace(',', '.'))
        except ValueError:
            pass

    # Скорость отжима
    spin_match = re.search(r'(\d{3,4})\s*(?:об\/мин|об|rpm)', full_text)
    if spin_match:
        try:
            spin_speed = int(spin_match.group(1))
        except ValueError:
            pass

    if 'узкая' in full_text:
        depth = 40.0
    elif 'суперузкая' in full_text:
        depth = 33.0
    elif 'стандартная' in full_text or 'полноразмерная' in full_text:
        depth = 55.0

    if 'вертикальн' in full_text:
        load_type = 'Вертикальная'
    else:
        load_type = 'Фронтальная'

    if any(k in full_text for k in ['инвертор', 'inverter', 'direct drive', 'прямой привод']):
        inverter = True
    if any(k in full_text for k in ['пар', 'steam']):
        steam = True
    if any(k in full_text for k in ['сушк', 'сушка', 'сушил', 'dry']):
        drying = True

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

async def parse_mvideo(max_pages: int = 2) -> List[Dict[str, Any]]:
    results = []
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir='./user_session_dns',
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--start-minimized']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # Куки города Георгиевск / Ставропольский край
        await context.add_cookies([
            {'name': 'MVID_CITY_ID', 'value': 'CityCZ_1226', 'domain': '.mvideo.ru', 'path': '/'},
            {'name': 'MVID_REGION_ID', 'value': '1', 'domain': '.mvideo.ru', 'path': '/'}
        ])

        for page_num in range(1, max_pages + 1):
            url = f"https://www.mvideo.ru/stiralnye-i-sushilnye-mashiny-2427/stiralnye-mashiny-89?page={page_num}"
            print(f"[М.Видео] Загрузка страницы {page_num}: {url}")
            
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
                await page.wait_for_timeout(4000)
            except Exception as e:
                print(f"[М.Видео] Ошибка загрузки страницы {page_num}: {e}")
                break

            if not captured_items:
                print(f"[М.Видео] На странице {page_num} нет товаров в API.")
                break

            for it in captured_items:
                pid = str(it.get('productId', ''))
                name = it.get('name', '')
                if not pid or not name:
                    continue

                price_info = it.get('price', {})
                price = price_info.get('salePrice') or price_info.get('basePrice') or 0
                old_price = price_info.get('basePrice') if price_info.get('salePrice') else 0

                # Картинка
                images = it.get('images', [])
                img_url = ''
                if images:
                    img_url = f"https://img.mvideo.ru/{images[0]}?width=300&fmt=avif"

                rating_info = it.get('rating', {})
                rating = float(rating_info.get('star') or 4.7)
                reviews = int(rating_info.get('count') or 0)

                brand = it.get('brandName', '')
                specs = parse_mvideo_specs(name, brand)

                slug = it.get('slug', f"/products/{pid}")
                if not slug.startswith('http'):
                    prod_url = f"https://www.mvideo.ru{slug}"
                else:
                    prod_url = slug

                results.append({
                    'id': f"mvideo_{pid}",
                    'store': 'М.Видео',
                    'title': name,
                    'brand': specs['brand'],
                    'model': '',
                    'price': price,
                    'old_price': old_price,
                    'rating': rating,
                    'reviews_count': reviews,
                    'url': prod_url,
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
                    'delivery_info': 'Доставка курьером на дом (Георгиевск)',
                    'city': 'Георгиевск'
                })

            print(f"[М.Видео] Собрано {len(captured_items)} товаров со страницы {page_num}")

        await context.close()

    print(f"[М.Видео] Всего успешно спарсено: {len(results)} товаров.")
    return results

if __name__ == '__main__':
    items = asyncio.run(parse_mvideo(1))
    print(f"Sample: {items[0] if items else 'None'}")
