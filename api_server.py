# Add this to your api_server.py imports and models section

from pydantic import BaseModel
from typing import Optional, List

# Updated Pydantic models
class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, running, completed, failed
    progress: Optional[str] = None
    videos: Optional[List[str]] = None
    images: Optional[List[str]] = None  # NEW: Add images field
    error: Optional[str] = None

# Update the synchronous endpoint response
@app.post("/generate-video-sync")
async def generate_video_sync(request: VideoGenerationRequest):
    """
    BLOCKING: Generate video and wait for completion
    Returns final result with download URLs for both videos and images
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
        
        logger.info(f"Automation service returned: {result}")
        
        if result["success"]:
            video_urls = result.get("videos", [])
            image_urls = result.get("images", [])  # NEW: Get image URLs
            
            logger.info(f"Got {len(video_urls)} video URLs and {len(image_urls)} image URLs from automation")
            
            if video_urls and len(video_urls) > 0:
                # These are already S3 URLs, so we can use them directly
                video_download_urls = video_urls  # S3 URLs can be used directly for download
                image_download_urls = image_urls  # S3 URLs can be used directly for download
                
                logger.info(f"Returning success response with {len(video_urls)} videos and {len(image_urls)} images")
                
                return {
                    "success": True,
                    "message": "Video generation completed successfully",
                    "prompt": request.prompt,
                    "videos": video_urls,
                    "images": image_urls,  # NEW: Include images in response
                    "download_urls": {     # NEW: Organize download URLs
                        "videos": video_download_urls,
                        "images": image_download_urls
                    },
                    "video_count": len(video_urls),
                    "image_count": len(image_urls),  # NEW: Include image count
                    "blocking": True
                }
            else:
                logger.error(f"Automation returned success but no video URLs: {result}")
                raise HTTPException(status_code=500, detail="Video generation succeeded but no videos were returned")
        else:
            logger.error(f"Automation service failed: {result}")
            raise HTTPException(status_code=500, detail=result.get("error", "Video generation failed"))
            
    except Exception as e:
        error_msg = f"Synchronous video generation failed: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# Update the asynchronous background task
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
            # Get both videos and images from the result
            video_urls = result.get("videos", [])
            image_urls = result.get("images", [])
            
            # Store both in the job status
            jobs[job_id]["status"] = "completed"
            jobs[job_id]["videos"] = video_urls
            jobs[job_id]["images"] = image_urls  # NEW: Store images
            jobs[job_id]["progress"] = f"Completed! {len(video_urls)} videos and {len(image_urls)} images uploaded to S3"
            
            logger.info(f"Job {job_id} completed successfully with {len(video_urls)} videos and {len(image_urls)} images")
            
        else:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = result["error"]
            logger.error(f"Job {job_id} failed: {result['error']}")
            
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        logger.error(f"Job {job_id} failed with exception: {e}")

# Update the async endpoint response
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
        
        # Initialize job status with images field
        jobs[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "progress": None,
            "videos": None,
            "images": None,  # NEW: Initialize images field
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
