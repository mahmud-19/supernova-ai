from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import User, UserRole


DEMO_USERS = [
    {
        "full_name": "Dr. Kim",
        "email": "sonologist@supernova.com",
        "username": "sonologist",
        "password": "12345678",
        "role": UserRole.sonologist,
    },
    {
        "full_name": "Dr. Lee",
        "email": "reviewer@supernova.com",
        "username": "reviewer",
        "password": "12345678",
        "role": UserRole.expert_reviewer,
    },
]


def seed_demo_users(db: Session) -> None:
    for demo in DEMO_USERS:
        existing = db.scalar(select(User).where(User.email == demo["email"]))
        if existing:
            continue
        db.add(
            User(
                full_name=demo["full_name"],
                email=demo["email"],
                username=demo["username"],
                hashed_password=hash_password(demo["password"]),
                role=demo["role"],
            )
        )
    db.commit()
