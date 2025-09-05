"""
UI interactions for Google Labs automation - button clicks, form filling
"""

class UIInteractions:
    def __init__(self, page):
        self.page = page
    
    async def click_new_project(self):
        """
        Find and click the 'New project' button using exact HTML selectors
        """
        print("🔍 Looking for 'New project' button...")
        
        try:
            # Wait for the page to be fully loaded first
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(3000)  # Extra wait for dynamic content
            
            # Use the exact selector from the provided HTML
            exact_selector = 'button.sc-7d2e2cf5-1.hoBDwb.sc-e877996-0.eCyFgY'
            
            print(f"   Looking for exact selector: {exact_selector}")
            
            # Try exact selector first
            success = await self._try_button_click(exact_selector, "exact selector")
            if success:
                return True
            
            # Fallback: try text-based selector
            print("🔄 Trying fallback text-based selector...")
            text_selector = 'button:has-text("New project")'
            success = await self._try_button_click(text_selector, "text-based selector")
            if success:
                return True
            
            # Debug: Show available buttons
            await self._debug_available_buttons()
            return False
            
        except Exception as e:
            print(f"❌ Error while trying to click 'New project': {e}")
            return False
    
    async def _try_button_click(self, selector, selector_type):
        """
        Try to click a button with the given selector
        """
        try:
            button = await self.page.wait_for_selector(selector, timeout=10000)
            if button:
                # Verify it's visible and enabled
                is_visible = await button.is_visible()
                is_enabled = await button.is_enabled()
                
                if is_visible and is_enabled:
                    print(f"✅ Found 'New project' button with {selector_type}!")
                    
                    # Scroll button into view if needed
                    await button.scroll_into_view_if_needed()
                    
                    # Click the button
                    await button.click()
                    print("🎯 Successfully clicked 'New project' button!")
                    
                    # Wait for any navigation or modal to appear
                    await self.page.wait_for_timeout(3000)
                    
                    # Take screenshot after clicking
                    await self.page.screenshot(path='after_new_project_click.png')
                    print("📸 Screenshot saved: 'after_new_project_click.png'")
                    
                    return True
                else:
                    print(f"   Button found but not clickable (visible: {is_visible}, enabled: {is_enabled})")
            return False
            
        except Exception:
            return False
    
    async def _debug_available_buttons(self):
        """
        Debug helper to show available buttons on the page
        """
        print("🔍 Showing available buttons for debugging...")
        try:
            all_buttons = await self.page.query_selector_all('button')
            print(f"   Found {len(all_buttons)} buttons on the page:")
            
            for i, button in enumerate(all_buttons[:5]):  # Show first 5 buttons
                try:
                    text = await button.text_content()
                    classes = await button.get_attribute('class')
                    print(f"   {i+1}. '{text.strip() if text else 'No text'}' | Classes: {classes}")
                except:
                    print(f"   {i+1}. Button (could not read)")
        except Exception as e:
            print(f"   Debug error: {e}")
    
    async def enter_prompt_and_go(self, prompt_text):
        """
        Enter a prompt into the textarea and click the Go button
        """
        print(f"✍️  Entering prompt: '{prompt_text[:50]}...'")
        
        try:
            # Wait for the page elements to be ready
            await self.page.wait_for_load_state('networkidle')
            await self.page.wait_for_timeout(2000)
            
            # Enter the prompt
            success = await self._enter_prompt_text(prompt_text)
            if not success:
                return False
            
            # Click the Go button
            success = await self._click_go_button()
            if not success:
                return False
            
            # Take screenshot after submitting
            await self.page.screenshot(path='after_prompt_submission.png')
            print("📸 Screenshot saved: 'after_prompt_submission.png'")
            
            return True
            
        except Exception as e:
            print(f"❌ Error entering prompt and clicking Go: {e}")
            await self._debug_available_inputs()
            return False
    
    async def _enter_prompt_text(self, prompt_text):
        """
        Enter text into the prompt textarea
        """
        # Find the textarea using the exact ID
        textarea_selector = '#PINHOLE_TEXT_AREA_ELEMENT_ID'
        print(f"🔍 Looking for textarea: {textarea_selector}")
        
        try:
            textarea = await self.page.wait_for_selector(textarea_selector, timeout=10000)
            if not textarea:
                print("❌ Could not find the prompt textarea")
                return False
            
            # Check if textarea is visible and enabled
            is_visible = await textarea.is_visible()
            is_enabled = await textarea.is_enabled()
            
            if not (is_visible and is_enabled):
                print(f"❌ Textarea not ready (visible: {is_visible}, enabled: {is_enabled})")
                return False
            
            print("✅ Found prompt textarea")
            
            # Clear any existing text and enter the prompt
            await textarea.click()  # Focus on the textarea
            await textarea.fill('')  # Clear existing content
            await textarea.fill(prompt_text)  # Instant text entry
            
            print("✅ Successfully entered prompt text")
            
            # Wait a moment for the text to be processed
            await self.page.wait_for_timeout(1000)
            
            return True
            
        except Exception as e:
            print(f"❌ Error entering text: {e}")
            return False
    
    async def _click_go_button(self):
        """
        Click the Go/Submit button
        """
        # Find the Go button using exact classes
        button_selector = 'button.sc-7d2e2cf5-1.hwJkVV.sc-408537d4-2.gdXWm'
        print(f"🔍 Looking for Go button: {button_selector}")
        
        try:
            go_button = await self.page.wait_for_selector(button_selector, timeout=10000)
            if not go_button:
                print("❌ Could not find the Go button")
                return False
            
            # Check if button is visible and enabled
            button_visible = await go_button.is_visible()
            button_enabled = await go_button.is_enabled()
            
            if not (button_visible and button_enabled):
                print(f"❌ Go button not ready (visible: {button_visible}, enabled: {button_enabled})")
                return False
            
            print("✅ Found Go button")
            
            # Scroll button into view and click
            await go_button.scroll_into_view_if_needed()
            await go_button.click()
            
            print("🚀 Successfully clicked Go button!")
            
            # Wait for any processing to start
            await self.page.wait_for_timeout(3000)
            
            return True
            
        except Exception as e:
            print(f"❌ Error clicking Go button: {e}")
            return False
    
    async def _debug_available_inputs(self):
        """
        Debug helper to show available inputs and buttons
        """
        print("🔍 Debug - looking for available inputs and buttons...")
        try:
            # Check textareas
            textareas = await self.page.query_selector_all('textarea')
            print(f"   Found {len(textareas)} textareas")
            for i, ta in enumerate(textareas[:3]):
                ta_id = await ta.get_attribute('id')
                ta_placeholder = await ta.get_attribute('placeholder')
                print(f"   {i+1}. ID: {ta_id}, Placeholder: {ta_placeholder}")
            
            # Check buttons
            buttons = await self.page.query_selector_all('button')
            print(f"   Found {len(buttons)} buttons")
            for i, btn in enumerate(buttons[:5]):
                btn_classes = await btn.get_attribute('class')
                btn_text = await btn.text_content()
                print(f"   {i+1}. Classes: {btn_classes[:50]}..., Text: {btn_text[:30] if btn_text else 'No text'}")
                
        except Exception as debug_error:
            print(f"   Debug error: {debug_error}")
    
    async def wait_for_element(self, selector, timeout=10000):
        """
        Wait for an element to appear on the page
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            return element is not None
        except:
            return False
    
    async def element_exists(self, selector):
        """
        Check if an element exists on the page
        """
        try:
            element = await self.page.query_selector(selector)
            return element is not None
        except:
            return False