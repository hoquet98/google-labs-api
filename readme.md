python -m venv venv

.\venv\Scripts\Activate

# Google Labs Video Generation API

Convert the Google Labs automation into a REST API service that can be called from N8N workflows.

## 🚀 Quick Deployment on Coolify

### 1. Create New Project in Coolify

1. Log into your Coolify dashboard
2. Click "New Project"
3. Choose "Docker Compose" deployment
4. Upload or paste the contents of your project files

### 2. Required Files

Upload these files to your Coolify project:

├── api_server.py              # Main FastAPI server
├── automation_service.py      # Automation service logic
├── cookie_handler.py          # Cookie management
├── navigation_handler.py      # Browser handling
├── ui_interactions.py         # UI interactions
├── video_handler.py           # Video processing
├── Dockerfile                 # Container configuration
├── docker-compose.yml         # Docker compose setup
├── requirements.txt           # Python dependencies
└── labs.google_cookies.json   # Your Google Labs cookies

### 3. Environment Variables

Set these in Coolify (optional):

- `PORT`: API port (default: 8000)
- `HOST`: Host address (default: 0.0.0.0)

### 4. Deploy

1. Click "Deploy" in Coolify
2. Wait for the build to complete
3. Your API will be available at: `https://your-domain.com`

## 📋 API Endpoints

### 🚀 NON-BLOCKING: Generate Video (Async)
```http
POST /generate-video
Returns immediately with a job ID. Use this for N8N workflows where you want to do other tasks while video generates.
Request Body:
json{
  "prompt": "A majestic golden retriever running through a meadow",
  "headless": true,
  "cookies_data": {...}  // Optional: provide cookies directly
}
Response:
json{
  "job_id": "uuid-string",
  "status": "pending",
  "message": "Video generation started",
  "prompt": "Your prompt here",
  "blocking": false
}
⏳ BLOCKING: Generate Video (Sync)
httpPOST /generate-video-sync
Waits 3-5 minutes and returns completed videos. Use this for simple workflows where you want to wait for results.
Request Body:
json{
  "prompt": "A majestic golden retriever running through a meadow",
  "headless": true,
  "cookies_data": {...}  // Optional
}
Response:
json{
  "success": true,
  "message": "Video generation completed successfully",
  "prompt": "Your prompt here",
  "videos": ["sync_video_1_timestamp.mp4", "sync_video_2_timestamp.mp4"],
  "download_urls": ["/download-direct/sync_video_1_timestamp.mp4", "/download-direct/sync_video_2_timestamp.mp4"],
  "video_count": 2,
  "blocking": true
}
Check Job Status
httpGET /job/{job_id}
Response:
json{
  "job_id": "uuid-string",
  "status": "completed",
  "progress": "Video generation completed!",
  "videos": ["uuid_video_1.mp4", "uuid_video_2.mp4"],
  "error": null
}
Upload Cookies
httpPOST /upload-cookies
Upload your labs.google_cookies.json file.
Download Video
httpGET /download/{job_id}/{video_filename}
Downloads the generated MP4 file.
List All Jobs
httpGET /jobs
Health Check
httpGET /health
🔧 N8N Integration
Option 1: Simple Blocking Approach (Easiest)
Single HTTP Request Node:
Method: POST
URL: https://your-api-domain.com/generate-video-sync
Headers: Content-Type: application/json
Body: {
  "prompt": "{{$node["Previous Node"].json["prompt"]}}",
  "headless": true
}
Timeout: 300000  // 5 minutes
Result: Get videos immediately in the response. Perfect for simple workflows.
Option 2: Non-blocking Approach (Advanced)

HTTP Request Node - Start video generation:
Method: POST
URL: https://your-api-domain.com/generate-video
Body: {
  "prompt": "{{$node["Previous Node"].json["prompt"]}}",
  "headless": true
}

Wait Node - Wait for processing:
Amount: 2
Unit: minutes

HTTP Request Node - Check status:
Method: GET
URL: https://your-api-domain.com/job/{{$node["Start Generation"].json["job_id"]}}

IF Node - Check if completed:
Condition: {{$node["Check Status"].json["status"]}} === "completed"

HTTP Request Node - Download videos:
Method: GET
URL: https://your-api-domain.com/download/{{$node["Start Generation"].json["job_id"]}}/{{$node["Check Status"].json["videos"][0]}}


Result: More complex but allows N8N to do other tasks while waiting.
🧪 Testing the API
Local Testing

Install dependencies:
bashpip install -r requirements.txt
playwright install chromium

Run locally:
bashpython api_server.py

Test with curl:
bash# Upload cookies
curl -X POST "http://localhost:8000/upload-cookies" \
     -F "file=@labs.google_cookies.json"

# Start video generation
curl -X POST "http://localhost:8000/generate-video" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "A beautiful sunset over mountains", "headless": true}'

# Check status (replace with actual job_id)
curl "http://localhost:8000/job/your-job-id-here"


Using the Test Script
Create test_api.py:
pythonimport requests
import time
import json

API_BASE = "http://localhost:8000"

# Test the API
def test_api():
    # 1. Health check
    response = requests.get(f"{API_BASE}/health")
    print("Health check:", response.json())
    
    # 2. Upload cookies (optional)
    with open("labs.google_cookies.json", "rb") as f:
        response = requests.post(f"{API_BASE}/upload-cookies", files={"file": f})
        print("Upload cookies:", response.json())
    
    # 3. Start video generation
    prompt = "A cat playing with a ball of yarn, slow motion"
    response = requests.post(f"{API_BASE}/generate-video", json={
        "prompt": prompt,
        "headless": True
    })
    result = response.json()
    print("Started generation:", result)
    
    job_id = result["job_id"]
    
    # 4. Poll for completion
    while True:
        response = requests.get(f"{API_BASE}/job/{job_id}")
        status = response.json()
        print("Status:", status["status"], status.get("progress", ""))
        
        if status["status"] in ["completed", "failed"]:
            break
            
        time.sleep(10)
    
    # 5. Download videos if successful
    if status["status"] == "completed":
        for video in status["videos"]:
            response = requests.get(f"{API_BASE}/download/{job_id}/{video}")
            with open(f"downloaded_{video}", "wb") as f:
                f.write(response.content)
            print(f"Downloaded: downloaded_{video}")

if __name__ == "__main__":
    test_api()
🔒 Security Notes

Keep your cookies file secure and private
Consider implementing API authentication for production use
Monitor resource usage as browser automation can be resource-intensive
Set up log monitoring in Coolify

📊 Monitoring

Health check endpoint: /health
Job status tracking: /jobs
Container logs available in Coolify dashboard
Set up alerts for failed jobs

🚨 Troubleshooting
Common Issues

"Cookie file not found"

Upload cookies using /upload-cookies endpoint
Ensure cookies file is in the container


"Navigation failed"

Check if Google Labs is accessible
Verify cookies are not expired


"Browser launch failed"

Ensure container has sufficient resources
Check Playwright installation in container


Long processing times

Video generation typically takes 2-5 minutes
Check progress via /job/{job_id} endpoint



Logs
Check application logs in Coolify dashboard for detailed error information.
📈 Scaling
For high-volume usage:

Deploy multiple instances behind a load balancer
Use Redis for job state management
Implement job queuing with Celery
Consider dedicated browser pool management