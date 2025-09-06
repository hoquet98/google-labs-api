"""
Automation service for API usage
Modified version of the original automation for web service use
"""
import asyncio
import os
from cookie_handler import CookieHandler
from navigation_handler import NavigationHandler
from ui_interactions import UIInteractions
from video_handler import download_generated_videos_and_images
import logging

logger = logging.getLogger(__name__)

class GoogleLabsService:
    def __init__(self):
        self.active_browsers = {}
    
    async def generate_video(
        self, 
        prompt: str, 
        headless: bool = True, 
        cookies_file: str = "labs.google_cookies.json",
        job_id: str = None,
        progress_callback=None
    ):
        """
        Generate video using Google Labs automation
        
        Args:
            prompt: Text prompt for video generation
            headless: Whether to run browser in headless mode
            cookies_file: Path to cookies JSON file
            job_id: Unique identifier for this job
            progress_callback: Function to call with progress updates
            
        Returns:
            dict: Result with success status, videos list, images list, or error message
        """
        
        def update_progress(message):
            if progress_callback:
                progress_callback(message)
            logger.info(f"Job {job_id}: {message}")
        
        cookie_handler = None
        navigation_handler = None
        ui_interactions = None
        page = None
        
        try:
            update_progress("Initializing automation components...")
            
            # Initialize components
            cookie_handler = CookieHandler(cookies_file)
            navigation_handler = NavigationHandler(headless=headless)
            
            # Setup browser and load cookies
            update_progress("Setting up browser and loading cookies...")
            context = await navigation_handler.setup_browser()
            await cookie_handler.load_cookies()
            await cookie_handler.add_cookies_to_context(context)
            
            # Create page and UI interactions
            page = await navigation_handler.create_page()
            ui_interactions = UIInteractions(page)
            
            # Store browser reference for cleanup
            if job_id:
                self.active_browsers[job_id] = navigation_handler
            
            update_progress("Navigating to Google Labs...")
            
            # Navigate to Google Labs
            success = await navigation_handler.navigate_to_google_labs()
            if not success:
                logger.error(f"Job {job_id}: Navigation to Google Labs failed")
                return {
                    "success": False,
                    "error": "Failed to navigate to Google Labs",
                    "videos": [],
                    "images": []
                }
            
            # Check authentication
            update_progress("Checking authentication status...")
            authenticated = await navigation_handler.check_authentication()
            
            if not authenticated:
                logger.warning(f"Job {job_id}: Authentication status unclear, proceeding anyway")
            
            # Create new project
            update_progress("Creating new project...")
            project_success = await ui_interactions.click_new_project()
            
            if not project_success:
                logger.error(f"Job {job_id}: Failed to create new project")
                return {
                    "success": False,
                    "error": "Failed to create new project - cookies may be expired",
                    "videos": [],
                    "images": []
                }
            
            # Wait for new project page to load
            await page.wait_for_timeout(5000)
            
            # Generate video
            update_progress(f"Submitting video prompt: '{prompt[:50]}...'")
            video_success = await ui_interactions.enter_prompt_and_go(prompt)
            
            if not video_success:
                logger.error(f"Job {job_id}: Failed to submit video generation prompt")
                return {
                    "success": False,
                    "error": "Failed to submit video generation prompt",
                    "videos": [],
                    "images": []
                }
            
            # Monitor video processing and download
            update_progress("Monitoring video generation progress...")
            result = await self._handle_video_workflow_with_progress(
                page, update_progress, job_id
            )
            
            logger.info(f"Job {job_id}: Video workflow returned: {result}")
            
            if result and (result.get("videos") or result.get("images")):
                video_urls = result.get("videos", [])
                image_urls = result.get("images", [])
                
                update_progress(f"Successfully uploaded {len(video_urls)} videos and {len(image_urls)} images to S3!")
                logger.info(f"Job {job_id}: Returning success with {len(video_urls)} videos and {len(image_urls)} images")
                
                return {
                    "success": True,
                    "error": None,
                    "videos": video_urls,
                    "images": image_urls,
                    "prompt": prompt
                }
            else:
                logger.error(f"Job {job_id}: No videos or images returned from workflow")
                return {
                    "success": False,
                    "error": "Video generation completed but S3 upload failed - no videos or images returned",
                    "videos": [],
                    "images": []
                }
                
        except Exception as e:
            error_msg = f"Automation error: {str(e)}"
            logger.error(f"Job {job_id}: {error_msg}")
            update_progress(f"Error: {error_msg}")
            
            return {
                "success": False,
                "error": error_msg,
                "videos": [],
                "images": []
            }
            
        finally:
            # Cleanup browser resources
            if navigation_handler:
                try:
                    await navigation_handler.cleanup()
                    if job_id and job_id in self.active_browsers:
                        del self.active_browsers[job_id]
                except Exception as e:
                    logger.warning(f"Error during cleanup: {e}")
    
    async def _handle_video_workflow_with_progress(self, page, progress_callback, job_id=None):
        """
        Modified video workflow with progress callbacks
        """
        progress_callback("Starting video monitoring and S3 upload workflow...")
        
        # Monitor progress until completion
        progress_complete = await self._monitor_video_progress_with_callback(
            page, progress_callback
        )
        
        if progress_complete:
            progress_callback("Videos are ready! Starting download and S3 upload...")
            
            # Download and upload the generated videos and images to S3
            result = await download_generated_videos_and_images(page, job_id)
            
            logger.info(f"Job {job_id}: download_generated_videos_and_images returned: {result}")
            
            if result and (result.get("videos") or result.get("images")):
                video_count = len(result.get("videos", []))
                image_count = len(result.get("images", []))
                progress_callback(f"SUCCESS! Uploaded {video_count} videos and {image_count} images to S3")
                logger.info(f"Job {job_id}: Successfully got {video_count} videos and {image_count} images")
                return result
            else:
                progress_callback("Videos appeared ready but S3 upload failed")
                logger.error(f"Job {job_id}: S3 upload failed - empty result returned")
                return {"videos": [], "images": []}
        else:
            progress_callback("Progress monitoring timed out or failed")
            logger.error(f"Job {job_id}: Progress monitoring failed")
            return {"videos": [], "images": []}
    
    async def _monitor_video_progress_with_callback(self, page, progress_callback):
        """
        Monitor video progress with progress callbacks
        """
        progress_callback("Monitoring video generation progress...")
        
        try:
            max_wait_time = 300  # 5 minutes max
            start_time = asyncio.get_event_loop().time()
            
            while True:
                current_time = asyncio.get_event_loop().time()
                if current_time - start_time > max_wait_time:
                    progress_callback("Timeout reached (5 minutes). Videos may still be processing.")
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
                                progress_callback(f"Video generation progress: {percentage}")
                                progress_found = True
                                
                                # Check if we've reached 100%
                                if '100%' in percentage:
                                    progress_callback("Video generation complete!")
                                    await asyncio.sleep(3)  # Wait a bit more for videos to be ready
                                    return True
                                break
                    except:
                        continue
                
                # If no progress found, check if videos are already available
                if not progress_found:
                    video_elements = await page.query_selector_all('video[src*="storage.googleapis.com"]')
                    if len(video_elements) >= 2:
                        progress_callback("Videos appear to be ready!")
                        return True
                
                await page.wait_for_timeout(2000)  # Wait 2 seconds before checking again
            
            return False
            
        except Exception as e:
            progress_callback(f"Error monitoring progress: {e}")
            return False
    
    async def cleanup(self):
        """
        Cleanup all active browser instances
        """
        for job_id, navigation_handler in self.active_browsers.items():
            try:
                await navigation_handler.cleanup()
                logger.info(f"Cleaned up browser for job {job_id}")
            except Exception as e:
                logger.warning(f"Error cleaning up browser for job {job_id}: {e}")
        
        self.active_browsers.clear()
    
    def get_active_jobs(self):
        """
        Get list of active job IDs
        """
        return list(self.active_browsers.keys())
    
    async def cancel_job(self, job_id: str):
        """
        Cancel a running job by cleaning up its browser
        """
        if job_id in self.active_browsers:
            try:
                await self.active_browsers[job_id].cleanup()
                del self.active_browsers[job_id]
                logger.info(f"Cancelled job {job_id}")
                return True
            except Exception as e:
                logger.error(f"Error cancelling job {job_id}: {e}")
                return False
        return False
