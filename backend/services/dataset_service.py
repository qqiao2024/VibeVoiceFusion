"""
Dataset management service - handles business logic for datasets
"""
import uuid
import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from werkzeug.datastructures import FileStorage

from backend.models.dataset import Dataset, DatasetItem
from backend.utils.file_handler import FileHandler


class DatasetService:
    """Service for managing datasets and their items within a project"""

    DATASETS_META_FILE = 'datasets.json'
    ITEMS_FILE = 'datasets.jsonl'
    AUDIO_DIR = 'audio'
    VOICE_PROMPTS_DIR = 'voice_prompts'
    ALLOWED_AUDIO_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.flac', '.webm'}

    def __init__(self, project_datasets_dir: Path):
        """
        Initialize dataset service for a specific project

        Args:
            project_datasets_dir: Path to project's datasets directory
        """
        self.datasets_dir = Path(project_datasets_dir)
        self.meta_file_path = self.datasets_dir / self.DATASETS_META_FILE
        self.file_handler = FileHandler()

        # Ensure datasets directory exists
        self.file_handler.ensure_directory(self.datasets_dir)

        # Initialize metadata file if it doesn't exist
        if not self.meta_file_path.exists():
            self._save_metadata({})

    def _load_metadata(self) -> Dict[str, Dict[str, Any]]:
        """
        Load datasets metadata from JSON file

        Returns:
            Dictionary mapping dataset_id to dataset data
        """
        try:
            return self.file_handler.read_json(self.meta_file_path)
        except FileNotFoundError:
            return {}
        except Exception as e:
            raise RuntimeError(f"Failed to load datasets metadata: {str(e)}")

    def _save_metadata(self, metadata: Dict[str, Dict[str, Any]]) -> None:
        """
        Atomically save datasets metadata to JSON file

        Args:
            metadata: Dictionary mapping dataset_id to dataset data
        """
        try:
            self.file_handler.write_json_atomic(self.meta_file_path, metadata)
        except Exception as e:
            raise RuntimeError(f"Failed to save datasets metadata: {str(e)}")

    def _generate_dataset_id(self, name: str) -> str:
        """
        Generate unique dataset ID from name

        Args:
            name: Dataset name

        Returns:
            Sanitized unique dataset ID
        """
        # Sanitize the name for use as directory name
        base_id = self.file_handler.sanitize_filename(name.lower().replace(' ', '-'))

        # Check if ID already exists
        metadata = self._load_metadata()
        if base_id not in metadata:
            return base_id

        # Append UUID suffix if name already exists
        return f"{base_id}-{str(uuid.uuid4())[:8]}"

    def _get_dataset_dir(self, dataset_id: str) -> Path:
        """Get path to dataset directory"""
        return self.datasets_dir / dataset_id

    def _get_items_file_path(self, dataset_id: str) -> Path:
        """Get path to dataset items file"""
        return self._get_dataset_dir(dataset_id) / self.ITEMS_FILE

    def _get_audio_dir(self, dataset_id: str) -> Path:
        """Get path to dataset audio directory"""
        return self._get_dataset_dir(dataset_id) / self.AUDIO_DIR

    def _get_voice_prompts_dir(self, dataset_id: str) -> Path:
        """Get path to dataset voice prompts directory"""
        return self._get_dataset_dir(dataset_id) / self.VOICE_PROMPTS_DIR

    def _load_items(self, dataset_id: str) -> List[DatasetItem]:
        """
        Load all items from dataset's JSONL file

        Args:
            dataset_id: Dataset identifier

        Returns:
            List of DatasetItem objects
        """
        items_file = self._get_items_file_path(dataset_id)
        if not items_file.exists():
            return []

        items = []
        try:
            with open(items_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    try:
                        item_data = json.loads(line)
                        items.append(DatasetItem.from_dict(item_data))
                    except json.JSONDecodeError as e:
                        raise RuntimeError(f"Invalid JSON at line {line_num}: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to load dataset items: {str(e)}")

        return items

    def _save_items(self, dataset_id: str, items: List[DatasetItem]) -> None:
        """
        Atomically save items to dataset's JSONL file

        Args:
            dataset_id: Dataset identifier
            items: List of DatasetItem objects
        """
        items_file = self._get_items_file_path(dataset_id)

        # Write to temporary file first
        temp_file = items_file.with_suffix('.tmp')
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                for item in items:
                    json_line = json.dumps(item.to_dict(), ensure_ascii=False)
                    f.write(json_line + '\n')

            # Atomically replace the original file
            temp_file.replace(items_file)
        except Exception as e:
            # Clean up temp file on error
            if temp_file.exists():
                temp_file.unlink()
            raise RuntimeError(f"Failed to save dataset items: {str(e)}")

    def _sync_item_count(self, dataset_id: str) -> None:
        """
        Synchronize item count in metadata with actual items file

        Args:
            dataset_id: Dataset identifier
        """
        metadata = self._load_metadata()
        if dataset_id not in metadata:
            return

        # Count items in JSONL file
        items = self._load_items(dataset_id)
        item_count = len(items)

        # Update metadata
        dataset_data = metadata[dataset_id]
        dataset = Dataset.from_dict(dataset_data)
        dataset.update(item_count=item_count)
        metadata[dataset_id] = dataset.to_dict()
        self._save_metadata(metadata)

    def _validate_audio_file(self, filename: str) -> bool:
        """
        Validate audio file extension

        Args:
            filename: Filename to validate

        Returns:
            True if valid, False otherwise
        """
        ext = Path(filename).suffix.lower()
        return ext in self.ALLOWED_AUDIO_EXTENSIONS

    def list_datasets(self) -> List[Dataset]:
        """
        List all datasets

        Returns:
            List of Dataset objects
        """
        metadata = self._load_metadata()
        return [Dataset.from_dict(data) for data in metadata.values()]

    def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """
        Get dataset by ID

        Args:
            dataset_id: Dataset identifier

        Returns:
            Dataset object or None if not found
        """
        metadata = self._load_metadata()
        dataset_data = metadata.get(dataset_id)

        if dataset_data:
            return Dataset.from_dict(dataset_data)
        return None

    def create_dataset(self, name: str, description: str = "") -> Dataset:
        """
        Create a new dataset

        Args:
            name: Dataset name
            description: Dataset description

        Returns:
            Created Dataset object

        Raises:
            ValueError: If dataset name is empty
            RuntimeError: If dataset creation fails
        """
        if not name or not name.strip():
            raise ValueError("Dataset name cannot be empty")

        # Generate unique dataset ID
        dataset_id = self._generate_dataset_id(name)

        # Create dataset directory structure
        dataset_dir = self._get_dataset_dir(dataset_id)
        try:
            self.file_handler.ensure_directory(dataset_dir)
            self.file_handler.ensure_directory(self._get_audio_dir(dataset_id))
            self.file_handler.ensure_directory(self._get_voice_prompts_dir(dataset_id))

            # Create empty items file
            items_file = self._get_items_file_path(dataset_id)
            items_file.touch()

        except Exception as e:
            # Cleanup on failure
            if dataset_dir.exists():
                self.file_handler.delete_directory(dataset_dir)
            raise RuntimeError(f"Failed to create dataset directory: {str(e)}")

        # Create dataset metadata
        dataset = Dataset.create(dataset_id, name.strip(), description.strip())

        # Save to metadata file
        metadata = self._load_metadata()
        metadata[dataset_id] = dataset.to_dict()
        self._save_metadata(metadata)

        return dataset

    def update_dataset(self, dataset_id: str, name: Optional[str] = None,
                       description: Optional[str] = None) -> Optional[Dataset]:
        """
        Update dataset metadata

        Args:
            dataset_id: Dataset identifier
            name: New dataset name (optional)
            description: New dataset description (optional)

        Returns:
            Updated Dataset object or None if not found
        """
        metadata = self._load_metadata()
        dataset_data = metadata.get(dataset_id)

        if not dataset_data:
            return None

        # Load dataset and update
        dataset = Dataset.from_dict(dataset_data)
        dataset.update(name=name, description=description)

        # Save updated metadata
        metadata[dataset_id] = dataset.to_dict()
        self._save_metadata(metadata)

        return dataset

    def delete_dataset(self, dataset_id: str) -> bool:
        """
        Delete dataset and its directory

        Args:
            dataset_id: Dataset identifier

        Returns:
            True if deleted successfully, False if dataset not found
        """
        metadata = self._load_metadata()

        if dataset_id not in metadata:
            return False

        # Delete dataset directory (includes all items, audio, and voice prompts)
        dataset_dir = self._get_dataset_dir(dataset_id)
        try:
            self.file_handler.delete_directory(dataset_dir)
        except Exception as e:
            raise RuntimeError(f"Failed to delete dataset directory: {str(e)}")

        # Remove from metadata
        del metadata[dataset_id]
        self._save_metadata(metadata)

        return True

    def list_items(self, dataset_id: str, offset: int = 0, limit: Optional[int] = None) -> tuple[List[DatasetItem], int]:
        """
        List items in a dataset with pagination support

        Args:
            dataset_id: Dataset identifier
            offset: Starting index (0-based, default: 0)
            limit: Maximum number of items to return (default: None for all items)

        Returns:
            Tuple of (list of DatasetItem objects, total count)

        Raises:
            ValueError: If dataset not found or invalid pagination parameters
        """
        if not self.get_dataset(dataset_id):
            raise ValueError("Dataset not found")

        if offset < 0:
            raise ValueError("Offset must be non-negative")

        if limit is not None and limit <= 0:
            raise ValueError("Limit must be positive")

        # Load all items
        all_items = self._load_items(dataset_id)
        total_count = len(all_items)

        # Apply pagination
        if limit is None:
            # Return all items from offset
            items = all_items[offset:]
        else:
            # Return items in the specified range
            items = all_items[offset:offset + limit]

        return items, total_count

    def add_item(self, dataset_id: str, text: str, audio_file: FileStorage,
                 voice_prompt_files: List[FileStorage]) -> DatasetItem:
        """
        Add a new item to the dataset

        Args:
            dataset_id: Dataset identifier
            text: Text content
            audio_file: Audio file
            voice_prompt_files: List of voice prompt files

        Returns:
            Created DatasetItem object

        Raises:
            ValueError: If validation fails
            RuntimeError: If operation fails
        """
        # Validate dataset exists
        if not self.get_dataset(dataset_id):
            raise ValueError("Dataset not found")

        # Validate inputs
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if not audio_file or not audio_file.filename:
            raise ValueError("Audio file is required")

        if not self._validate_audio_file(audio_file.filename):
            raise ValueError(f"Invalid audio file. Allowed extensions: {', '.join(self.ALLOWED_AUDIO_EXTENSIONS)}")

        if not voice_prompt_files or len(voice_prompt_files) == 0:
            raise ValueError("At least one voice prompt file is required")

        # Validate all voice prompt files
        for vp_file in voice_prompt_files:
            if not vp_file or not vp_file.filename:
                raise ValueError("Invalid voice prompt file")
            if not self._validate_audio_file(vp_file.filename):
                raise ValueError(f"Invalid voice prompt file. Allowed extensions: {', '.join(self.ALLOWED_AUDIO_EXTENSIONS)}")

        # Generate unique filenames
        audio_ext = Path(audio_file.filename).suffix.lower()
        audio_filename = f"{uuid.uuid4().hex}{audio_ext}"

        voice_prompt_filenames = []
        for vp_file in voice_prompt_files:
            vp_ext = Path(vp_file.filename).suffix.lower()
            vp_filename = f"{uuid.uuid4().hex}{vp_ext}"
            voice_prompt_filenames.append(vp_filename)

        # Save files
        audio_dir = self._get_audio_dir(dataset_id)
        voice_prompts_dir = self._get_voice_prompts_dir(dataset_id)

        saved_files = []
        try:
            # Save audio file
            audio_path = audio_dir / audio_filename
            audio_file.save(str(audio_path))
            saved_files.append(audio_path)

            # Save voice prompt files
            for vp_file, vp_filename in zip(voice_prompt_files, voice_prompt_filenames):
                vp_path = voice_prompts_dir / vp_filename
                vp_file.save(str(vp_path))
                saved_files.append(vp_path)

            # Create dataset item
            item = DatasetItem(
                text=text.strip(),
                audio=audio_filename,
                voice_prompts=voice_prompt_filenames
            )

            # Load existing items and append
            items = self._load_items(dataset_id)
            items.append(item)
            self._save_items(dataset_id, items)

            # Sync item count
            self._sync_item_count(dataset_id)

            return item

        except Exception as e:
            # Cleanup saved files on failure
            for file_path in saved_files:
                if file_path.exists():
                    file_path.unlink()
            raise RuntimeError(f"Failed to add dataset item: {str(e)}")

    def update_item(self, dataset_id: str, item_index: int, text: Optional[str] = None,
                    audio_file: Optional[FileStorage] = None,
                    voice_prompt_files: Optional[List[FileStorage]] = None) -> Optional[DatasetItem]:
        """
        Update an existing dataset item

        Args:
            dataset_id: Dataset identifier
            item_index: Index of item to update (0-based)
            text: New text content (optional)
            audio_file: New audio file (optional)
            voice_prompt_files: New voice prompt files (optional)

        Returns:
            Updated DatasetItem object or None if not found

        Raises:
            ValueError: If validation fails
            RuntimeError: If operation fails
        """
        # Validate dataset exists
        if not self.get_dataset(dataset_id):
            raise ValueError("Dataset not found")

        # Load items
        items = self._load_items(dataset_id)

        if item_index < 0 or item_index >= len(items):
            return None

        item = items[item_index]
        old_audio_filename = item.audio
        old_voice_prompt_filenames = item.voice_prompts.copy()

        # Update text if provided
        if text is not None:
            if not text.strip():
                raise ValueError("Text cannot be empty")
            item.text = text.strip()

        # Update audio file if provided
        new_audio_path = None
        if audio_file:
            if not self._validate_audio_file(audio_file.filename):
                raise ValueError(f"Invalid audio file. Allowed extensions: {', '.join(self.ALLOWED_AUDIO_EXTENSIONS)}")

            audio_ext = Path(audio_file.filename).suffix.lower()
            audio_filename = f"{uuid.uuid4().hex}{audio_ext}"
            audio_dir = self._get_audio_dir(dataset_id)
            new_audio_path = audio_dir / audio_filename

            try:
                audio_file.save(str(new_audio_path))
                item.audio = audio_filename
            except Exception as e:
                if new_audio_path and new_audio_path.exists():
                    new_audio_path.unlink()
                raise RuntimeError(f"Failed to save audio file: {str(e)}")

        # Update voice prompt files if provided
        new_vp_paths = []
        if voice_prompt_files:
            if len(voice_prompt_files) == 0:
                raise ValueError("At least one voice prompt file is required")

            # Validate all files first
            for vp_file in voice_prompt_files:
                if not vp_file or not vp_file.filename:
                    raise ValueError("Invalid voice prompt file")
                if not self._validate_audio_file(vp_file.filename):
                    raise ValueError(f"Invalid voice prompt file. Allowed extensions: {', '.join(self.ALLOWED_AUDIO_EXTENSIONS)}")

            voice_prompts_dir = self._get_voice_prompts_dir(dataset_id)
            new_vp_filenames = []

            try:
                for vp_file in voice_prompt_files:
                    vp_ext = Path(vp_file.filename).suffix.lower()
                    vp_filename = f"{uuid.uuid4().hex}{vp_ext}"
                    vp_path = voice_prompts_dir / vp_filename
                    vp_file.save(str(vp_path))
                    new_vp_paths.append(vp_path)
                    new_vp_filenames.append(vp_filename)

                item.voice_prompts = new_vp_filenames

            except Exception as e:
                # Cleanup new voice prompt files
                for vp_path in new_vp_paths:
                    if vp_path.exists():
                        vp_path.unlink()
                # Cleanup new audio file if it was saved
                if new_audio_path and new_audio_path.exists():
                    new_audio_path.unlink()
                raise RuntimeError(f"Failed to save voice prompt files: {str(e)}")

        # Save updated items
        try:
            self._save_items(dataset_id, items)

            # Delete old files after successful save
            if new_audio_path:
                old_audio_path = self._get_audio_dir(dataset_id) / old_audio_filename
                if old_audio_path.exists():
                    old_audio_path.unlink()

            if new_vp_paths:
                voice_prompts_dir = self._get_voice_prompts_dir(dataset_id)
                for old_vp_filename in old_voice_prompt_filenames:
                    old_vp_path = voice_prompts_dir / old_vp_filename
                    if old_vp_path.exists():
                        old_vp_path.unlink()

            return item

        except Exception as e:
            # Cleanup new files if save failed
            if new_audio_path and new_audio_path.exists():
                new_audio_path.unlink()
            for vp_path in new_vp_paths:
                if vp_path.exists():
                    vp_path.unlink()
            raise RuntimeError(f"Failed to update dataset item: {str(e)}")

    def delete_item(self, dataset_id: str, item_index: int) -> bool:
        """
        Delete a dataset item

        Args:
            dataset_id: Dataset identifier
            item_index: Index of item to delete (0-based)

        Returns:
            True if deleted successfully, False if not found
        """
        # Validate dataset exists
        if not self.get_dataset(dataset_id):
            return False

        # Load items
        items = self._load_items(dataset_id)

        if item_index < 0 or item_index >= len(items):
            return False

        item = items[item_index]

        try:
            # Delete associated files
            audio_path = self._get_audio_dir(dataset_id) / item.audio
            if audio_path.exists():
                audio_path.unlink()

            voice_prompts_dir = self._get_voice_prompts_dir(dataset_id)
            for vp_filename in item.voice_prompts:
                vp_path = voice_prompts_dir / vp_filename
                if vp_path.exists():
                    vp_path.unlink()

            # Remove item from list
            items.pop(item_index)
            self._save_items(dataset_id, items)

            # Sync item count
            self._sync_item_count(dataset_id)

            return True

        except Exception as e:
            raise RuntimeError(f"Failed to delete dataset item: {str(e)}")

    def export_dataset(self, dataset_id: str, export_path: Path) -> None:
        """
        Export dataset to a zip file

        Args:
            dataset_id: Dataset identifier
            export_path: Path where to save the export (should end with .zip)

        Raises:
            ValueError: If dataset not found
            RuntimeError: If export fails
        """
        if not self.get_dataset(dataset_id):
            raise ValueError("Dataset not found")

        try:
            # Create zip archive of dataset directory
            shutil.make_archive(
                str(export_path.with_suffix('')),  # Remove .zip suffix as make_archive adds it
                'zip',
                self.datasets_dir,
                dataset_id
            )
        except Exception as e:
            raise RuntimeError(f"Failed to export dataset: {str(e)}")

    def import_dataset(self, import_file: FileStorage, dataset_name: Optional[str] = None) -> Dataset:
        """
        Import dataset from a zip file

        Args:
            import_file: Zip file containing dataset
            dataset_name: Optional name for imported dataset (uses original name if not provided)

        Returns:
            Imported Dataset object

        Raises:
            ValueError: If validation fails
            RuntimeError: If import fails
        """
        import tempfile
        import zipfile

        if not import_file or not import_file.filename:
            raise ValueError("Import file is required")

        if not import_file.filename.lower().endswith('.zip'):
            raise ValueError("Import file must be a ZIP archive")

        # Create temporary directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            zip_path = temp_path / 'dataset.zip'

            try:
                # Save uploaded file
                import_file.save(str(zip_path))

                # Extract zip file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)

                # Find the dataset directory (should be the only directory)
                extracted_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
                if len(extracted_dirs) != 1:
                    raise ValueError("Invalid dataset archive: must contain exactly one dataset directory")

                extracted_dir = extracted_dirs[0]

                # Validate structure
                items_file = extracted_dir / self.ITEMS_FILE
                audio_dir = extracted_dir / self.AUDIO_DIR
                voice_prompts_dir = extracted_dir / self.VOICE_PROMPTS_DIR

                if not items_file.exists():
                    raise ValueError(f"Invalid dataset archive: missing {self.ITEMS_FILE}")
                if not audio_dir.exists() or not audio_dir.is_dir():
                    raise ValueError(f"Invalid dataset archive: missing {self.AUDIO_DIR} directory")
                if not voice_prompts_dir.exists() or not voice_prompts_dir.is_dir():
                    raise ValueError(f"Invalid dataset archive: missing {self.VOICE_PROMPTS_DIR} directory")

                # Load items to validate and count
                temp_items = []
                with open(items_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            item_data = json.loads(line)
                            item = DatasetItem.from_dict(item_data)
                            item.validate()
                            temp_items.append(item)
                        except (json.JSONDecodeError, ValueError) as e:
                            raise ValueError(f"Invalid item at line {line_num}: {str(e)}")

                # Use provided name or extract from directory name
                if dataset_name:
                    name = dataset_name.strip()
                else:
                    name = extracted_dir.name.replace('-', ' ').title()

                # Generate unique dataset ID
                dataset_id = self._generate_dataset_id(name)
                new_dataset_dir = self._get_dataset_dir(dataset_id)

                # Copy dataset directory to datasets directory
                shutil.copytree(extracted_dir, new_dataset_dir)

                # Create dataset metadata
                dataset = Dataset.create(dataset_id, name, "Imported dataset")
                dataset.update(item_count=len(temp_items))

                # Save to metadata file
                metadata = self._load_metadata()
                metadata[dataset_id] = dataset.to_dict()
                self._save_metadata(metadata)

                return dataset

            except Exception as e:
                # Cleanup if import failed
                dataset_dir = self._get_dataset_dir(dataset_id) if 'dataset_id' in locals() else None
                if dataset_dir and dataset_dir.exists():
                    self.file_handler.delete_directory(dataset_dir)
                raise RuntimeError(f"Failed to import dataset: {str(e)}")
