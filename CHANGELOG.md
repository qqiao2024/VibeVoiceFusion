# Changelog

All notable changes to VibeVoice will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v2.2.0] - 2026-01-09

### Added

- **Quick Generation**: Simplified voice generation workflow without project context
  - One-click generation with preset voice selection
  - Support for multiple voice prompt files
  - Multiple prompt voices displayed in generation history detail view
  - Task indicator for quick generation status
  - Per-item progress tracking for each generating voice

- **Navigation Enhancement**: Click logo to return to home page

### Fixed

- Task indicator display bugs in quick generation
- Card status not updating in time
- Styling consistency for deleting generation history

---

## [v2.1.0] - 2025-12-28

### Added

- **Narration Mode Editor**: New editing mode for single-speaker narration content
  - Support for changing narrator
  - Plain text editing without speaker prefixes

- **Preset Voices Management**: Manage preset voice samples for quick speaker creation

- **Auto Version Generation**: Frontend version automatically generated from git

### Fixed

- Offloading config save issue during inference
- Offloading config error
- Duplicated speaker ID issue
- Missing tags in Docker repository
- Dockerfile dependency errors

---

## [v2.0.0] - 2025-12-19

### Added

- **Fine-Tuning Support**: Full LoRA training workflow with real-time metrics
  - Training page with live progress bars and configuration options
  - Training metrics charts (Loss/LR/Timing) with 5-second auto-refresh
  - Support for layer offloading presets (Balanced/Aggressive/Extreme)
  - Gradient accumulation steps and checkpoint saving per epoch
  - TensorBoard metrics reader for training visualization

- **Dataset Management**: Complete dataset CRUD operations
  - Dataset list and detail pages with pagination
  - Import/Export functionality for datasets
  - JSONL format for efficient line-by-line operations
  - Scripts for generating datasets from Mozilla Common Voice and KeSpeech

- **Multi-Generation**: Batch generation with different random seeds
  - Generate 2-20 audio variations in a single request
  - Per-item progress tracking with individual audio players
  - Expandable history view with aggregate statistics

- **LoRA Inference**: Apply trained LoRA models during voice generation
  - Select LoRA model from training output directory
  - Configurable LoRA weight (0-1]

- **Unified Task API**: Single endpoint for checking any running task (inference or training)

- **Preset Voice Feature**: Quick speaker creation from preset voice samples

- **Audio Denoising**: Scripts for audio denoising with DeepFilter

- **Dataset Processing Scripts**:
  - Script for ASR-SCCantDuSC (Scripted Chinese Cantonese Daily-use Speech Corpus)
  - Script for Mozilla Common Voice datasets

### Changed

- Improved training completion UI with better status display
- Enhanced training history list to display all information regardless of success/failure
- Better estimated training time calculation
- Increased file upload limits (500MB configurable)
- Project-scoped current generation and training API endpoints

### Fixed

- Training metadata update error
- Generated voices having same name in batch generation
- Seeds reset issue with multi-generation
- CUDA resource cleanup when training finishes or fails
- Invalid audio and voice_prompts field values in datasets.jsonl
- Delete training history validation
- OOM error handling with specific error messages
- Various npm build errors and UI style issues

## [v1.0.0] - 2025-11-14

### Added

- **Core TTS Model**: AR + diffusion architecture for multi-speaker text-to-speech synthesis
  - Float8 inference support for optimized performance
  - Mono model file inference support

- **Full-Stack Web Application**:
  - Next.js frontend with responsive UI
  - Flask backend with RESTful API
  - Static export for production deployment

- **Project Management**: Create and manage multiple voice projects

- **Speaker Voice Management**:
  - Upload and manage speaker voices
  - Voice recording directly in browser
  - Auto-assigned speaker names ("Speaker 1", etc.)

- **Dialog Editor**: 4-panel layout for creating and editing dialog sessions
  - Clickable session names in generation history
  - Session navigation to voice editor

- **Voice Generation**:
  - Live progress monitoring
  - Generation history with pagination
  - Audio playback and download
  - Task icon notification in navigation

- **Layer Offloading**: VRAM optimization for GPU memory constraints
  - Configurable number of layers for GPU/CPU
  - Async transfers with ThreadPoolExecutor
  - Smart cache clearing for performance

- **Internationalization (i18n)**: Full bilingual support
  - English and Chinese languages
  - Auto-detection via browser settings
  - Persistence in localStorage

- **Docker Support**:
  - Dockerfile for containerized deployment
  - GPU support with nvidia-docker

- **Documentation**:
  - Comprehensive API documentation
  - Architecture diagrams with Mermaid
  - Offloading configuration guide

### Fixed

- Invisible text color in browser dark theme
- Frontend project selection issues
- Refresh page navigation bugs
- Layout issues in various components
- Scripts not starting with ID 1
- Various typos and documentation errors

[v2.2.0]: https://github.com/zhao-kun/vibevoice/compare/v2.1.0...v2.2.0
[v2.1.0]: https://github.com/zhao-kun/vibevoice/compare/v2.0.0...v2.1.0
[v2.0.0]: https://github.com/zhao-kun/vibevoice/compare/v1.0.0...v2.0.0
[v1.0.0]: https://github.com/zhao-kun/vibevoice/releases/tag/v1.0.0
