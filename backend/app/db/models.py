from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime

from app.db.database import Base


class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    vertical = Column(String(50), nullable=True)
    answer = Column(Text, nullable=True)
    sources = Column(Text, nullable=True)  # JSON string
    source_type = Column(String(20), default="text")  # text | upload
    created_at = Column(DateTime, default=datetime.utcnow)
