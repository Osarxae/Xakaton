import requests
from bs4 import BeautifulSoup
import json
import time
from geopy.geocoders import Yandex
import ssl
import certifi

# Настройки
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
REGION_CODE = "61"
YANDEX_API_KEY = "f83bb662-ff9c-432c-a7d6-b1d437d8b012"
BASE_URL = "https://sudrf.ru/index.php?id=300&act=go_ms_search&searchtype=ms&var=true&ms_type=ms&ms_subj={region}"

geolocator = Yandex(api_key=YANDEX_API_KEY, ssl_context=ssl.create_default_context(cafile=certifi.where()))


def geocode_address(address: str):
    if "Не найден" in address:
        return None, None
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        return None, None
    except Exception as e:
        print(f"Ошибка геокодирования {address}: {str(e)}")
        return None, None


def parse_court_details(site: str):
    """Парсинг адреса, телефона, email и территории подсудности."""
    try:
        # Основная страница
        response = requests.get(site, headers={"User-Agent": USER_AGENT}, timeout=10, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        address_elem = soup.find("p", id="court_address")
        address = address_elem.text.strip() if address_elem else "Не найден адрес"

        phone_elem = soup.find("p", class_="person-phone")
        phone = phone_elem.find("span", class_="right").text.strip() if phone_elem and phone_elem.find("span",
                                                                                                       class_="right") else "Не найден телефон"

        email_elem = soup.find("p", id="court_email")
        email = email_elem.text.strip() if email_elem else "Не найден email"

        # Страница подсудности
        territory_url = f"{site}/modules.php?name=sud_delo&op=terr"
        territory_response = requests.get(territory_url, headers={"User-Agent": USER_AGENT}, timeout=10, verify=False)
        territory_soup = BeautifulSoup(territory_response.text, "html.parser")

        # Ищем текст территории (обычно в div или table)
        territory_elem = territory_soup.find("div", class_="content") or territory_soup.find("table")
        territory = territory_elem.text.strip() if territory_elem else "Не найдена территория"

        return address, phone, email, territory
    except Exception as e:
        print(f"Ошибка парсинга {site}: {str(e)}")
        return "Не найден адрес", "Не найден телефон", "Не найден email", "Не найдена территория"


def parse_courts(region_code: str = REGION_CODE):
    url = BASE_URL.format(region=region_code)
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        courts = []
        court_rows = soup.select("table.msSearchResultTbl tr")

        for row in court_rows:
            name_link = row.select_one("a[onclick^='listcontrol']")
            if not name_link:
                continue
            name = name_link.text.strip()

            info_div = row.select_one("div.courtInfoCont")
            if not info_div:
                continue

            code_elem = info_div.find("b", string="Классификационный код:")
            if not code_elem:
                continue
            code = code_elem.next_sibling.strip()

            if not code.startswith("61MS"):
                print(f"Пропущен суд вне Ростовской области: {name} (код: {code})")
                continue

            site_link = info_div.select_one("a[target='_blank']")
            site = site_link["href"] if site_link else None

            address, phone, email, territory = parse_court_details(site) if site else (
            "Не найден адрес", "Не найден телефон", "Не найден email", "Не найдена территория")
            lat, lon = geocode_address(address)

            court_data = {
                "name": name,
                "code": code,
                "address": address,
                "phone": phone,
                "email": email,
                "coordinates": {"lat": lat, "lon": lon},
                "website": site,
                "territory": territory  # Добавляем текстовое описание территории
            }
            courts.append(court_data)
            print(f"Спарсен: {name} -> {address} -> {territory[:50]}...")
            time.sleep(1)

        return courts

    except Exception as e:
        print(f"Общая ошибка: {str(e)}")
        return []


def save_to_json(courts, filename="rostov_courts_with_territory.json"):
    try:
        print(f"Попытка сохранить {len(courts)} судов в {filename}")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(courts, f, ensure_ascii=False, indent=4)
        print(f"Данные сохранены в {filename}")
    except Exception as e:
        print(f"Ошибка сохранения: {str(e)}")


if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    courts = parse_courts(REGION_CODE)
    if courts:
        save_to_json(courts)