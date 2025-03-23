# app/api/endpoints/courts.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional
from app.services.court_finder import find_court
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/courts",
    tags=["courts"],
    responses={404: {"description": "Суд не найден"}}
)


class CourtRequest(BaseModel):
    address: str = Field(..., min_length=5, description="Адрес должника")
    debt_amount: float = Field(..., ge=0, description="Сумма долга в рублях")
    case_type: str = Field(..., min_length=3, description="Тип дела (например, имущественный_спор)")

    @validator("address")
    def address_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Адрес не может быть пустым")
        return v.strip()

    @validator("case_type")
    def case_type_must_be_valid(cls, v):
        valid_types = ["имущественный_спор", "расторжение_брака", "алименты", "раздел_имущества"]
        if v not in valid_types:
            logger.warning(f"Указан неизвестный тип дела: {v}")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "address": "Ростов-на-Дону, ул. Ленина, 1",
                "debt_amount": 30000.0,
                "case_type": "имущественный_спор"
            }
        }


class CourtResponse(BaseModel):
    name: str
    type: str
    address: str
    phone: Optional[str] = None
    email: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    website: Optional[str] = None
    electronic_filing: str = "Не указана"  # Добавили поле
    polygon: str


@router.post("/find_court/", response_model=dict, summary="Поиск суда")
async def find_court_endpoint(request: CourtRequest):
    logger.info(
        f"Получен запрос: address={request.address}, debt_amount={request.debt_amount}, case_type={request.case_type}")
    try:
        result = await find_court(request.address, request.debt_amount, request.case_type)
        if "status" in result and result["status"] == "error":
            logger.warning(f"Ошибка поиска суда: {result['message']}")
            raise HTTPException(status_code=404, detail=result["message"])
        court = CourtResponse(**result)
        logger.info(f"Найден суд: {court.name}")
        return {"status": "success", "court": court}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Неизвестная ошибка при поиске суда: {str(e)}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/case_types/", response_model=dict, summary="Список доступных типов дел")
async def get_case_types():
    case_types = ["имущественный_спор", "расторжение_брака", "алименты", "раздел_имущества"]
    return {"case_types": case_types}