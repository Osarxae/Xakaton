# app/services/geocoder.py
import httpx
from typing import Tuple, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


async def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    try:
        logger.info(f"Запрос геокодирования для адреса: {address}")
        logger.info(f"Используемый API-ключ: {settings.YANDEX_GEOCODER_API_KEY[:4]}...")
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://geocode-maps.yandex.ru/1.x/",
                params={
                    "apikey": settings.YANDEX_GEOCODER_API_KEY,
                    "geocode": address,
                    "format": "json"
                },
                timeout=10.0
            )
            logger.info(f"Статус ответа API: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Ошибка API геокодирования: статус {response.status_code}, текст: {response.text}")
                return None
            data = response.json()
            geo_objects = data["response"]["GeoObjectCollection"]["featureMember"]
            if not geo_objects:
                logger.warning(f"Адрес не найден: {address}")
                return None
            pos = geo_objects[0]["GeoObject"]["Point"]["pos"]
            lon, lat = map(float, pos.split())
            logger.info(f"Успешное геокодирование адреса {address}: ({lat}, {lon})")
            return (lat, lon)
    except httpx.TimeoutException:
        logger.error(f"Превышено время ожидания при геокодировании адреса: {address}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Ошибка запроса к API геокодирования: {str(e)}")
        return None
    except (KeyError, ValueError) as e:
        logger.error(f"Ошибка обработки ответа API: {str(e)}, данные: {data}")
        return None
    except Exception as e:
        logger.error(f"Неизвестная ошибка в geocode_address: {str(e)}")
        return None
