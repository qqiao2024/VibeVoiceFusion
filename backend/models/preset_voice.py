"""
Preset voice data models - metadata parsed from filename convention
Filename format: {language}-{name}_{gender}[_bgm].wav
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import re


@dataclass
class PresetVoice:
    """Preset voice metadata model - parsed from filename"""
    filename: str       # Full filename: "en-Alice_woman.wav"
    language: str       # Language code: "en", "zh", "in"
    name: str           # Voice name: "Alice"
    gender: str         # Gender: "man", "woman"
    has_bgm: bool       # Whether has background music
    display_name: str   # Localized display name: "Alice (English, Female)"

    def to_dict(self) -> Dict[str, Any]:
        """Convert preset voice to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PresetVoice':
        """Create preset voice from dictionary"""
        return cls(**data)

    @classmethod
    def from_filename(cls, filename: str, locale: str = 'en') -> Optional['PresetVoice']:
        """
        Parse preset voice metadata from filename

        Filename convention: {language}-{name}_{gender}[_bgm].wav

        Args:
            filename: Filename like "en-Alice_woman.wav" or "zh-Bowen_man_bgm.wav"
            locale: Locale for display name generation

        Returns:
            PresetVoice object or None if parsing fails
        """
        # Pattern: {lang}-{name}_{gender}[_bgm].wav
        pattern = r'^([a-z]{2})-([A-Za-z]+)_(man|woman)(_bgm)?\.wav$'
        match = re.match(pattern, filename)

        if not match:
            return None

        language = match.group(1)
        name = match.group(2)
        gender = match.group(3)
        has_bgm = match.group(4) is not None

        # Generate display name
        display_name = cls._generate_display_name(name, language, gender, locale)

        return cls(
            filename=filename,
            language=language,
            name=name,
            gender=gender,
            has_bgm=has_bgm,
            display_name=display_name
        )

    @staticmethod
    def _generate_display_name(name: str, language: str, gender: str, locale: str = 'en') -> str:
        """Generate localized display name"""
        language_names = {
            'en': {'en': 'English', 'zh': 'Chinese', 'in': 'Indian English'},
            'zh': {'en': '英语', 'zh': '中文', 'in': '印度英语'}
        }

        gender_names = {
            'en': {'man': 'Male', 'woman': 'Female'},
            'zh': {'man': '男声', 'woman': '女声'}
        }

        lang_display = language_names.get(locale, language_names['en']).get(language, language.upper())
        gender_display = gender_names.get(locale, gender_names['en']).get(gender, gender)

        return f"{name} ({lang_display}, {gender_display})"

    @staticmethod
    def generate_filename(name: str, language: str, gender: str, has_bgm: bool) -> str:
        """
        Generate filename from metadata

        Args:
            name: Voice name (will be capitalized)
            language: Language code (en, zh, in)
            gender: Gender (man, woman)
            has_bgm: Whether has background music

        Returns:
            Filename like "en-Alice_woman.wav" or "zh-Bowen_man_bgm.wav"
        """
        # Capitalize name and clean it (only allow letters)
        clean_name = ''.join(c for c in name if c.isalpha())
        clean_name = clean_name.capitalize()

        bgm_suffix = '_bgm' if has_bgm else ''
        return f"{language}-{clean_name}_{gender}{bgm_suffix}.wav"
