import asyncio
import json
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright

DNS_BASE_URL = "https://www.dns-shop.ru"

def parse_specs_from_title(title: str) -> Dict[str, Any]:
    specs = {
        'brand': '',
        'model': '',
        'load_capacity': 0.0,
        'spin_speed': 0,
        'load_type': 'Фронтальная',
        'depth': 0.0,
        'inverter': False,
        'steam': False,
        'drying': False
    }
    
    title_lower = title.lower()
    
    brands = [
        'LG', 'Samsung', 'Bosch', 'Haier', 'Beko', 'Indesit', 'Candy', 'Gorenje',
        'Whirlpool', 'Electrolux', 'AEG', 'Siemens', 'Weissgauff', 'Midea',
        'DEXP', 'TCL', 'Hisense', 'Hotpoint-Ariston', 'Zanussi', 'Kraft', 'Centek'
    ]
    for b in brands:
        if b.lower() in title_lower:
            specs['brand'] = b
            break
            
    # Загрузка (кг)
    load_match = re.search(r'(?:стирка\s*-\s*)?(\d+[\.,]?\d*)\s*(?:кг|kg)', title_lower)
    if load_match:
        try:
            specs['load_capacity'] = float(load_match.group(1).replace(',', '.'))
        except ValueError:
            pass

    # Скорость отжима (об/мин)
    spin_match = re.search(r'(\d{3,4})\s*(?:об\/мин|об|rpm)', title_lower)
    if spin_match:
        try:
            specs['spin_speed'] = int(spin_match.group(1))
        except ValueError:
            pass

    # Глубина (из формата "60 см x 85 см x 44 см")
    depth_match = re.findall(r'(\d+[\.,]?\d*)\s*см', title_lower)
    if len(depth_match) >= 3:
        try:
            specs['depth'] = float(depth_match[2].replace(',', '.'))
        except ValueError:
            pass

    if 'вертикальн' in title_lower:
        specs['load_type'] = 'Вертикальная'
    else:
        specs['load_type'] = 'Фронтальная'

    if any(k in title_lower for k in ['инвертор', 'inverter', 'прямой привод', 'direct drive']):
        specs['inverter'] = True
    if any(k in title_lower for k in ['пар', 'steam']):
        specs['steam'] = True
    if any(k in title_lower for k in ['сушк', 'сушка', 'dry']):
        specs['drying'] = True

    return specs

async def parse_dns(max_pages: int = 2) -> List[Dict[str, Any]]:
    results = []
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir='./user_session_dns',
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--start-minimized']
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # Ставим куку для Георгиевска
        await context.add_cookies([{
            'name': 'city_path',
            'value': 'georgievsk',
            'domain': '.dns-shop.ru',
            'path': '/'
        }])

        for page_num in range(1, max_pages + 1):
            url = f"https://www.dns-shop.ru/catalog/c01df46f39137fd7/stiralnye-masiny/?p={page_num}&order=6"
            print(f"[DNS] Загрузка страницы {page_num}: {url}")
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=25000)
                await page.wait_for_timeout(3500)
            except Exception as e:
                print(f"[DNS] Ошибка перехода на страницу {page_num}: {e}")
                break

            items = await page.evaluate('''() => {
                const els = Array.from(document.querySelectorAll('.catalog-product'));
                return els.map(e => {
                    const titleEl = e.querySelector('a.catalog-product__name');
                    const priceEl = e.querySelector('.product-buy__price');
                    const availEl = e.querySelector('.order-avail-wrap');
                    const imgEl = e.querySelector('img');
                    const code = e.getAttribute('data-code') || '';
                    return {
                        id: code ? 'dns_' + code : null,
                        title: titleEl ? titleEl.innerText.trim() : '',
                        url: titleEl ? 'https://www.dns-shop.ru' + titleEl.getAttribute('href') : '',
                        price_str: priceEl ? priceEl.innerText.trim() : '0',
                        avail: availEl ? availEl.innerText.trim() : '',
                        image_url: imgEl ? (imgEl.src || imgEl.getAttribute('data-src')) : ''
                    };
                });
            }''')

            if not items:
                print(f"[DNS] На странице {page_num} нет товаров.")
                break

            for item in items:
                if not item['title'] or not item['id']:
                    continue
                
                digits = re.sub(r'[^\d]', '', item['price_str'])
                price = int(digits) if digits else 0
                specs = parse_specs_from_title(item['title'])
                
                delivery_available = True
                delivery_info = "Доставка на дом / самовывоз в Георгиевске"
                if item['avail']:
                    delivery_info = f"Георгиевск: {item['avail']}"

                clean_title = re.sub(r'\s*\[.*?\]', '', item['title']).strip()

                prod = {
                    'id': item['id'],
                    'store': 'DNS',
                    'title': clean_title,
                    'brand': specs['brand'] or 'Другой',
                    'model': '',
                    'price': price,
                    'old_price': 0,
                    'rating': 4.8,
                    'reviews_count': 0,
                    'url': item['url'],
                    'image_url': item['image_url'],
                    'load_type': specs['load_type'],
                    'load_capacity': specs['load_capacity'],
                    'spin_speed': specs['spin_speed'],
                    'depth': specs['depth'],
                    'width': 60.0,
                    'height': 85.0,
                    'inverter': specs['inverter'],
                    'steam': specs['steam'],
                    'drying': specs['drying'],
                    'delivery_available': delivery_available,
                    'delivery_info': delivery_info,
                    'city': 'Георгиевск'
                }
                results.append(prod)

            print(f"[DNS] Собрано {len(items)} товаров со страницы {page_num}")

        await context.close()

    print(f"[DNS] Всего успешно спарсено: {len(results)} стиральных машин.")
    return results

if __name__ == '__main__':
    prods = asyncio.run(parse_dns(1))
    print(f"Parsed {len(prods)} products")
