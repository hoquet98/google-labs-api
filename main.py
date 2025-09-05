"""
Main orchestrator for Google Labs automation
Coordinates all modules and handles user interaction
"""
import asyncio
from cookie_handler import CookieHandler
from navigation_handler import NavigationHandler
from ui_interactions import UIInteractions
from video_handler import handle_video_workflow

class GoogleLabsAutomation:
    def __init__(self):
        self.cookie_handler = None
        self.navigation_handler = None
        self.ui_interactions = None
        self.page = None
    
    def get_user_preferences(self):
        """
        Ask user for their preferences
        """
        print("🤖 Google Labs Automation Setup")
        print("=" * 40)
        
        while True:
            headless_input = input("Do you want to run in headless mode? (y/n): ").lower().strip()
            if headless_input in ['y', 'yes']:
                return True
            elif headless_input in ['n', 'no']:
                return False
            else:
                print("Please enter 'y' for yes or 'n' for no")
    
    async def setup_components(self, headless_mode):
        """
        Initialize all components
        """
        print("🔧 Setting up automation components...")
        
        # Initialize cookie handler
        self.cookie_handler = CookieHandler()
        
        # Initialize navigation handler
        self.navigation_handler = NavigationHandler(headless=headless_mode)
        
        # Setup browser and load cookies
        context = await self.navigation_handler.setup_browser()
        await self.cookie_handler.load_cookies()
        await self.cookie_handler.add_cookies_to_context(context)
        
        # Create page and setup UI interactions
        self.page = await self.navigation_handler.create_page()
        self.ui_interactions = UIInteractions(self.page)
        
        print("✅ All components initialized successfully")
    
    async def navigate_and_authenticate(self):
        """
        Navigate to Google Labs and check authentication
        """
        print("\n" + "="*50)
        print("🌐 NAVIGATION & AUTHENTICATION")
        print("="*50)
        
        # Navigate to Google Labs
        success = await self.navigation_handler.navigate_to_google_labs()
        if not success:
            return False
        
        # Check authentication
        authenticated = await self.navigation_handler.check_authentication()
        
        if authenticated:
            print("✅ Successfully authenticated and ready to proceed!")
        else:
            print("⚠️  Authentication status unclear - proceeding anyway")
        
        return True
    
    async def create_new_project(self):
        """
        Click the 'New project' button
        """
        print("\n" + "="*50)
        print("🚀 CREATING NEW PROJECT")
        print("="*50)
        
        success = await self.ui_interactions.click_new_project()
        
        if success:
            print("✅ Successfully initiated new project creation!")
            print("👀 New project interface should be loaded")
            
            # Wait for the new project page to load
            await self.page.wait_for_timeout(5000)
            return True
        else:
            print("⚠️  Could not automatically click 'New project'")
            print("💡 You may need to click it manually in the browser")
            return False
    
    async def generate_video(self, prompt):
        """
        Enter prompt and generate video
        """
        print("\n" + "="*50)
        print("🎬 VIDEO GENERATION")
        print("="*50)
        
        print(f"📝 Using prompt: '{prompt}'")
        
        success = await self.ui_interactions.enter_prompt_and_go(prompt)
        
        if success:
            print("✅ Successfully submitted video generation prompt!")
            print("🎬 Video generation should now be starting...")
            return True
        else:
            print("⚠️  Could not submit prompt automatically")
            print("💡 You may need to enter it manually in the browser")
            return False
    
    async def handle_video_processing(self):
        """
        Monitor video progress and download when complete
        """
        print("\n" + "="*50)
        print("📊 VIDEO PROCESSING & DOWNLOAD")
        print("="*50)
        
        # Use the video handler module for monitoring and downloading
        downloaded_files = await handle_video_workflow(self.page)
        
        if downloaded_files:
            print(f"\n🎉 COMPLETE! Successfully downloaded {len(downloaded_files)} videos")
            print("📁 Files saved to 'downloads' folder:")
            for file in downloaded_files:
                print(f"   📄 {file}")
            return True
        else:
            print("\n💡 Video processing completed but download failed")
            print("💡 You can manually download videos from the browser if needed")
            return False
    
    async def wait_for_user_review(self, headless_mode):
        """
        Wait for user to review results
        """
        print("\n" + "="*50)
        print("⏰ COMPLETION")
        print("="*50)
        
        if headless_mode:
            print("🔇 Process completed in headless mode")
            print("💡 Press Ctrl+C to stop if needed")
            print("📁 Check the 'downloads' folder for your MP4 files!")
            
            # In headless mode, wait less time since user can't interact
            try:
                await self.page.wait_for_timeout(60000)  # Wait 60 seconds
            except KeyboardInterrupt:
                print("\n🛑 Stopped by user")
        else:
            print("👁️  Browser will stay open for 3 minutes for you to review results")
            print("💡 Close manually anytime or press Ctrl+C to stop")
            print("📁 Check the 'downloads' folder for your MP4 files!")
            
            # Keep browser open for inspection in visible mode
            try:
                await self.page.wait_for_timeout(180000)  # Wait 3 minutes
            except KeyboardInterrupt:
                print("\n🛑 Stopped by user")
    
    async def cleanup(self):
        """
        Clean up all resources
        """
        if self.navigation_handler:
            await self.navigation_handler.cleanup()
        print("✅ Cleanup completed")
    
    async def run_full_automation(self):
        """
        Run the complete automation workflow
        """
        headless_mode = None
        
        try:
            # Get user preferences
            headless_mode = self.get_user_preferences()
            
            print("-" * 50)
            if headless_mode:
                print("🔇 Headless mode selected - no browser window will be shown")
                print("📊 Progress will be shown in the terminal")
            else:
                print("👁️  Visible mode selected - browser window will open")
                print("👀 You'll be able to see the automation in action")
            print("-" * 50)
            
            # Setup all components
            await self.setup_components(headless_mode)
            
            # Navigate and authenticate
            nav_success = await self.navigate_and_authenticate()
            if not nav_success:
                print("❌ Navigation failed - stopping automation")
                return
            
            # Create new project
            project_success = await self.create_new_project()
            if not project_success:
                print("⚠️  New project creation failed - you may need to do this manually")
                await self.wait_for_user_review(headless_mode)
                return
            
            # Generate video with test prompt
            test_prompt = "A majestic golden retriever running through a sunlit meadow with wildflowers, slow motion, cinematic lighting, beautiful nature background"
            
            video_success = await self.generate_video(test_prompt)
            if not video_success:
                print("⚠️  Video generation failed - you may need to do this manually")
                await self.wait_for_user_review(headless_mode)
                return
            
            # Handle video processing and download
            await self.handle_video_processing()
            
            # Wait for user review
            await self.wait_for_user_review(headless_mode)
            
        except Exception as e:
            print(f"❌ Automation error: {e}")
            if headless_mode is not None:
                await self.wait_for_user_review(headless_mode)
        
        finally:
            await self.cleanup()

async def main():
    """
    Main entry point
    """
    print("🚀 Starting Google Labs automation with video download...")
    print("📁 Using cookies from: labs.google_cookies.json")
    print("🎯 Target URL: https://labs.google/fx/tools/flow")
    print("⬇️  Will automatically download generated MP4 videos")
    print("-" * 50)
    
    automation = GoogleLabsAutomation()
    await automation.run_full_automation()

if __name__ == "__main__":
    asyncio.run(main())