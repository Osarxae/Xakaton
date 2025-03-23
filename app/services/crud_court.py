# app/services/crud_court.py
from typing import Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.court import Court


class CRUDCourt:
    async def get_court_by_coords(
            self,
            db: AsyncSession,
            lat: float,
            lng: float,
            court_type: str
    ) -> Optional[Court]:
        point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
        result = await db.execute(
            select(Court).where(
                Court.type == court_type,
                func.ST_Within(point, Court.geometry)
            )
        )
        return result.scalars().first()


crud_court = CRUDCourt()
