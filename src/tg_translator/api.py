import logging
import os
import shutil
import time
import uuid
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000
    formatted_process_time = "{0:.2f}".format(process_time)
    logger.info(
        f"RID: {uuid.uuid4().hex[:8]} | {request.method} {request.url.path} | "
        f"Status: {response.status_code} | Time: {formatted_process_time}ms"
    )
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "message": str(exc)},
    )


# --- Data Models ---
class TranslateRequest(BaseModel):
    text: str = Field(..., description="Text to translate")
    source_lang: str = Field(
        "auto", description="Source language code (e.g., 'ru', 'en') or 'auto'"
    )
    target_lang: str = Field(
        "en", description="Target language code (e.g., 'en', 'es')"
    )
    chat_id: Optional[str] = Field(
        None, description="Optional chat/user ID for custom dictionary lookup"
    )


class TTSRequest(BaseModel):
    text: str = Field(..., description="Text to synthesize")
    lang: str = Field(..., description="Language code (ru, en, de, es, fr, ua)")
    gender: str = Field(
        "male", description="Preferred voice gender ('male' or 'female')"
    )


class LanguageInfo(BaseModel):
    code: str
    name: str


class SpeakerInfo(BaseModel):
    name: str
    gender: str


class VoicesResponse(BaseModel):
    language: str
    speakers: list[SpeakerInfo]


class ChatStatusResponse(BaseModel):
    chat_id: str
    mode: str
    languages: list[str]
    voice_gender: str
    dictionary_count: int
    presets: dict[str, str]


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


# --- Metadata Constants ---
# Extracted from Silero configuration and handlers
SPEAKERS_DATA = {
    "ru": [
        {"name": "aidar", "gender": "male"},
        {"name": "baya", "gender": "female"},
        {"name": "kseniya", "gender": "female"},
        {"name": "xenia", "gender": "female"},
        {"name": "eugene", "gender": "male"},
        {"name": "random", "gender": "unknown"},
    ],
    "ua": [{"name": "mykyta", "gender": "male"}],
    "uk": [{"name": "mykyta", "gender": "male"}],
    "de": [{"name": "thorsten", "gender": "male"}],
    "es": [{"name": "es_0", "gender": "male"}],
    "fr": [
        {"name": "fr_0", "gender": "male"},
        {"name": "fr_1", "gender": "female"},
        {"name": "fr_2", "gender": "male"},
        {"name": "fr_3", "gender": "male"},
        {"name": "fr_4", "gender": "male"},
        {"name": "fr_5", "gender": "female"},
    ],
}


# --- Endpoints ---


@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "service": "tg-translator-ai"}


@app.get("/languages", response_model=list[LanguageInfo], tags=["Metadata"])
async def list_languages():
    """Returns a list of all supported translation languages."""
    supported = service.get_supported_languages()
    return [
        LanguageInfo(code=code, name=name.title())
        for name, code in sorted(supported.items())
    ]


@app.get("/voices/{lang_code}", response_model=VoicesResponse, tags=["Metadata"])
async def list_voices(lang_code: str):
    """
    Returns available TTS speakers for a specific language.
    Note: 'en' (English) returns a generic list en_0..en_117.
    """
    lang = lang_code.lower()
    if lang == "en":
        speakers = [SpeakerInfo(name=f"en_{i}", gender="unknown") for i in range(118)]
        return VoicesResponse(language="en", speakers=speakers)

    if lang in SPEAKERS_DATA:
        speakers = [SpeakerInfo(**s) for s in SPEAKERS_DATA[lang]]
        return VoicesResponse(language=lang, speakers=speakers)

    raise HTTPException(
        status_code=404,
        detail=f"No high-quality TTS voices found for language: {lang_code}",
    )


@app.get("/status/{chat_id}", response_model=ChatStatusResponse, tags=["Metadata"])
async def get_chat_status(chat_id: str):
    """
    Retrieves the current settings for a specific chat_id.
    Includes translation mode, language pair, and voice preferences.
    """
    mode = db.get_mode(chat_id)
    l1, l2 = db.get_languages(chat_id)
    gender = db.get_voice_gender(chat_id)

    # Dictionary count
    langs = sorted([l1, l2])
    lang_pair = f"{langs[0]}-{langs[1]}"
    terms = db.get_terms(chat_id, lang_pair)
    dict_count = len(terms) if terms else 0

    # Presets
    presets = {}
    for lang in [l1, l2]:
        preset = db.get_voice_preset(chat_id, lang, gender)
        if preset:
            presets[lang] = preset

    return ChatStatusResponse(
        chat_id=chat_id,
        mode=mode,
        languages=[l1, l2],
        voice_gender=gender,
        dictionary_count=dict_count,
        presets=presets,
    )


@app.post("/translate", tags=["Core"])
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


@app.post("/stt", tags=["Core"])
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


@app.post("/tts", tags=["Core"])
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


@app.post("/dict/add", tags=["Dictionary"])
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


@app.post("/dict/remove", tags=["Dictionary"])
async def remove_term(req: DictRemoveRequest):
    """Remove a term from the custom dictionary."""
    langs = sorted([req.source_lang, req.target_lang])
    lang_pair = f"{langs[0]}-{langs[1]}"

    if db.remove_term(req.chat_id, req.source, lang_pair):
        return {"status": "ok"}
    else:
        raise HTTPException(status_code=404, detail="Term not found")


@app.get("/dict/list/{chat_id}", tags=["Dictionary"])
async def list_terms(chat_id: str, source_lang: str = "ru", target_lang: str = "en"):
    """List terms for a chat and language pair."""
    langs = sorted([source_lang, target_lang])
    lang_pair = f"{langs[0]}-{langs[1]}"

    terms = db.get_terms(chat_id, lang_pair)
    return {"terms": terms}
