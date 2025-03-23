import requests
from bs4 import BeautifulSoup
import json
import time
from geopy.geocoders import Yandex
import ssl
import certifi
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройки
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
REGION_CODE = "61"
YANDEX_API_KEY = "f83bb662-ff9c-432c-a7d6-b1d437d8b012"
BASE_URL = "https://sudrf.ru/index.php?id=300&act=go_search&searchtype=fs&court_name=&court_subj={region}&court_type=0&court_okrug=0&vcourt_okrug=0"

# Геокодирование
geolocator = Yandex(api_key=YANDEX_API_KEY, ssl_context=ssl.create_default_context(cafile=certifi.where()))


def geocode_address(address: str):
    if "Не найден" in address:
        return None, None
    try:
        location = geolocator.geocode(address)
        if location:
            logger.debug(f"Геокодирован адрес {address}: {location.latitude}, {location.longitude}")
            return location.latitude, location.longitude
        logger.warning(f"Не удалось геокодировать адрес: {address}")
        return None, None
    except Exception as e:
        logger.error(f"Ошибка геокодирования {address}: {str(e)}")
        return None, None


def parse_courts(region_code: str = REGION_CODE):
    url = BASE_URL.format(region=region_code)
    headers = {"User-Agent": USER_AGENT}

    try:
        logger.info(f"Начинаем парсинг судов для региона {region_code}")
        logger.info(f"URL запроса: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info("Запрос успешно выполнен")
        soup = BeautifulSoup(response.text, "html.parser")

        courts = []
        court_items = soup.select("li")  # Все элементы <li>

        logger.info(f"Найдено элементов <li>: {len(court_items)}")
        if not court_items:
            logger.warning("Не найдено элементов <li> с судами")

        for item in court_items:
            name_link = item.select_one("a.court-result")
            if not name_link:
                continue
            name = name_link.text.strip()

            # Фильтруем только районные и областные суды
            if "мировой" in name.lower() or "участок" in name.lower():
                logger.debug(f"Пропущен мировой суд: {name}")
                continue

            info_div = item.select_one("div.courtInfoCont")
            if not info_div:
                logger.warning(f"Не найден div.courtInfoCont для суда: {name}")
                continue

            # Извлекаем код
            code_elem = info_div.find("b", string="Классификационный код:")
            code = code_elem.next_sibling.strip() if code_elem else "Не найден код"
            if not code.startswith("61"):
                logger.info(f"Пропущен суд вне Ростовской области: {name} (код: {code})")
                continue

            # Извлекаем адрес
            address_elem = info_div.find("b", string="Адрес:")
            address = address_elem.next_sibling.strip() if address_elem else "Не найден адрес"

            # Извлекаем телефон
            phone_elem = info_div.find("b", string="Телефон:")
            phone = phone_elem.next_sibling.strip() if phone_elem else "Не найден телефон"

            # Извлекаем email
            email_link = info_div.find("a", href=lambda x: x and "mailto:" in x)
            email = email_link.text.strip() if email_link else "Не найден email"

            # Извлекаем сайт
            site_link = info_div.find("a", href=lambda x: x and "sudrf.ru" in x and "mailto:" not in x)
            site = site_link["href"] if site_link else "Не найден сайт"

            lat, lon = geocode_address(address)
            court_type = "областной" if "областной" in name.lower() else "районный"

            court_data = {
                "name": name,
                "type": court_type,
                "address": address,
                "phone": phone,
                "email": email,
                "latitude": lat,
                "longitude": lon,
                "website": site,
                "polygon": ""
            }
            courts.append(court_data)
            logger.info(f"Спарсен: {name} -> {address}")

        return courts

    except Exception as e:
        logger.error(f"Общая ошибка: {str(e)}")
        return []


def update_json_file(courts, filename="data/courts_rostov-old.json"):
    """Добавляет новые суды в существующий JSON-файл."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            existing_data = json.load(f)
    except FileNotFoundError:
        logger.warning(f"Файл {filename} не найден, создаём новый")
        existing_data = []

    existing_names = {court["name"] for court in existing_data}
    for court in courts:
        if court["name"] not in existing_names:
            existing_data.append(court)
            logger.info(f"Добавлен в JSON: {court['name']}")
        else:
            logger.debug(f"Суд уже существует в JSON: {court['name']}")

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)
    logger.info(f"Файл {filename} успешно обновлён с {len(existing_data)} судами")


if __name__ == "__main__":
    logger.info("Скрипт запущен")
    requests.packages.urllib3.disable_warnings()
    courts = parse_courts(REGION_CODE)
    if courts:
        update_json_file(courts)
    else:
        logger.warning("Не удалось собрать данные о судах")
