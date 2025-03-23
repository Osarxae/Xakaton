# app/services/court_finder.py
import json
from pathlib import Path
from typing import List, Dict, Optional
import logging
import requests
from bs4 import BeautifulSoup
from geopy.distance import geodesic
from app.services.geocoder import geocode_address

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CourtFinder:
    courts_data: List[Dict] = []

    @classmethod
    def load_courts_data(cls):
        file_path = Path(__file__).parent.parent.parent / "data" / "courts_rostov.json"  # Обновили путь
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                cls.courts_data = data if isinstance(data, list) else data.get("courts", [])
            for court in cls.courts_data:
                if "coordinates" in court and "lat" in court["coordinates"] and "lon" in court["coordinates"]:
                    court["latitude"] = court["coordinates"]["lat"]
                    court["longitude"] = court["coordinates"]["lon"]
                elif "latitude" not in court or "longitude" not in court:
                    logger.warning(f"Суд '{court.get('name')}' не имеет координат")
                court["type"] = court.get("type", "мировой" if "Судебный участок" in court["name"] else "районный")
            logger.info(f"Данные о {len(cls.courts_data)} судах успешно загружены")
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {str(e)}")
            cls.courts_data = []

    @classmethod
    async def find_nearest_court(cls, user_coords: tuple, target_type: str) -> Optional[Dict]:
        if not cls.courts_data:
            logger.error("Данные о судах не загружены")
            return None

        min_distance = float('inf')
        nearest_court = None

        logger.debug(f"Поиск ближайшего суда типа '{target_type}' для координат {user_coords}")

        for court in cls.courts_data:
            lat = court.get("latitude")
            lon = court.get("longitude")
            if lat is None or lon is None:
                logger.debug(f"Пропущен суд '{court.get('name')}' из-за отсутствия координат")
                continue

            court_type = court.get("type", "").lower()
            if target_type != court_type:
                continue

            coords = (lat, lon)
            distance = geodesic(user_coords, coords).kilometers
            if distance < min_distance:
                min_distance = distance
                nearest_court = court

        if nearest_court:
            logger.info(f"Найден ближайший суд: '{nearest_court['name']}' ({min_distance:.2f} км)")
            return {
                "name": nearest_court["name"],
                "type": nearest_court["type"],
                "address": nearest_court["address"],
                "phone": nearest_court.get("phone", ""),
                "email": nearest_court.get("email", ""),
                "latitude": nearest_court.get("latitude"),
                "longitude": nearest_court.get("longitude"),
                "website": nearest_court.get("website", ""),
                "electronic_filing": nearest_court.get("electronic_filing", "Не указана"),  # Добавили
                "polygon": ""
            }
        logger.warning(f"Ближайший суд типа '{target_type}' не найден")
        return None

    @classmethod
    def search_courts_by_address_sudrf(cls, address: str, target_type: str) -> List[dict]:
        url = "https://sudrf.ru/index.php"
        params = {
            "id": "300",
            "act": "go_ms_search" if target_type == "мировой" else "go_search",
            "searchtype": "ms" if target_type == "мировой" else "fs",
            "court_subj": "61"
        }
        data = {"court_addr": address}
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
        try:
            logger.info(f"Запрос на sudrf.ru с адресом: {address}, тип: {target_type}")
            response = requests.post(url, params=params, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            courts_found = []
            if target_type == "мировой":
                court_rows = soup.select("table tr")
                for row in court_rows:
                    name_cell = row.select_one("td:nth-child(2) a")
                    if name_cell:
                        court_name = name_cell.text.strip()
                        court_link = row.select_one("td:nth-child(5) a")
                        website = court_link["href"] if court_link else ""
                        courts_found.append({"name": court_name, "website": website})
            else:
                court_items = soup.select("li")
                for item in court_items:
                    name_link = item.select_one("a.court-result")
                    if name_link:
                        court_name = name_link.text.strip()
                        court_link = item.select_one("a[target='_blank']")
                        website = court_link["href"] if court_link else ""
                        courts_found.append({"name": court_name, "website": website})
            logger.info(f"Найдено судов на sudrf.ru: {len(courts_found)}")
            return courts_found
        except Exception as e:
            logger.error(f"Ошибка запроса к sudrf.ru: {str(e)}")
            return []

    @classmethod
    def get_district_from_address(cls, address: str) -> str:
        address = address.replace("\xa0", " ").strip()
        districts = [
            "Азовский", "Аксайский", "Багаевский", "Белокалитвинский", "Боковский",
            "Верхнедонской", "Весёловский", "Волгодонской", "Дубовский", "Егорлыкский",
            "Заветинский", "Зерноградский", "Зимовниковский", "Кагальницкий", "Каменский",
            "Кашарский", "Константиновский", "Красносулинский", "Куйбышевский", "Мартыновский",
            "Матвеево-Курганский", "Миллеровский", "Милютинский", "Морозовский", "Мясниковский",
            "Неклиновский", "Обливский", "Октябрьский", "Орловский", "Песчанокопский",
            "Пролетарский", "Ремонтненский", "Родионово-Несветайский", "Сальский", "Семикаракорский",
            "Советский", "Тарасовский", "Тацинский", "Усть-Донецкий", "Целинский",
            "Цимлянский", "Чертковский", "Шолоховский",
            "Ворошиловский", "Ленинский", "Кировский", "Железнодорожный",
            "Октябрьский", "Первомайский", "Пролетарский", "Советский"
        ]
        address_lower = address.lower()
        for district in districts:
            if district.lower() in address_lower:
                logger.info(f"Район адреса: {district}")
                return district
        logger.warning(f"Район не определён для адреса: {address}")
        return "Неизвестный"

    @classmethod
    def extract_district_from_court_name(cls, court_name: str) -> Optional[str]:
        districts = {
            "Азовский": "Азовского", "Аксайский": "Аксайского", "Багаевский": "Багаевского",
            "Белокалитвинский": "Белокалитвинского", "Боковский": "Боковского",
            "Верхнедонской": "Верхнедонского", "Весёловский": "Весёловского",
            "Волгодонской": "Волгодонского", "Дубовский": "Дубовского",
            "Егорлыкский": "Егорлыкского", "Заветинский": "Заветинского",
            "Зерноградский": "Зерноградского", "Зимовниковский": "Зимовниковского",
            "Кагальницкий": "Кагальницкого", "Каменский": "Каменского",
            "Кашарский": "Кашарского", "Константиновский": "Константиновского",
            "Красносулинский": "Красносулинского", "Куйбышевский": "Куйбышевского",
            "Мартыновский": "Мартыновского", "Матвеево-Курганский": "Матвеево-Курганского",
            "Миллеровский": "Миллеровского", "Милютинский": "Милютинского",
            "Морозовский": "Морозовского", "Мясниковский": "Мясниковского",
            "Неклиновский": "Неклиновского", "Обливский": "Обливского",
            "Октябрьский": "Октябрьского", "Орловский": "Орловского",
            "Песчанокопский": "Песчанокопского", "Пролетарский": "Пролетарского",
            "Ремонтненский": "Ремонтненского", "Родионово-Несветайский": "Родионово-Несветайского",
            "Сальский": "Сальского", "Семикаракорский": "Семикаракорского",
            "Советский": "Советского", "Тарасовский": "Тарасовского",
            "Тацинский": "Тацинского", "Усть-Донецкий": "Усть-Донецкого",
            "Целинский": "Целинского", "Цимлянский": "Цимлянского",
            "Чертковский": "Чертковского", "Шолоховский": "Шолоховского",
            "Ворошиловский": "Ворошиловского", "Ленинский": "Ленинского",
            "Кировский": "Кировского", "Железнодорожный": "Железнодорожного",
            "Октябрьский": "Октябрьского", "Первомайский": "Первомайского",
            "Пролетарский": "Пролетарского", "Советский": "Советского"
        }
        court_name_lower = court_name.lower().replace("\xa0", " ").strip()
        for nominative, genitive in districts.items():
            if nominative.lower() in court_name_lower or genitive.lower() in court_name_lower:
                logger.debug(f"Извлечён район: {nominative} из {court_name}")
                return nominative
        logger.warning(f"Район не извлечён из: {court_name}")
        return None

    @classmethod
    def determine_court_type(cls, debt_amount: float) -> str:
        debt_threshold = 50000.0
        return "мировой" if debt_amount <= debt_threshold else "районный"

    @classmethod
    async def find_court(cls, address: str, debt_amount: float, case_type: str) -> Dict:
        try:
            logger.info(f"Поиск суда для адреса: {address}, сумма: {debt_amount}, тип дела: {case_type}")
            if not cls.courts_data:
                logger.error("Данные о судах не загружены")
                return {"status": "error", "message": "Данные о судах не загружены"}

            target_type = cls.determine_court_type(debt_amount)
            logger.info(f"Требуемый тип суда: {target_type}")

            coords = await geocode_address(address)
            if coords:
                nearest_court = await cls.find_nearest_court(coords, target_type)
                if nearest_court:
                    return nearest_court

            address_district = cls.get_district_from_address(address)
            logger.info(f"Район адреса: {address_district}")
            courts_found = cls.search_courts_by_address_sudrf(address, target_type)
            if not courts_found:
                logger.warning("Суды не найдены на sudrf.ru")
                return await cls.fallback_search(address_district, target_type, address)

            selected_court = None
            for court in courts_found:
                court_name = court["name"]
                is_world_court = "Судебный участок" in court_name
                is_district_court = "районный суд" in court_name.lower()
                court_district = cls.extract_district_from_court_name(court_name)

                if court_district and court_district.lower() == address_district.lower():
                    if (target_type == "мировой" and is_world_court) or (
                            target_type == "районный" and is_district_court):
                        selected_court = court
                        logger.debug(f"Первый подходящий суд найден: {court_name}")
                        break

            if not selected_court:
                logger.warning("Подходящий суд не найден среди результатов sudrf.ru")
                return await cls.fallback_search(address_district, target_type, address)

            logger.info(f"Выбран суд с sudrf.ru: {selected_court['name']}")
            local_court = next((c for c in cls.courts_data if c["name"] == selected_court["name"]), None)
            if local_court:
                logger.info(f"Найден суд в JSON: {local_court['name']}")
                return {
                    "name": local_court["name"],
                    "type": local_court["type"],
                    "address": local_court["address"],
                    "phone": local_court.get("phone", ""),
                    "email": local_court.get("email", ""),
                    "latitude": local_court.get("latitude"),
                    "longitude": local_court.get("longitude"),
                    "website": local_court.get("website", selected_court["website"]),
                    "electronic_filing": local_court.get("electronic_filing", "Не указана"),  # Добавили
                    "polygon": ""
                }
            else:
                logger.warning(f"Суд {selected_court['name']} не найден в JSON")
                lat, lon = coords if coords else (None, None)
                return {
                    "name": selected_court["name"],
                    "type": target_type,
                    "address": address,
                    "website": selected_court["website"],
                    "latitude": lat,
                    "longitude": lon,
                    "electronic_filing": "Не указана",  # Значение по умолчанию
                    "polygon": ""
                }

        except Exception as e:
            logger.error(f"Ошибка в find_court: {str(e)}")
            return {"status": "error", "message": "Внутренняя ошибка сервера"}

    @classmethod
    async def fallback_search(cls, address_district: str, target_type: str, address: str) -> Dict:
        logger.info(f"Резервный поиск для района: {address_district}, тип: {target_type}")
        suitable_courts = []
        for court in cls.courts_data:
            court_name = court["name"]
            court_type = court.get("type", "").lower()
            court_district = cls.extract_district_from_court_name(court_name)

            if court_district and court_district.lower() == address_district.lower():
                if (target_type == "мировой" and "судебный участок" in court_name.lower()) or \
                        (target_type == "районный" and court_type == "районный"):
                    suitable_courts.append(court)

        if suitable_courts:
            court = suitable_courts[0]
            logger.info(f"Выбран суд из JSON: {court['name']}")
            return {
                "name": court["name"],
                "type": court["type"],
                "address": court["address"],
                "phone": court.get("phone", ""),
                "email": court.get("email", ""),
                "latitude": court.get("latitude"),
                "longitude": court.get("longitude"),
                "website": court.get("website", ""),
                "electronic_filing": court.get("electronic_filing", "Не указана"),  # Добавили
                "polygon": ""
            }

        coords = await geocode_address(address)
        if coords:
            nearest_court = await cls.find_nearest_court(coords, target_type)
            if nearest_court:
                return nearest_court

        logger.warning(f"Суд не найден в резервном поиске")
        lat, lon = coords if coords else (None, None)
        return {
            "name": f"{address_district} районный суд" if target_type == "районный" else f"Судебный участок {address_district} район",
            "type": target_type,
            "address": address,
            "website": "",
            "latitude": lat,
            "longitude": lon,
            "electronic_filing": "Не указана",  # Значение по умолчанию
            "polygon": ""
        }


CourtFinder.load_courts_data()


async def find_court(address: str, debt_amount: float, case_type: str) -> Dict:
    return await CourtFinder.find_court(address, debt_amount, case_type)