from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import User, Profile
from app.schemas.auth import RegisterRequest, LoginRequest, TokenPair
from app.core.security import hash_password, verify_password, token_pair

router = APIRouter(prefix='/auth', tags=['auth'])

@router.post('/register', response_model=TokenPair, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail='Email already registered')
    user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
    user.profile = Profile(display_name=payload.display_name)
    db.add(user); db.commit(); db.refresh(user)
    access, refresh = token_pair(user.id)
    return TokenPair(access_token=access, refresh_token=refresh)

@router.post('/login', response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid credentials')
    access, refresh = token_pair(user.id)
    return TokenPair(access_token=access, refresh_token=refresh)
