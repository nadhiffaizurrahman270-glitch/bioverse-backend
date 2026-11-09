from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Schema untuk Materi
class MateriBase(BaseModel):
    judul: str
    kategori: str
    konten: str

class MateriCreate(MateriBase):
    pass

class MateriResponse(MateriBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Schema untuk User & Score
class UserCreate(BaseModel):
    username: str
    email: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True

class ScoreSubmit(BaseModel):
    user_id: int
    skor: int

class AITutorRequest(BaseModel):
    pertanyaan: str