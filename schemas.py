from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

# Schema untuk Materi
class MateriBase(BaseModel):
    judul: str
    deskripsi: Optional[str] = None
    kategori: Optional[str] = "General"
    level: Optional[str] = "Beginner"
    konten: str
    video_id: Optional[str] = None

class MateriCreate(MateriBase):
    pass

class MateriOut(MateriBase):
    id: int

    class Config:
        from_attributes = True

class MateriResponse(MateriBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schema untuk User & Score
class UserCreate(BaseModel):
    nama: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    nama: str
    email: EmailStr
    role: str
    is_active: bool

    class Config:
        from_attributes = True

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True

# Untuk Input Login
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Untuk Token JWT
class Token(BaseModel):
    access_token: str
    token_type: str

class ScoreSubmit(BaseModel):
    user_id: int
    skor: int

class AITutorRequest(BaseModel):
    pertanyaan: str

# --- SCORE SCHEMAS ---
class ScoreCreate(BaseModel):
    kategori_quiz: str
    skor: int

class ScoreOut(BaseModel):
    id: int
    user_id: int
    kategori_quiz: str
    skor: int
    created_at: datetime

    class Config:
        from_attributes = True