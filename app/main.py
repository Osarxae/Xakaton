# app/main.py
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from app.api.endpoints.courts import router as courts_router
from app.services.court_finder import CourtFinder

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Удаляем старые обработчики, если они есть
if logger.handlers:
    logger.handlers.clear()

# Формат логов
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Обработчик для файла
file_handler = logging.FileHandler("court_finder.log")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)

# Обработчик для консоли
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)

# Добавляем обработчики к корневому логгеру
logging.getLogger('').addHandler(file_handler)  # Корневой логгер, чтобы все модули его унаследовали
logging.getLogger('').addHandler(console_handler)

app = FastAPI(
    title="Court Jurisdiction API",
    description="API для определения подсудности по адресу должника, сумме долга и типу дела",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.include_router(courts_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Инициализация приложения при старте."""
    try:
        CourtFinder.load_courts_data()
        logger.info("Приложение успешно запущено")
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {str(e)}")
        raise


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    """Обработка HTTP-исключений с кастомным форматом."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "detail": exc.detail}
    )


@app.get("/", summary="Корневой эндпоинт")
async def root():
    """Возвращает приветственное сообщение."""
    return JSONResponse(
        content={"message": "Добро пожаловать в API определения подсудности!"},
        media_type="application/json; charset=utf-8"
    )


@app.get("/health", summary="Проверка состояния API")
async def health_check():
    """Проверяет состояние приложения."""
    if not hasattr(app, "courts_loaded"):
        CourtFinder.load_courts_data()
        app.courts_loaded = True
    return {"status": "healthy", "version": app.version}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
