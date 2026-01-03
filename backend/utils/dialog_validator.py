"""
Dialog text parser and validator utilities
"""
import re
from typing import List, Set, Tuple, Optional
from pathlib import Path


class DialogValidator:
    """Utility class for parsing and validating dialog text files"""

    # Pattern: "Speaker N: dialog text" where N is a positive integer
    DIALOG_LINE_PATTERN = re.compile(r'^Speaker\s+(\d+):\s*(.+)$')

    @staticmethod
    def parse_narration_text(text: str) -> List[str]:
        """
        Parse plain text for narration mode.
        Returns list of non-empty paragraphs.

        Args:
            text: Plain text content (no Speaker N: formatting required)

        Returns:
            List of text paragraphs (non-empty lines/blocks)
        """
        if not text or not text.strip():
            return []

        # Split by double newlines (paragraph separator) or single newlines
        # and filter out empty paragraphs
        lines = text.strip().split('\n')
        paragraphs = []
        current_paragraph = []

        for line in lines:
            stripped = line.strip()
            if stripped:
                current_paragraph.append(stripped)
            elif current_paragraph:
                # Empty line - save accumulated paragraph
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []

        # Don't forget the last paragraph
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))

        return paragraphs

    @staticmethod
    def validate_narration_text(text: str, narrator_speaker_id: str,
                                 valid_speaker_ids: Set[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate narration mode text and narrator speaker.

        Args:
            text: Plain text content
            narrator_speaker_id: The speaker ID to use for narration (e.g., "Speaker 1")
            valid_speaker_ids: Set of valid speaker IDs from speaker management system

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Narrator speaker ID is required for narration mode
        if not narrator_speaker_id:
            return False, "Narrator speaker ID is required for narration mode"

        # Validate narrator speaker exists
        if valid_speaker_ids and narrator_speaker_id not in valid_speaker_ids:
            return False, f"Invalid narrator speaker ID: {narrator_speaker_id}"

        # Parse narration text (can be empty)
        paragraphs = DialogValidator.parse_narration_text(text)

        # Text can be empty - user can add later
        return True, None

    @staticmethod
    def convert_narration_to_dialog(text: str, narrator_speaker_id: str) -> List[Tuple[str, str]]:
        """
        Convert narration text to dialog format (speaker_id, text) tuples.

        Args:
            text: Plain text content
            narrator_speaker_id: The speaker ID to assign to all text (e.g., "Speaker 1")

        Returns:
            List of (speaker_id, dialog_text) tuples
        """
        paragraphs = DialogValidator.parse_narration_text(text)
        return [(narrator_speaker_id, paragraph) for paragraph in paragraphs]

    @staticmethod
    def parse_dialog_text(text: str) -> List[Tuple[str, str]]:
        """
        Parse dialog text into list of (speaker_id, dialog_text) tuples

        Args:
            text: Dialog text content

        Returns:
            List of (speaker_id, dialog_text) tuples

        Raises:
            ValueError: If text format is invalid
        """
        # Allow empty text - return empty list
        if not text or not text.strip():
            return []

        lines = text.strip().split('\n')
        dialogs = []
        current_line_num = 0

        for line in lines:
            current_line_num += 1

            # Skip empty lines (they are separators)
            if not line.strip():
                continue

            # Match dialog line pattern
            match = DialogValidator.DIALOG_LINE_PATTERN.match(line)
            if not match:
                raise ValueError(
                    f"Invalid dialog format at line {current_line_num}: '{line}'. "
                    f"Expected format: 'Speaker N: dialog text'"
                )

            speaker_num = match.group(1)
            speaker_id = f"Speaker {speaker_num}"
            dialog_text = match.group(2).strip()

            if not dialog_text:
                raise ValueError(
                    f"Dialog text cannot be empty at line {current_line_num} for {speaker_id}"
                )

            dialogs.append((speaker_id, dialog_text))

        # Allow empty dialogs - user can add them later
        return dialogs

    @staticmethod
    def extract_speaker_ids(text: str) -> Set[str]:
        """
        Extract all unique speaker IDs from dialog text

        Args:
            text: Dialog text content

        Returns:
            Set of speaker IDs (e.g., {"Speaker 1", "Speaker 2"})

        Raises:
            ValueError: If text format is invalid
        """
        dialogs = DialogValidator.parse_dialog_text(text)
        return {speaker_id for speaker_id, _ in dialogs}

    @staticmethod
    def validate_speaker_ids(text: str, valid_speaker_ids: Set[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate that all speaker IDs in text exist in the valid set

        Args:
            text: Dialog text content
            valid_speaker_ids: Set of valid speaker IDs from speaker management system

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            used_speaker_ids = DialogValidator.extract_speaker_ids(text)
        except ValueError as e:
            return False, str(e)

        # Check for invalid speaker IDs
        invalid_speakers = used_speaker_ids - valid_speaker_ids
        if invalid_speakers:
            return False, f"Invalid speaker IDs found: {', '.join(sorted(invalid_speakers))}"

        return True, None

    @staticmethod
    def format_dialog_text(dialogs: List[Tuple[str, str]]) -> str:
        """
        Format list of (speaker_id, dialog_text) tuples into dialog text

        Args:
            dialogs: List of (speaker_id, dialog_text) tuples

        Returns:
            Formatted dialog text string
        """
        lines = []
        for speaker_id, dialog_text in dialogs:
            lines.append(f"{speaker_id}: {dialog_text}")
            lines.append("")  # Empty line separator

        # Remove trailing empty line
        return '\n'.join(lines).rstrip() + '\n'

    @staticmethod
    def read_and_validate_file(file_path: Path, valid_speaker_ids: Set[str]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Read and validate a dialog file

        Args:
            file_path: Path to dialog text file
            valid_speaker_ids: Set of valid speaker IDs

        Returns:
            Tuple of (is_valid, error_message, file_content)
        """
        try:
            if not file_path.exists():
                return False, "File does not exist", None

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            is_valid, error_msg = DialogValidator.validate_speaker_ids(content, valid_speaker_ids)
            return is_valid, error_msg, content

        except Exception as e:
            return False, f"Failed to read file: {str(e)}", None
