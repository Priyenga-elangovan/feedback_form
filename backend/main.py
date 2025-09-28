from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
import secrets

DATABASE_URL = "sqlite:///./feedback.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "supersecret"

Base.metadata.create_all(bind=engine)

class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50))
    last_name = Column(String(50))
    email = Column(String(100))
    rating = Column(Integer)
    feedback = Column(Text)

class FeedbackCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    rating: int = Field(..., ge=1, le=5)
    feedback: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    rating: int
    feedback: Optional[str]

    class Config:
        orm_mode = True

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Update if frontend URL changes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBasic()

def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    if not (correct_username and correct_password):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@app.post("/", response_model=FeedbackResponse)
def create_feedback(data: FeedbackCreate):
    db = SessionLocal()
    new_entry = Feedback(
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        rating=data.rating,
        feedback=data.feedback
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    db.close()
    return new_entry


@app.get("/feedbacks/", response_model=List[FeedbackResponse])
def get_feedbacks(rating: Optional[int] = Query(None, ge=1, le=5)):
    db = SessionLocal()
    if rating is not None:
        feedback_list = db.query(Feedback).filter(Feedback.rating == rating).all()
    else:
        feedback_list = db.query(Feedback).all()
    db.close()
    return feedback_list

@app.delete("/feedback/{feedback_id}", status_code=204)
def delete_feedback(feedback_id: int, admin: str = Depends(get_current_admin)):
    db = SessionLocal()
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        db.close()
        raise HTTPException(status_code=404, detail="Feedback not found")
    db.delete(feedback)
    db.commit()
    db.close()
    return

@app.put("/feedback/{feedback_id}", response_model=FeedbackResponse)
def update_feedback(feedback_id: int, data: FeedbackCreate, admin: str = Depends(get_current_admin)):
    db = SessionLocal()
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        db.close()
        raise HTTPException(status_code=404, detail="Feedback not found")
    feedback.first_name = data.first_name
    feedback.last_name = data.last_name
    feedback.email = data.email
    feedback.rating = data.rating
    feedback.feedback = data.feedback
    db.commit()
    db.refresh(feedback)
    db.close()
    return feedback
