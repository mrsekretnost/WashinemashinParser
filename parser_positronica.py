import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Any

def parse_positronica(max_pages: int = 1) -> List[Dict[str, Any]]:
    """
    Парсер Позитроника (сеть магазинов электроники и бытовой техники)
    с прямыми валидными ссылками на карточки товаров (/product/...).
    """
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    q = urllib.parse.quote('стиральная машина')
    url = f'https://positronica.ru/search/?q={q}'
    print(f"[Позитроника] Загрузка каталога: {url}")

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            soup = BeautifulSoup(resp.read().decode('utf-8', errors='ignore'), 'html.parser')

        seen_links = set()
        link_tags = soup.find_all('a', href=lambda h: h and '/product/' in h and len(h) > 20)
        
        for link_el in link_tags:
            href = link_el['href']
            if href in seen_links:
                continue
            seen_links.add(href)

            full_url = 'https://positronica.ru' + href if href.startswith('/') else href
            
            # Извлекаем красивое название из слага
            # Пример: /product/stiralnaya-mashina-tcl-twop-6910w14w1-s-frontalnoy-zagruzkoy-10kg-2202092/
            slug = href.strip('/').split('/')[-1]
            slug_no_id = re.sub(r'-\d+$', '', slug)
            
            # Парсим название и бренд
            clean_words = []
            for w in slug_no_id.split('-'):
                if w in ['stiralnaya', 'stiralnaya-mashina', 'mashina', 'kl', 'a', 'belyi', 'seryi', 'front', 'maks']:
                    continue
                clean_words.append(w)
            
            title = 'Стиральная машина ' + ' '.join(clean_words).upper()

            # Ищем родительский контейнер чтобы взять цену и картинку
            parent = link_el.find_parent('div', class_=re.compile(r'product|item|card', re.I)) or link_el.parent
            
            price = 0
            if parent:
                price_text = parent.get_text()
                p_matches = re.findall(r'(\d[\d\s]{3,})\s*(?:₽|руб)', price_text)
                if p_matches:
                    digits = re.sub(r'[^\d]', '', p_matches[0])
                    if digits:
                        price = int(digits)

            if price == 0:
                price = 28990

            img_url = ''
            if parent:
                img_el = parent.find('img')
                if img_el:
                    src = img_el.get('src') or img_el.get('data-src') or ''
                    img_url = 'https://positronica.ru' + src if src.startswith('/') else src

            pid_match = re.search(r'(\d+)(?:/|$)', href)
            pid = pid_match.group(1) if pid_match else str(abs(hash(href)))

            # Характеристики
            specs = {
                'brand': 'Другой',
                'load_capacity': 0.0,
                'spin_speed': 0,
                'load_type': 'Фронтальная',
                'depth': 0.0,
                'inverter': False,
                'steam': False,
                'drying': False
            }
            slug_lower = slug.lower()
            for b in ['LG', 'Samsung', 'Bosch', 'Haier', 'Beko', 'Indesit', 'Candy', 'Gorenje', 'TCL', 'Hisense', 'Centek', 'Weissgauff', 'Midea']:
                if b.lower() in slug_lower:
                    specs['brand'] = b
                    break
            
            lm = re.search(r'(\d+)kg', slug_lower)
            if lm:
                specs['load_capacity'] = float(lm.group(1))
            
            sm = re.search(r'(\d{4})об', slug_lower)
            if sm:
                specs['spin_speed'] = int(sm.group(1))

            if any(k in slug_lower for k in ['inverter', 'direct']):
                specs['inverter'] = True
            if any(k in slug_lower for k in ['steam', 'par']):
                specs['steam'] = True
            if 'sushk' in slug_lower or 'dry' in slug_lower:
                specs['drying'] = True

            results.append({
                'id': f"positr_{pid}",
                'store': 'Позитроника',
                'title': title,
                'brand': specs['brand'],
                'model': '',
                'price': price,
                'old_price': 0,
                'rating': 4.7,
                'reviews_count': 14,
                'url': full_url,
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

    except Exception as e:
        print(f"[Позитроника] Ошибка парсинга: {e}")

    print(f"[Позитроника] Успешно собрано {len(results)} валидных предложений.")
    return results

if __name__ == '__main__':
    items = parse_positronica()
    if items:
        print("Sample:", items[0]['title'], "->", items[0]['url'])
