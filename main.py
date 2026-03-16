import sys
import re
import json
import math
import zipfile
import ssl
import certifi
import urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse
from datetime import datetime

import cloudscraper
from bs4 import BeautifulSoup
from colorama import init, Fore

init(autoreset=True)

BASE_URL = "https://ua.iherb.com"
VAT = 1.05
MAX_CHARS = 850
DATA_DIR = Path("/Users/rika/Documents/iherb_parse_data")
DATA_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

scraper = cloudscraper.create_scraper()
USER_DISCOUNT = None
USD_RATE = None  # загружается один раз в parse_product


# ================= КУРС НБУ =================

def get_usd_uah_rate() -> float:
    """Получает актуальный курс USD→UAH с API Национального банка Украины."""
    try:
        url = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?valcode=USD&json"
        ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(url, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read())
            rate = float(data[0]["rate"])
            print(Fore.CYAN + f"  Курс НБУ: 1 USD = {rate} UAH")
            return rate
    except Exception as e:
        print(Fore.YELLOW + f"  Не вдалося отримати курс НБУ ({e}), використовую 41.0")
        return 41.0


# ================= UTILS =================

def normalize_link(link: str) -> str:
    link = urljoin(BASE_URL, link)
    parsed = urlparse(link)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def parse_price(text: str):
    """
    Надёжно извлекает число из строки цены.
    Поддерживает форматы: 1,234.56 / 1 234,56 / $12.99 / 12,99
    """
    if not text:
        return None
    # Убираем пробелы, валютные символы и неразрывные пробелы
    text = re.sub(r"[^\d.,]", "", text.replace("\xa0", ""))
    if not text:
        return None
    # Есть и запятая и точка → запятая = разделитель тысяч
    if "," in text and "." in text:
        text = text.replace(",", "")
    # Только запятая → определяем роль по количеству цифр после неё
    elif "," in text:
        parts = text.split(",")
        if len(parts) == 2 and len(parts[1]) in (2, 3) and len(parts[0]) <= 4:
            # Скорее всего десятичный разделитель: 12,99
            text = text.replace(",", ".")
        else:
            # Разделитель тысяч: 1,234
            text = text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def extract_price_from_soup(soup):
    """
    Возвращает (raw_text, parsed_float, currency).
    iherb UA отдаёт цены в USD — конвертация в UAH происходит снаружи.
    """

    # 1. JSON-LD — самый надёжный источник (чистое число без мусора)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            offers = data.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0]
            raw = str(offers.get("price", ""))
            currency = offers.get("priceCurrency", "USD")
            val = parse_price(raw)
            if val and val > 0:
                return raw, val, currency
        except Exception:
            pass

    # 2. itemprop="price" — числовой атрибут
    for selector, attr in [
        ("[itemprop='price']", "content"),
        ("[itemprop='price']", "data-price"),
        ("[data-price]", "data-price"),
    ]:
        el = soup.select_one(selector)
        if el:
            raw = el.get(attr, "").strip()
            val = parse_price(raw)
            if val and val > 0:
                return raw, val, "USD"

    # 3. CSS — ищем элемент с $ и разумной ценой (1–2000 USD)
    for selector in [
        ".price-container .price",
        ".product-price-container .price",
        ".our-price",
        ".product-price .price",
        "#price",
        "span.price",
        ".price",
    ]:
        for el in soup.select(selector):
            text = el.get_text(strip=True)
            # берём только если есть $ и строка не замусорена
            if "$" in text and len(text) < 20:
                val = parse_price(text)
                if val and 1 < val < 2000:
                    return text, val, "USD"

    return None, None, None


def extract_discount(soup):
    if USER_DISCOUNT is not None:
        return USER_DISCOUNT
    for selector in [".percent-off", ".discount-percent", "[data-discount]", ".sale-percent"]:
        el = soup.select_one(selector)
        if el:
            raw = el.get("data-discount") or el.get_text(strip=True)
            m = re.search(r"(\d{1,2})\s*%", raw)
            if m:
                return int(m.group(1))
    return 15  # дефолт


# ================= PARSING =================

def get_links(url):
    r = scraper.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    product_div = (
        soup.find("div", class_="products product-cells clearfix")
        or soup.find("div", id="category-products-grid")
        or soup.find("ul", class_="products-grid")
        or soup.find("div", attrs={"data-context": "category"})
    )

    if not product_div:
        raise RuntimeError("Не знайдено список товарів. Перевірте URL або структуру сторінки.")

    links = []
    for a in product_div.find_all("a", href=True):
        link = normalize_link(a["href"])
        if "/r/" in link or link == BASE_URL:
            continue
        if re.search(r"/pr/|/p/|\d{5,}", link):
            links.append(link)

    return list(dict.fromkeys(links))


def parse_product(url):
    global USD_RATE
    if USD_RATE is None:
        USD_RATE = get_usd_uah_rate()

    r = scraper.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, "html.parser")

    # Заголовок
    title_el = soup.select_one("h1.product-title, h1[itemprop='name'], h1")
    title = title_el.get_text(strip=True) if title_el else "Без назви"

    # Цена и скидка (нужны раньше — для расчёта бюджета описания)
    raw_text, price_usd, currency = extract_price_from_soup(soup)
    discount = extract_discount(soup)

    if price_usd:
        price_uah = price_usd * USD_RATE
        price_after_discount = price_uah * (1 - discount / 100)  # применяем скидку
        final_price = math.ceil(price_after_discount * VAT)  # + НДС 5%
        print(
            Fore.CYAN + f"  {raw_text!r} ({currency}) → {price_usd} USD × {USD_RATE:.2f} × {1 - discount / 100} × {VAT} = {final_price} грн")
    else:
        final_price = None
        print(Fore.YELLOW + f"  Ціну не знайдено на {url}")

    # Описание — режем пункты пока весь итоговый текст не влезает в MAX_CHARS
    desc_ul = soup.select_one(".inner-content .item-row ul")
    if desc_ul:
        items = [li.get_text(strip=True) for li in desc_ul.find_all("li") if li.get_text(strip=True)]

        # Считаем сколько символов займёт шаблон без описания
        template = (
            f"🔥 -{discount}% Цiна {final_price} грн. *{title}*\n\n"
            f"✏️ *Рекомендації*\n\n\n"
            f"🔗 {url}"
        )
        budget = MAX_CHARS - len(template)

        lines = []
        for item in items:
            line = f"• {item}"
            chunk = "\n".join(lines + [line])
            if len(chunk) > budget:
                break
            lines.append(line)

        description = "\n".join(lines)
    else:
        # fallback на старые селекторы
        desc_el = soup.select_one(
            ".prodOverviewDetail, .product-overview, [itemprop='description'], .overview-content"
        )
        description = desc_el.get_text(strip=True) if desc_el else ""

    # Изображение
    img_el = (
        soup.select_one("#iherb-product-image")
        or soup.select_one("[itemprop='image']")
        or soup.select_one(".product-image img")
        or soup.select_one("img.product-photo")
    )
    img_url = None
    if img_el:
        img_url = img_el.get("src") or img_el.get("data-src")

    return {
        "title": title,
        "description": description,
        "price": final_price,
        "discount": discount,
        "img": img_url,
    }


# ================= FILES =================

def save_product(data, url, index):
    if data["price"] is None:
        return False

    txt_path = DATA_DIR / f"{index}.txt"
    img_path = DATA_DIR / f"{index}.jpg"

    text = (
        f"🔥 -{data['discount']}% Цiна {data['price']} грн. *{data['title']}*\n\n"
        f"✏️ *Рекомендації*\n{data['description']}\n\n"
        f"🔗 {url}"
    )

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    if data["img"]:
        try:
            img_data = scraper.get(data["img"]).content
            with open(img_path, "wb") as f:
                f.write(img_data)
        except Exception:
            txt_path.unlink(missing_ok=True)
            return False

    return True


# ================= ZIP =================

def pack():
    date = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
    archive = DATA_DIR / f"iherb_data_{date}.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for f in DATA_DIR.glob("*"):
            if f.suffix != ".zip":
                z.write(f, f.name)
                f.unlink()
    print("Архів створено:", archive)


# ================= MAIN =================

def main():
    global USER_DISCOUNT

    if len(sys.argv) != 4:
        sys.exit("Використання: python main.py COUNT URL DISCOUNT")

    count = int(sys.argv[1])
    url = sys.argv[2]
    discount = int(sys.argv[3])

    if discount > 0:
        USER_DISCOUNT = discount

    links = get_links(url)[:count]
    print(f"Знайдено посилань: {len(links)}")

    for i, link in enumerate(links):
        try:
            data = parse_product(link)
            if save_product(data, link, i):
                print(Fore.GREEN + f"OK {i}: {data['title']} — {data['price']} грн")
            else:
                print(Fore.YELLOW + f"Пропущено {link}")
        except Exception as e:
            print(Fore.RED + f"Помилка [{link}]: {e}")

    pack()


if __name__ == "__main__":
    main()