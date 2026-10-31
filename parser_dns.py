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
        'width': 60.0,
        'height': 85.0,
        'inverter': False,
        'steam': False,
        'drying': False,
        'programs_count': 0
    }
    
    title_lower = title.lower()
    
    brands = [
        'LG', 'Samsung', 'Bosch', 'Haier', 'Beko', 'Indesit', 'Candy', 'Gorenje',
        'Whirlpool', 'Electrolux', 'AEG', 'Siemens', 'Weissgauff', 'Midea',
        'DEXP', 'TCL', 'Hisense', 'Hotpoint-Ariston', 'Hotpoint', 'Zanussi', 'Kraft', 'Centek', 'Aceline'
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
    spin_match = re.search(r'(?:отжим\s*-\s*)?(\d{3,4})\s*(?:об\/мин|об|rpm)', title_lower)
    if spin_match:
        try:
            specs['spin_speed'] = int(spin_match.group(1))
        except ValueError:
            pass

    # Габариты (например, "60 см x 85 см x 44 см" или "60 см x 84.5 см x 37 см")
    dim_match = re.findall(r'(\d+[\.,]?\d*)\s*см', title_lower)
    if len(dim_match) >= 3:
        try:
            specs['width'] = float(dim_match[0].replace(',', '.'))
            specs['height'] = float(dim_match[1].replace(',', '.'))
            specs['depth'] = float(dim_match[2].replace(',', '.'))
        except ValueError:
            pass
    elif len(dim_match) == 1:
        try:
            specs['depth'] = float(dim_match[0].replace(',', '.'))
        except ValueError:
            pass

    # Программ
    prog_match = re.search(r'программ\s*-\s*(\d+)', title_lower)
    if prog_match:
        try:
            specs['programs_count'] = int(prog_match.group(1))
        except ValueError:
            pass

    if 'вертикальн' in title_lower:
        specs['load_type'] = 'Вертикальная'
    else:
        specs['load_type'] = 'Фронтальная'

    if any(k in title_lower for k in ['инвертор', 'inverter', 'прямой привод', 'direct drive']):
        specs['inverter'] = True
    if any(k in title_lower for k in ['пар', 'steam', 'обработка паром']):
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

        await context.add_cookies([{
            'name': 'city_path',
            'value': 'georgievsk',
            'domain': '.dns-shop.ru',
            'path': '/'
        }])

        for page_num in range(1, max_pages + 1):
            url = f"https://www.dns-shop.ru/catalog/c01df46f39137fd7/stiralnye-masiny/?p={page_num}&order=6"
            print(f"[DNS] Страница {page_num}: {url}")
            try:
                await page.goto(url, wait_until='domcontentloaded', timeout=25000)
                await page.wait_for_timeout(3500)
            except Exception as e:
                print(f"[DNS] Ошибка перехода: {e}")
                break

            items = await page.evaluate('''() => {
                const els = Array.from(document.querySelectorAll('.catalog-product'));
                return els.map(e => {
                    const titleEl = e.querySelector('a.catalog-product__name');
                    const priceEl = e.querySelector('.product-buy__price');
                    const availEl = e.querySelector('.order-avail-wrap');
                    const imgEl = e.querySelector('img');
                    const ratingEl = e.querySelector('.catalog-product__rating, [data-rating], [class*="rating"]');
                    const code = e.getAttribute('data-code') || '';
                    return {
                        id: code ? 'dns_' + code : null,
                        title_clean: titleEl ? titleEl.innerText.trim() : '',
                        full_text: titleEl ? titleEl.textContent.trim() : '',
                        url: titleEl ? 'https://www.dns-shop.ru' + titleEl.getAttribute('href') : '',
                        price_str: priceEl ? priceEl.innerText.trim() : '0',
                        avail: availEl ? availEl.innerText.trim() : '',
                        rating_str: ratingEl ? ratingEl.innerText.trim() : '',
                        image_url: imgEl ? (imgEl.src || imgEl.getAttribute('data-src')) : ''
                    };
                });
            }''')

            if not items:
                break

            for item in items:
                if not item['full_text'] or not item['id']:
                    continue
                
                digits = re.sub(r'[^\d]', '', item['price_str'])
                price = int(digits) if digits else 0
                specs = parse_specs_from_title(item['full_text'])
                
                # Парсинг рейтинга и отзывов: "4.84 | 3.2k отзывов"
                rating = 4.8
                reviews_count = 50
                r_str = item.get('rating_str', '')
                if r_str:
                    r_match = re.search(r'(\d+[\.,]?\d*)', r_str)
                    if r_match:
                        try:
                            rating = float(r_match.group(1).replace(',', '.'))
                        except ValueError:
                            pass
                    rev_match = re.search(r'([\d\.]+)\s*k?\s*отзыв', r_str, re.IGNORECASE)
                    if rev_match:
                        try:
                            val = float(rev_match.group(1).replace(',', '.'))
                            if 'k' in r_str.lower():
                                val = int(val * 1000)
                            reviews_count = int(val)
                        except ValueError:
                            pass

                delivery_info = "Доставка на дом / самовывоз в Георгиевске"
                if item['avail']:
                    delivery_info = f"Георгиевск: {item['avail']}"

                clean_title = re.sub(r'\s*\[.*?\]', '', item['full_text']).strip()

                prod = {
                    'id': item['id'],
                    'store': 'DNS',
                    'title': clean_title or item['title_clean'],
                    'brand': specs['brand'] or 'Другой',
                    'model': '',
                    'price': price,
                    'old_price': 0,
                    'rating': rating,
                    'reviews_count': reviews_count,
                    'url': item['url'],
                    'image_url': item['image_url'],
                    'load_type': specs['load_type'],
                    'load_capacity': specs['load_capacity'],
                    'spin_speed': specs['spin_speed'],
                    'depth': specs['depth'],
                    'width': specs['width'],
                    'height': specs['height'],
                    'inverter': specs['inverter'],
                    'steam': specs['steam'],
                    'drying': specs['drying'],
                    'delivery_available': True,
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
    print(f"Sample: {prods[0] if prods else 'None'}")
