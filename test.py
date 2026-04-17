import app.models  # penting supaya semua model ter-load
from app.db.base import Base

print(Base.metadata.tables.keys())
