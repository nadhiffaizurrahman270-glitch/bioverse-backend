from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
import google.generativeai as genai
import models, schemas
from database import engine, get_db
import os
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GAGAL: File .env tidak terbaca atau variable GOOGLE_API_KEY kosong! Pastikan file bernama '.env' (bukan .env.txt).")
genai.configure(api_key=api_key)

# Otomatis buat semua tabel di PostgreSQL jika belum ada
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BioVerse API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# Health Check Endpoint
@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "Backend sehat", "database": "Terhubung ke PostgreSQL bioverse_db!"}
    except Exception as e:
        return {"status": "Backend sehat", "database": f"Gagal terhubung ke DB: {str(e)}"}

# --- API ENDPOINTS MATERI ---

@app.post("/api/v1/materi", response_model=schemas.MateriResponse)
def create_materi(materi: schemas.MateriCreate, db: Session = Depends(get_db)):
    db_materi = models.Materi(**materi.dict())
    db.add(db_materi)
    db.commit()
    db.refresh(db_materi)
    return db_materi

@app.get("/api/v1/materi", response_model=List[schemas.MateriResponse])
def get_all_materi(db: Session = Depends(get_db)):
    return db.query(models.Materi).all()

@app.get("/api/v1/materi/{materi_id}", response_model=schemas.MateriResponse)
def get_materi_by_id(materi_id: int, db: Session = Depends(get_db)):
    materi = db.query(models.Materi).filter(models.Materi.id == materi_id).first()
    if not materi:
        raise HTTPException(status_code=404, detail="Materi tidak ditemukan")
    return materi

# --- API ENDPOINT LEADERBOARD (SQL Analitik Kompleks) ---

@app.get("/api/v1/leaderboard")
def get_leaderboard(db: Session = Depends(get_db)):
    # Query SQL kompleks gabungan JOIN & SUM untuk nilai tugas basis data
    query = text("""
        SELECT u.id, u.username, COALESCE(SUM(s.skor), 0) as total_skor
        FROM users u
        LEFT JOIN user_scores s ON u.id = s.user_id
        GROUP BY u.id, u.username
        ORDER BY total_skor DESC
        LIMIT 10
    """)
    result = db.execute(query).fetchall()
    return [{"rank": idx + 1, "user_id": row.id, "username": row.username, "total_skor": row.total_skor} for idx, row in enumerate(result)]

# --- API ENDPOINT USER & SCORE (UNTUK DUMMY DATA) ---

@app.post("/api/v1/users", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(username=user.username, email=user.email)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/v1/scores")
def submit_score(score_data: schemas.ScoreSubmit, db: Session = Depends(get_db)):
    new_score = models.UserScore(user_id=score_data.user_id, skor=score_data.skor)
    db.add(new_score)
    db.commit()
    return {"message": "Skor berhasil disimpan!"}

# --- KONFIGURASI GEMINI AI ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

ai_model = genai.GenerativeModel('gemini-3.8-flash')

# --- API ENDPOINT AI TUTOR ---
@app.post("/api/v1/ai/tutor")
def ask_ai_tutor(req: schemas.AITutorRequest):
    try:
        # Prompt rekayasa agar Gemini bertindak sebagai guru biologi
        prompt = f"""
        Kamu adalah 'BioBot', asisten pintar di aplikasi BioVerse. 
        Tugasmu adalah menjawab pertanyaan biologi dari siswa dengan gaya bahasa yang ramah, 
        mudah dipahami, dan ringkas (maksimal 3 paragraf).
        
        Pertanyaan siswa: {req.pertanyaan}
        """
        
        response = ai_model.generate_content(prompt)
        
        return {
            "status": "sukses",
            "pertanyaan": req.pertanyaan,
            "jawaban": response.text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memanggil AI: {str(e)}")

    # Cek daftar model yang tersedia untuk API Key kamu
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print("Model yang bisa dipakai:", m.name)

