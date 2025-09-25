# Audio Transcription Setup Guide

## Issue: "The system cannot find the file specified" Error

If you're seeing this error when trying to transcribe audio files:

```
ERROR:core.enhanced_audio_transcriber:Whisper transcribe error: [WinError 2] The system cannot find the file specified
```

**This means ffmpeg is not installed on your system.** Whisper requires ffmpeg to process audio files.

## Quick Fix

### Option 1: Automated Installation (Recommended)

1. **Run the installation script as Administrator:**
   ```powershell
   # Right-click PowerShell -> "Run as Administrator"
   # Then run:
   .\install_ffmpeg.ps1
   ```

2. **Restart your Python application** after installation

### Option 2: Manual Installation

#### Using Chocolatey (if available):
```powershell
# Run PowerShell as Administrator
choco install ffmpeg -y
```

#### Using Winget (Windows 10/11):
```powershell
# Run PowerShell as Administrator
winget install ffmpeg
```

#### Manual Download:
1. Visit [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
2. Download the Windows build
3. Extract to `C:\ffmpeg`
4. Add `C:\ffmpeg\bin` to your PATH environment variable
5. Restart your command prompt and applications

## Verify Installation

Test if ffmpeg is working:
```cmd
ffmpeg -version
```

You should see version information if it's installed correctly.

## What is ffmpeg?

FFmpeg is a free, open-source multimedia framework that can decode, encode, transcode, mux, demux, stream, filter, and play audio and video files. Whisper uses it internally to:

- Convert various audio formats (MP3, MP4, WAV, etc.)
- Resample audio to the correct format
- Extract audio from video files

## Troubleshooting

### Still getting errors after installation?

1. **Restart everything:**
   - Close all command prompts/PowerShell windows
   - Restart your Python application
   - Try the transcription again

2. **Check PATH variable:**
   - Open System Properties → Environment Variables
   - Make sure ffmpeg's bin directory is in your PATH

3. **Test ffmpeg manually:**
   ```cmd
   ffmpeg -version
   ```

4. **Try a different audio file:**
   - Some corrupted files can cause issues
   - Try with a simple WAV file first

### Alternative Solutions

If you continue having issues with ffmpeg, you can:

1. **Use the OpenAI API instead** (requires API key):
   - Set `OPENAI_API_KEY` environment variable
   - The system will automatically use the API for transcription

2. **Use faster-whisper** (if available):
   - Install with: `pip install faster-whisper`
   - Requires less setup than standard Whisper

## System Requirements

- **Windows 10/11** (this guide)
- **Administrator access** for installation
- **Internet connection** for downloading ffmpeg
- **~100MB free space** for ffmpeg installation

## Support

If you're still having issues:

1. Check the application logs for detailed error messages
2. Verify your audio file is not corrupted
3. Try with a different audio format (WAV is most reliable)
4. Ensure you have sufficient disk space

---

*This issue is common when setting up Whisper-based transcription systems. Following this guide should resolve the problem completely.*