"""RetailIQ MVP API: stateless CSV analysis per request."""
from pathlib import Path
import os
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from .analytics import DataError, analyze_csv

app = FastAPI(title="RetailIQ API", version="0.1.0")
allowed_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=False,
                   allow_methods=["GET", "POST"], allow_headers=["*"])
SAMPLE = Path(__file__).resolve().parents[1] / "data" / "sample_sales.csv"
MAX_UPLOAD_BYTES = 8 * 1024 * 1024


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "RetailIQ"}


@app.get("/api/demo")
def demo():
    return analyze_csv(SAMPLE.read_bytes())


@app.post("/api/analyze")
async def analyze_upload(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="CSV exceeds the 8 MB upload limit")
    try:
        return analyze_csv(content)
    except DataError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
