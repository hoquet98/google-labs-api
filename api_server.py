"""
FastAPI server for Google Labs automation
Can be called from N8N workflows
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import asyncio
import json
import os
import uuid
import logging
from typing import Optional, List
from automation_service import GoogleLabsService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Google Labs Video Generation API",
    description="Generate videos using Google Labs and download them automatically",
    version="1.0.0"
)

# Global service instance
labs_service = GoogleLabsService()

# Pydantic models for API requests
class VideoGenerationRequest(BaseModel):
    prompt: str
    headless: bool = True
    cookies_data: Optional[dict] = None

class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed
    progress: Optional[str] = None
    videos: Optional[List[str]] = None
    error: Optional[str] = None

# In-memory job storage (in production, use Redis or database)
jobs = {}

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Google Labs Video Generation API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "google-labs-api",
        "timestamp": "2025-01-27T00:00:00Z"
    }

@app.post("/generate-video")
async def generate_video_async(
    request: VideoGenerationRequest,
    background_tasks: BackgroundTasks
):
    """
    NON-BLOCKING: Start video generation job
    Returns job ID immediately for tracking progress
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job status
        jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": None,
            "videos": None,
            "error": None,
            "prompt": request.prompt
        }
        
        # Start background task
        background_tasks.add_task(
            run_video_generation,
            job_id,
            request.prompt,
            request.headless,
            request.cookies_data
        )
        
        logger.info(f"Started video generation job {job_id} with prompt: {request.prompt[:50]}...")
        
        return {
            "job_id": job_id,
            "status": "pending",
            "message": "Video generation started",
            "prompt": request.prompt,
            "blocking": False
        }
        
    except Exception as e:
        logger.error(f"Error starting video generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-video-sync")
async def generate_video_sync(request: VideoGenerationRequest):
    """
    BLOCKING: Generate video and wait for completion
    Returns final result with download URLs
    This will take 3-5 minutes to complete
    """
    try:
        logger.info(f"Starting synchronous video generation with prompt: {request.prompt[:50]}...")
        
        # Use cookies data if provided, otherwise use default file
        cookies_file = "uploaded_cookies.json" if request.cookies_data else "labs.google_cookies.json"
        
        if request.cookies_data:
            with open("uploaded_cookies.json", 'w') as f:
                json.dump(request.cookies_data, f)
        
        # Run the automation synchronously
        result = await labs_service.generate_video(
            prompt=request.prompt,
            headless=request.headless,
            cookies_file=cookies_file,
            job_id="sync_" + str(uuid.uuid4())[:8],
            progress_callback=lambda msg: logger.info(f"Progress: {msg}")
        )
        
        if result["success"]:
            # Move downloaded files to accessible location
            video_files = []
            download_urls = []
            
            for i, video_path in enumerate(result["videos"], 1):
                if os.path.exists(video_path):
                    # Create a simple accessible filename
                    filename = f"sync_video_{i}_{int(asyncio.get_event_loop().time())}.mp4"
                    new_path = f"downloads/{filename}"
                    os.rename(video_path, new_path)
                    video_files.append(filename)
                    download_urls.append(f"/download-direct/{filename}")
            
            logger.info(f"Sync generation completed successfully with {len(video_files)} videos")
            
            return {
                "success": True,
                "message": "Video generation completed successfully",
                "prompt": request.prompt,
                "videos": video_files,
                "download_urls": download_urls,
                "video_count": len(video_files),
                "blocking": True
            }
            
        else:
            logger.error(f"Sync generation failed: {result['error']}")
            raise HTTPException(status_code=500, detail=result["error"])
            
    except Exception as e:
        error_msg = f"Synchronous video generation failed: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """
    Get status of a video generation job
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]

@app.get("/jobs")
async def list_jobs():
    """
    List all jobs (recent first)
    """
    job_list = list(jobs.values())
    return {"jobs": job_list[-10:]}  # Return last 10 jobs

@app.post("/upload-cookies")
async def upload_cookies(file: UploadFile = File(...)):
    """
    Upload cookies JSON file
    """
    try:
        # Read and validate cookies file
        content = await file.read()
        cookies_data = json.loads(content)
        
        # Save cookies to file
        cookies_path = "uploaded_cookies.json"
        with open(cookies_path, 'w') as f:
            json.dump(cookies_data, f)
        
        logger.info(f"Uploaded cookies file with {len(cookies_data)} cookies")
        
        return {
            "message": "Cookies uploaded successfully",
            "cookie_count": len(cookies_data),
            "filename": file.filename
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"Error uploading cookies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-direct/{video_filename}")
async def download_video_direct(video_filename: str):
    """
    Download a video file directly (for synchronous generation)
    """
    file_path = f"downloads/{video_filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        path=file_path,
        filename=video_filename,
        media_type='video/mp4'
    )

@app.get("/download/{job_id}/{video_filename}")
async def download_video(job_id: str, video_filename: str):
    """
    Download a generated video file (for asynchronous generation)
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    file_path = f"downloads/{job_id}_{video_filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found")
    
    return FileResponse(
        path=file_path,
        filename=video_filename,
        media_type='video/mp4'
    )

@app.delete("/job/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a job and its associated files
    """
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Clean up video files
    try:
        downloads_dir = "downloads"
        if os.path.exists(downloads_dir):
            for filename in os.listdir(downloads_dir):
                if filename.startswith(job_id):
                    os.remove(os.path.join(downloads_dir, filename))
    except Exception as e:
        logger.warning(f"Error cleaning up files for job {job_id}: {e}")
    
    # Remove job from memory
    del jobs[job_id]
    
    return {"message": f"Job {job_id} deleted successfully"}

async def run_video_generation(job_id: str, prompt: str, headless: bool, cookies_data: dict = None):
    """
    Background task to run video generation
    """
    try:
        # Update job status
        jobs[job_id]["status"] = "running"
        jobs[job_id]["progress"] = "Starting automation..."
        
        logger.info(f"Running video generation for job {job_id}")
        
        # Use cookies data if provided, otherwise use default file
        cookies_file = "uploaded_cookies.json" if cookies_data else "labs.google_cookies.json"
        
        if cookies_data:
            with open("uploaded_cookies.json", 'w') as f:
                json.dump(cookies_data, f)
        
        # Run the automation
        result = await labs_service.generate_video(
            prompt=prompt,
            headless=headless,
            cookies_file=cookies_file,
            job_id=job_id,
            progress_callback=lambda msg: update_job_progress(job_id, msg)
        )
        
        if result["success"]:
            # Move downloaded files to job-specific names
            video_files = []
            for i, video_path in enumerate(result["videos"], 1):
                if os.path.exists(video_path):
                    new_filename = f"{job_id}_video_{i}.mp4"
                    new_path = f"downloads/{new_filename}"
                    os.rename(video_path, new_path)
                    video_files.append(new_filename)
            
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["videos"] = video_files
            jobs[job_id]["progress"] = "Video generation completed!"
            
            logger.info(f"Job {job_id} completed successfully with {len(video_files)} videos")
            
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = result["error"]
            logger.error(f"Job {job_id} failed: {result['error']}")
            
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        logger.error(f"Job {job_id} failed with exception: {e}")

def update_job_progress(job_id: str, message: str):
    """
    Update job progress message
    """
    if job_id in jobs:
        jobs[job_id]["progress"] = message
        logger.info(f"Job {job_id} progress: {message}")

# Startup event to create necessary directories
@app.on_event("startup")
async def startup_event():
    """
    Initialize the application
    """
    os.makedirs("downloads", exist_ok=True)
    logger.info("Google Labs API server started")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup on shutdown
    """
    await labs_service.cleanup()
    logger.info("Google Labs API server stopped")

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        "api_server:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )