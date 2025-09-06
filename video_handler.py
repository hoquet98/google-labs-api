"""
Video monitoring and download functionality for Google Labs automation
"""
import asyncio
import aiohttp
import os
import boto3
from botocore.exceptions import ClientError
import tempfile
import logging

logger = logging.getLogger(__name__)

class S3Config:
    def __init__(self):
        self.endpoint_url = os.getenv('S3_ENDPOINT_URL', 'http://minio:9000')
        self.access_key = os.getenv('S3_ACCESS_KEY')
        self.secret_key = os.getenv('S3_SECRET_KEY')
        self.bucket_name = os.getenv('S3_BUCKET_NAME', 'google-labs-videos')
        self.region = os.getenv('S3_REGION', 'us-east-1')

def get_s3_client():
    """Get configured S3 client for MinIO"""
    config = S3Config()
    
    return boto3.client(
        's3',
        endpoint_url=config.endpoint_url,
        aws_access_key_id=config.access_key,
        aws_secret_access_key=config.secret_key,
        region_name=config.region
    )

def ensure_bucket_exists(s3_client, bucket_name):
    """Create S3 bucket if it doesn't exist"""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            try:
                s3_client.create_bucket(Bucket=bucket_name)
                logger.info(f"Created S3 bucket: {bucket_name}")
            except ClientError as create_error:
                logger.error(f"Failed to create bucket {bucket_name}: {create_error}")
                raise
        else:
            logger.error(f"Error checking bucket {bucket_name}: {e}")
            raise

async def monitor_video_progress(page):
    """
    Monitor video generation progress until completion
    """
    print("📊 Monitoring video generation progress...")
    
    try:
        max_wait_time = 300  # 5 minutes max
        start_time = asyncio.get_event_loop().time()
        
        while True:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > max_wait_time:
                print("⏰ Timeout reached (5 minutes). Videos may still be processing.")
                break
            
            # Look for progress indicators
            progress_selectors = [
                '.sc-dd6abb21-1.iEQNVH',  # From your HTML
                '[class*="progress"]',
                '[class*="percentage"]'
            ]
            
            progress_found = False
            for selector in progress_selectors:
                try:
                    progress_elements = await page.query_selector_all(selector)
                    for element in progress_elements:
                        text = await element.text_content()
                        if text and '%' in text:
                            percentage = text.strip()
                            print(f"🎬 Video generation progress: {percentage}")
                            progress_found = True
                            
                            # Check if we've reached 100%
                            if '100%' in percentage:
                                print("✅ Video generation complete!")
                                await asyncio.sleep(3)  # Wait a bit more for videos to be ready
                                return True
                            break
                except:
                    continue
            
            # If no progress found, check if videos are already available
            if not progress_found:
                video_elements = await page.query_selector_all('video[src*="storage.googleapis.com"]')
                if len(video_elements) >= 2:
                    print("✅ Videos appear to be ready!")
                    return True
            
            await page.wait_for_timeout(2000)  # Wait 2 seconds before checking again
        
        return False
        
    except Exception as e:
        print(f"❌ Error monitoring progress: {e}")
        return False

async def download_and_upload_video(session, video_url, s3_key, job_id=None):
    """
    Download video from URL and upload directly to S3
    """
    try:
        print(f"Downloading and uploading: {s3_key}")
        
        async with session.get(video_url) as response:
            if response.status == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                    temp_path = temp_file.name
                    async for chunk in response.content.iter_chunked(8192):
                        temp_file.write(chunk)
                
                # Simple S3 upload
                s3_client = boto3.client(
                    's3',
                    endpoint_url=os.getenv('S3_ENDPOINT_URL'),
                    aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
                    aws_secret_access_key=os.getenv('S3_SECRET_KEY'),
                    region_name=os.getenv('S3_REGION', 'us-east-1')
                )
                
                s3_client.upload_file(
                    temp_path, 
                    'veo3',  # hardcoded bucket name
                    s3_key,
                    ExtraArgs={'ContentType': 'video/mp4'}
                )
                
                os.unlink(temp_path)
                s3_url = f"{os.getenv('S3_ENDPOINT_URL')}/veo3/{s3_key}"
                print(f"Uploaded to S3: {s3_url}")
                return s3_url
                
    except Exception as e:
        print(f"Error: {e}")
        return None
        
async def download_generated_videos(page, job_id=None):
    """
    Find and download all generated videos, upload to S3
    """
    print("🎬 Looking for generated videos to download and upload to S3...")
    
    try:
        # Wait for videos to be fully loaded
        await page.wait_for_timeout(3000)
        
        # Find all video elements with Google Storage URLs
        video_elements = await page.query_selector_all('video[src*="storage.googleapis.com"]')
        
        if not video_elements:
            print("❌ No videos found to download")
            return []
        
        print(f"🎯 Found {len(video_elements)} videos to download and upload")
        
        uploaded_urls = []
        
        # Create aiohttp session for downloads
        async with aiohttp.ClientSession() as session:
            for i, video_element in enumerate(video_elements, 1):
                try:
                    video_url = await video_element.get_attribute('src')
                    if video_url:
                        # Generate S3 key (path in bucket)
                        job_prefix = job_id or f"video_{int(asyncio.get_event_loop().time())}"
                        s3_key = f"google-labs/{job_prefix}/video_{i}.mp4"
                        
                        # Download and upload to S3
                        s3_url = await download_and_upload_video(session, video_url, s3_key, job_id)
                        if s3_url:
                            uploaded_urls.append(s3_url)
                    
                except Exception as e:
                    print(f"❌ Error processing video {i}: {e}")
        
        if uploaded_urls:
            print(f"🎉 Successfully uploaded {len(uploaded_urls)} videos to S3!")
            for url in uploaded_urls:
                print(f"   🔗 {url}")
        else:
            print("❌ No videos were uploaded successfully")
        
        return uploaded_urls
        
    except Exception as e:
        print(f"❌ Error downloading/uploading videos: {e}")
        return []

async def handle_video_workflow(page, job_id=None):
    """
    Complete video workflow: monitor progress and upload to S3
    """
    print("\n📊 Starting video monitoring and S3 upload workflow...")
    
    # Monitor progress until completion
    progress_complete = await monitor_video_progress(page)
    
    if progress_complete:
        print("\n⬇️  Videos are ready! Starting download and S3 upload...")
        
        # Download and upload the generated videos
        uploaded_urls = await download_generated_videos(page, job_id)
        
        if uploaded_urls:
            print(f"\n🎉 SUCCESS! Uploaded {len(uploaded_urls)} videos to S3:")
            for url in uploaded_urls:
                print(f"   🔗 {url}")
            print("💡 Videos are now stored in your MinIO S3 bucket")
            return uploaded_urls
        else:
            print("\n⚠️  Videos appeared ready but S3 upload failed")
            print("💡 Check S3 credentials and connectivity")
            return []
    else:
        print("\n⏰ Progress monitoring timed out or failed")
        print("💡 Videos may still be processing - check the browser")
        return []

