from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy import func
from passlib.context import CryptContext
from typing import List
import google.generativeai as genai
import models, schemas
from database import engine, get_db
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import JWTError, jwt

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

# Konfigurasi Enkripsi Password
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

SECRET_KEY = "rahasia_bioverse_super_aman" # Di aplikasi nyata, simpan ini di file .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Skema untuk membaca Header "Authorization: Bearer <token>"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# Fungsi Dependency untuk memvalidasi token dan mengambil data user
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau telah kadaluwarsa",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def get_password_hash(password):
    return pwd_context.hash(password)


# --- API ENDPOINTS MATERI ---

@app.post("/api/v1/materi", response_model=schemas.MateriResponse)
def create_materi(
    materi: schemas.MateriCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)):
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
    leaderboard = (
        db.query(
            models.User.id.label("user_id"),
            models.User.email,  # 👈 Diganti dari username ke email
            func.coalesce(func.sum(models.UserScore.skor), 0).label("total_score")
        )
        .outerjoin(models.UserScore, models.User.id == models.UserScore.user_id)
        .group_by(models.User.id, models.User.email)  # 👈 Diganti ke email
        .order_by(func.sum(models.UserScore.skor).desc().nullslast())
        .all()
    )
    
    return [
        {
            "user_id": item.user_id,
            "email": item.email,  # 👈 Return email
            "total_score": item.total_score
        }
        for item in leaderboard
    ]


# --- API ENDPOINT USER & SCORE (UNTUK DUMMY DATA) ---

# Endpoint untuk Registrasi Pengguna Baru
@app.post("/api/v1/auth/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Cek apakah email sudah terdaftar
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")
    
    # Enkripsi password sebelum disimpan ke database
    hashed_pwd = get_password_hash(user.password)
    
    # Buat user baru
    new_user = models.User(
        nama=user.nama,
        email=user.email,
        hashed_password=hashed_pwd
    )
    
    # Simpan ke PostgreSQL
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

# Endpoint untuk Login
@app.post("/api/v1/auth/login", response_model=schemas.Token)
def login_user(db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()):
    # Cek apakah user dengan email tersebut ada
    # Catatan: form_data.username akan kita isi dengan email dari frontend
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # Jika user tidak ada atau password salah
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Buat Token jika berhasil
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

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

