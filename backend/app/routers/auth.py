from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import authenticate_user, create_access_token, get_current_user
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserRead
from app.services.audit import write_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate_user(db, payload.identifier, payload.password, payload.role)
    if user is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username/email or password")
    write_audit_log(db, "login", user_id=user.id, ip_address=request.client.host if request.client else None)
    db.commit()
    return TokenResponse(access_token=create_access_token(user), user=UserRead.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    write_audit_log(db, "logout", user_id=current_user.id, ip_address=request.client.host if request.client else None)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
