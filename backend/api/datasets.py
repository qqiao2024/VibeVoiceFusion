"""
Datasets API endpoints (project-scoped)
"""
from flask import request, jsonify, current_app, send_file
from pathlib import Path
from backend.api import api_bp
from backend.services.dataset_service import DatasetService
from backend.services.project_service import ProjectService
from backend.i18n import t


def get_dataset_service(project_id: str) -> DatasetService:
    """Get DatasetService instance for a specific project"""
    # Get project service to verify project exists
    project_service = ProjectService(
        workspace_dir=current_app.config['WORKSPACE_DIR'],
        meta_file_name=current_app.config['PROJECTS_META_FILE']
    )

    # Get project path
    project_path = project_service.get_project_path(project_id)
    if not project_path:
        return None

    # Return dataset service for project's datasets directory
    return DatasetService(project_path / 'datasets')


@api_bp.route('/projects/<project_id>/datasets', methods=['GET'])
def list_datasets(project_id):
    """
    List all datasets for a project

    Args:
        project_id: Project identifier

    Returns:
        JSON response with list of datasets
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        datasets = service.list_datasets()

        return jsonify({
            'datasets': [d.to_dict() for d in datasets],
            'count': len(datasets)
        }), 200

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/datasets/<dataset_id>', methods=['GET'])
def get_dataset(project_id, dataset_id):
    """
    Get dataset by ID

    Args:
        project_id: Project identifier
        dataset_id: Dataset identifier

    Returns:
        JSON response with dataset data
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        dataset = service.get_dataset(dataset_id)

        if not dataset:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.dataset_not_found')
            }), 404

        return jsonify(dataset.to_dict()), 200

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/datasets', methods=['POST'])
def create_dataset(project_id):
    """
    Create a new dataset

    Args:
        project_id: Project identifier

    Request body:
        {
            "name": "Dataset name",
            "description": "Dataset description"
        }

    Returns:
        JSON response with created dataset data
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        data = request.get_json()
        if not data:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': 'Request body must be JSON'
            }), 400

        name = data.get('name', '').strip()
        description = data.get('description', '').strip()

        if not name:
            return jsonify({
                'error': t('errors.validation_error'),
                'message': t('errors.dataset_name_required')
            }), 400

        dataset = service.create_dataset(name, description)

        return jsonify(dataset.to_dict()), 201

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


@api_bp.route('/projects/<project_id>/datasets/<dataset_id>', methods=['PUT'])
def update_dataset(project_id, dataset_id):
    """
    Update dataset metadata

    Args:
        project_id: Project identifier
        dataset_id: Dataset identifier

    Request body:
        {
            "name": "Updated name",
            "description": "Updated description"
        }

    Returns:
        JSON response with updated dataset data
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        data = request.get_json()
        if not data:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': 'Request body must be JSON'
            }), 400

        name = data.get('name')
        description = data.get('description')

        dataset = service.update_dataset(dataset_id, name, description)

        if not dataset:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.dataset_not_found')
            }), 404

        return jsonify(dataset.to_dict()), 200

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/datasets/<dataset_id>', methods=['DELETE'])
def delete_dataset(project_id, dataset_id):
    """
    Delete dataset

    Args:
        project_id: Project identifier
        dataset_id: Dataset identifier

    Returns:
        JSON response confirming deletion
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        success = service.delete_dataset(dataset_id)

        if not success:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.dataset_not_found')
            }), 404

        return jsonify({
            'message': t('success.dataset_deleted'),
            'dataset_id': dataset_id
        }), 200

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/datasets/<dataset_id>/export', methods=['GET'])
def export_dataset(project_id, dataset_id):
    """
    Export dataset as a zip file

    Args:
        project_id: Project identifier
        dataset_id: Dataset identifier

    Returns:
        Zip file containing dataset
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        dataset = service.get_dataset(dataset_id)

        if not dataset:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.dataset_not_found')
            }), 404

        # Create temporary export file
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        export_path = temp_dir / f"{dataset_id}.zip"

        service.export_dataset(dataset_id, export_path)

        # Send file and cleanup
        return send_file(
            export_path,
            as_attachment=True,
            download_name=f"{dataset.name}.zip",
            mimetype='application/zip'
        )

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


@api_bp.route('/projects/<project_id>/datasets/import', methods=['POST'])
def import_dataset(project_id):
    """
    Import dataset from a zip file

    Args:
        project_id: Project identifier

    Form data:
        dataset_file: Zip file containing dataset (required)
        name: Optional name for imported dataset

    Returns:
        JSON response with imported dataset data
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        dataset_file = request.files.get('dataset_file')
        if not dataset_file:
            return jsonify({
                'error': t('errors.bad_request'),
                'message': t('errors.file_upload_error')
            }), 400

        # Get optional name from form data
        dataset_name = request.form.get('name')

        dataset = service.import_dataset(dataset_file, dataset_name)

        return jsonify(dataset.to_dict()), 201

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


# Dataset Items endpoints

@api_bp.route('/projects/<project_id>/datasets/<dataset_id>/items', methods=['GET'])
def list_dataset_items(project_id, dataset_id):
    """
    List all items in a dataset

    Args:
        project_id: Project identifier
        dataset_id: Dataset identifier

    Returns:
        JSON response with list of dataset items
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        if not service.get_dataset(dataset_id):
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.dataset_not_found')
            }), 404

        items = service.list_items(dataset_id)

        return jsonify({
            'items': [item.to_dict() for item in items],
            'count': len(items)
        }), 200

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500


@api_bp.route('/projects/<project_id>/datasets/<dataset_id>/items', methods=['POST'])
def add_dataset_item(project_id, dataset_id):
    """
    Add a new item to the dataset

    Args:
        project_id: Project identifier
        dataset_id: Dataset identifier

    Form data:
        text: Text content (required)
        audio_file: Audio file (required)
        voice_prompt_files: Voice prompt files (required, multiple)

    Returns:
        JSON response with created dataset item
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        if not service.get_dataset(dataset_id):
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.dataset_not_found')
            }), 404

        # Get form data
        text = request.form.get('text', '').strip()
        audio_file = request.files.get('audio_file')
        voice_prompt_files = request.files.getlist('voice_prompt_files')

        if not text:
            return jsonify({
                'error': t('errors.validation_error'),
                'message': t('errors.text_required')
            }), 400

        if not audio_file:
            return jsonify({
                'error': t('errors.validation_error'),
                'message': t('errors.audio_file_required')
            }), 400

        if not voice_prompt_files or len(voice_prompt_files) == 0:
            return jsonify({
                'error': t('errors.validation_error'),
                'message': t('errors.voice_prompts_required')
            }), 400

        item = service.add_item(dataset_id, text, audio_file, voice_prompt_files)

        return jsonify(item.to_dict()), 201

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


@api_bp.route('/projects/<project_id>/datasets/<dataset_id>/items/<int:item_index>', methods=['PUT'])
def update_dataset_item(project_id, dataset_id, item_index):
    """
    Update a dataset item

    Args:
        project_id: Project identifier
        dataset_id: Dataset identifier
        item_index: Index of item to update (0-based)

    Form data:
        text: Text content (optional)
        audio_file: Audio file (optional)
        voice_prompt_files: Voice prompt files (optional, multiple)

    Returns:
        JSON response with updated dataset item
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        if not service.get_dataset(dataset_id):
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.dataset_not_found')
            }), 404

        # Get form data
        text = request.form.get('text')
        audio_file = request.files.get('audio_file')
        voice_prompt_files = request.files.getlist('voice_prompt_files')

        # Convert empty list to None
        if voice_prompt_files and len(voice_prompt_files) == 0:
            voice_prompt_files = None

        item = service.update_item(dataset_id, item_index, text, audio_file, voice_prompt_files)

        if not item:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.item_not_found')
            }), 404

        return jsonify(item.to_dict()), 200

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


@api_bp.route('/projects/<project_id>/datasets/<dataset_id>/items/<int:item_index>', methods=['DELETE'])
def delete_dataset_item(project_id, dataset_id, item_index):
    """
    Delete a dataset item

    Args:
        project_id: Project identifier
        dataset_id: Dataset identifier
        item_index: Index of item to delete (0-based)

    Returns:
        JSON response confirming deletion
    """
    try:
        service = get_dataset_service(project_id)
        if not service:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.project_not_found')
            }), 404

        if not service.get_dataset(dataset_id):
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.dataset_not_found')
            }), 404

        success = service.delete_item(dataset_id, item_index)

        if not success:
            return jsonify({
                'error': t('errors.not_found'),
                'message': t('errors.item_not_found')
            }), 404

        return jsonify({
            'message': t('success.item_deleted'),
            'item_index': item_index
        }), 200

    except Exception as e:
        return jsonify({
            'error': t('errors.internal_error'),
            'message': str(e)
        }), 500
