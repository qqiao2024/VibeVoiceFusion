"""
Preset voices API endpoints
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
    List all available preset voices with optional filtering

    Query Parameters:
        language: Filter by language code (en, zh, in)
        gender: Filter by gender (man, woman)
        has_bgm: Filter by BGM presence (true, false)

    Returns:
        JSON response with list of preset voices
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

        presets = service.list_presets(
            language=language,
            gender=gender,
            has_bgm=has_bgm,
            locale=locale
        )

        return jsonify({
            'presets': [p.to_dict() for p in presets],
            'count': len(presets)
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


@api_bp.route('/preset-voices/<filename>/preview', methods=['GET'])
def preview_preset_voice(filename):
    """
    Get audio file for preview/playback

    Args:
        filename: Preset voice filename

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
