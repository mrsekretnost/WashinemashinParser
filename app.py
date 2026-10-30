import streamlit as st
import pandas as pd
import sqlite3
import asyncio
import io
import re
from collections import defaultdict
from database import (
    init_db,
    get_filtered_products,
    add_to_watchlist,
    remove_from_watchlist,
    get_watchlist,
    get_price_history,
    DB_PATH
)
from scraper import run_all_parsers

st.set_page_config(
    page_title="Сравнение цен стиральных машин • Георгиевск",
    page_icon="🧺",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_db()

st.markdown("""
<style>
    .store-badge-dns {
        background-color: #f08c00;
        color: white !important;
        padding: 3px 8px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .store-badge-mvideo {
        background-color: #e03131;
        color: white !important;
        padding: 3px 8px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .store-badge-eldorado {
        background-color: #7950f2;
        color: white !important;
        padding: 3px 8px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .store-badge-citilink {
        background-color: #1c7ed6;
        color: white !important;
        padding: 3px 8px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .store-badge-positr {
        background-color: #0ca678;
        color: white !important;
        padding: 3px 8px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .best-price-badge {
        background-color: #2b8a3e;
        color: white !important;
        padding: 3px 8px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 0.78rem;
    }
    .price-val {
        font-size: 1.25rem;
        font-weight: 800;
    }
    .diff-badge {
        color: #e03131;
        font-weight: 600;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧺 Стиральные машины: сравнение цен по магазинам")
st.caption("Группировка одной и той же модели по DNS, М.Видео, Эльдорадо, Ситилинку и Позитронике с доставкой в г. Георгиевск")

tab_catalog, tab_watchlist, tab_update = st.tabs(["🛒 Каталог со сравнением цен", "🔔 Мониторинг цен", "⚡ Сбор данных / Парсинг"])

def extract_model_key(brand: str, title: str):
    brand_clean = (brand or '').upper().strip()
    cleaned = title.upper()
    stopwords = [
        'СТИРАЛЬНАЯ', 'МАШИНА', 'УЗКАЯ', 'ПОЛНОРАЗМЕРНАЯ', 'АВТОМАТ',
        'БЕЛЫЙ', 'СЕРЫЙ', 'СЕРЕБРИСТЫЙ', 'АНТРАЦИТ', 'ЧЕРНЫЙ',
        'WHITE', 'SILVER', 'BLACK', 'GREY', 'С СУШКОЙ', 'АКТИВАТОРНАЯ'
    ]
    if brand_clean:
        stopwords.append(brand_clean)

    for word in stopwords:
        cleaned = cleaned.replace(word, ' ')

    tokens = re.findall(r'[A-Z0-9\-\/]{3,}', cleaned)
    digit_tokens = [t.strip('-/') for t in tokens if any(c.isdigit() for c in t)]
    model_code = digit_tokens[0] if digit_tokens else (tokens[0] if tokens else '')
    return brand_clean, model_code

def get_store_badge_class(store: str) -> str:
    if store == 'DNS':
        return 'store-badge-dns'
    elif store == 'М.Видео':
        return 'store-badge-mvideo'
    elif store == 'Эльдорадо':
        return 'store-badge-eldorado'
    elif store == 'Ситилинк':
        return 'store-badge-citilink'
    else:
        return 'store-badge-positr'

with st.sidebar:
    st.header("⚙️ Фильтры поиска")
    st.info("📍 **Локация**: г. Георгиевск (Ставропольский край)")

    # Список доступных магазинов
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT store FROM products WHERE store != '' ORDER BY store ASC")
    db_stores = [r[0] for r in cur.fetchall()]
    conn.close()

    selected_stores = st.multiselect("Магазины", options=db_stores, default=db_stores)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT brand FROM products WHERE brand != '' AND brand != 'Другой' ORDER BY brand ASC")
    db_brands = [r[0] for r in cur.fetchall()]
    conn.close()

    selected_brands = st.multiselect("Производители / Бренды", options=db_brands, default=[])

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT MIN(price), MAX(price) FROM products WHERE price > 0")
    price_min_max = cur.fetchone()
    conn.close()

    default_min = price_min_max[0] if (price_min_max and price_min_max[0]) else 10000
    default_max = price_min_max[1] if (price_min_max and price_min_max[1]) else 150000

    price_range = st.slider(
        "Диапазон цены (₽)",
        min_value=int(default_min),
        max_value=int(default_max),
        value=(int(default_min), int(default_max)),
        step=500
    )

    st.subheader("Характеристики")
    load_type_opt = st.selectbox("Тип загрузки", options=["Все", "Фронтальная", "Вертикальная"])
    min_load = st.selectbox("Мин. загрузка белья (кг)", options=[0.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0], format_func=lambda x: "Любая" if x == 0.0 else f"от {x} кг")
    max_depth_opt = st.selectbox("Макс. глубина корпуса", options=[0.0, 35.0, 40.0, 45.0, 50.0, 60.0], format_func=lambda x: "Любая" if x == 0.0 else f"до {x} см (узкая)")

    only_inverter = st.checkbox("Инверторный мотор / прямой привод", value=False)
    only_drying = st.checkbox("С функцией сушки", value=False)
    only_multi_store = st.checkbox("🔥 Только модели в нескольких магазинах (сравнение)", value=False)

    st.divider()
    search_keyword = st.text_input("🔍 Быстрый поиск по названию / модели", "")

with tab_catalog:
    raw_products = get_filtered_products(
        stores=selected_stores if selected_stores else None,
        brands=selected_brands if selected_brands else None,
        min_price=price_range[0],
        max_price=price_range[1],
        min_load=min_load if min_load > 0 else None,
        max_depth=max_depth_opt if max_depth_opt > 0 else None,
        load_type=load_type_opt,
        inverter_only=only_inverter,
        drying_only=only_drying,
        delivery_only=True
    )

    if search_keyword:
        kw = search_keyword.lower()
        raw_products = [p for p in raw_products if kw in p['title'].lower() or kw in p['brand'].lower()]

    grouped_models = defaultdict(list)
    for p in raw_products:
        b, c = extract_model_key(p['brand'], p['title'])
        key = f"{b}_{c}" if c else f"single_{p['id']}"
        grouped_models[key].append(p)

    if only_multi_store:
        grouped_models = {k: v for k, v in grouped_models.items() if len(set(x['store'] for x in v)) > 1}

    sorted_groups = sorted(grouped_models.values(), key=lambda items: min(x['price'] for x in items if x['price'] > 0) if items else 0)

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Уникальных моделей", len(sorted_groups))
    with col_m2:
        multi_count = sum(1 for g in sorted_groups if len(set(x['store'] for x in g)) > 1)
        st.metric("Доступно в 2+ магазинах", multi_count)
    with col_m3:
        total_offers = sum(len(g) for g in sorted_groups)
        st.metric("Всего предложений", total_offers)
    with col_m4:
        st.metric("Город доставки", "Георгиевск")

    st.write("")

    if sorted_groups:
        export_rows = []
        for g in sorted_groups:
            main_p = g[0]
            prices_by_store = {x['store']: x['price'] for x in g}
            export_rows.append({
                'Бренд': main_p['brand'],
                'Название': main_p['title'],
                'Цена DNS': prices_by_store.get('DNS', '—'),
                'Цена М.Видео': prices_by_store.get('М.Видео', '—'),
                'Цена Эльдорадо': prices_by_store.get('Эльдорадо', '—'),
                'Цена Ситилинк': prices_by_store.get('Ситилинк', '—'),
                'Цена Позитроника': prices_by_store.get('Позитроника', '—'),
                'Лучшая цена': min(x['price'] for x in g if x['price'] > 0),
                'Разница в цене': (max(x['price'] for x in g) - min(x['price'] for x in g)) if len(g) > 1 else 0,
                'Загрузка (кг)': main_p['load_capacity'] or '—',
                'Отжим (об/мин)': main_p['spin_speed'] or '—',
                'Глубина (см)': main_p['depth'] or '—',
                'Город': 'Георгиевск'
            })
        df_export = pd.DataFrame(export_rows)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_export.to_excel(writer, index=False, sheet_name='Сравнение_цен')
        excel_data = buffer.getvalue()

        col_e1, col_e2, _ = st.columns([1.5, 1.5, 5])
        with col_e1:
            st.download_button(
                label="📥 Скачать сравнение в Excel (.xlsx)",
                data=excel_data,
                file_name=f"washers_comparison_georgievsk.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with col_e2:
            st.download_button(
                label="📄 Скачать в CSV",
                data=df_export.to_csv(index=False).encode('utf-8-sig'),
                file_name=f"washers_comparison_georgievsk.csv",
                mime="text/csv"
            )

    st.write("---")

    if not sorted_groups:
        st.warning("По выбранным критериям моделей не найдено.")
    else:
        view_mode = st.radio("Вид отображения:", [" Карточки моделей с ценами каждого магазина", "📊 Сводная таблица сравнения"], horizontal=True)

        if view_mode == "📊 Сводная таблица сравнения":
            st.dataframe(
                df_export,
                use_container_width=True
            )
        else:
            for g in sorted_groups:
                main_item = g[0]
                min_price = min(x['price'] for x in g if x['price'] > 0)
                max_price = max(x['price'] for x in g if x['price'] > 0)
                price_diff = max_price - min_price
                stores_in_group = set(x['store'] for x in g)

                with st.container(border=True):
                    col_t1, col_t2 = st.columns([3, 1])
                    with col_t1:
                        st.subheader(f"{main_item['title']}")
                    with col_t2:
                        if len(stores_in_group) > 1 and price_diff > 0:
                            st.markdown(f"<div style='text-align:right;'><span class='diff-badge'>Выгода до {price_diff:,} ₽</span></div>".replace(',', ' '), unsafe_allow_html=True)

                    c_img, c_specs, c_stores = st.columns([1, 1.3, 2.2])

                    with c_img:
                        img_to_show = next((x['image_url'] for x in g if x['image_url']), '')
                        if img_to_show:
                            st.image(img_to_show, use_container_width=True)
                        else:
                            st.caption("📦 Фото отсутствует")

                    with c_specs:
                        st.markdown(f"**Характеристики:**")
                        specs_list = []
                        if main_item['load_capacity']:
                            specs_list.append(f"• Загрузка: **{main_item['load_capacity']} кг**")
                        if main_item['spin_speed']:
                            specs_list.append(f"• Отжим: **{main_item['spin_speed']} об/мин**")
                        if main_item['depth']:
                            specs_list.append(f"• Глубина: **{main_item['depth']} см**")
                        if main_item['load_type']:
                            specs_list.append(f"• Тип: **{main_item['load_type']}**")
                        if main_item['inverter']:
                            specs_list.append("• **Инверторный мотор**")
                        if main_item['steam']:
                            specs_list.append("• **Обработка паром**")
                        if main_item['drying']:
                            specs_list.append("• **Сушка**")

                        if specs_list:
                            st.markdown("<br>".join(specs_list), unsafe_allow_html=True)
                        else:
                            st.caption("Стандартные габариты 60×85 см")

                    with c_stores:
                        st.markdown(f"**Цены в магазинах с доставкой в Георгиевск:**")
                        sorted_offers = sorted(g, key=lambda x: x['price'])
                        for offer in sorted_offers:
                            store_name = offer['store']
                            badge_cls = get_store_badge_class(store_name)
                            is_best = (offer['price'] == min_price and len(stores_in_group) > 1)

                            col_s1, col_s2, col_s3, col_s4 = st.columns([1, 1.2, 1.3, 0.8])
                            with col_s1:
                                st.markdown(f"<span class='{badge_cls}'>{store_name}</span>", unsafe_allow_html=True)
                            with col_s2:
                                p_fmt = f"{offer['price']:,} ₽".replace(',', ' ')
                                if is_best:
                                    st.markdown(f"**{p_fmt}** <span class='best-price-badge'>ЛУЧШАЯ</span>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"**{p_fmt}**", unsafe_allow_html=True)
                            with col_s3:
                                st.caption(f"🚚 {offer['delivery_info']}")
                            with col_s4:
                                st.link_button("Купить", offer['url'], use_container_width=True)

                    st.divider()
                    c_act1, c_act2 = st.columns([1, 4])
                    with c_act1:
                        if st.button("🔔 Отслеживать цену модели", key=f"track_model_{main_item['id']}"):
                            add_to_watchlist(main_item['id'], target_price=int(min_price * 0.95))
                            st.toast(f"Добавлено в мониторинг (цель: {int(min_price * 0.95):,} ₽)!", icon="🔔")

with tab_watchlist:
    st.subheader("🔔 Отслеживание цен и уведомления")
    st.caption("Здесь находятся модели, за ценой которых вы следите. При снижении цены приложение отправит системное уведомление на рабочий стол.")

    watch_items = get_watchlist()
    if not watch_items:
        st.info("Пока нет отслеживаемых моделей. Нажмите кнопку «🔔 Отслеживать цену модели» на любой карточке в каталоге.")
    else:
        for w in watch_items:
            with st.container(border=True):
                st.markdown(f"**{w['title']}**")
                st.caption(f"Магазин: {w['store']} | Доставка: {w['delivery_info']} | Добавлено: {w['added_at'][:10]}")

                col_w1, col_w2, col_w3 = st.columns([1.5, 1, 1])
                with col_w1:
                    new_target = st.number_input(
                        "Целевая цена (₽)",
                        min_value=1000,
                        max_value=300000,
                        value=int(w['target_price'] or w['price']),
                        step=500,
                        key=f"target_input_{w['product_id']}"
                    )
                    if new_target != w['target_price']:
                        add_to_watchlist(w['product_id'], target_price=new_target)
                with col_w2:
                    st.write("")
                    st.write("")
                    st.link_button("Купить в магазине", w['url'], use_container_width=True)
                with col_w3:
                    st.write("")
                    st.write("")
                    if st.button("❌ Удалить", key=f"del_{w['product_id']}", use_container_width=True):
                        remove_from_watchlist(w['product_id'])
                        st.rerun()

                history = get_price_history(w['product_id'])
                if len(history) > 1:
                    st.write("История изменения цены:")
                    df_h = pd.DataFrame(history)
                    df_h['recorded_at'] = pd.to_datetime(df_h['recorded_at'])
                    st.line_chart(df_h.set_index('recorded_at')['price'])

with tab_update:
    st.subheader("⚡ Принудительное обновление каталога")
    st.markdown("""
    Парсер подключен к 5 крупнейшим федеральным сетям:
    - **DNS** (г. Георгиевск, региональный склад и магазины)
    - **М.Видео** (доставка курьером на дом по Ставропольскому краю)
    - **Эльдорадо** (программа утилизации и акции)
    - **Ситилинк** (курьерская доставка крупной бытовой техники)
    - **Позитроника** (партнерская сеть доставки электроники)
    """)

    pages_to_crawl = st.slider("Глубина сбора (страниц с каждого магазина):", min_value=1, max_value=5, value=2)

    if st.button("🚀 Запустить полное обновление базы прямо сейчас", type="primary"):
        with st.spinner("Сбор стиральных машин со всех магазинов... Это займет от 30 до 60 секунд..."):
            count = asyncio.run(run_all_parsers(pages_per_store=pages_to_crawl))
            st.success(f"Обновление успешно завершено! Собрано и обновлено: {count} предложений.")
            st.rerun()
