# SuperNova AI - Lesion Boundary Detection System

Human-AI collaborative ultrasound lesion boundary review app. Sonologists upload PNG/JPEG ultrasound images, the backend preprocesses them, a mock AI creates a lesion mask plus uncertainty heatmap, and expert reviewers can reupload, reannotate, finalize, and export the result.

## Requirements

- Python 3.11+
- Node.js 18+
- No GPU, no external services, no real ML model required

## Backend

```bash
cd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API runs at `http://localhost:8000`. Swagger UI is at `http://localhost:8000/docs`.

Configuration is environment-based:

- `DATABASE_URL`, default `sqlite:///./app.db`
- `SECRET_KEY`, default local development value
- `ACCESS_TOKEN_EXPIRE_MINUTES`, default `30`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

The frontend defaults to `http://localhost:8000/api`. For unusual local port conflicts, start Vite with `VITE_API_BASE_URL=http://localhost:<port>/api`.

## Demo Logins

- Sonologist: `sonologist@supernova.com` / `12345678`
- Expert Reviewer: `reviewer@supernova.com` / `87654321`

The role selector must match the account role.

## Real Model Swap Point

The only model integration point is:

`backend/app/ml/inference.py`

Replace the body of `run_inference(preprocessed_image_path: str)` at the `# TODO: load and run the trained model here` marker. Keep returning `InferenceOutput` with the same fields: saved mask path, contour JSON, heatmap path, confidence score, lesion count, and pixel count. No other backend or frontend file should need to change.

## Export

The Export screen downloads a ZIP containing:

- `preprocessed.png`
- `final_mask.png`
- `uncertainty_heatmap.png`
- `summary.json`
