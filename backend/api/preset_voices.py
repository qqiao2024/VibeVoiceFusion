"""
Preset voices API endpoints

Filename convention: {language}-{name}_{gender}[_bgm].wav
The filename serves as the unique identifier for each preset.
"""
from flask import request, jsonify, current_app, send_file
from backend.api import api_bp
from backend.services.preset_voice_service import PresetVoiceService
from backend.i18n import t, get_locale


def get_preset_service() -> PresetVoiceService:
    """Get PresetVoiceService instance"""
    return PresetVoiceService(current_app.config['PRESET_VOICE_DIR'])


@api_bp.route('/preset-voices', methods=['GET'])
def list_preset_voices():
    """
    List all preset voices with optional filtering and pagination

    Query Parameters:
        language: Filter by language code (en, zh, in)
        gender: Filter by gender (man, woman)
        has_bgm: Filter by BGM presence (true, false)
        offset: Number of items to skip (default: 0)
        limit: Maximum items per page (optional)

    Returns:
        JSON response with list of preset voices and pagination info
    """
    try:
        service = get_preset_service()
        locale = get_locale()

        # Parse query parameters
        language = request.args.get('language')
        gender = request.args.get('gender')
        has_bgm_param = request.args.get('has_bgm')
        has_bgm = None
        if has_bgm_param is not None:
            has_bgm = has_bgm_param.lower() == 'true'

        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', type=int)

        presets, total = service.list_presets(
            language=language,
            gender=gender,
            has_bgm=has_bgm,
            offset=offset,
            limit=limit,
            locale=locale
        )

        return jsonify({
            'presets': [p.to_dict() for p in presets],
            'count': len(presets),
            'total': total,
            'offset': offset,
            'limit': limit
        }), 200

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/preset-voices', methods=['POST'])
def add_preset_voice():
    """
    Add a new preset voice

    Form data:
        name: Voice name - letters only, will be capitalized (required)
        language: Language code - 'en', 'zh', or 'in' (required)
        gender: Gender - 'man' or 'woman' (required)
        has_bgm: Whether has background music - 'true' or 'false' (default: false)
        voice_file: Audio file (required)

    The file will be saved as: {language}-{name}_{gender}[_bgm].wav

    Returns:
        JSON response with created preset voice
    """
    try:
        service = get_preset_service()

        # Get form data
        name = request.form.get('name', '').strip()
        language = request.form.get('language', '').strip()
        gender = request.form.get('gender', '').strip()
        has_bgm_param = request.form.get('has_bgm', 'false')
        has_bgm = has_bgm_param.lower() == 'true'
        voice_file = request.files.get('voice_file')

        if not name:
            return jsonify({
                'error': t('errors.validation_error'),
                'message': t('errors.preset_name_required')
            }), 400

        if not language:
            return jsonify({
                'error': t('errors.validation_error'),
                'message': t('errors.preset_language_required')
            }), 400

        if not gender:
            return jsonify({
                'error': t('errors.validation_error'),
                'message': t('errors.preset_gender_required')
            }), 400

        if not voice_file:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': t('errors.file_upload_error')
            }), 400

        preset = service.add_preset(name, language, gender, has_bgm, voice_file)

        return jsonify(preset.to_dict()), 201

    except ValueError as e:
        return jsonify({
            'error': t('errors.validation_error'),
            'message': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/preset-voices/<path:filename>', methods=['GET'])
def get_preset_voice(filename):
    """
    Get preset voice by filename

    Args:
        filename: Preset filename (e.g., "en-Alice_woman.wav")

    Returns:
        JSON response with preset voice data
    """
    try:
        service = get_preset_service()
        locale = get_locale()
        preset = service.get_preset(filename, locale)

        if not preset:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.preset_voice_not_found')
            }), 404

        return jsonify(preset.to_dict()), 200

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/preset-voices/<path:filename>', methods=['DELETE'])
def delete_preset_voice(filename):
    """
    Delete preset voice

    Args:
        filename: Preset filename (e.g., "en-Alice_woman.wav")

    Returns:
        JSON response confirming deletion
    """
    try:
        service = get_preset_service()

        success = service.delete_preset(filename)
        if not success:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.preset_voice_not_found')
            }), 404

        return jsonify({
            'message': t('success.preset_voice_deleted'),
            'filename': filename
        }), 200

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/preset-voices/batch-delete', methods=['POST'])
def batch_delete_preset_voices():
    """
    Delete multiple preset voices

    Request body (JSON):
        filenames: List of preset filenames to delete

    Returns:
        JSON response with deletion results
    """
    try:
        service = get_preset_service()

        data = request.get_json()
        if not data or 'filenames' not in data:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': 'filenames is required'
            }), 400

        filenames = data.get('filenames', [])
        if not isinstance(filenames, list):
            return jsonify({
                'error': t('errors.bad_request'),
                'message': 'filenames must be a list'
            }), 400

        deleted, failed = service.batch_delete_presets(filenames)

        return jsonify({
            'message': t('success.preset_voices_deleted'),
            'deleted_count': len(deleted),
            'failed_count': len(failed),
            'deleted': deleted,
            'failed': failed
        }), 200

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/preset-voices/languages', methods=['GET'])
def list_preset_languages():
    """Get available languages for preset voices"""
    try:
        service = get_preset_service()
        locale = get_locale()
        languages = service.get_available_languages(locale=locale)
        return jsonify({
            'languages': languages
        }), 200
    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/preset-voices/<path:filename>/preview', methods=['GET'])
def preview_preset_voice(filename):
    """
    Get audio file for preview/playback

    Args:
        filename: Preset filename (e.g., "en-Alice_woman.wav")

    Returns:
        Audio file for streaming
    """
    try:
        service = get_preset_service()
        file_path = service.get_preset_path(filename)

        if not file_path:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.preset_voice_not_found')
            }), 404

        return send_file(file_path, mimetype='audio/wav')

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500
