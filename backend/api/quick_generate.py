"""
Quick Generate API endpoints
"""
import json
from flask import request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename

from backend.api import api_bp
from backend.services.quick_generate_service import QuickGenerateService
from backend.inference.quick_generate_inference import QuickGenerateInferenceBase
from backend.task_manager.task import gm, Task
from backend.i18n import t
from config.configuration_vibevoice import InferencePhase
from util.logger import get_logger

logger = get_logger(__name__)

# Allowed audio file extensions
ALLOWED_EXTENSIONS = {'wav', 'mp3', 'm4a', 'flac', 'webm', 'ogg'}


def _allowed_file(filename: str) -> bool:
    """Check if file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _get_quick_generate_service() -> QuickGenerateService:
    """Get QuickGenerateService instance"""
    return QuickGenerateService(
        workspace_dir=current_app.config['WORKSPACE_DIR'],
        fake_model=current_app.config.get('FAKE_MODEL', False)
    )


def _validate_offloading_config(offloading: dict) -> dict:
    """
    Validate offloading configuration from request.

    Args:
        offloading: Offloading config dict from request (can be None)

    Returns:
        Validated offloading config dict or None if disabled/not provided

    Raises:
        ValueError: If config is invalid
    """
    if not offloading or not offloading.get('enabled', False):
        return None

    mode = offloading.get('mode', 'preset')

    if mode not in ['preset', 'manual']:
        raise ValueError(f"Invalid offloading mode: '{mode}'. Must be 'preset' or 'manual'")

    if mode == 'preset':
        preset = offloading.get('preset', 'balanced')
        valid_presets = ['balanced', 'aggressive', 'extreme']
        if preset not in valid_presets:
            raise ValueError(f"Invalid preset: '{preset}'. Must be one of: {', '.join(valid_presets)}")

        return {
            'enabled': True,
            'mode': 'preset',
            'preset': preset
        }

    elif mode == 'manual':
        num_gpu_layers = offloading.get('num_gpu_layers')
        if num_gpu_layers is None:
            raise ValueError("num_gpu_layers is required for manual mode")

        if not isinstance(num_gpu_layers, int) or num_gpu_layers < 1 or num_gpu_layers > 28:
            raise ValueError(f"num_gpu_layers must be an integer between 1 and 28, got: {num_gpu_layers}")

        return {
            'enabled': True,
            'mode': 'manual',
            'num_gpu_layers': num_gpu_layers
        }


@api_bp.route('/quick-generate', methods=['POST'])
def start_quick_generation():
    """
    Start a new quick generation task.

    Form Data:
        - voice_file: Audio file (required)
        - text: Text to generate (required)
        - seeds: Random seed (optional, default: random)
        - batch_size: Number of generations 1-20 (optional, default: 1)
        - cfg_scale: CFG scale (optional, default: 1.3)
        - model_dtype: Model dtype (optional, default: "bf16")
        - offloading: JSON string of offloading config (optional)

    Returns:
        JSON with request_id, detected_mode, and status
    """
    try:
        # Check for voice file
        if 'voice_file' not in request.files:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': t('errors.quick_generate_voice_required')
            }), 400

        voice_file = request.files['voice_file']
        if voice_file.filename == '':
            return jsonify({
                'error': t('errors.bad_request'),
                'message': t('errors.quick_generate_voice_required')
            }), 400

        if not _allowed_file(voice_file.filename):
            return jsonify({
                'error': t('errors.bad_request'),
                'message': t('errors.invalid_file_type', formats=', '.join(ALLOWED_EXTENSIONS))
            }), 400

        # Get text
        text = request.form.get('text', '').strip()
        if not text:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': t('errors.quick_generate_text_required')
            }), 400

        # Get optional parameters
        import random
        seeds = request.form.get('seeds')
        if seeds:
            try:
                seeds = int(seeds)
            except ValueError:
                seeds = random.randint(0, 2**64 - 1)
        else:
            seeds = random.randint(0, 2**64 - 1)

        batch_size = request.form.get('batch_size', '1')
        try:
            batch_size = int(batch_size)
            batch_size = max(1, min(20, batch_size))  # Clamp to 1-20
        except ValueError:
            batch_size = 1

        cfg_scale = request.form.get('cfg_scale', '1.3')
        try:
            cfg_scale = float(cfg_scale)
        except ValueError:
            cfg_scale = 1.3

        model_dtype = request.form.get('model_dtype', 'bf16')
        attn_implementation = request.form.get('attn_implementation', 'sdpa')

        # Parse offloading config
        offloading_str = request.form.get('offloading', '')
        validated_offloading = None
        if offloading_str:
            try:
                offloading = json.loads(offloading_str)
                validated_offloading = _validate_offloading_config(offloading)
            except (json.JSONDecodeError, ValueError) as e:
                return jsonify({
                    'error': t('errors.validation_error'),
                    'message': str(e)
                }), 400

        # Get service
        service = _get_quick_generate_service()

        # Save voice file
        voice_data = voice_file.read()
        voice_filename = service.save_voice_file(voice_data, voice_file.filename)

        # Start generation
        quick_gen = service.start_generation(
            voice_file=voice_filename,
            text=text,
            seeds=seeds,
            batch_size=batch_size,
            cfg_scale=cfg_scale,
            model_dtype=model_dtype,
            attn_implementation=attn_implementation,
            offloading_config=validated_offloading
        )

        if not quick_gen:
            return jsonify({
                'error': t('errors.conflict'),
                'message': t('errors.task_manager_busy')
            }), 409

        return jsonify({
            'message': t('success.quick_generate_started'),
            'request_id': quick_gen.request_id,
            'detected_mode': quick_gen.detected_mode,
            'status': quick_gen.status.value if isinstance(quick_gen.status, InferencePhase) else quick_gen.status
        }), 200

    except Exception as e:
        logger.error(f"Error starting quick generation: {e}", exc_info=True)
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/quick-generate/<request_id>', methods=['GET'])
def get_quick_generation(request_id: str):
    """
    Get status of a quick generation request.

    Args:
        request_id: Generation request ID

    Returns:
        JSON with generation status and details
    """
    try:
        # First check if it's the current running task
        task: Task = gm.get_current_task()
        if task:
            inference = task.unwrap()
            if isinstance(inference, QuickGenerateInferenceBase):
                current_gen = inference.get_quick_generate()
                if current_gen and current_gen.request_id == request_id:
                    gen_dict = current_gen.to_dict()
                    return jsonify(gen_dict), 200

        # Check history
        service = _get_quick_generate_service()
        quick_gen = service.get_generation(request_id)

        if not quick_gen:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.quick_generate_not_found')
            }), 404

        return jsonify(quick_gen.to_dict()), 200

    except Exception as e:
        logger.error(f"Error getting quick generation: {e}", exc_info=True)
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/quick-generate/current', methods=['GET'])
def get_current_quick_generation():
    """
    Get the current running quick generation task.

    Returns:
        JSON with current quick generation status or null if none running
    """
    try:
        task: Task = gm.get_current_task()
        if task:
            inference = task.unwrap()
            if isinstance(inference, QuickGenerateInferenceBase):
                current_gen = inference.get_quick_generate()
                if current_gen:
                    return jsonify({
                        'message': 'Current quick generation retrieved successfully',
                        'generation': current_gen.to_dict()
                    }), 200

        return jsonify({
            'message': 'No active quick generation task',
            'generation': None
        }), 200

    except Exception as e:
        logger.error(f"Error getting current quick generation: {e}", exc_info=True)
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/quick-generate/history', methods=['GET'])
def list_quick_generation_history():
    """
    List quick generation history with pagination.

    Query params:
        - limit: Maximum items (default: 20)
        - offset: Items to skip (default: 0)

    Returns:
        JSON with generations list, count, and total
    """
    try:
        limit = request.args.get('limit', '20')
        offset = request.args.get('offset', '0')

        try:
            limit = int(limit)
            offset = int(offset)
        except ValueError:
            limit = 20
            offset = 0

        service = _get_quick_generate_service()
        result = service.list_history(limit=limit, offset=offset)

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error listing quick generation history: {e}", exc_info=True)
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/quick-generate/<request_id>/download', methods=['GET'])
def download_quick_generation_audio(request_id: str):
    """
    Download generated audio file.

    Query params:
        - download: If 'true', force download. Otherwise serve inline.

    Args:
        request_id: Generation request ID

    Returns:
        Audio file or error message
    """
    try:
        service = _get_quick_generate_service()
        audio_path = service.get_audio_path(request_id, item_index=0)

        if not audio_path:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.quick_generate_not_found')
            }), 404

        force_download = request.args.get('download', 'false').lower() == 'true'

        return send_file(
            str(audio_path),
            mimetype='audio/wav',
            as_attachment=force_download,
            download_name=audio_path.name if force_download else None
        )

    except Exception as e:
        logger.error(f"Error downloading quick generation audio: {e}", exc_info=True)
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/quick-generate/<request_id>/items/<int:item_index>/download', methods=['GET'])
def download_quick_generation_item_audio(request_id: str, item_index: int):
    """
    Download individual audio file from multi-generation batch.

    Query params:
        - download: If 'true', force download. Otherwise serve inline.

    Args:
        request_id: Generation request ID
        item_index: Index of the generation item (0-based)

    Returns:
        Audio file or error message
    """
    try:
        service = _get_quick_generate_service()
        audio_path = service.get_audio_path(request_id, item_index=item_index)

        if not audio_path:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.quick_generate_item_not_found')
            }), 404

        force_download = request.args.get('download', 'false').lower() == 'true'

        return send_file(
            str(audio_path),
            mimetype='audio/wav',
            as_attachment=force_download,
            download_name=audio_path.name if force_download else None
        )

    except Exception as e:
        logger.error(f"Error downloading quick generation item audio: {e}", exc_info=True)
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/quick-generate/<request_id>', methods=['DELETE'])
def delete_quick_generation(request_id: str):
    """
    Delete a quick generation and its files.

    Args:
        request_id: Generation request ID

    Returns:
        Success message or error
    """
    try:
        service = _get_quick_generate_service()
        success = service.delete_generation(request_id)

        if not success:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.quick_generate_not_found')
            }), 404

        return jsonify({
            'message': t('success.quick_generate_deleted'),
            'request_id': request_id
        }), 200

    except Exception as e:
        logger.error(f"Error deleting quick generation: {e}", exc_info=True)
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/quick-generate/<request_id>/voice/preview', methods=['GET'])
def preview_quick_generation_voice(request_id: str):
    """
    Preview the voice file used in a quick generation.

    Args:
        request_id: Generation request ID

    Returns:
        Voice audio file or error message
    """
    try:
        service = _get_quick_generate_service()
        quick_gen = service.get_generation(request_id)

        if not quick_gen:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.quick_generate_not_found')
            }), 404

        voice_path = service.get_voice_path(quick_gen.voice_file)
        if not voice_path:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.quick_generate_voice_not_found')
            }), 404

        return send_file(
            str(voice_path),
            mimetype='audio/wav'
        )

    except Exception as e:
        logger.error(f"Error previewing quick generation voice: {e}", exc_info=True)
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500
