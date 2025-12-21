"""
Preset voice management service - metadata parsed from filenames

Filename convention: {language}-{name}_{gender}[_bgm].wav
Examples:
  - en-Alice_woman.wav
  - zh-Bowen_man.wav
  - en-Mary_woman_bgm.wav
"""
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from werkzeug.datastructures import FileStorage

from backend.models.preset_voice import PresetVoice


class PresetVoiceService:
    """Service for managing preset voice samples with filename-based metadata"""

    SUPPORTED_LANGUAGES = {'zh', 'en', 'in'}
    SUPPORTED_GENDERS = {'man', 'woman'}

    # Allowed input formats for conversion
    ALLOWED_INPUT_EXTENSIONS = {'.wav', '.mp3', '.m4a', '.flac', '.webm', '.ogg', '.aac'}

    LANGUAGE_NAMES = {
        'en': {'en': 'English', 'zh': 'Chinese', 'in': 'Indian English'},
        'zh': {'en': '英语', 'zh': '中文', 'in': '印度英语'}
    }

    def __init__(self, preset_dir: Path):
        """
        Initialize preset voice service

        Args:
            preset_dir: Path to preset voices directory
        """
        self.preset_dir = Path(preset_dir)
        # Ensure preset directory exists
        self.preset_dir.mkdir(parents=True, exist_ok=True)

    def _validate_audio_file(self, filename: str) -> bool:
        """Validate audio file extension"""
        ext = Path(filename).suffix.lower()
        return ext in self.ALLOWED_INPUT_EXTENSIONS

    def _validate_language(self, language: str) -> bool:
        """Validate language code"""
        return language in self.SUPPORTED_LANGUAGES

    def _validate_gender(self, gender: str) -> bool:
        """Validate gender"""
        return gender in self.SUPPORTED_GENDERS

    def _validate_name(self, name: str) -> bool:
        """Validate voice name (only letters allowed)"""
        return bool(name) and name.replace(' ', '').isalpha()

    def _scan_presets(self, locale: str = 'en') -> List[PresetVoice]:
        """
        Scan preset directory and parse all valid preset voice files

        Args:
            locale: Locale for display names

        Returns:
            List of PresetVoice objects
        """
        presets = []
        if not self.preset_dir.exists():
            return presets

        for file_path in self.preset_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.wav':
                preset = PresetVoice.from_filename(file_path.name, locale)
                if preset:
                    presets.append(preset)

        # Sort by name
        presets.sort(key=lambda p: p.name.lower())
        return presets

    def list_presets(
        self,
        language: Optional[str] = None,
        gender: Optional[str] = None,
        has_bgm: Optional[bool] = None,
        offset: int = 0,
        limit: Optional[int] = None,
        locale: str = 'en'
    ) -> Tuple[List[PresetVoice], int]:
        """
        List all preset voices with optional filtering and pagination

        Args:
            language: Filter by language code (en, zh, in)
            gender: Filter by gender (man, woman)
            has_bgm: Filter by BGM presence
            offset: Number of items to skip
            limit: Maximum number of items to return (None for all)
            locale: Locale for display names (en, zh)

        Returns:
            Tuple of (List of PresetVoice objects, total count matching filters)
        """
        presets = self._scan_presets(locale)

        # Apply filters
        if language is not None:
            presets = [p for p in presets if p.language == language]
        if gender is not None:
            presets = [p for p in presets if p.gender == gender]
        if has_bgm is not None:
            presets = [p for p in presets if p.has_bgm == has_bgm]

        total = len(presets)

        # Apply pagination
        if limit is not None:
            presets = presets[offset:offset + limit]
        elif offset > 0:
            presets = presets[offset:]

        return presets, total

    def get_preset(self, filename: str, locale: str = 'en') -> Optional[PresetVoice]:
        """
        Get preset voice by filename

        Args:
            filename: Preset filename (e.g., "en-Alice_woman.wav")
            locale: Locale for display name

        Returns:
            PresetVoice object or None if not found
        """
        file_path = self.preset_dir / filename
        if file_path.exists() and file_path.is_file():
            return PresetVoice.from_filename(filename, locale)
        return None

    def get_preset_path(self, filename: str) -> Optional[Path]:
        """
        Get full path to preset voice file

        Args:
            filename: Voice filename

        Returns:
            Path to voice file or None if not found
        """
        file_path = self.preset_dir / filename
        if file_path.exists() and file_path.is_file():
            return file_path
        return None

    def add_preset(
        self,
        name: str,
        language: str,
        gender: str,
        has_bgm: bool,
        voice_file: FileStorage
    ) -> PresetVoice:
        """
        Add a new preset voice by saving with naming convention

        The file will be converted to WAV format and saved as:
        {language}-{name}_{gender}[_bgm].wav

        Args:
            name: Voice name (letters only, will be capitalized)
            language: Language code (zh, en, in)
            gender: Gender (man, woman)
            has_bgm: Whether has background music
            voice_file: Uploaded voice file

        Returns:
            Created PresetVoice object

        Raises:
            ValueError: If validation fails
            RuntimeError: If operation fails
        """
        # Validation
        if not name or not name.strip():
            raise ValueError("Voice name is required")

        clean_name = name.strip()
        if not self._validate_name(clean_name):
            raise ValueError("Voice name must contain only letters")

        if not self._validate_language(language):
            raise ValueError(f"Invalid language. Supported: {', '.join(sorted(self.SUPPORTED_LANGUAGES))}")

        if not self._validate_gender(gender):
            raise ValueError(f"Invalid gender. Supported: {', '.join(sorted(self.SUPPORTED_GENDERS))}")

        if not voice_file or not voice_file.filename:
            raise ValueError("Voice file is required")

        if not self._validate_audio_file(voice_file.filename):
            raise ValueError(f"Invalid audio file. Allowed extensions: {', '.join(sorted(self.ALLOWED_INPUT_EXTENSIONS))}")

        # Generate target filename
        target_filename = PresetVoice.generate_filename(clean_name, language, gender, has_bgm)
        target_path = self.preset_dir / target_filename

        # Check if preset already exists
        if target_path.exists():
            raise ValueError(f"Preset voice '{target_filename}' already exists")

        # Save and convert to WAV
        source_ext = Path(voice_file.filename).suffix.lower()
        temp_path = self.preset_dir / f"_temp_{target_filename.replace('.wav', source_ext)}"

        try:
            # Save uploaded file temporarily
            voice_file.save(str(temp_path))

            # Convert to WAV if needed
            if source_ext != '.wav':
                self._convert_to_wav(temp_path, target_path)
                temp_path.unlink()  # Remove temp file
            else:
                # Just rename if already WAV
                temp_path.rename(target_path)

            # Return parsed preset
            preset = PresetVoice.from_filename(target_filename)
            if not preset:
                raise RuntimeError("Failed to parse created preset")
            return preset

        except Exception as e:
            # Cleanup on failure
            if temp_path.exists():
                temp_path.unlink()
            if target_path.exists():
                target_path.unlink()
            raise RuntimeError(f"Failed to add preset voice: {str(e)}")

    def _convert_to_wav(self, source_path: Path, target_path: Path) -> None:
        """
        Convert audio file to WAV format using ffmpeg

        Args:
            source_path: Source audio file path
            target_path: Target WAV file path

        Raises:
            RuntimeError: If conversion fails
        """
        try:
            result = subprocess.run([
                'ffmpeg', '-y', '-i', str(source_path),
                '-acodec', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '1',
                str(target_path)
            ], capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio conversion timed out")
        except FileNotFoundError:
            raise RuntimeError("ffmpeg not found. Please install ffmpeg.")

    def delete_preset(self, filename: str) -> bool:
        """
        Delete preset voice file

        Args:
            filename: Preset filename (e.g., "en-Alice_woman.wav")

        Returns:
            True if deleted successfully, False if not found
        """
        file_path = self.preset_dir / filename

        if not file_path.exists():
            return False

        # Validate filename format before deletion
        preset = PresetVoice.from_filename(filename)
        if not preset:
            return False

        try:
            file_path.unlink()
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to delete preset voice: {str(e)}")

    def batch_delete_presets(self, filenames: List[str]) -> Tuple[List[str], List[str]]:
        """
        Delete multiple preset voices

        Args:
            filenames: List of preset filenames to delete

        Returns:
            Tuple of (successfully deleted filenames, failed filenames)
        """
        deleted = []
        failed = []

        for filename in filenames:
            try:
                if self.delete_preset(filename):
                    deleted.append(filename)
                else:
                    failed.append(filename)
            except Exception:
                failed.append(filename)

        return deleted, failed

    def get_available_languages(self, locale: str = 'en') -> List[Dict[str, Any]]:
        """
        Get list of available languages with counts

        Args:
            locale: Locale for language names (en, zh)

        Returns:
            List of dictionaries with language code, name, and count
        """
        presets = self._scan_presets(locale)
        lang_counts: Dict[str, Dict[str, Any]] = {}

        lang_names = self.LANGUAGE_NAMES.get(locale, self.LANGUAGE_NAMES['en'])

        for preset in presets:
            if preset.language not in lang_counts:
                lang_counts[preset.language] = {
                    'code': preset.language,
                    'name': lang_names.get(preset.language, preset.language.upper()),
                    'count': 0
                }
            lang_counts[preset.language]['count'] += 1

        return list(lang_counts.values())
