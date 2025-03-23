import json
import requests
from bs4 import BeautifulSoup
import logging
from pathlib import Path
import time
from urllib3.exceptions import InsecureRequestWarning
import warnings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Заголовки для имитации браузера
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def load_courts_data(file_path: str) -> list:
    """Загружает данные о судах из JSON."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else data.get("courts", [])
    except Exception as e:
        logger.error(f"Ошибка загрузки данных из {file_path}: {str(e)}")
        return []


def setup_session_with_retries():
    """Настраивает сессию с повторными попытками."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,  # Максимум 3 попытки
        backoff_factor=1,  # Задержка между попытками: 1, 2, 4 секунды
        status_forcelist=[500, 502, 503, 504]  # Повторять при этих ошибках сервера
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    return session


def check_electronic_filing(website: str, session: requests.Session) -> str:
    """Проверяет наличие ссылки на обращения граждан, указывающей на электронную подачу."""
    if website.startswith("http://"):
        website = website.replace("http://", "https://")

    try:
        response = session.get(website, headers=HEADERS, timeout=20, verify=False)  # Увеличен timeout до 20 секунд
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Ищем ссылку с href="/modules.php?name=gbook"
        gbook_link = soup.find("a", href="/modules.php?name=gbook")
        if gbook_link:
            logger.info(f"Найдена ссылка на обращения граждан на {website}, электронная подача поддерживается")
            return "да"
        else:
            logger.info(f"Ссылка на обращения граждан не найдена на {website}")
            return "нет"
    except requests.RequestException as e:
        logger.warning(f"Ошибка доступа к {website}: {str(e)}. Присваиваем 'неизвестно'")
        return "неизвестно"


def update_courts_with_electronic_filing(courts: list) -> list:
    """Обновляет данные судов, добавляя поле electronic_filing."""
    session = setup_session_with_retries()  # Создаём сессию с повторными попытками
    for court in courts:
        if "website" in court and court["website"]:
            logger.info(f"Проверка сайта: {court['website']}")
            court["electronic_filing"] = check_electronic_filing(court["website"], session)
            time.sleep(1)  # Задержка между судами
        else:
            logger.warning(f"У суда '{court.get('name', 'Без названия')}' нет сайта")
            court["electronic_filing"] = "неизвестно"
    return courts


def save_updated_courts(courts: list, output_path: str):
    """Сохраняет обновлённые данные в JSON."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(courts, f, ensure_ascii=False, indent=4)
        logger.info(f"Обновлённые данные сохранены в {output_path}")
    except Exception as e:
        logger.error(f"Ошибка сохранения данных в {output_path}: {str(e)}")


def main():
    # Путь к исходному JSON
    input_file = Path("data/courts_rostov-old.json")
    output_file = Path("data/courts_rostov.json")

    # Загрузка данных
    courts = load_courts_data(input_file)
    if not courts:
        logger.error("Нет данных для обработки. Завершение.")
        return

    # Обновление данных
    updated_courts = update_courts_with_electronic_filing(courts)

    # Сохранение результата
    save_updated_courts(updated_courts, output_file)


if __name__ == "__main__":
    warnings.simplefilter('ignore', InsecureRequestWarning)
    main()