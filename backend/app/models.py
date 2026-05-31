import enum
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    sonologist = "sonologist"
    expert_reviewer = "expert_reviewer"
    admin = "admin"


class CaseStatus(str, enum.Enum):
    pending = "pending"
    in_review = "in_review"
    approved = "approved"


class ResultSource(str, enum.Enum):
    ai = "ai"
    expert = "expert"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    cases = relationship("Case", back_populates="owner")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    display_code: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)
    owner_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploader_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.pending, nullable=False)
    original_image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    preprocessed_image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    file_format: Mapped[str] = mapped_column(String(20), nullable=False)
    bit_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    contrast_adjusted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Patient / exam metadata
    patient_id: Mapped[Optional[str]] = mapped_column(String(80), unique=True, nullable=True)
    patient_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sonologist_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    owner = relationship("User", back_populates="cases")
    inference_results = relationship("InferenceResult", back_populates="case", cascade="all, delete-orphan")
    annotations = relationship("Annotation", back_populates="case", cascade="all, delete-orphan")


class InferenceResult(Base):
    __tablename__ = "inference_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[ResultSource] = mapped_column(Enum(ResultSource), nullable=False)
    mask_path: Mapped[str] = mapped_column(String(500), nullable=False)
    contour_json: Mapped[list] = mapped_column(JSON, nullable=False)
    uncertainty_map_path: Mapped[str] = mapped_column(String(500), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    total_lesions: Mapped[int] = mapped_column(Integer, nullable=False)
    total_pixels: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    case = relationship("Case", back_populates="inference_results")


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    editor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    mask_path: Mapped[str] = mapped_column(String(500), nullable=False)
    contour_json: Mapped[list] = mapped_column(JSON, nullable=False)
    confidence_map_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_finalized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    case = relationship("Case", back_populates="annotations")
    editor = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    case_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cases.id"), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    user = relationship("User")


class RetrainingLog(Base):
    __tablename__ = "retraining_logs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), default="running")
    model_version_after: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    dice_after: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class RetrainingState(Base):
    __tablename__ = "retraining_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    approved_since_last_retrain: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
