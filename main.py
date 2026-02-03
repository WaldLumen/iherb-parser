import sys
import re
import time
import math
import os
import zipfile
import shutil
from pathlib import Path

from urllib.parse import urljoin, urlparse, urlunparse
from datetime import datetime

import cloudscraper

from bs4 import BeautifulSoup
from colorama import init, Fore

init(autoreset=True)

# ===================== КОНСТАНТЫ =====================

BASE_URL = "https://ua.iherb.com"
VAT = 1.05
DEFAULT_DISCOUNT = 15
MAX_CHARS = 850
DATA_DIR = "C:/Users/rika/Documents/iherb_parser_data"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cookie": "iher-pref1=storeid=0&sccode=UA&lan=uk-UA&scurcode=UAH&wp=2"
}

FEATURE_BLACKLIST = {"містить", "інгредієнти", "склад", "зберігати"}

BLOCK_PATTERNS = [
    r"/r/",
    r"New-Products",
    r"Specials",
    r"Trial-Pricing",
    r"21st-century",
    r"nmn"
]

scraper = cloudscraper.create_scraper()

# ===================== УТИЛИТЫ =====================
def pack_and_cleanup(folder_path, archive_name="archive.zip"):
    folder = Path(folder_path).resolve()
    archive_path = folder / archive_name

    if not folder.is_dir():
        raise ValueError("Указанный путь не является папкой")

    # Создаём архив
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for item in folder.iterdir():
            if item.name == archive_name:
                continue
            if item.is_file():
                zipf.write(item, arcname=item.name)
            else:
                for sub in item.rglob("*"):
                    zipf.write(sub, arcname=sub.relative_to(folder))

    # Удаляем всё кроме архива
    for item in folder.iterdir():
        if item.name == archive_name:
            continue
        if item.is_file():
            item.unlink()
        else:
            shutil.rmtree(item)

    print(f"Готово: создан архив {archive_path}")


def normalize_link(link: str) -> str:
    link = urljoin(BASE_URL, link)
    parsed = urlparse(link)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def parse_price(text: str) -> float | None:
    if not text:
        return None

    text = text.replace("\xa0", "").replace(" ", "")
    match = re.search(r"[\d.,]+", text)
    if not match:
        return None

    value = match.group()

    if "," in value and "." in value:
        value = value.replace(",", "")
    else:
        value = value.replace(",", ".")

    try:
        return float(value)
    except ValueError:
        return None


def extract_discount(soup: BeautifulSoup) -> int:
    span = soup.select_one(".percent-off")
    if not span:
        return DEFAULT_DISCOUNT

    text = span.get_text(strip=True)
    # text -> "(Знижка 55 %)" или "(Знижка 55 %)"

    match = re.search(r"(\d+)\s*%", text)
    if not match:
        return DEFAULT_DISCOUNT

    return int(match.group(1))

    match = re.search(r"(\d{1,2})%", div.text)
    return max(DEFAULT_DISCOUNT, int(match.group(1))) if match else DEFAULT_DISCOUNT


def is_valid_feature(text: str) -> bool:
    t = text.lower()
    return not any(word in t for word in FEATURE_BLACKLIST)

# ===================== ПАРСИНГ =====================

def get_links(url: str) -> list[str]:
    soup = BeautifulSoup(
        scraper.get(url, headers=HEADERS, timeout=15).text,
        "html.parser"
    )

    div = soup.find("div", class_="products product-cells clearfix")
    if not div:
        raise RuntimeError("Список товарів не знайдено")

    links = [normalize_link(a["href"]) for a in div.find_all("a", href=True)]

    result = []
    for link in links:
        if any(re.search(p, link) for p in BLOCK_PATTERNS):
            continue
        result.append(link)

    return list(dict.fromkeys(result))


def parse_summary(url: str):
    soup = BeautifulSoup(
        scraper.get(url, headers=HEADERS, timeout=15).text,
        "html.parser"
    )

    title = soup.find("h1")
    title = title.get_text(strip=True) if title else "Без назви"

    desc_div = soup.find("div", class_="prodOverviewDetail")
    description = desc_div.get_text(strip=True) if desc_div else "Опис відсутній"

    price_div = soup.find("div", class_="list-price")
    price_value = parse_price(price_div.text if price_div else "")

    discount = extract_discount(soup)

    if price_value:
        price_value = math.ceil(price_value * (1 - discount / 100) * VAT)

    features = [
        li.get_text(strip=True)
        for col in soup.find_all("div", class_="col-xs-24")
        for li in col.find_all("li")
    ]

    return title, description, price_value, discount, features[:len(features)//2]


def get_image(url: str, file_name: str, retries=3) -> bool:
    for _ in range(retries):
        try:
            soup = BeautifulSoup(
                scraper.get(url, headers=HEADERS, timeout=15).text,
                "html.parser"
            )

            img = soup.find("img", id="iherb-product-image")
            if not img or not img.get("src"):
                return False

            data = scraper.get(img["src"], headers=HEADERS).content
            with open(file_name, "wb") as f:
                f.write(data)

            return True
        except Exception:
            time.sleep(2)

    return False


def print_text(url: str, file: str) -> bool:
    title, description, price, discount, items = parse_summary(url)

    if price is None:
        return False

    features = [i for i in items if is_valid_feature(i)]

    def build(features_list):
        return (
            f"🔥 -{discount}% Цiна {price} грн. *{title}*\n\n"
            + "\n".join(f"✅ {i}" for i in features_list)
            + f"\n\n✏️ *Рекомендації*\n{description}\n\n🔗 {url}"
        )

    text = build(features)

    while len(text) > MAX_CHARS and features:
        features.pop()
        text = build(features)

    with open(file, "w", encoding="utf-8") as f:
        f.write(text)

    return True


# ===================== MAIN =====================

def main():
    if len(sys.argv) != 3:
        sys.exit("Використання: python script.py <COUNT> <URL>")

    count = int(sys.argv[1])
    url = sys.argv[2]

    links = get_links(url)[:count]

    for i, link in enumerate(links):
        txt = f"{DATA_DIR}/{i}.txt"
        img = f"{DATA_DIR}/{i}.jpg"

        try:
            # если цены нет — файл не создаётся
            if not print_text(link, txt):
                print(f"{Fore.YELLOW}Без ціни → пропущено: {link}")
                continue

            # если фото не скачалось — удаляем текст
            if not get_image(link, img):
                os.remove(txt)
                print(f"{Fore.YELLOW}Без фото → текст видалено: {link}")
                continue

            print(f"{Fore.GREEN}OK: {i}")

        except Exception as e:
            if os.path.exists(txt):
                os.remove(txt)
            if os.path.exists(img):
                os.remove(img)
            print(f"{Fore.RED}Помилка: {e}")

    date_str = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    archive_name = f"iherb_data_{date_str}.zip"

    pack_and_cleanup(DATA_DIR, archive_name)

if __name__ == "__main__":
    main()
