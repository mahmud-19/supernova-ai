from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_role, hash_password
from app.database import get_db
from app.models import User, UserRole
from app.schemas import AdminUserRead, UserCreate, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=list[AdminUserRead])
def list_users(
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
) -> list[AdminUserRead]:
    """Return all non-admin users."""
    stmt = select(User).where(User.role != UserRole.admin).order_by(User.id.desc())
    return db.scalars(stmt).all()

@router.post("/users", response_model=AdminUserRead)
def create_user(
    payload: UserCreate,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    """Create a new non-admin user."""
    # Check email uniqueness
    existing_email = db.scalar(select(User).where(User.email == payload.email))
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
        
    # Check username uniqueness
    existing_username = db.scalar(select(User).where(User.username == payload.username))
    if existing_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user = User(
        full_name=payload.full_name,
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=UserRole(payload.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.put("/users/{user_id}", response_model=AdminUserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    """Update a user's details."""
    user = db.get(User, user_id)
    if not user or user.role == UserRole.admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Check email uniqueness
    existing_email = db.scalar(select(User).where(User.email == payload.email, User.id != user_id))
    if existing_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    # Check username uniqueness
    existing_username = db.scalar(select(User).where(User.username == payload.username, User.id != user_id))
    if existing_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user.full_name = payload.full_name
    user.username = payload.username
    user.email = payload.email
    user.role = UserRole(payload.role)
    if payload.password:
        user.hashed_password = hash_password(payload.password)
        
    db.commit()
    db.refresh(user)
    return user

@router.delete("/users/{user_id}", response_model=AdminUserRead)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
) -> User:
    """Hard delete a user."""
    user = db.get(User, user_id)
    if not user or user.role == UserRole.admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    db.delete(user)
    db.commit()
    return user
