"""
Preset voice management service - handles preset voice discovery and metadata
"""
import re
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class PresetVoice:
    """Preset voice metadata model"""
    filename: str           # Original filename (e.g., "en-Alice_woman.wav")
    language: str           # Language code (e.g., "en", "zh", "in")
    name: str               # Voice name (e.g., "Alice", "Bowen")
    gender: str             # Gender (e.g., "man", "woman")
    has_bgm: bool           # Whether has background music
    display_name: str       # Human-readable name (e.g., "Alice (English, Female)")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PresetVoiceService:
    """Service for managing preset voice samples"""

    # Filename pattern: {lang}-{name}_{gender}[_bgm].wav
    FILENAME_PATTERN = re.compile(
        r'^(?P<lang>[a-z]{2})-(?P<name>[A-Za-z]+)_(?P<gender>man|woman)(?P<bgm>_bgm)?\.wav$'
    )

    LANGUAGE_NAMES = {
        'en': 'English',
        'zh': 'Chinese',
        'in': 'Indian English'
    }

    LANGUAGE_NAMES_ZH = {
        'en': '英语',
        'zh': '中文',
        'in': '印度英语'
    }

    def __init__(self, preset_dir: Path):
        self.preset_dir = Path(preset_dir)

    def _parse_filename(self, filename: str, locale: str = 'en') -> Optional[PresetVoice]:
        """Parse preset voice metadata from filename"""
        match = self.FILENAME_PATTERN.match(filename)
        if not match:
            return None

        lang = match.group('lang')
        name = match.group('name')
        gender = match.group('gender')
        has_bgm = match.group('bgm') is not None

        # Get localized language name
        if locale == 'zh':
            lang_name = self.LANGUAGE_NAMES_ZH.get(lang, lang.upper())
            gender_display = '女' if gender == 'woman' else '男'
            bgm_suffix = ', 带BGM' if has_bgm else ''
        else:
            lang_name = self.LANGUAGE_NAMES.get(lang, lang.upper())
            gender_display = 'Female' if gender == 'woman' else 'Male'
            bgm_suffix = ', with BGM' if has_bgm else ''

        display_name = f"{name} ({lang_name}, {gender_display}{bgm_suffix})"

        return PresetVoice(
            filename=filename,
            language=lang,
            name=name,
            gender=gender,
            has_bgm=has_bgm,
            display_name=display_name
        )

    def list_presets(
        self,
        language: Optional[str] = None,
        gender: Optional[str] = None,
        has_bgm: Optional[bool] = None,
        locale: str = 'en'
    ) -> List[PresetVoice]:
        """
        List all preset voices with optional filtering

        Args:
            language: Filter by language code (en, zh, in)
            gender: Filter by gender (man, woman)
            has_bgm: Filter by BGM presence
            locale: Locale for display names (en, zh)

        Returns:
            List of PresetVoice objects
        """
        if not self.preset_dir.exists():
            return []

        presets = []
        for file_path in self.preset_dir.glob('*.wav'):
            preset = self._parse_filename(file_path.name, locale)
            if preset:
                # Apply filters
                if language and preset.language != language:
                    continue
                if gender and preset.gender != gender:
                    continue
                if has_bgm is not None and preset.has_bgm != has_bgm:
                    continue
                presets.append(preset)

        # Sort by language, then name
        presets.sort(key=lambda p: (p.language, p.name))
        return presets

    def get_preset(self, filename: str, locale: str = 'en') -> Optional[PresetVoice]:
        """Get preset voice by filename"""
        file_path = self.preset_dir / filename
        if not file_path.exists():
            return None
        return self._parse_filename(filename, locale)

    def get_preset_path(self, filename: str) -> Optional[Path]:
        """Get full path to preset voice file"""
        file_path = self.preset_dir / filename
        if file_path.exists():
            return file_path
        return None

    def get_available_languages(self, locale: str = 'en') -> List[Dict[str, Any]]:
        """
        Get list of available languages with counts

        Args:
            locale: Locale for language names (en, zh)

        Returns:
            List of dictionaries with language code, name, and count
        """
        presets = self.list_presets(locale=locale)
        lang_counts: Dict[str, Dict[str, Any]] = {}

        lang_names = self.LANGUAGE_NAMES_ZH if locale == 'zh' else self.LANGUAGE_NAMES

        for preset in presets:
            if preset.language not in lang_counts:
                lang_counts[preset.language] = {
                    'code': preset.language,
                    'name': lang_names.get(preset.language, preset.language.upper()),
                    'count': 0
                }
            lang_counts[preset.language]['count'] += 1

        return list(lang_counts.values())
