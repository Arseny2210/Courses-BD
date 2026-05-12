from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.session import get_db
from app.models import Cart, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserRead

router = APIRouter(prefix="/auth", tags=["Авторизация"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
    description="Создаёт нового пользователя, автоматически создаёт для него корзину и возвращает JWT-токен.",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    # Проверяем, не занят ли email другим пользователем.
    existing_user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower()))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким email уже существует")

    users_count = db.scalar(select(func.count()).select_from(User)) or 0
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name.strip(),
        hashed_password=get_password_hash(payload.password),
        is_admin=users_count == 0,
    )
    # У каждого пользователя должна быть своя корзина сразу после регистрации.
    user.cart = Cart()
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(str(user.id))
    return TokenResponse(access_token=access_token, user=UserRead.model_validate(user))


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Вход в систему",
    description="Проверяет email и пароль, после чего возвращает токен доступа.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")

    access_token = create_access_token(str(user.id))
    return TokenResponse(access_token=access_token, user=UserRead.model_validate(user))


@router.get(
    "/me",
    response_model=UserRead,
    summary="Текущий пользователь",
    description="Возвращает данные пользователя по текущему JWT-токену.",
)
def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
