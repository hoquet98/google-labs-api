"""
Browser setup and navigation for Google Labs automation
"""
from playwright.async_api import async_playwright

class NavigationHandler:
    def __init__(self, headless=False):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    async def setup_browser(self):
        """
        Initialize Playwright and browser
        """
        if self.headless:
            print("🔇 Running in headless mode (no browser window)")
        else:
            print("👁️  Running in visible mode (browser window will open)")
        
        # Start Playwright
        self.playwright = await async_playwright().start()
        
        # Launch browser with user's headless preference
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        
        # Create browser context
        self.context = await self.browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        print("✅ Browser setup complete")
        return self.context
    
    async def create_page(self):
        """
        Create a new page in the browser context
        """
        if not self.context:
            raise ValueError("Browser context not initialized. Call setup_browser() first.")
        
        self.page = await self.context.new_page()
        print("✅ New page created")
        return self.page
    
    async def navigate_to_google_labs(self):
        """
        Navigate to Google Labs Flow Tools
        """
        if not self.page:
            raise ValueError("Page not created. Call create_page() first.")
        
        print("🌐 Navigating to Google Labs...")
        
        try:
            # First try the main labs page
            await self.page.goto('https://labs.google', timeout=30000)
            await self.page.wait_for_load_state('networkidle')
            print("✅ Successfully loaded main Google Labs page")
            
            # Then try to navigate to the flow tools
            print("🔄 Navigating to Flow Tools...")
            await self.page.goto('https://labs.google/fx/tools/flow', timeout=30000)
            await self.page.wait_for_load_state('networkidle')
            print("✅ Successfully loaded Google Labs Flow Tools")
            
            return True
            
        except Exception as nav_error:
            print(f"⚠️  Navigation error: {nav_error}")
            print("🔄 Trying alternative approach...")
            
            try:
                # Alternative: try going directly to labs.google
                await self.page.goto('https://labs.google', timeout=30000)
                await self.page.wait_for_load_state('networkidle')
                print("✅ Loaded main Google Labs page as fallback")
                return True
                
            except Exception as fallback_error:
                print(f"❌ Could not load Google Labs: {fallback_error}")
                print("💡 This might be a network issue or the cookies might be expired")
                return False
    
    async def check_authentication(self):
        """
        Check if user is authenticated on Google Labs
        """
        if not self.page:
            raise ValueError("Page not created. Call create_page() first.")
        
        print("🔍 Checking authentication status...")
        
        # Get current URL and page info
        current_url = self.page.url
        print(f"📍 Current URL: {current_url}")
        
        # Take a screenshot for verification
        await self.page.screenshot(path='google_labs_loaded.png')
        print("📸 Screenshot saved as 'google_labs_loaded.png'")
        
        # Get page title
        title = await self.page.title()
        print(f"📄 Page title: {title}")
        
        try:
            # Wait a moment for any redirects or dynamic content
            await self.page.wait_for_timeout(3000)
            
            # Check for common Google authentication indicators
            auth_indicators = [
                'img[alt*="profile"]',
                '[data-ogsr-up]',
                '.gb_d',
                '[aria-label*="Account"]',
                '.gb_D'
            ]
            
            authenticated = False
            for selector in auth_indicators:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=2000)
                    if element:
                        print(f"✅ Authentication confirmed! Found: {selector}")
                        authenticated = True
                        break
                except:
                    continue
            
            if not authenticated:
                print("🤔 No clear authentication indicators found, but you may still be logged in")
                print("👀 Check the browser window to see if you have access to the tools")
            
            return authenticated
            
        except Exception as e:
            print(f"⚠️  Error checking authentication: {e}")
            return False
    
    async def get_page_info(self):
        """
        Get current page information
        """
        if not self.page:
            return None
        
        return {
            'url': self.page.url,
            'title': await self.page.title()
        }
    
    async def take_screenshot(self, filename):
        """
        Take a screenshot of the current page
        """
        if not self.page:
            raise ValueError("Page not created.")
        
        await self.page.screenshot(path=filename)
        print(f"📸 Screenshot saved as '{filename}'")
    
    async def wait_for_page_load(self, timeout=30000):
        """
        Wait for page to be fully loaded
        """
        if not self.page:
            raise ValueError("Page not created.")
        
        await self.page.wait_for_load_state('networkidle', timeout=timeout)
        print("✅ Page loaded completely")
    
    async def cleanup(self):
        """
        Clean up browser resources
        """
        if self.browser:
            await self.browser.close()
            print("🧹 Browser closed")
        
        if self.playwright:
            await self.playwright.stop()
            print("🧹 Playwright stopped")
    
    def is_headless(self):
        """
        Check if running in headless mode
        """
        return self.headless