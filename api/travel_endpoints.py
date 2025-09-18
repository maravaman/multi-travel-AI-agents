@@ .. @@
@router.post("/upload_audio", response_model=TranscriptionJobResponse)
async def upload_audio(
    user_id: int = Form(...),
    auto_analyze: bool = Form(False),
    language: Optional[str] = Form("auto"),
    engine: Optional[str] = Form("auto"),
    audio: UploadFile = File(...),
    current_user: Dict = Depends(get_optional_current_user)
):
    """Upload an audio file and start transcription job with progress tracking."""
    try:
        from core.enhanced_audio_transcriber import enhanced_transcriber
        
        logger.info(f"Audio upload request for user {user_id}: {audio.filename} ({audio.content_type})")
        
-        # Save uploaded file to temporary location
-        import uuid
-        unique_filename = f"{uuid.uuid4()}_{audio.filename}"
-        temp_file_path = enhanced_transcriber.temp_dir / unique_filename
+        # Enhanced file handling with proper validation
+        if not audio.filename:
+            raise HTTPException(status_code=400, detail="No filename provided")
+        
+        # Validate file type
+        file_extension = Path(audio.filename).suffix.lower()
+        if file_extension not in enhanced_transcriber.supported_formats:
+            raise HTTPException(
+                status_code=400, 
+                detail=f"Unsupported file format: {file_extension}. Supported: {', '.join(enhanced_transcriber.supported_formats)}"
+            )
+        
+        # Create secure filename
+        import uuid
+        safe_filename = f"{uuid.uuid4().hex[:8]}_{audio.filename}"
+        temp_file_path = enhanced_transcriber.temp_dir / safe_filename
+        
+        # Ensure temp directory exists
+        enhanced_transcriber.temp_dir.mkdir(parents=True, exist_ok=True)
        
-        with open(temp_file_path, "wb") as temp_file:
-            content = await audio.read()
-            temp_file.write(content)
+        # Save uploaded file with proper error handling
+        try:
+            content = await audio.read()
+            
+            # Validate content size
+            if len(content) == 0:
+                raise HTTPException(status_code=400, detail="Uploaded file is empty")
+            
+            if len(content) > enhanced_transcriber.max_file_size_mb * 1024 * 1024:
+                raise HTTPException(
+                    status_code=400, 
+                    detail=f"File too large: {len(content)/1024/1024:.1f}MB. Max: {enhanced_transcriber.max_file_size_mb}MB"
+                )
+            
+            # Write file securely
+            with open(temp_file_path, "wb") as temp_file:
+                temp_file.write(content)
+            
+            # Verify file was written correctly
+            if not temp_file_path.exists() or temp_file_path.stat().st_size != len(content):
+                raise Exception("File write verification failed")
+                
+            logger.info(f"✅ File saved successfully: {temp_file_path} ({len(content)} bytes)")
+            
+        except Exception as e:
+            # Clean up on error
+            if temp_file_path.exists():
+                try:
+                    temp_file_path.unlink()
+                except:
+                    pass
+            raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")
        
        # Start transcription job
        job_id = enhanced_transcriber.start_transcription(
            file_path=temp_file_path,
            language=language or "auto",
            engine=engine or "auto"
        )
        
        # Store metadata for later analysis
-        enhanced_transcriber.progress_tracker[job_id].file_info.update({
-            "user_id": user_id,
-            "auto_analyze": auto_analyze,
-            "original_filename": audio.filename,
-            "temp_path": str(temp_file_path)
-        })
+        if job_id in enhanced_transcriber.progress_tracker:
+            enhanced_transcriber.progress_tracker[job_id].file_info.update({
+                "user_id": user_id,
+                "auto_analyze": auto_analyze,
+                "original_filename": audio.filename,
+                "temp_path": str(temp_file_path),
+                "content_type": audio.content_type,
+                "file_size": len(content)
+            })
        
        # Get initial status
        status = enhanced_transcriber.get_transcription_status(job_id)
        
        return TranscriptionJobResponse(
            job_id=job_id,
            status=status["status"],
            message=status["message"],
            progress_percent=status["progress_percent"],
            file_info=status["file_info"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Audio upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Audio upload failed: {str(e)}")