from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nama = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="student")  # 'student' atau 'admin'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    scores = relationship("UserScore", back_populates="user", cascade="all, delete-orphan")

class Materi(Base):
    __tablename__ = "materi"

    id = Column(Integer, primary_key=True, index=True)
    judul = Column(String(150), nullable=False)
    kategori = Column(String(50), default="Biologi Dasar") # misal: Sel, Genetika, Ekologi
    level = Column(String(50), default="SMA")           # misal: SMA, SMP, Umum
    deskripsi = Column(Text, nullable=True)
    konten = Column(Text, nullable=False)
    video_id = Column(String(100), nullable=True)         # ID YouTube untuk video edukasi
    created_at = Column(DateTime, default=datetime.utcnow)

class UserScore(Base):
    __tablename__ = "user_scores"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    skor = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="scores")