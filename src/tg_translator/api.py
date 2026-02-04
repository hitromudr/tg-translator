import logging
import os
import shutil
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from tg_translator.db import Database
from tg_translator.translator_service import TranslatorService

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment
load_dotenv()

# Initialize App
app = FastAPI(
    title="Roy AI Bridge",
    description="Internal AI Service for Roy Messenger (Translation, STT, TTS)",
    version="1.0.0",
)

# Initialize Database and Service
# We use the same DB as the bot to share dictionaries
db = Database()
service = TranslatorService(db=db)


# --- Data Models ---
class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "auto"
    target_lang: str = "en"
    chat_id: Optional[str] = None  # Optional context for dictionary


class TTSRequest(BaseModel):
    text: str
    lang: str
    gender: str = "male"  # male/female


class DictAddRequest(BaseModel):
    chat_id: str
    source: str
    target: str
    source_lang: str = "ru"
    target_lang: str = "en"


class DictRemoveRequest(BaseModel):
    chat_id: str
    source: str
    source_lang: str = "ru"
    target_lang: str = "en"


# --- Endpoints ---


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "tg-translator-ai"}


@app.post("/translate")
async def translate_text(req: TranslateRequest):
    """
    Smart Translation endpoint.
    Uses Groq (Llama 3) with Google Translate fallback.
    """
    try:
        # Use the internal sync method via executor to support Groq/Google logic
        # We manually invoke the logic similar to translate_message but without DB lookup
        import asyncio

        loop = asyncio.get_running_loop()

        # Logic from TranslatorService._translate_sync but we call it directly via executor
        # If chat_id provided, apply dictionary first
        text_to_process = req.text
        if req.chat_id:
            langs = sorted([req.source_lang, req.target_lang])
            lang_pair = f"{langs[0]}-{langs[1]}"
            text_to_process = service._apply_custom_dictionary(
                req.text, req.chat_id, lang_pair
            )  # type: ignore (db.py now supports str chat_id)

        result = await loop.run_in_executor(
            service._executor,
            service._translate_sync,
            text_to_process,
            req.source_lang,  # Treating as 'primary' for heuristic checks
            req.target_lang,  # Treating as 'secondary'
            req.text,  # original_text (for heuristic detection)
        )

        if not result:
            raise HTTPException(
                status_code=500, detail="Translation returned empty result"
            )

        return {
            "translation": result,
            "source": req.source_lang,
            "target": req.target_lang,
        }

    except Exception as e:
        logger.error(f"API Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """
    Speech-to-Text endpoint.
    Accepts audio file (multipart/form-data).
    Uses Groq Whisper V3 (Cloud) with Local Whisper fallback.
    """
    temp_filename = f"tmp/roy_upload_{uuid.uuid4()}_{file.filename}"
    os.makedirs("tmp", exist_ok=True)

    try:
        # Save uploaded file
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Transcribe
        # transcribe_audio is already async and handles executor internally
        text = await service.transcribe_audio(temp_filename)

        if not text:
            raise HTTPException(
                status_code=500, detail="Transcription returned empty result"
            )

        return {"text": text}

    except Exception as e:
        logger.error(f"API STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except Exception:
                pass


@app.post("/tts")
async def text_to_speech(req: TTSRequest):
    """
    Text-to-Speech endpoint.
    Uses Silero TTS.
    Returns audio file (audio/mpeg).
    """
    try:
        # generate_audio is async wrapper
        path = await service.generate_audio(req.text, req.lang, req.gender)

        if not path or not os.path.exists(path):
            raise HTTPException(status_code=500, detail="TTS generation failed")

        # Return file directly.
        # Note: In production heavily loaded env, better to return URL or stream.
        # For sidecar usage, sending file bytes is fine.
        return FileResponse(
            path,
            media_type="audio/mpeg",
            filename=f"tts_{req.lang}.mp3",
            # We can use a background task to clean up the file after sending,
            # but FastAPI BackgroundTasks makes it easy.
        )

    except Exception as e:
        logger.error(f"API TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Cleanup helper (Optional, to be used with BackgroundTasks if needed)
def remove_file(path: str):
    try:
        os.remove(path)
    except Exception:
        pass


@app.post("/dict/add")
async def add_term(req: DictAddRequest):
    """Add a term to the custom dictionary."""
    langs = sorted([req.source_lang, req.target_lang])
    lang_pair = f"{langs[0]}-{langs[1]}"

    # Use HeuristicInflector if available, or just add directly
    from tg_translator.inflector import HeuristicInflector

    variations = HeuristicInflector.get_variations(req.source)
    if not variations:
        variations = {req.source}

    count = 0
    for variant in variations:
        if db.add_term(req.chat_id, variant, req.target, lang_pair):
            count += 1

    return {"status": "ok", "added_count": count}


@app.post("/dict/remove")
async def remove_term(req: DictRemoveRequest):
    """Remove a term from the custom dictionary."""
    langs = sorted([req.source_lang, req.target_lang])
    lang_pair = f"{langs[0]}-{langs[1]}"

    if db.remove_term(req.chat_id, req.source, lang_pair):
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=404, detail="Term not found")


@app.get("/dict/list/{chat_id}")
async def list_terms(chat_id: str, source_lang: str = "ru", target_lang: str = "en"):
    """List terms for a chat and language pair."""
    langs = sorted([source_lang, target_lang])
    lang_pair = f"{langs[0]}-{langs[1]}"

    terms = db.get_terms(chat_id, lang_pair)
    return {"terms": terms}
