import os
import tempfile
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from shazamio import Shazam

app = FastAPI(title="SoundTube VN — ShazamIO Free Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"


@app.get("/")
async def serve_frontend():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    return {"status": "ok", "message": "SoundTube VN ShazamIO Backend is running"}


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "engine": "shazamio", "free": True}


@app.post("/api/recognize")
async def recognize_audio(file: UploadFile = File(...)):
    raw_bytes = await file.read()
    if not raw_bytes or len(raw_bytes) < 1000:
        raise HTTPException(status_code=400, detail="File âm thanh quá ngắn hoặc rỗng.")

    suffix = Path(file.filename or "clip.wav").suffix or ".wav"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(raw_bytes)
            tmp_path = tmp.name

        shazam = Shazam()
        result = await shazam.recognize(tmp_path)
        track = result.get("track") if isinstance(result, dict) else None

        if not track:
            return {"status": "no_match", "message": "Chưa nhận diện được bài hát."}

        title = track.get("title", "").strip()
        artist = track.get("subtitle", "").strip()
        cover = (track.get("images") or {}).get("coverart", "")
        shazam_url = track.get("url", "")
        query = f"{title} {artist}".strip()

        return {
            "status": "success",
            "title": title,
            "artist": artist,
            "query": query,
            "cover": cover,
            "shazam_url": shazam_url,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi nhận diện ShazamIO: {exc}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
