#!/usr/bin/env python3
"""
Debug script to isolate the Whisper transcription issue
"""

import os
import tempfile
from pathlib import Path
import uuid
import wave
import struct

def create_simple_wav():
    """Create a minimal WAV file for testing"""
    temp_dir = Path(tempfile.gettempdir()) / "travel_transcription"
    temp_dir.mkdir(exist_ok=True)
    
    test_file = temp_dir / f"debug_test_{uuid.uuid4().hex[:8]}.wav"
    
    # Create a 1-second 440Hz sine wave
    sample_rate = 8000  # Lower sample rate for simplicity
    duration = 1.0
    frequency = 440.0
    
    samples = []
    for i in range(int(sample_rate * duration)):
        t = float(i) / sample_rate
        value = int(16384 * 0.5 * (1 + 0.5 * (t % (1/frequency))))  # Simple sine
        samples.append(struct.pack('<h', value))
    
    with wave.open(str(test_file), 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(samples))
    
    return test_file

def test_whisper_direct():
    """Test Whisper directly without our wrapper"""
    print("🎤 Testing Whisper directly...")
    
    try:
        import whisper
        
        # Create test file
        test_file = create_simple_wav()
        print(f"📁 Test file: {test_file}")
        print(f"📊 File size: {test_file.stat().st_size} bytes")
        print(f"📊 File exists: {test_file.exists()}")
        
        # Load the smallest model first
        print("📥 Loading Whisper tiny model...")
        model = whisper.load_model("tiny")
        
        print("🎯 Starting direct transcription...")
        result = model.transcribe(str(test_file.resolve()))
        
        print("✅ Direct transcription completed!")
        print(f"📝 Text: {result.get('text', 'No text')}")
        print(f"🌐 Language: {result.get('language', 'Unknown')}")
        
        # Clean up
        os.remove(test_file)
        print("🧹 Cleaned up test file")
        
        return True
        
    except Exception as e:
        print(f"❌ Direct Whisper test failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Try to clean up
        try:
            if 'test_file' in locals() and test_file.exists():
                os.remove(test_file)
        except:
            pass
        
        return False

def test_file_access():
    """Test basic file access patterns"""
    print("\n🔍 Testing file access patterns...")
    
    try:
        test_file = create_simple_wav()
        print(f"📁 Created: {test_file}")
        
        # Test different path representations
        str_path = str(test_file)
        resolved_path = str(test_file.resolve())
        absolute_path = test_file.absolute()
        
        print(f"📍 String path: {str_path}")
        print(f"📍 Resolved path: {resolved_path}")
        print(f"📍 Absolute path: {absolute_path}")
        
        print(f"✅ String path exists: {Path(str_path).exists()}")
        print(f"✅ Resolved path exists: {Path(resolved_path).exists()}")
        print(f"✅ Absolute path exists: {absolute_path.exists()}")
        
        # Test file permissions
        print(f"📋 Readable: {os.access(test_file, os.R_OK)}")
        print(f"📋 Writable: {os.access(test_file, os.W_OK)}")
        
        # Clean up
        os.remove(test_file)
        print("🧹 Cleaned up test file")
        
        return True
        
    except Exception as e:
        print(f"❌ File access test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Debug Whisper Issue...\n")
    
    # Test file access first
    file_test = test_file_access()
    
    # Test Whisper directly
    whisper_test = test_whisper_direct()
    
    print(f"\n📊 Debug Results:")
    print(f"   File Access: {'✅ PASS' if file_test else '❌ FAIL'}")
    print(f"   Direct Whisper: {'✅ PASS' if whisper_test else '❌ FAIL'}")
    
    if whisper_test:
        print("\n🎉 Whisper works fine directly! The issue is in our wrapper.")
    else:
        print("\n⚠️ Whisper has issues even directly. May need to check installation.")