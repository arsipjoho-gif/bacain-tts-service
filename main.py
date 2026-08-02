import asyncio
import base64
import os
import tempfile

import edge_tts
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="BACAIN TTS Service")

# CORS agar bisa dipanggil dari Apps Script
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# Daftar suara yang didukung
ALLOWED_VOICES = [
    "id-ID-ArdiNeural",    # Pria Indonesia
    "id-ID-GadisNeural",   # Wanita Indonesia
]

class TTSRequest(BaseModel):
    text: str
    voice: str = "id-ID-GadisNeural"
    rate: str = "+0%"
    pitch: str = "+0%"

@app.get("/")
def root():
    return {
        "service": "BACAIN TTS Service",
        "status": "running",
        "voices": ALLOWED_VOICES
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/synthesize")
async def synthesize(req: TTSRequest):
    # Validasi voice
    if req.voice not in ALLOWED_VOICES:
        raise HTTPException(
            status_code=400,
            detail=f"Voice tidak didukung. Pilih: {', '.join(ALLOWED_VOICES)}"
        )

    # Validasi panjang teks
    if not req.text or len(req.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Teks tidak boleh kosong.")

    if len(req.text) > 5000:
        raise HTTPException(status_code=400, detail="Teks maksimal 5000 karakter per request.")

    try:
        # Generate audio ke file temporary
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        communicate = edge_tts.Communicate(
            text=req.text.strip(),
            voice=req.voice,
            rate=req.rate,
            pitch=req.pitch
        )

        await communicate.save(tmp_path)

        # Baca file MP3 dan konversi ke Base64
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        os.unlink(tmp_path)

        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        return {
            "ok": True,
            "audio_base64": audio_base64,
            "voice": req.voice,
            "char_count": len(req.text)
        }

    except Exception as e:
        # Pastikan file temporary dibersihkan
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Gagal generate audio: {str(e)}")
