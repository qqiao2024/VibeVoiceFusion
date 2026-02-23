"""
OpenAI-Compatible TTS API endpoint

Implements POST /v1/audio/speech for drop-in compatibility with OpenAI TTS clients.
This uses a separate blueprint registered at /v1 (not /api/v1) to match the OpenAI URL scheme.
"""
from flask import Blueprint, request, jsonify, send_file, current_app

from backend.services.openai_compat_service import (
    OpenAICompatService, MODEL_MAPPING, FORMAT_MIME_TYPES,
)
from util.logger import get_logger

logger = get_logger(__name__)

# Separate blueprint for OpenAI-compatible routes (mounted at /v1)
openai_bp = Blueprint('openai_compat', __name__)


def _openai_error(message: str, error_type: str = "invalid_request_error",
                  code: str = None, status: int = 400) -> tuple:
    """Return an OpenAI-style error response."""
    body = {
        "error": {
            "message": message,
            "type": error_type,
        }
    }
    if code:
        body["error"]["code"] = code
    return jsonify(body), status


def _get_service() -> OpenAICompatService:
    """Get OpenAICompatService instance from app config."""
    return OpenAICompatService(
        workspace_dir=current_app.config['WORKSPACE_DIR'],
        preset_dir=current_app.config['PRESET_VOICE_DIR'],
        fake_model=current_app.config.get('FAKE_MODEL', False),
    )


@openai_bp.route('/audio/speech', methods=['POST'])
def create_speech():
    """
    OpenAI-compatible TTS endpoint.

    Request (application/json):
        {
            "model": "vibevoice-7b",         // Required
            "input": "Hello world",           // Required, max 4096 chars
            "voice": "Alice",                 // Required, preset voice name
            "response_format": "wav",         // Optional, default: wav (supports: wav, mp3, flac, opus, aac, pcm)
            "speed": 1.0                      // Optional, accepted but ignored
        }

    Response:
        Binary audio data with appropriate Content-Type header.
    """
    service = _get_service()

    # --- Authentication ---
    auth_header = request.headers.get('Authorization')
    if not service.validate_api_key(auth_header):
        return _openai_error(
            "Invalid API key provided.",
            error_type="authentication_error",
            code="invalid_api_key",
            status=401,
        )

    # --- Parse JSON body ---
    if not request.is_json:
        return _openai_error("Request body must be JSON (Content-Type: application/json).")

    data = request.get_json(silent=True)
    if not data:
        return _openai_error("Invalid JSON in request body.")

    # --- Validate required fields ---
    model = data.get('model')
    if not model:
        return _openai_error("Missing required parameter: 'model'.", code="missing_model")

    input_text = data.get('input')
    if not input_text:
        return _openai_error("Missing required parameter: 'input'.", code="missing_input")

    if len(input_text) > 4096:
        return _openai_error(
            f"Input text is too long ({len(input_text)} chars). Maximum is 4096 characters.",
            code="input_too_long",
        )

    voice = data.get('voice')
    if not voice:
        return _openai_error("Missing required parameter: 'voice'.", code="missing_voice")

    # --- Validate optional fields ---
    response_format = data.get('response_format', 'wav')
    if response_format not in FORMAT_MIME_TYPES:
        supported = ', '.join(sorted(FORMAT_MIME_TYPES.keys()))
        return _openai_error(
            f"Unsupported response_format '{response_format}'. Supported formats: {supported}",
            code="unsupported_format",
        )

    # speed is accepted but ignored (not supported by engine)
    # data.get('speed', 1.0)

    # --- Resolve model (fallback to bf16 if unknown) ---
    model_dtype, err = service.resolve_model(model)
    if err:
        logger.warning(f"Unknown model '{model}', falling back to bf16")
        model_dtype = 'bf16'

    # --- Resolve voice ---
    voice_filename, err = service.resolve_voice(voice)
    if err:
        return _openai_error(err, code="voice_not_found")

    # --- Generate speech ---
    try:
        audio_path, err, status_code = service.generate_speech(
            text=input_text,
            voice_filename=voice_filename,
            model_dtype=model_dtype,
            response_format=response_format,
        )
    except Exception as e:
        logger.error(f"Unexpected error in speech generation: {e}", exc_info=True)
        return _openai_error(
            "An internal error occurred during speech generation.",
            error_type="server_error",
            status=500,
        )

    if err:
        error_type = "server_error" if status_code >= 500 else "invalid_request_error"
        return _openai_error(err, error_type=error_type, status=status_code)

    # --- Return audio ---
    mime_type = FORMAT_MIME_TYPES[response_format]
    # Map format to download extension (opus→ogg, pcm→raw)
    ext_map = {'opus': 'ogg', 'pcm': 'raw'}
    ext = ext_map.get(response_format, response_format)
    return send_file(
        str(audio_path),
        mimetype=mime_type,
        as_attachment=False,
        download_name=f"speech.{ext}",
    )


@openai_bp.route('/models', methods=['GET'])
def list_models():
    """
    List available models (OpenAI-compatible format).

    Returns a list of model objects matching OpenAI's /v1/models response format.
    """
    models = []
    seen = set()
    for model_name in sorted(MODEL_MAPPING.keys()):
        if model_name not in seen:
            seen.add(model_name)
            models.append({
                "id": model_name,
                "object": "model",
                "created": 0,
                "owned_by": "vibevoice",
            })

    return jsonify({
        "object": "list",
        "data": models,
    })
