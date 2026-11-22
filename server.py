import json
import os
import subprocess
import tempfile
from pathlib import Path
from fastapi import Body, FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from shazamio import Shazam

app = FastAPI(title="Tìm Nhạc — ShazamIO & FFmpeg Audio Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"
ADS_CONFIG_FILE = BASE_DIR / "ads_config.json"
ADMIN_USER = os.environ.get("ADMIN_USER", "Admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "824036")

ALLOWED_FORMATS = {
    "mp3": ("audio/mpeg", ["-c:a", "libmp3lame", "-b:a", "320k"]),
    "wav": ("audio/wav", ["-c:a", "pcm_s16le"]),
    "m4a": ("audio/mp4", ["-c:a", "aac", "-b:a", "256k"]),
    "flac": ("audio/flac", ["-c:a", "flac"]),
    "ogg": ("audio/ogg", ["-c:a", "libvorbis", "-q:a", "6"]),
    "webm": ("audio/webm", ["-c:a", "libopus", "-b:a", "192k"]),
}


def _get_monetag_verify_content() -> str:
    env_val = os.environ.get("MONETAG_VERIFY", "").strip()
    if env_val:
        return env_val
    if ADS_CONFIG_FILE.exists():
        try:
            cfg = json.loads(ADS_CONFIG_FILE.read_text(encoding="utf-8"))
            return str(((cfg or {}).get("monetag") or {}).get("verifyMeta", "")).strip()
        except Exception:
            pass
    return ""


@app.get("/")
async def serve_frontend():
    if INDEX_FILE.exists():
        html = INDEX_FILE.read_text(encoding="utf-8")
        verify_code = _get_monetag_verify_content()
        if verify_code and 'name="monetag"' not in html:
            meta_tag = f'  <meta name="monetag" content="{verify_code}" />\n'
            html = html.replace("<head>", "<head>\n" + meta_tag, 1)
        return HTMLResponse(content=html)
    return {"status": "ok", "message": "Tìm Nhạc Backend is running"}


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "engine": "shazamio+ffmpeg", "free": True}


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


@app.post("/api/convert")
async def convert_audio(
    file: UploadFile = File(...),
    target_format: str = Form("mp3"),
    sample_rate: int = Form(44100),
    channels: int = Form(2),
    trim_start: float = Form(0.0),
    trim_end: float = Form(0.0),
    normalize: str = Form("0"),
):
    fmt = target_format.lower().strip()
    if fmt not in ALLOWED_FORMATS:
        raise HTTPException(status_code=400, detail="Định dạng đầu ra không hỗ trợ.")

    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="File âm thanh rỗng.")

    in_suffix = Path(file.filename or "input.audio").suffix or ".bin"
    in_path = None
    out_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=in_suffix) as tin:
            tin.write(raw_bytes)
            in_path = tin.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{fmt}") as tout:
            out_path = tout.name

        mime, codec_args = ALLOWED_FORMATS[fmt]
        cmd = ["ffmpeg", "-y", "-i", in_path, "-vn"]
        if trim_start > 0:
            cmd += ["-ss", str(trim_start)]
        if trim_end > trim_start:
            cmd += ["-to", str(trim_end)]
        if normalize == "1":
            cmd += ["-af", "loudnorm"]
        cmd += ["-ar", str(sample_rate), "-ac", str(1 if channels == 1 else 2)]
        cmd += codec_args + [out_path]

        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode != 0 or not os.path.exists(out_path):
            raise HTTPException(status_code=500, detail="FFmpeg không thể chuyển đổi file này.")

        out_bytes = Path(out_path).read_bytes()
        return Response(
            content=out_bytes,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="converted.{fmt}"'},
        )
    finally:
        for p in (in_path, out_path):
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except OSError:
                    pass



@app.get("/api/ads-config")
async def get_ads_config():
    if ADS_CONFIG_FILE.exists():
        try:
            return {"status": "ok", "config": json.loads(ADS_CONFIG_FILE.read_text(encoding="utf-8"))}
        except Exception:
            pass
    return {"status": "ok", "config": None}


@app.post("/api/ads-config")
async def save_ads_config(payload: dict = Body(...)):
    user = str(payload.get("admin_user", ""))
    pw = str(payload.get("admin_pass", ""))
    if user.strip().lower() != ADMIN_USER.strip().lower() or pw.strip().lower() != ADMIN_PASS.strip().lower():
        raise HTTPException(status_code=403, detail="Sai thông tin Quản trị viên.")
    cfg = payload.get("config")
    if not isinstance(cfg, dict):
        raise HTTPException(status_code=400, detail="Cấu hình quảng cáo không hợp lệ.")
    ADS_CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "ok"}



ALLOWED_ROOT_EXTS = {".js", ".html", ".txt", ".json", ".ico", ".png", ".svg"}
BLOCKED_ROOT_FILES = {"server.py", "ads_config.json", "requirements.txt", "dockerfile", "readme.md"}


@app.get("/{filename}")
async def serve_root_verification_file(filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=404, detail="Not found")
    if filename.lower() in BLOCKED_ROOT_FILES:
        raise HTTPException(status_code=404, detail="Not found")
    target = (BASE_DIR / filename).resolve()
    if target.parent != BASE_DIR or not target.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    if target.suffix.lower() not in ALLOWED_ROOT_EXTS:
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(target)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
