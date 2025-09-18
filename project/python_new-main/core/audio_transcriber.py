"""
Audio transcription utilities for the Travel Assistant.
Attempts to use faster-whisper if available, otherwise falls back to openai-whisper.
Both options require ffmpeg to be available on the system PATH.
"""
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

class AudioTranscriber:
    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._backend = None  # 'faster-whisper' | 'whisper'
        self._model = None
        self._initialized = False

    def _init_backend(self):
        # Try faster-whisper first
        try:
            from faster_whisper import WhisperModel  # type: ignore
            self._model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            self._backend = 'faster-whisper'
            logger.info(f"AudioTranscriber using faster-whisper ({self.model_size})")
            return
        except Exception as e:
            logger.info(f"faster-whisper not available or failed to load: {e}")
        # Fallback to openai-whisper
        try:
            import whisper  # type: ignore
            self._model = whisper.load_model(self.model_size)
            self._backend = 'whisper'
            logger.info(f"AudioTranscriber using whisper ({self.model_size})")
            return
        except Exception as e:
            logger.warning(f"openai-whisper not available or failed to load: {e}")
            self._backend = None
            self._model = None

    def is_available(self) -> bool:
        return self._backend is not None and self._model is not None

    def transcribe_file(self, file_path: str, language: Optional[str] = None) -> str:
        if not self._initialized:
            self._init_backend()
            self._initialized = True
        if not self.is_available():
            raise RuntimeError(
                "No transcription backend available. Install 'faster-whisper' or 'openai-whisper' and ensure ffmpeg is installed and on PATH."
            )
        if self._backend == 'faster-whisper':
            return self._transcribe_faster_whisper(file_path, language)
        else:
            return self._transcribe_whisper(file_path, language)

    def _transcribe_faster_whisper(self, file_path: str, language: Optional[str]) -> str:
        assert self._backend == 'faster-whisper' and self._model is not None
        try:
            segments, info = self._model.transcribe(file_path, language=language)
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
            return "\n".join([t for t in text_parts if t])
        except Exception as e:
            logger.error(f"faster-whisper transcription failed: {e}")
            raise

    def _transcribe_whisper(self, file_path: str, language: Optional[str]) -> str:
        assert self._backend == 'whisper' and self._model is not None
        try:
            import whisper  # type: ignore
            result = self._model.transcribe(file_path, language=language)
            return (result.get('text') or '').strip()
        except Exception as e:
            logger.error(f"whisper transcription failed: {e}")
            raise

# Singleton
audio_transcriber = AudioTranscriber(model_size=os.getenv("WHISPER_MODEL", "base"))
