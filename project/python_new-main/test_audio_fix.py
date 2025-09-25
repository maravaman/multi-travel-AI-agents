#!/usr/bin/env python3
"""
Test script to diagnose the audio transcription file path issue
"""

import os
import tempfile
from pathlib import Path
import uuid

def test_file_handling():
    """Test the file handling logic that's causing the issue"""
    
    print("🔍 Testing audio file handling...")
    
    # Simulate the same logic used in the endpoints
    from core.enhanced_audio_transcriber import enhanced_transcriber
    
    # Create a fake audio file for testing
    temp_dir = enhanced_transcriber.temp_dir
    print(f"📁 Temp directory: {temp_dir}")
    print(f"📁 Temp directory exists: {temp_dir.exists()}")
    
    # Create a dummy audio file like the upload endpoint does
    test_filename = "test_audio.mp3"
    unique_filename = f"{uuid.uuid4()}_{test_filename}"
    temp_file_path = temp_dir / unique_filename
    
    print(f"📄 Test file path: {temp_file_path}")
    
    # Create a dummy file with some content
    try:
        with open(temp_file_path, "wb") as f:
            f.write(b"fake audio content for testing")
        
        print(f"✅ Test file created successfully")
        print(f"📊 File exists: {temp_file_path.exists()}")
        print(f"📊 File size: {temp_file_path.stat().st_size} bytes")
        
        # Now test the validation
        validation = enhanced_transcriber.validate_audio_file(temp_file_path)
        print(f"✅ Validation result: {validation}")
        
        # Clean up
        os.remove(temp_file_path)
        print(f"🧹 Test file cleaned up")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

def test_whisper_availability():
    """Test if Whisper is available and working"""
    print("\n🎤 Testing Whisper availability...")
    
    try:
        import whisper
        print("✅ Whisper module available")
        
        # Try to load a model (this might take a while on first run)
        print("📥 Loading Whisper base model...")
        model = whisper.load_model("base")
        print("✅ Whisper model loaded successfully")
        
    except ImportError:
        print("❌ Whisper module not available")
    except Exception as e:
        print(f"❌ Error loading Whisper: {e}")

if __name__ == "__main__":
    test_file_handling()
    test_whisper_availability()