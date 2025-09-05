"""
Video monitoring and download functionality for Google Labs automation
"""
import asyncio
import aiohttp
import os

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

async def download_video(session, video_url, filename):
    """
    Download a single video from URL
    """
    try:
        print(f"⬇️  Downloading: {filename}")
        
        async with session.get(video_url) as response:
            if response.status == 200:
                # Create downloads directory if it doesn't exist
                os.makedirs('downloads', exist_ok=True)
                
                filepath = os.path.join('downloads', filename)
                
                with open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                
                print(f"✅ Downloaded: {filepath}")
                return filepath
            else:
                print(f"❌ Failed to download {filename}: HTTP {response.status}")
                return None
                
    except Exception as e:
        print(f"❌ Error downloading {filename}: {e}")
        return None

async def download_generated_videos(page):
    """
    Find and download all generated videos
    """
    print("🎬 Looking for generated videos to download...")
    
    try:
        # Wait for videos to be fully loaded
        await page.wait_for_timeout(3000)
        
        # Find all video elements with Google Storage URLs
        video_elements = await page.query_selector_all('video[src*="storage.googleapis.com"]')
        
        if not video_elements:
            print("❌ No videos found to download")
            return []
        
        print(f"🎯 Found {len(video_elements)} videos to download")
        
        downloaded_files = []
        
        # Create aiohttp session for downloads
        async with aiohttp.ClientSession() as session:
            for i, video_element in enumerate(video_elements, 1):
                try:
                    video_url = await video_element.get_attribute('src')
                    if video_url:
                        # Generate filename
                        filename = f"google_labs_video_{i}.mp4"
                        
                        # Download the video
                        filepath = await download_video(session, video_url, filename)
                        if filepath:
                            downloaded_files.append(filepath)
                    
                except Exception as e:
                    print(f"❌ Error processing video {i}: {e}")
        
        if downloaded_files:
            print(f"🎉 Successfully downloaded {len(downloaded_files)} videos!")
            for file in downloaded_files:
                print(f"   📁 {file}")
        else:
            print("❌ No videos were downloaded successfully")
        
        return downloaded_files
        
    except Exception as e:
        print(f"❌ Error downloading videos: {e}")
        return []

async def handle_video_workflow(page):
    """
    Complete video workflow: monitor progress and download videos
    """
    print("\n📊 Starting video monitoring and download workflow...")
    
    # Monitor progress until completion
    progress_complete = await monitor_video_progress(page)
    
    if progress_complete:
        print("\n⬇️  Videos are ready! Starting download...")
        
        # Download the generated videos
        downloaded_files = await download_generated_videos(page)
        
        if downloaded_files:
            print(f"\n🎉 SUCCESS! Downloaded {len(downloaded_files)} videos:")
            for file in downloaded_files:
                print(f"   📁 {file}")
            print("💡 Check the 'downloads' folder in your project directory")
            return downloaded_files
        else:
            print("\n⚠️  Videos appeared ready but download failed")
            print("💡 You can manually download them from the browser")
            return []
    else:
        print("\n⏰ Progress monitoring timed out or failed")
        print("💡 Videos may still be processing - check the browser")
        return []