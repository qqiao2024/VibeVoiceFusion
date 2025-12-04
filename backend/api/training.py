"""
Training API endpoints
"""
from typing import Dict, Any
from flask import request, jsonify, current_app, send_file
from backend.api import api_bp
from backend.services.training_service import TrainingService
from backend.services.project_service import ProjectService
from backend.utils.tensorboard_reader import TensorBoardReader
from backend.i18n import t
from util.logger import get_logger

from vibevoice.training.trainer import TrainConfig

logger = get_logger(__name__)


def _get_training_service(project_id: str) -> tuple:
    """
    Helper function to get TrainingService instance for a project

    Returns:
        Tuple of (TrainingService, 200) or (error_response, error_code)
    """
    try:
        # Get project service
        project_service = ProjectService(
            workspace_dir=current_app.config['WORKSPACE_DIR'],
            meta_file_name=current_app.config['PROJECTS_META_FILE']
        )

        # Get project path
        project_path = project_service.get_project_path(project_id)
        if not project_path:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        # Create training service
        training_dir = project_path / 'training'
        service = TrainingService(
            project_training_dir=training_dir,
            fake_engine=current_app.config.get('FAKE_MODEL', False)
        )

        return service, 200

    except Exception as e:
        logger.error(f"Error creating training service: {e}")
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/training', methods=['POST'])
def create_training_job(project_id: str):
    """
    Create and start a new training job

    Request body:
        {
            "job_name": "My Training Job",
            "config": {
                "lora_name": "my_lora",
                "epochs": 10,
                "batch_size": 1,
                ...
            }
        }

    Returns:
        201: Training job created and started (returns TrainingState)
        400: Invalid request
        404: Project not found
        409: Task manager is busy (another task is running)
        500: Internal error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': 'Request body must be JSON'
            }), 400

        # Validate required fields
        job_name = data.get('job_name')
        if not job_name:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': t('errors.validation_error')
            }), 400

        config_dict = data.get('config', {})
        if not config_dict:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': 'Training configuration is required'
            }), 400

        # Create TrainConfig from dict
        try:
            train_config = TrainConfig.from_dict(config_dict)
        except Exception as e:
            logger.error(f"Failed to create TrainConfig: {e}")
            return jsonify({
                'error': t('errors.validation_error'),
                'message': f'Invalid training configuration: {str(e)}'
            }), 400

        # Get training service
        result = _get_training_service(project_id)
        if isinstance(result[0], TrainingService):
            service = result[0]
        else:
            return result  # Return error response

        # Create training job (may raise ValueError for duplicate job_name)
        try:
            state = service.create_training_job(job_name, train_config, project_id)
        except ValueError as e:
            # Job name is not unique
            return jsonify({
                'error': t('errors.conflict'),
                'message': t('errors.job_name_duplicate')
            }), 409

        if not state:
            # Task manager is busy
            return jsonify({
                'error': t('errors.conflict'),
                'message': t('errors.task_manager_busy')
            }), 409

        return jsonify({
            'message': t('success.training_started'),
            'task_id': state.task_id,
            'state': state.to_dict()
        }), 201

    except Exception as e:
        logger.error(f"Error creating training job job_name: {job_name} train_config: {train_config.to_dict()}", exc_info=e)
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/training', methods=['GET'])
def list_training_jobs(project_id: str):
    """
    List all training jobs for a project

    Returns:
        200: List of TrainingState objects
        404: Project not found
        500: Internal error
    """
    try:
        # Get training service
        result = _get_training_service(project_id)
        if isinstance(result[0], TrainingService):
            service = result[0]
        else:
            return result

        # List all jobs
        states = service.list_jobs()

        return jsonify({
            'states': [state.to_dict() for state in states],
            'count': len(states)
        }), 200

    except Exception as e:
        logger.error(f"Error listing training jobs: {e}")
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/training/current', methods=['GET'])
def get_current_training_job(project_id: str):
    """
    Get the currently running training job with live metrics

    Returns:
        200: Current TrainingState (null if none active)
        404: Project not found
        500: Internal error
    """
    try:
        # Get training service
        result = _get_training_service(project_id)
        if isinstance(result[0], TrainingService):
            service = result[0]
        else:
            return result

        # Get current job
        current_state = service.get_current_job()

        if current_state:
            return jsonify({
                'message': 'Current training job retrieved successfully',
                'state': current_state.to_dict()
            }), 200
        else:
            return jsonify({
                'message': 'No active training job at the moment',
                'state': None
            }), 200

    except Exception as e:
        logger.error(f"Error getting current training job: {e}")
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/training/<job_id>', methods=['GET'])
def get_training_job(project_id: str, job_id: str):
    """
    Get a specific training job by ID

    Returns:
        200: TrainingState details
        404: Job or project not found
        500: Internal error
    """
    try:
        # Get training service
        result = _get_training_service(project_id)
        if isinstance(result[0], TrainingService):
            service = result[0]
        else:
            return result

        # Get job
        state = service.get_job(job_id)

        if not state:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.training_job_not_found')
            }), 404

        return jsonify({
            'state': state.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Error getting training job: {e}")
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/training/<job_id>', methods=['DELETE'])
def delete_training_job(project_id: str, job_id: str):
    """
    Delete a training job (only if not currently running)

    Returns:
        200: Job deleted successfully
        400: Cannot delete running job
        404: Job or project not found
        500: Internal error
    """
    try:
        # Get training service
        result = _get_training_service(project_id)
        if isinstance(result[0], TrainingService):
            service = result[0]
        else:
            return result

        # Delete job
        success = service.delete_job(job_id)

        if not success:
            # Could be not found or not completed
            state = service.get_job(job_id)
            if not state:
                return jsonify({
                    'error': t('errors.not_found'),
                    'message': t('errors.training_job_not_found')
                }), 404
            else:
                return jsonify({
                    'error': t('errors.bad_request'),
                    'message': t('errors.cannot_delete_non_completed_job')
                }), 400

        return jsonify({
            'message': t('success.training_job_deleted'),
            'job_id': job_id
        }), 200

    except Exception as e:
        logger.error(f"Error deleting training job: {e}")
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/training/batch-delete', methods=['POST'])
def batch_delete_training_jobs(project_id: str):
    """
    Delete multiple training jobs in batch

    Request body:
        {
            "job_ids": ["id1", "id2", ...]
        }

    Returns:
        200: Batch deletion results
        400: Invalid request
        404: Project not found
        500: Internal error
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': 'Request body must be JSON'
            }), 400

        job_ids = data.get('job_ids', [])
        if not job_ids or not isinstance(job_ids, list):
            return jsonify({
                'error': t('errors.bad_request'),
                'message': t('errors.validation_error')
            }), 400

        # Get training service
        result = _get_training_service(project_id)
        if isinstance(result[0], TrainingService):
            service = result[0]
        else:
            return result

        # Delete jobs in batch
        result = service.delete_jobs_batch(job_ids)

        return jsonify({
            'message': t('success.training_jobs_deleted'),
            'deleted_count': result['deleted_count'],
            'failed_count': result['failed_count'],
            'deleted_ids': result['deleted_ids'],
            'failed_ids': result['failed_ids']
        }), 200

    except Exception as e:
        logger.error(f"Error batch deleting training jobs: {e}")
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/training/<job_id>/lora/<filename>', methods=['GET'])
def download_lora_file(project_id: str, job_id: str, filename: str):
    """
    Download a LoRA file from a completed training job

    Returns:
        200: LoRA file download
        404: Job, project, or file not found
        400: Job is not completed
        500: Internal error
    """
    try:
        # Get training service
        result = _get_training_service(project_id)
        if isinstance(result[0], TrainingService):
            service = result[0]
        else:
            return result

        # Get LoRA file path
        lora_file_path = service.get_lora_file_path(job_id, filename)

        if not lora_file_path:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.lora_file_not_found')
            }), 404

        # Send file for download
        return send_file(
            lora_file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        logger.error(f"Error downloading LoRA file: {e}")
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/training/<job_id>/metrics', methods=['GET'])
def get_training_metrics(project_id: str, job_id: str):
    """
    Get training metrics from TensorBoard logs

    Query parameters:
        - max_points: Maximum number of data points per metric (default: 500)
        - metrics: Comma-separated list of metric types (loss, learning_rate, timing, all)

    Returns:
        200: Training metrics data
        404: Job or project not found, or tensorboard logs not available
        500: Internal error
    """
    try:
        # Get training service
        result = _get_training_service(project_id)
        if isinstance(result[0], TrainingService):
            service = result[0]
        else:
            return result

        # Get job to access tensorboard_logdir
        state = service.get_job(job_id)

        if not state:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.training_job_not_found')
            }), 404

        # Check if tensorboard logs exist
        if not state.tensorboard_logdir:
            return jsonify({
                'error': t('errors.not_found'),
                'message': 'TensorBoard logs not available for this job'
            }), 404

        # Parse query parameters
        max_points = request.args.get('max_points', default=500, type=int)
        metrics_param = request.args.get('metrics', default='all', type=str)

        # Read tensorboard logs
        reader = TensorBoardReader(state.tensorboard_logdir)

        # Get requested metrics
        if metrics_param == 'all':
            metrics_data = reader.get_all_metrics(max_points)
        else:
            metrics_types = [m.strip() for m in metrics_param.split(',')]
            metrics_data = {}

            if 'loss' in metrics_types:
                metrics_data['loss'] = reader.get_loss_metrics(max_points)
            if 'learning_rate' in metrics_types:
                metrics_data['learning_rate'] = reader.get_learning_rate(max_points)
            if 'timing' in metrics_types:
                metrics_data['timing'] = reader.get_timing_metrics(max_points)

        return jsonify({
            'message': 'Training metrics retrieved successfully',
            'job_id': job_id,
            'metrics': metrics_data
        }), 200

    except Exception as e:
        logger.error(f"Error getting training metrics: {e}")
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500
