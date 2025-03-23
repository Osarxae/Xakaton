from geoalchemy2 import Geometry
from sqlalchemy import Column, Integer, String
from app.db.base import Base


class Court(Base):
    __tablename__ = "courts"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(String(20), nullable=False)  # "мировой" или "районный"
    geometry = Column(Geometry(geometry_type='POLYGON', srid=4326))  # Геометрия в WGS84
    electronic_form_url = Column(String(512))
