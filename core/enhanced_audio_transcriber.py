"""
Enhanced Audio Transcription System with Robust Error Handling and UI Progress Tracking
Fixed for Windows compatibility and proper file handling
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
import subprocess
import platform
import uuid

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
    Fixed for Windows compatibility and proper file handling
    """
    
    def __init__(self):
        self.progress_tracker = {}  # job_id -> TranscriptionProgress
        self.max_file_size_mb = 25  # Maximum file size in MB
        self.supported_formats = ['.wav', '.mp3', '.m4a', '.ogg', '.flac', '.webm', '.mp4']
        
        # Create secure temp directory
        self.temp_dir = self._create_secure_temp_dir()
        
        # Initialize transcription engines
        self.whisper_model = None
        self.faster_whisper_model = None
        self.openai_client = None
        
        # Check system dependencies first
        self._check_system_dependencies()
        
        # Check available transcription methods
        self._check_available_engines()
        
        logger.info("✅ Enhanced Audio Transcriber initialized")
    
    def _create_secure_temp_dir(self) -> Path:
        """Create secure temporary directory with proper permissions"""
        try:
            # Use system temp directory with unique subdirectory
            base_temp = Path(tempfile.gettempdir())
            temp_dir = base_temp / f"travel_transcription_{uuid.uuid4().hex[:8]}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Set proper permissions on Windows
            if platform.system() == "Windows":
                try:
                    import stat
                    os.chmod(temp_dir, stat.S_IRWXU | stat.S_IRWXG)
                except Exception as e:
                    logger.debug(f"Could not set directory permissions: {e}")
            
            logger.info(f"✅ Created temp directory: {temp_dir}")
            return temp_dir
            
        except Exception as e:
            logger.error(f"Failed to create temp directory: {e}")
            # Fallback to current directory
            fallback_dir = Path.cwd() / "temp_audio"
            fallback_dir.mkdir(exist_ok=True)
            return fallback_dir
    
    def _check_system_dependencies(self):
        """Check if required system dependencies are available"""
        self.system_dependencies = {
            'ffmpeg': False,
            'python_audio_libs': False
        }
        
        # Check for ffmpeg
        try:
            if platform.system() == "Windows":
                # Try common Windows locations
                ffmpeg_paths = [
                    "ffmpeg",
                    "ffmpeg.exe",
                    r"C:\ffmpeg\bin\ffmpeg.exe",
                    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"
                ]
                
                for ffmpeg_path in ffmpeg_paths:
                    try:
                        result = subprocess.run([ffmpeg_path, '-version'], 
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            self.system_dependencies['ffmpeg'] = True
                            logger.info(f"✅ FFmpeg found at: {ffmpeg_path}")
                            break
                    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                        continue
            else:
                # Unix/Linux/Mac
                result = subprocess.run(['ffmpeg', '-version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.system_dependencies['ffmpeg'] = True
                    logger.info("✅ FFmpeg found and working")
            
            if not self.system_dependencies['ffmpeg']:
                logger.warning("⚠️ FFmpeg not found - audio conversion may fail")
                logger.info("💡 Install FFmpeg: https://ffmpeg.org/download.html")
                
        except Exception as e:
            logger.warning(f"⚠️ FFmpeg check failed: {e}")
        
        # Check Python audio libraries
        try:
            import wave
            import audioop
            self.system_dependencies['python_audio_libs'] = True
            logger.info("✅ Python audio libraries available")
        except ImportError:
            logger.warning("⚠️ Python audio libraries not available")
    
    def _check_available_engines(self):
        """Check which transcription engines are available"""
        self.available_engines = []
        
        # Check faster-whisper
        try:
            from faster_whisper import WhisperModel
            self.available_engines.append("faster_whisper")
            logger.info("✅ faster-whisper available")
        except ImportError:
            logger.warning("⚠️ faster-whisper not available")
        
        # Check OpenAI Whisper
        try:
            import whisper
            self.available_engines.append("whisper")
            logger.info("✅ OpenAI Whisper available")
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
        
        # Add fallback transcription engine
        self.available_engines.append("fallback")
        logger.info("✅ Fallback transcription engine available")
        
        if not self.available_engines:
            logger.error("❌ No transcription engines available")
        else:
            logger.info(f"📊 Available engines: {', '.join(self.available_engines)}")
    
    def validate_audio_file(self, file_path: Union[str, Path], max_size_mb: int = None) -> Dict[str, Any]:
        """Validate audio file format and size with enhanced error handling"""
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
                "extension": file_path.suffix.lower(),
                "absolute_path": str(file_path.absolute())
            }
        }
        
        try:
            # Check if file exists with absolute path
            if not file_path.exists():
                # Try to find the file in common locations
                possible_paths = [
                    file_path,
                    Path.cwd() / file_path.name,
                    self.temp_dir / file_path.name
                ]
                
                file_found = False
                for possible_path in possible_paths:
                    if possible_path.exists():
                        file_path = possible_path
                        file_found = True
                        logger.info(f"✅ Found file at: {file_path}")
                        break
                
                if not file_found:
                    validation_result["errors"].append(f"File does not exist at: {file_path}")
                    validation_result["errors"].append(f"Searched locations: {[str(p) for p in possible_paths]}")
                    return validation_result
            
            # Get file info
            file_size = file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            validation_result["file_info"].update({
                "size_bytes": file_size,
                "size_mb": round(file_size_mb, 2),
                "absolute_path": str(file_path.absolute())
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
            
            # Check file accessibility
            try:
                with open(file_path, 'rb') as f:
                    f.read(1024)  # Try to read first 1KB
                logger.debug(f"✅ File is readable: {file_path}")
            except Exception as e:
                validation_result["errors"].append(f"File is not readable: {e}")
            
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
        Enhanced with better file handling and error recovery
        """
        job_id = f"transcribe_{int(time.time() * 1000)}"
        
        # Create progress tracker
        progress = TranscriptionProgress(job_id)
        self.progress_tracker[job_id] = progress
        
        # Convert to Path object and resolve
        file_path = Path(file_path).resolve()
        
        # Validate file with enhanced checking
        validation = self.validate_audio_file(file_path)
        progress.file_info = validation["file_info"]
        
        if not validation["valid"]:
            error_msg = f"File validation failed: {'; '.join(validation['errors'])}"
            progress.update(
                status=TranscriptionStatus.FAILED,
                message=error_msg
            )
            progress.error = validation["errors"]
            logger.error(f"❌ Validation failed for {file_path}: {error_msg}")
            return job_id
        
        # Copy file to secure temp location to avoid path issues
        try:
            secure_filename = f"{job_id}_{file_path.name}"
            secure_path = self.temp_dir / secure_filename
            
            # Copy file to secure location
            shutil.copy2(file_path, secure_path)
            progress.file_info["secure_path"] = str(secure_path)
            logger.info(f"✅ File copied to secure location: {secure_path}")
            
        except Exception as e:
            progress.update(
                status=TranscriptionStatus.FAILED,
                message=f"Failed to secure file: {e}"
            )
            progress.error = str(e)
            logger.error(f"❌ Failed to secure file: {e}")
            return job_id
        
        # Start transcription in background thread
        thread = threading.Thread(
            target=self._transcribe_worker,
            args=(job_id, secure_path, language, engine),
            name=f"Transcriber-{job_id}",
            daemon=True
        )
        thread.start()
        
        progress.update(
            status=TranscriptionStatus.PROCESSING,
            progress=5,
            message="Starting transcription..."
        )
        
        logger.info(f"🎤 Started transcription job {job_id} for {file_path.name}")
        return job_id
    
    def _transcribe_worker(self, job_id: str, file_path: Path, 
                          language: str, engine: str):
        """Background worker for transcription with enhanced error handling"""
        progress = self.progress_tracker[job_id]
        
        try:
            # Update progress
            progress.update(progress=10, message="Preparing audio file...")
            
            # Verify file still exists
            if not file_path.exists():
                raise FileNotFoundError(f"Secure file not found: {file_path}")
            
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
            elif selected_engine == "fallback":
                result = self._transcribe_with_fallback(file_path, language, progress)
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
        
        finally:
            # Clean up secure file
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"🧹 Cleaned up secure file: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not clean up file {file_path}: {e}")
    
    def _select_engine(self, preferred_engine: str) -> Optional[str]:
        """Select the best available transcription engine"""
        if preferred_engine != "auto" and preferred_engine in self.available_engines:
            return preferred_engine
        
        # Auto-select based on priority
        engine_priority = ["faster_whisper", "whisper", "openai_api", "fallback"]
        
        for engine in engine_priority:
            if engine in self.available_engines:
                return engine
        
        return "fallback"  # Always have fallback available
    
    def _transcribe_with_faster_whisper(self, file_path: Path, language: str, 
                                      progress: TranscriptionProgress) -> Dict[str, Any]:
        """Transcribe using faster-whisper with enhanced error handling"""
        try:
            from faster_whisper import WhisperModel
            
            progress.update(progress=30, message="Loading faster-whisper model...")
            
            if not self.faster_whisper_model:
                # Use smaller model for better performance
                model_size = "base.en" if language == "en" else "base"
                self.faster_whisper_model = WhisperModel(
                    model_size, 
                    device="cpu", 
                    compute_type="int8",
                    download_root=str(self.temp_dir / "models")
                )
            
            progress.update(progress=50, message="Processing audio...")
            
            # Detect language if auto
            detect_language = language if language != "auto" else None
            
            # Transcribe with error handling
            segments, info = self.faster_whisper_model.transcribe(
                str(file_path),
                language=detect_language,
                beam_size=5,
                temperature=0.0,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500)
            )
            
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
            
        except Exception as e:
            logger.error(f"faster-whisper transcription failed: {e}")
            raise
    
    def _transcribe_with_whisper(self, file_path: Path, language: str, 
                                progress: TranscriptionProgress) -> Dict[str, Any]:
        """Transcribe using OpenAI Whisper with enhanced error handling"""
        try:
            import whisper
            
            progress.update(progress=30, message="Loading OpenAI Whisper model...")
            
            if not self.whisper_model:
                # Use base model for balance of speed and accuracy
                model_size = "base.en" if language == "en" else "base"
                self.whisper_model = whisper.load_model(
                    model_size,
                    download_root=str(self.temp_dir / "whisper_models")
                )
            
            progress.update(progress=50, message="Processing audio...")
            
            # Transcribe with enhanced options
            result = self.whisper_model.transcribe(
                str(file_path),
                language=language if language != "auto" else None,
                temperature=0.0,
                no_speech_threshold=0.6,
                logprob_threshold=-1.0,
                compression_ratio_threshold=2.4
            )
            
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
            
        except Exception as e:
            logger.error(f"whisper transcription failed: {e}")
            raise
    
    def _transcribe_with_openai_api(self, file_path: Path, language: str, 
                                   progress: TranscriptionProgress) -> Dict[str, Any]:
        """Transcribe using OpenAI API with enhanced error handling"""
        try:
            from openai import OpenAI
            
            progress.update(progress=30, message="Connecting to OpenAI API...")
            
            if not self.openai_client:
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            progress.update(progress=50, message="Uploading audio to OpenAI...")
            
            # Open audio file with proper error handling
            with open(file_path, "rb") as audio_file:
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
            
        except Exception as e:
            logger.error(f"OpenAI API transcription failed: {e}")
            raise
    
    def _transcribe_with_fallback(self, file_path: Path, language: str,
                                 progress: TranscriptionProgress) -> Dict[str, Any]:
        """Fallback transcription using basic audio analysis"""
        try:
            progress.update(progress=30, message="Using fallback transcription...")
            
            # Get basic file info
            file_size = file_path.stat().st_size
            duration_estimate = max(file_size / (16000 * 2), 1.0)  # Rough estimate
            
            progress.update(progress=60, message="Analyzing audio properties...")
            
            # Create a basic transcription result
            fallback_text = f"[Audio file processed: {file_path.name}]\n"
            fallback_text += f"Duration: ~{duration_estimate:.1f} seconds\n"
            fallback_text += f"File size: {file_size / 1024 / 1024:.1f} MB\n"
            fallback_text += "Note: This is a fallback transcription. Install whisper or faster-whisper for actual speech-to-text."
            
            progress.update(progress=90, message="Creating fallback result...")
            
            return {
                "engine": "fallback",
                "language": language if language != "auto" else "unknown",
                "language_probability": 0.5,
                "duration": duration_estimate,
                "full_text": fallback_text,
                "segments": [{
                    "start": 0.0,
                    "end": duration_estimate,
                    "text": fallback_text
                }],
                "word_count": len(fallback_text.split()),
                "confidence": "low"
            }
            
        except Exception as e:
            logger.error(f"Fallback transcription failed: {e}")
            raise
    
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
            # Clean up any temp files
            progress = self.progress_tracker[job_id]
            secure_path = progress.file_info.get("secure_path")
            if secure_path and Path(secure_path).exists():
                try:
                    Path(secure_path).unlink()
                    logger.debug(f"🧹 Cleaned up secure file: {secure_path}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not clean up secure file: {e}")
            
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
        Synchronous transcription with timeout and enhanced error handling
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