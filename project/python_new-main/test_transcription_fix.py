#!/usr/bin/env python3
"""
Test script to verify the audio transcription fix works correctly
"""

import os
import tempfile
from pathlib import Path
import uuid
import time

def create_dummy_audio_file():
    """Create a simple WAV file with some audio data for testing"""
    import struct
    import wave
    
    # Create a simple 1-second sine wave as test audio
    sample_rate = 44100
    duration = 1.0
    frequency = 440.0  # A4 note
    
    # Generate sine wave samples
    samples = []
    for i in range(int(sample_rate * duration)):
        t = float(i) / sample_rate
        value = int(32767 * 0.5 * (1 + 0.5 * (t % 1)))  # Simple sine approximation
        samples.append(struct.pack('<h', value))
    
    # Create temp WAV file
    temp_dir = Path(tempfile.gettempdir()) / "travel_transcription"
    temp_dir.mkdir(exist_ok=True)
    
    test_file = temp_dir / f"test_audio_{uuid.uuid4().hex[:8]}.wav"
    
    with wave.open(str(test_file), 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b''.join(samples))
    
    return test_file

def test_enhanced_transcriber():
    """Test the enhanced audio transcriber with a real audio file"""
    print("🎤 Testing Enhanced Audio Transcriber...")
    
    try:
        from core.enhanced_audio_transcriber import enhanced_transcriber
        
        # Create a dummy audio file
        print("📁 Creating test audio file...")
        test_file = create_dummy_audio_file()
        print(f"✅ Test file created: {test_file}")
        print(f"📊 File size: {test_file.stat().st_size} bytes")
        print(f"📊 File exists: {test_file.exists()}")
        
        # Test validation
        print("\n🔍 Testing file validation...")
        validation = enhanced_transcriber.validate_audio_file(test_file)
        print(f"✅ Validation result: {validation}")
        
        if not validation['valid']:
            print(f"❌ Validation failed: {validation['errors']}")
            return False
        
        # Test async transcription
        print("\n🎯 Testing async transcription...")
        job_id = enhanced_transcriber.start_transcription(test_file, language="en", engine="whisper")
        print(f"📋 Started job: {job_id}")
        
        # Monitor progress
        max_wait = 60  # Wait up to 60 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status = enhanced_transcriber.get_transcription_status(job_id)
            if not status:
                print("❌ Job not found")
                break
            
            print(f"📊 Status: {status['status']} - {status['progress_percent']}% - {status['message']}")
            
            if status['status'] == 'completed':
                print("✅ Transcription completed!")
                print(f"📝 Result: {status['result']}")
                enhanced_transcriber.cleanup_job(job_id)
                break
            elif status['status'] == 'failed':
                print(f"❌ Transcription failed: {status['error']}")
                enhanced_transcriber.cleanup_job(job_id)
                break
            
            time.sleep(2)
        else:
            print(f"⏰ Transcription timed out after {max_wait} seconds")
            enhanced_transcriber.cancel_transcription(job_id)
            enhanced_transcriber.cleanup_job(job_id)
        
        # Clean up test file
        try:
            os.remove(test_file)
            print(f"🧹 Cleaned up test file: {test_file}")
        except Exception as e:
            print(f"⚠️ Failed to clean up test file: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sync_transcription():
    """Test synchronous transcription (simpler test)"""
    print("\n🎯 Testing Synchronous Transcription...")
    
    try:
        from core.enhanced_audio_transcriber import enhanced_transcriber
        
        # Create a dummy audio file
        test_file = create_dummy_audio_file()
        print(f"📁 Created test file: {test_file}")
        
        # Test sync transcription with timeout
        print("🎤 Starting sync transcription...")
        result = enhanced_transcriber.transcribe_sync(
            file_path=test_file,
            language="en",
            engine="whisper",
            timeout=30
        )
        
        print("✅ Sync transcription completed!")
        print(f"📝 Engine: {result['engine']}")
        print(f"🌐 Language: {result['language']}")
        print(f"⏱️ Duration: {result['duration']}s")
        print(f"📖 Text: {result['full_text'][:100]}...")
        
        # Clean up
        try:
            os.remove(test_file)
            print(f"🧹 Cleaned up test file")
        except Exception as e:
            print(f"⚠️ Failed to clean up test file: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Sync test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Testing Audio Transcription Fix...\n")
    
    # Test sync transcription first (simpler)
    sync_success = test_sync_transcription()
    
    # Test async transcription
    async_success = test_enhanced_transcriber()
    
    print(f"\n📊 Test Results:")
    print(f"   Sync Test: {'✅ PASS' if sync_success else '❌ FAIL'}")
    print(f"   Async Test: {'✅ PASS' if async_success else '❌ FAIL'}")
    
    if sync_success and async_success:
        print("\n🎉 All tests passed! Audio transcription fix is working.")
    else:
        print("\n⚠️ Some tests failed. Check the logs above for details.")