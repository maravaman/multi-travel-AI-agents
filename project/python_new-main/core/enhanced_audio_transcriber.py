"""
Enhanced Audio Transcription System with Robust Error Handling and UI Progress Tracking
Designed to handle audio uploads reliably and provide user feedback
"""

import os
import logging
import tempfile
import shutil
import threading
from typing import Optional, Dict, Any, Callable, Union, List
from pathlib import Path
import time
from enum import Enum

logger = logging.getLogger(__name__)

class TranscriptionStatus(Enum):
    """Transcription status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TranscriptionProgress:
    """Progress tracking for transcription operations"""
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = TranscriptionStatus.PENDING
        self.progress_percent = 0
        self.message = "Initializing transcription..."
        self.result = None
        self.error = None
        self.start_time = time.time()
        self.end_time = None
        self.file_info = {}
    
    def update(self, status: TranscriptionStatus = None, progress: int = None, message: str = None):
        """Update progress information"""
        if status:
            self.status = status
        if progress is not None:
            self.progress_percent = max(0, min(100, progress))
        if message:
            self.message = message
        
        if status in [TranscriptionStatus.COMPLETED, TranscriptionStatus.FAILED, TranscriptionStatus.CANCELLED]:
            self.end_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert progress to dictionary for API responses"""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "duration": (self.end_time or time.time()) - self.start_time,
            "file_info": self.file_info
        }

class EnhancedAudioTranscriber:
    """
    Enhanced audio transcription with robust error handling and progress tracking
    """
    
    def __init__(self):
        self.progress_tracker = {}  # job_id -> TranscriptionProgress
        self.max_file_size_mb = 25  # Maximum file size in MB
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.webm', '.mp4']
        self.temp_dir = Path(tempfile.gettempdir()) / "travel_transcription"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize transcription engines
        self.whisper_model = None
        self.faster_whisper_model = None
        self.openai_client = None
        
        # Check available transcription methods
        self._check_available_engines()
        
        logger.info("✅ Enhanced Audio Transcriber initialized")
    
    def _check_ffmpeg_availability(self) -> bool:
        """Check if ffmpeg is available in the system"""
        try:
            import subprocess
            result = subprocess.run(["ffmpeg", "-version"], 
                                  capture_output=True, 
                                  timeout=5,
                                  text=True)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError, OSError):
            return False
    
    def _check_available_engines(self):
        """Check which transcription engines are available"""
        self.available_engines = []
        ffmpeg_available = self._check_ffmpeg_availability()
        
        if not ffmpeg_available:
            logger.error("❌ ffmpeg not found! Whisper-based transcription will not work.")
            logger.error("   To fix this, install ffmpeg:")
            logger.error("   - Windows: Run PowerShell as Admin and execute 'choco install ffmpeg'")
            logger.error("   - Or download from https://ffmpeg.org/download.html")
            logger.error("   - Or use 'winget install ffmpeg' (Windows 10/11)")
        
        # Check faster-whisper
        try:
            from faster_whisper import WhisperModel
            if ffmpeg_available:
                self.available_engines.append("faster_whisper")
                logger.info("✅ faster-whisper available")
            else:
                logger.warning("⚠️ faster-whisper available but ffmpeg missing")
        except ImportError:
            logger.warning("⚠️ faster-whisper not available")
        
        # Check OpenAI Whisper
        try:
            import whisper
            if ffmpeg_available:
                self.available_engines.append("whisper")
                logger.info("✅ OpenAI Whisper available")
            else:
                logger.warning("⚠️ OpenAI Whisper available but ffmpeg missing")
        except ImportError:
            logger.warning("⚠️ OpenAI Whisper not available")
        
        # Check OpenAI API
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.available_engines.append("openai_api")
                logger.info("✅ OpenAI API available")
            else:
                logger.info("ℹ️ OpenAI API key not found")
        except ImportError:
            logger.warning("⚠️ OpenAI API not available")
        
        if not self.available_engines:
            logger.error("❌ No transcription engines available")
        else:
            logger.info(f"📊 Available engines: {', '.join(self.available_engines)}")
    
    def _validate_file_access(self, file_path: Path) -> Dict[str, Any]:
        """Validate file access and return detailed information"""
        validation_info = {
            "exists": file_path.exists(),
            "is_file": file_path.is_file() if file_path.exists() else False,
            "readable": False,
            "size": 0,
            "absolute_path": str(file_path.resolve()),
            "parent_exists": file_path.parent.exists() if file_path.exists() else False
        }
        
        try:
            if validation_info["exists"]:
                validation_info["size"] = file_path.stat().st_size
                # Test if file is readable
                with open(file_path, 'rb') as f:
                    f.read(1)  # Try to read first byte
                validation_info["readable"] = True
        except Exception as e:
            logger.warning(f"File access validation error: {e}")
            validation_info["error"] = str(e)
        
        return validation_info
    
    def validate_audio_file(self, file_path: Union[str, Path], max_size_mb: int = None) -> Dict[str, Any]:
        """Validate audio file format and size"""
        file_path = Path(file_path)
        max_size_mb = max_size_mb or self.max_file_size_mb
        
        validation_result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "file_info": {
                "name": file_path.name,
                "size_bytes": 0,
                "size_mb": 0,
                "extension": file_path.suffix.lower()
            }
        }
        
        try:
            # Check if file exists
            if not file_path.exists():
                validation_result["errors"].append("File does not exist")
                return validation_result
            
            # Get file info
            file_size = file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            validation_result["file_info"].update({
                "size_bytes": file_size,
                "size_mb": round(file_size_mb, 2)
            })
            
            # Check file size
            if file_size_mb > max_size_mb:
                validation_result["errors"].append(f"File size ({file_size_mb:.1f}MB) exceeds limit ({max_size_mb}MB)")
            
            # Check file format
            if file_path.suffix.lower() not in self.supported_formats:
                validation_result["errors"].append(f"Unsupported format '{file_path.suffix}'. Supported: {', '.join(self.supported_formats)}")
            
            # Check if file is empty
            if file_size == 0:
                validation_result["errors"].append("File is empty")
            
            # File is valid if no errors
            validation_result["valid"] = len(validation_result["errors"]) == 0
            
            # Add warnings for large files
            if file_size_mb > 10:
                validation_result["warnings"].append("Large file may take longer to process")
            
        except Exception as e:
            validation_result["errors"].append(f"File validation error: {str(e)}")
            logger.error(f"File validation error: {e}")
        
        return validation_result
    
    def start_transcription(self, file_path: Union[str, Path], language: str = "auto", 
                          engine: str = "auto") -> str:
        """
        Start transcription job and return job ID for tracking
        """
        job_id = f"transcribe_{int(time.time() * 1000)}"
        
        # Create progress tracker
        progress = TranscriptionProgress(job_id)
        self.progress_tracker[job_id] = progress
        
        # Validate file
        validation = self.validate_audio_file(file_path)
        progress.file_info = validation["file_info"]
        
        if not validation["valid"]:
            progress.update(
                status=TranscriptionStatus.FAILED,
                message=f"File validation failed: {'; '.join(validation['errors'])}"
            )
            progress.error = validation["errors"]
            return job_id
        
        # Start transcription in background thread
        thread = threading.Thread(
            target=self._transcribe_worker,
            args=(job_id, file_path, language, engine),
            name=f"Transcriber-{job_id}"
        )
        thread.daemon = True
        thread.start()
        
        progress.update(
            status=TranscriptionStatus.PROCESSING,
            progress=5,
            message="Starting transcription..."
        )
        
        logger.info(f"🎤 Started transcription job {job_id} for {Path(file_path).name}")
        return job_id
    
    def _transcribe_worker(self, job_id: str, file_path: Union[str, Path], 
                          language: str, engine: str):
        """Background worker for transcription"""
        progress = self.progress_tracker[job_id]
        file_path = Path(file_path)
        
        try:
            # Update progress
            progress.update(progress=10, message="Preparing audio file...")
            
            # Choose transcription engine
            selected_engine = self._select_engine(engine)
            if not selected_engine:
                raise Exception("No transcription engines available")
            
            progress.update(
                progress=20, 
                message=f"Using {selected_engine} engine..."
            )
            
            # Perform transcription based on engine
            if selected_engine == "faster_whisper":
                result = self._transcribe_with_faster_whisper(file_path, language, progress)
            elif selected_engine == "whisper":
                result = self._transcribe_with_whisper(file_path, language, progress)
            elif selected_engine == "openai_api":
                result = self._transcribe_with_openai_api(file_path, language, progress)
            else:
                raise Exception(f"Unknown engine: {selected_engine}")
            
            # Success
            progress.update(
                status=TranscriptionStatus.COMPLETED,
                progress=100,
                message="Transcription completed successfully"
            )
            progress.result = result
            
            logger.info(f"✅ Transcription job {job_id} completed successfully")
            
        except Exception as e:
            # Error handling
            progress.update(
                status=TranscriptionStatus.FAILED,
                progress=0,
                message=f"Transcription failed: {str(e)}"
            )
            progress.error = str(e)
            logger.error(f"❌ Transcription job {job_id} failed: {e}")
    
    def _select_engine(self, preferred_engine: str) -> Optional[str]:
        """Select the best available transcription engine"""
        if preferred_engine != "auto" and preferred_engine in self.available_engines:
            return preferred_engine
        
        # Auto-select based on priority
        engine_priority = ["faster_whisper", "whisper", "openai_api"]
        
        for engine in engine_priority:
            if engine in self.available_engines:
                return engine
        
        return None
    
    def _transcribe_with_faster_whisper(self, file_path: Path, language: str, 
                                      progress: TranscriptionProgress) -> Dict[str, Any]:
        """Transcribe using faster-whisper"""
        from faster_whisper import WhisperModel
        
        progress.update(progress=30, message="Loading faster-whisper model...")
        
        if not self.faster_whisper_model:
            # Use smaller model for better performance
            model_size = "base.en" if language == "en" else "base"
            self.faster_whisper_model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        progress.update(progress=50, message="Processing audio...")
        
        # Verify file exists and is accessible before proceeding
        file_access_info = self._validate_file_access(file_path)
        logger.info(f"File access validation: {file_access_info}")
        
        if not file_access_info["exists"]:
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        if not file_access_info["is_file"]:
            raise FileNotFoundError(f"Path is not a file: {file_path}")
            
        if not file_access_info["readable"]:
            error_msg = file_access_info.get("error", "Unknown access error")
            raise PermissionError(f"Cannot read audio file: {file_path} - {error_msg}")
        
        # Detect language if auto
        detect_language = language if language != "auto" else None
        
        # Convert path to absolute path string
        absolute_path = str(file_path.resolve())
        logger.info(f"Transcribing file with faster-whisper: {absolute_path}")
        logger.info(f"Original file_path: {file_path}")
        logger.info(f"File exists before transcription: {Path(absolute_path).exists()}")
        
        # Transcribe with error handling
        try:
            segments, info = self.faster_whisper_model.transcribe(
                absolute_path,
                language=detect_language,
                beam_size=5,
                temperature=0.0
            )
        except Exception as transcribe_error:
            logger.error(f"faster-whisper transcribe error: {transcribe_error}")
            logger.error(f"File exists during error: {Path(absolute_path).exists()}")
            raise
        
        progress.update(progress=80, message="Extracting text...")
        
        # Extract segments
        transcript_segments = []
        full_text = []
        
        for segment in segments:
            segment_data = {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip()
            }
            transcript_segments.append(segment_data)
            full_text.append(segment.text.strip())
        
        progress.update(progress=90, message="Finalizing results...")
        
        return {
            "engine": "faster_whisper",
            "language": info.language,
            "language_probability": round(info.language_probability, 2),
            "duration": round(info.duration, 2),
            "full_text": " ".join(full_text).strip(),
            "segments": transcript_segments,
            "word_count": len(" ".join(full_text).split()),
            "confidence": "high" if info.language_probability > 0.8 else "medium"
        }
    
    def _transcribe_with_whisper(self, file_path: Path, language: str, 
                                progress: TranscriptionProgress) -> Dict[str, Any]:
        """Transcribe using OpenAI Whisper"""
        import whisper
        
        progress.update(progress=30, message="Loading OpenAI Whisper model...")
        
        # Verify file exists and is accessible before proceeding
        file_access_info = self._validate_file_access(file_path)
        logger.info(f"File access validation: {file_access_info}")
        
        if not file_access_info["exists"]:
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        if not file_access_info["is_file"]:
            raise FileNotFoundError(f"Path is not a file: {file_path}")
            
        if not file_access_info["readable"]:
            error_msg = file_access_info.get("error", "Unknown access error")
            raise PermissionError(f"Cannot read audio file: {file_path} - {error_msg}")
        
        if not self.whisper_model:
            # Use base model for balance of speed and accuracy
            model_size = "base.en" if language == "en" else "base"
            self.whisper_model = whisper.load_model(model_size)
        
        progress.update(progress=50, message="Processing audio...")
        
        # Convert path to absolute path string to ensure Whisper can find it
        # Use forward slashes for better cross-platform compatibility
        absolute_path = str(file_path.resolve()).replace('\\', '/')
        logger.info(f"Transcribing file: {absolute_path}")
        logger.info(f"Original file_path: {file_path}")
        logger.info(f"Resolved path: {file_path.resolve()}")
        logger.info(f"File exists before transcription: {Path(absolute_path).exists()}")
        logger.info(f"File size before transcription: {Path(absolute_path).stat().st_size if Path(absolute_path).exists() else 'N/A'} bytes")
        
        # Verify file still exists just before transcription
        if not Path(absolute_path).exists():
            # Try with original path format as fallback
            original_absolute = str(file_path.resolve())
            if not Path(original_absolute).exists():
                raise FileNotFoundError(f"Audio file disappeared before transcription. Tried paths: {absolute_path}, {original_absolute}")
            else:
                absolute_path = original_absolute
                logger.info(f"Using original path format: {absolute_path}")
        
        # Transcribe with additional error handling
        # Try both path formats for maximum compatibility
        try:
            result = self.whisper_model.transcribe(
                absolute_path,
                language=language if language != "auto" else None,
                temperature=0.0,
                no_speech_threshold=0.6
            )
        except Exception as transcribe_error:
            logger.error(f"Whisper transcribe error: {transcribe_error}")
            logger.error(f"File exists during error: {Path(absolute_path).exists()}")
            
            # Check if this is likely an ffmpeg issue
            error_str = str(transcribe_error).lower()
            if "system cannot find the file" in error_str or "winerror 2" in error_str:
                # This is likely a missing ffmpeg issue
                if not self._check_ffmpeg_availability():
                    raise Exception(
                        "Audio transcription failed: ffmpeg is not installed or not in system PATH. "
                        "Please install ffmpeg: 1) Run PowerShell as Admin, 2) Execute 'choco install ffmpeg' or 'winget install ffmpeg', "
                        "3) Restart the application. Alternative: Download from https://ffmpeg.org/download.html"
                    )
            
            # Try with original Windows path format as fallback
            original_absolute = str(file_path.resolve())
            if absolute_path != original_absolute:
                logger.info(f"Retrying transcription with original path format: {original_absolute}")
                try:
                    result = self.whisper_model.transcribe(
                        original_absolute,
                        language=language if language != "auto" else None,
                        temperature=0.0,
                        no_speech_threshold=0.6
                    )
                    logger.info("Transcription succeeded with original path format")
                except Exception as retry_error:
                    logger.error(f"Retry with original path also failed: {retry_error}")
                    # Check for ffmpeg issue again
                    retry_error_str = str(retry_error).lower()
                    if "system cannot find the file" in retry_error_str or "winerror 2" in retry_error_str:
                        if not self._check_ffmpeg_availability():
                            raise Exception(
                                "Audio transcription failed: ffmpeg is not installed or not in system PATH. "
                                "Please install ffmpeg: 1) Run PowerShell as Admin, 2) Execute 'choco install ffmpeg' or 'winget install ffmpeg', "
                                "3) Restart the application. Alternative: Download from https://ffmpeg.org/download.html"
                            )
                    raise transcribe_error  # Raise the original error
            else:
                raise
        
        progress.update(progress=80, message="Extracting segments...")
        
        # Process segments
        transcript_segments = []
        
        for segment in result.get("segments", []):
            segment_data = {
                "start": round(segment["start"], 2),
                "end": round(segment["end"], 2),
                "text": segment["text"].strip()
            }
            transcript_segments.append(segment_data)
        
        progress.update(progress=90, message="Finalizing results...")
        
        return {
            "engine": "whisper",
            "language": result.get("language", "unknown"),
            "language_probability": 0.9,  # Whisper doesn't provide this
            "duration": max([s["end"] for s in transcript_segments]) if transcript_segments else 0,
            "full_text": result.get("text", "").strip(),
            "segments": transcript_segments,
            "word_count": len(result.get("text", "").split()),
            "confidence": "high"
        }
    
    def _transcribe_with_openai_api(self, file_path: Path, language: str, 
                                   progress: TranscriptionProgress) -> Dict[str, Any]:
        """Transcribe using OpenAI API"""
        from openai import OpenAI
        
        progress.update(progress=30, message="Connecting to OpenAI API...")
        
        if not self.openai_client:
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        progress.update(progress=50, message="Uploading audio to OpenAI...")
        
        # Verify file exists before proceeding
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        
        # Convert to absolute path
        absolute_path = file_path.resolve()
        logger.info(f"Transcribing file with OpenAI API: {absolute_path}")
        
        # Open audio file
        with open(absolute_path, "rb") as audio_file:
            transcript = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language if language != "auto" else None,
                response_format="verbose_json",
                temperature=0.0
            )
        
        progress.update(progress=80, message="Processing API response...")
        
        # Process segments
        transcript_segments = []
        
        for segment in transcript.segments:
            segment_data = {
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip()
            }
            transcript_segments.append(segment_data)
        
        progress.update(progress=90, message="Finalizing results...")
        
        return {
            "engine": "openai_api",
            "language": transcript.language,
            "language_probability": 0.95,  # OpenAI API doesn't provide this
            "duration": transcript.duration,
            "full_text": transcript.text.strip(),
            "segments": transcript_segments,
            "word_count": len(transcript.text.split()),
            "confidence": "high"
        }
    
    def get_transcription_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get transcription status and progress"""
        progress = self.progress_tracker.get(job_id)
        if not progress:
            return None
        
        return progress.to_dict()
    
    def cancel_transcription(self, job_id: str) -> bool:
        """Cancel an ongoing transcription"""
        progress = self.progress_tracker.get(job_id)
        if not progress:
            return False
        
        if progress.status == TranscriptionStatus.PROCESSING:
            progress.update(
                status=TranscriptionStatus.CANCELLED,
                message="Transcription cancelled by user"
            )
            logger.info(f"🚫 Transcription job {job_id} cancelled")
            return True
        
        return False
    
    def cleanup_job(self, job_id: str) -> bool:
        """Clean up completed transcription job"""
        if job_id in self.progress_tracker:
            del self.progress_tracker[job_id]
            logger.info(f"🧹 Cleaned up transcription job {job_id}")
            return True
        return False
    
    def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all transcription jobs"""
        return {job_id: progress.to_dict() 
                for job_id, progress in self.progress_tracker.items()}
    
    def transcribe_sync(self, file_path: Union[str, Path], language: str = "auto", 
                       engine: str = "auto", timeout: int = 300) -> Dict[str, Any]:
        """
        Synchronous transcription with timeout
        For simpler use cases where you want to wait for the result
        """
        job_id = self.start_transcription(file_path, language, engine)
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_transcription_status(job_id)
            
            if not status:
                raise Exception("Transcription job not found")
            
            if status["status"] == TranscriptionStatus.COMPLETED.value:
                result = status["result"]
                self.cleanup_job(job_id)
                return result
            
            elif status["status"] == TranscriptionStatus.FAILED.value:
                error = status["error"] or "Unknown error"
                self.cleanup_job(job_id)
                raise Exception(f"Transcription failed: {error}")
            
            elif status["status"] == TranscriptionStatus.CANCELLED.value:
                self.cleanup_job(job_id)
                raise Exception("Transcription was cancelled")
            
            # Wait a bit before checking again
            time.sleep(0.5)
        
        # Timeout reached
        self.cancel_transcription(job_id)
        self.cleanup_job(job_id)
        raise TimeoutError(f"Transcription timed out after {timeout} seconds")
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats"""
        return self.supported_formats.copy()
    
    def get_available_engines(self) -> List[str]:
        """Get list of available transcription engines"""
        return self.available_engines.copy()
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.temp_dir.mkdir(exist_ok=True)
            logger.info("🧹 Temporary transcription files cleaned up")
        except Exception as e:
            logger.warning(f"⚠️ Error cleaning temp files: {e}")

# Global enhanced transcriber instance
enhanced_transcriber = EnhancedAudioTranscriber()

def transcribe_audio(file_path: Union[str, Path], language: str = "auto", 
                    engine: str = "auto") -> Dict[str, Any]:
    """Convenience function for synchronous transcription"""
    return enhanced_transcriber.transcribe_sync(file_path, language, engine)