from urllib.parse import urljoin, urlparse, urlunparse

import cloudscraper
import sys
import time
from colorama import init, Fore, Style
init()

scraper = cloudscraper.create_scraper()  # Используется для всех запросов
filter_keywords = ['Gold', 'Виготовлено', 'гарантія', 'клінічні випробування', 'підтверджена наукою', 'Довгострокова підтримка', 'Palmer\'s', 'Використовуйте', 'Нанесіть', 'Протестовано', 'учасниць', 'дослідження', 'проконсультуватись', 'Наносіть', 'Містить', 'Шрами', 'Розтяжки', 'Без мінеральної олії', 'Без парабенів', 'Без фталатів', 'Швидке поглинання', 'Глибоке зволоження', 'Флакон із дозатором', 'Некомедогенний засіб' 'сімейному підприємстві', 'Вироблено', 'вироблено', 'Компанію засновано', 'Проконсультуйтеся з лікарем', 'Не слід купувати продукт, якщо зовнішня захисна плівка пошкоджена', 'Не слід перевищувати рекомендовану дозу.', 'Зберігати в недоступному для дітей місці.', 'Сімейне підприємство', 'Без ГМО: сертифікат Non GMO LE Certified', 'Сертифікат', 'Certified', 'Перед прийомом', 'Не купуйте, якщо зовнішня захисна плівка пошкоджена або пошкоджена', 'Візьміть одну попередньо виміряну дозу.', 'Розкрийте пакет із фольги на надрізаному кінці', 'Світовий лідер у галузі гомеопатичних препаратів', 'Зберігати в прохолодному місці, захищеному від прямих сонячних променів.', 'Припиніть використання та зверніться до лікаря, якщо з’являється висип.', 'Зберігайте невикористані патчі в пластиковій упаковці і тримайте її щільно закритою для збереження свіжості', 'Наносьте на чисту суху шкіру до будь-яких інших кроків з догляду за шкірою', 'Перед прийманням дієтичних добавок проконсультуйтеся з лікарем, якщо ви проходите курс лікування від захворювання, а також у період вагітності та грудного вигодування.', 'Сертифікат Non-GMO Project Verified', 'Виготовлено з найкращих натуральних плодів монаха', '1:1, як цукор', 'Повністю натуральний продукт', 'Натуральні продукти без глютену', 'Простий і чистий список інгредієнтів', 'Виготовлено зі справжніх фруктів і овочів', 'Без штучних інгредієнтів', 'Сертифікат USDA Organic', 'Сертифікат Non-GMO\xa0Project\xa0Verified', 'Органічний продукт, сертифікований QAI',  'Дата', 'Кокос', 'Овес', 'Груша', 'Яблуко', 'Полуниця', 'Малина', 'Буряк', 'Гарбуз', 'Ваніль', 'Cosmos Natural сертифіковано Ecocert Greenlife згідно зі стандартом COSMOS', 'штучних ароматизаторів;', 'фталатів;', 'сульфатів;', 'парабенів;', 'ЕДТК;', 'глютенів;', 'барвників.', 'Скрутіть', 'Видавіть', 'Дієтична добавка', 'Можна давати окремо або легко додавати до суміші, молока, соку або їжі', 'Провідний виробник мелатоніну', 'Не містить речовин, що ведуть до звикання', 'Для дітей від 4 років', 'Рекомендовано педіатрами', 'Найсолодший сон']


import re
import math
from bs4 import BeautifulSoup

def parse_summary(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cookie': 'iher-pref1=storeid=0&sccode=UA&lan=uk-UA&scurcode=UAH&wp=2; '
                  'ih-preference=store=0; '
                  'ihr-lac=rturl%3Dhttp%3A%2F%2Fcatalog.app.iherb.com%2Fcatalog%2FcurrentUser'
    }

    response = scraper.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Название товара
    title_tag = soup.find('h1')
    title = title_tag.get_text(strip=True) if title_tag else 'Без назви'
    print(f"[DEBUG] Название: {title}")

    # Описание
    desc_div = soup.find('div', class_='prodOverviewDetail')
    description = desc_div.get_text(strip=True) if desc_div else 'Опис відсутній'
    print(f"[DEBUG] Описание: {description}")

    # Цена
    price_div = soup.find('div', class_='list-price')
    price = price_div.get_text(strip=True) if price_div else 'Ціна не знайдена'
    print(f"[DEBUG] Цена (сырой текст): {price}")

    price_numeric = None
    discount_percent = 20

    if price != 'Ціна не знайдена':
        price_clean = re.sub(r'[^\d\.]', '', price.replace(',', '.'))
        print(f"[DEBUG] Очищенная цена: {price_clean}")
        try:
            price_numeric = float(price_clean)
            print(f"[DEBUG] Числовая цена: {price_numeric}")
        except ValueError:
            price_numeric = None
            print(f"[DEBUG] Ошибка преобразования цены")

        # Скидка
        discount_div = soup.find('div', class_='discount-title')
        if discount_div:
            match = re.search(r'(\d{1,2})\s*%', discount_div.get_text())
            if match:
                if discount_percent < int(match.group(1)):
                    discount_percent = int(match.group(1))
                    print(f"[DEBUG] Скидка найдена: {discount_percent}%")
            else:
                print("[DEBUG] Скидка не найдена, но div есть")


        print(f"[DEBUG] Скидка: {discount_percent}")

        # Финальная цена
        if price_numeric is not None:
            discount_multiplier = 1 - discount_percent / 100
            price_numeric *= discount_multiplier
            price_numeric *= 1.05  # НДС
            price_numeric = math.ceil(price_numeric)
            print(f"[DEBUG] Финальная цена с учетом скидки и НДС: {price_numeric}")
    else:
        print("[DEBUG] Цена не найдена")

    # Характеристики
    col_divs = soup.find_all('div', class_='col-xs-24')
    li_items = [li.get_text(strip=True) for col in col_divs for li in col.find_all('li')]
    li_half = li_items[:len(li_items) // 2]
    print(f"[DEBUG] Первая половина характеристик: {li_half[:6]}")

    return title, description, price, price_numeric, li_half, url, discount_percent


def get_links(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cookie': 'iher-pref1=storeid=0&sccode=UA&lan=uk-UA&scurcode=UAH&wp=2; '
                  'ih-preference=store=0; '
                  'ihr-lac=rturl%3Dhttp%3A%2F%2Fcatalog.app.iherb.com%2Fcatalog%2FcurrentUser'
    }

    response = scraper.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    div = soup.find('div', class_='products product-cells clearfix')

    def normalize_link(link):
        link = urljoin("https://ua.iherb.com", link)
        parsed = urlparse(link)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))

    links = [normalize_link(a['href']) for a in div.find_all('a', href=True)]

    filtered_links = [
        link for link in links
        if not re.match(r'https://ua\.iherb\.com/r', link)
        and not re.match(r'.*/New-Products', link)
        and not re.match(r'.*/Specials', link)
        and not re.match(r'.*/Trial-Pricing', link)
        and not link.startswith('#')
        and not re.search(r'21st-century', link)
        and not re.search(r'nmn', link)
    ]

    # Удаляем дубликаты, сохраняя порядок
    filtered_links = list(dict.fromkeys(filtered_links))

    val = int(sys.argv[1])
    return filtered_links[:val]


def get_image(url, file_name, max_retries=5, delay=3):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'Cookie': 'iher-pref1=storeid=0&sccode=UA&lan=uk-UA&scurcode=UAH&wp=2&ifv=1&accsave=0&lchg=1;'
    }

    attempt = 0
    while attempt < max_retries:
        try:
            response = scraper.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                break
            else:
                print(f"⚠️ Спроба {attempt + 1}: Статус {response.status_code}. Повтор через {delay} сек...")
        except Exception as e:
            print(f"⚠️ Спроба {attempt + 1}: Помилка — {e}. Повтор через {delay} сек...")

        attempt += 1
        time.sleep(delay)
    else:
        print("❌ Не вдалося отримати сторінку після кількох спроб.")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    img_tag = soup.find('img', id='iherb-product-image')

    if img_tag and img_tag.get('src'):
        img_url = img_tag['src']
        print(f"Завантаження зображення з: {img_url}")
        img_data = scraper.get(img_url, headers=headers).content
        with open(file_name, 'wb') as f:
            f.write(img_data)
        print(f"✅ Зображення збережено у файл {file_name}")
    else:
        print("❌ Зображення не знайдено.")


def parse_summary(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
        'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cookie': 'iher-pref1=storeid=0&sccode=UA&lan=uk-UA&scurcode=UAH&wp=2; '
                  'ih-preference=store=0; '
                  'ihr-lac=rturl%3Dhttp%3A%2F%2Fcatalog.app.iherb.com%2Fcatalog%2FcurrentUser'
    }

    MAX_CHARS = 850

    response = scraper.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Название товара
    title_tag = soup.find('h1')
    title = title_tag.get_text(strip=True) if title_tag else 'Без назви'

    # Описание
    desc_div = soup.find('div', class_='prodOverviewDetail')
    description = desc_div.get_text(strip=True) if desc_div else 'Опис відсутній'

    # Цена
    price_div = soup.find('div', class_='list-price')
    price = price_div.get_text(strip=True) if price_div else 'Ціна не знайдена'

    price_numeric = None
    discount_percent = 20

    if price != 'Ціна не знайдена':
        price_clean = re.sub(r'[^\d\.]', '', price.replace(',', '.'))
        try:
            price_numeric = float(price_clean)
        except ValueError:
            price_numeric = None

        # Проверка скидки
        discount_div = soup.find('div', class_='discount-title')
        if discount_div:
            match = re.search(r'(\d{1,2})\s*%', discount_div.get_text())
            if match:
                discount_percent = max(discount_percent, int(match.group(1)))

        # Финальная цена
        if price_numeric is not None:
            price_numeric *= (1 - discount_percent / 100)
            price_numeric *= 1.05  # НДС
            price_numeric = math.ceil(price_numeric)

    # Характеристики
    col_divs = soup.find_all('div', class_='col-xs-24')
    li_items = [li.get_text(strip=True) for col in col_divs for li in col.find_all('li')]
    li_half = li_items[:len(li_items) // 2]

    def build_text(features_list):
        parts = [
            f"Назва: {title}",
            f"Опис: {description}",
            f"Ціна: {price_numeric if price_numeric else price}",
            f"Знижка: {discount_percent}%",
            f"Характеристики: {', '.join(features_list)}" if features_list else "",
            f"Посилання: {url}"
        ]
        return "\n".join(part for part in parts if part)

    summary_text = build_text(li_half)

    # 🔄 Ограничение длины
    while len(summary_text) > MAX_CHARS and li_half:
        removed = li_half.pop()
        print(f"[DEBUG] Видалено характеристику: {removed}")
        summary_text = build_text(li_half)

    # 🔪 Если всё ещё длиннее — сокращаем описание
    if len(summary_text) > MAX_CHARS:
        excess = len(summary_text) - MAX_CHARS
        original_len = len(description)
        description = description[:-excess - 5].rsplit(' ', 1)[0] + "..."
        print(f"[DEBUG] Скорочено опис з {original_len} до {len(description)} символів")
        summary_text = build_text(li_half)

    print(f"[DEBUG] Итоговая длина: {len(summary_text)} символів, залишилось характеристик: {len(li_half)}")

    return title, description, price, price_numeric, li_half, url, discount_percent


def print_text(url, file):
    title, description, price, price_numeric, items, link, discount_percent = parse_summary(url)

    # 🧩 Фильтр-слова, которые нужно пропускать
    filter_keywords = ["містить", "інгредієнти", "склад", "зберігати"]

    with open(file, "w", encoding="utf-8") as f:
        f.write(f"🔥 -{discount_percent}% Цiна {price_numeric} грн. *{title}*\n\n")
        for item in items:
            if all(keyword.lower() not in item.lower() for keyword in filter_keywords):
                f.write(f"✅ {item.replace('*', '')}\n")
        f.write(f"\n✏️ *Рекомендації по застосуванню*\n{description}\n")
        f.write(f"\n🔗 {link}\n")

    print(link)
    print(f"{Fore.MAGENTA}{file}{Style.RESET_ALL} - {Fore.GREEN}success!{Style.RESET_ALL}")

def main():
    if len(sys.argv) != 3:
        print("Використання: python parse_summary.py <LNKS_NUM> <URL>")
        sys.exit(1)

    url = sys.argv[2]

    while True:
        try:
            links = get_links(url)
            break
        except Exception as e:
            print(f"Помилка при отриманні посилань: {e}. Повтор спроби...")

    print(links)

    for i in range(len(links)):
        while True:
            try:
                print_text(links[i], f"C:/Users/sylv/Documents/iherb_parser_data/{i}.txt")
                get_image(links[i], f"C:/Users/sylv/Documents/iherb_parser_data/{i}.jpg")
                i += 1
                break
            except Exception as e:
                print(f"{Fore.RED}Помилка при отриманні тексту: {e}. Повтор спроби...{Style.RESET_ALL}")



if __name__ == "__main__":
    main()
