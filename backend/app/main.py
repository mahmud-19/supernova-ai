from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.routers import auth, cases
from app.seed import seed_demo_users


settings = get_settings()
app = FastAPI(title="SuperNova AI API", version="0.1.0")
cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Refreshed-Token"],
)


@app.middleware("http")
async def attach_refreshed_token(request: Request, call_next):
    response = await call_next(request)
    refreshed = getattr(request.state, "refreshed_token", None)
    if refreshed:
        response.headers["X-Refreshed-Token"] = refreshed
    return response


def migrate_to_new_layout() -> None:
    import shutil
    from pathlib import Path
    from sqlalchemy import select
    from app.models import Case, InferenceResult, Annotation, CaseStatus

    storage_dir = settings.storage_dir
    images_dir = storage_dir / "Images"
    masks_dir = storage_dir / "Masks"
    images_dir.mkdir(parents=True, exist_ok=True)
    masks_dir.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db:
        cases = db.scalars(select(Case)).all()
        for case in cases:
            if not case.patient_id:
                continue

            # 1. Migrate preprocessed image
            old_img_path_str = case.preprocessed_image_path
            new_img_path = images_dir / f"{case.patient_id}.png"
            
            if old_img_path_str and "storage/Images" not in old_img_path_str and old_img_path_str != "pending":
                old_path = Path(old_img_path_str)
                if old_path.exists():
                    shutil.move(str(old_path), str(new_img_path))
                    case.preprocessed_image_path = str(new_img_path)
                elif (storage_dir / str(case.id) / "preprocessed.png").exists():
                    shutil.move(str(storage_dir / str(case.id) / "preprocessed.png"), str(new_img_path))
                    case.preprocessed_image_path = str(new_img_path)
                else:
                    case.preprocessed_image_path = str(new_img_path)

            # 2. Migrate finalized approved masks
            if case.status == CaseStatus.approved:
                result = db.scalar(
                    select(InferenceResult)
                    .where(InferenceResult.case_id == case.id)
                    .order_by(InferenceResult.version.desc())
                    .limit(1)
                )
                new_mask_path = masks_dir / f"mask_{case.patient_id}.png"
                if result:
                    old_mask_str = result.mask_path
                    if old_mask_str and "storage/Masks" not in old_mask_str:
                        old_mask_path = Path(old_mask_str)
                        if old_mask_path.exists():
                            shutil.move(str(old_mask_path), str(new_mask_path))
                            result.mask_path = str(new_mask_path)
                        elif (storage_dir / str(case.id) / old_mask_path.name).exists():
                            shutil.move(str(storage_dir / str(case.id) / old_mask_path.name), str(new_mask_path))
                            result.mask_path = str(new_mask_path)
                        else:
                            result.mask_path = str(new_mask_path)

                annotations = db.scalars(
                    select(Annotation).where(Annotation.case_id == case.id)
                ).all()
                for ann in annotations:
                    old_ann_str = ann.mask_path
                    if old_ann_str and "storage/Masks" not in old_ann_str:
                        old_ann_path = Path(old_ann_str)
                        if old_ann_path.exists():
                            if not new_mask_path.exists():
                                shutil.move(str(old_ann_path), str(new_mask_path))
                            ann.mask_path = str(new_mask_path)
                        else:
                            ann.mask_path = str(new_mask_path)
        db.commit()


@app.on_event("startup")
def startup() -> None:
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_users(db)
    migrate_to_new_layout()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
