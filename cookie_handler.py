"""
Cookie loading and management for Google Labs automation
"""
import json
import os

class CookieHandler:
    def __init__(self, cookies_file="labs.google_cookies.json"):
        self.cookies_file = cookies_file
        self.cookies = []
    
    async def load_cookies(self):
        """
        Load cookies from JSON file and clean them for Playwright compatibility
        """
        print(f"🍪 Loading cookies from {self.cookies_file}...")
        
        try:
            if not os.path.exists(self.cookies_file):
                raise FileNotFoundError(f"Cookie file '{self.cookies_file}' not found!")
            
            with open(self.cookies_file, 'r') as f:
                raw_cookies = json.load(f)
            
            # Clean up cookies for Playwright compatibility
            self.cookies = self._clean_cookies(raw_cookies)
            
            print(f"✅ Loaded {len(self.cookies)} cookies successfully!")
            
            # Print email info for verification
            self._print_email_info()
            
            return self.cookies
            
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
            raise
        except json.JSONDecodeError:
            print(f"❌ Error: Invalid JSON in {self.cookies_file}!")
            raise
        except Exception as e:
            print(f"❌ Error loading cookies: {e}")
            raise
    
    def _clean_cookies(self, raw_cookies):
        """
        Clean and format cookies for Playwright compatibility
        """
        cleaned_cookies = []
        
        for cookie in raw_cookies:
            # Fix sameSite values - Playwright only accepts: Strict, Lax, None
            same_site = cookie.get('sameSite', 'Lax')
            if same_site == 'unspecified':
                same_site = 'Lax'
            elif same_site.lower() == 'lax':
                same_site = 'Lax'
            elif same_site.lower() == 'strict':
                same_site = 'Strict'
            elif same_site.lower() == 'none':
                same_site = 'None'
            
            # Create clean cookie with only required attributes
            cleaned_cookie = {
                'name': cookie['name'],
                'value': cookie['value'],
                'domain': cookie['domain'],
                'path': cookie['path'],
                'secure': cookie.get('secure', False),
                'httpOnly': cookie.get('httpOnly', False),
                'sameSite': same_site
            }
            
            # Add expiration if it exists and is not a session cookie
            if not cookie.get('session', True) and 'expirationDate' in cookie:
                cleaned_cookie['expires'] = cookie['expirationDate']
            
            cleaned_cookies.append(cleaned_cookie)
        
        return cleaned_cookies
    
    def _print_email_info(self):
        """
        Print email information from cookies for verification
        """
        for cookie in self.cookies:
            if cookie['name'] in ['email', 'EMAIL']:
                print(f"👤 Found email cookie: {cookie['value']}")
    
    async def add_cookies_to_context(self, context):
        """
        Add loaded cookies to the browser context
        """
        if not self.cookies:
            raise ValueError("No cookies loaded. Call load_cookies() first.")
        
        try:
            await context.add_cookies(self.cookies)
            print(f"✅ Added {len(self.cookies)} cookies to browser context")
            return True
        except Exception as e:
            print(f"❌ Error adding cookies to context: {e}")
            raise
    
    def get_cookie_count(self):
        """
        Get the number of loaded cookies
        """
        return len(self.cookies)
    
    def has_email_cookie(self):
        """
        Check if email cookies are present
        """
        email_cookies = [c for c in self.cookies if c['name'] in ['email', 'EMAIL']]
        return len(email_cookies) > 0
    
    def get_email_from_cookies(self):
        """
        Extract email from cookies if available
        """
        for cookie in self.cookies:
            if cookie['name'] == 'email':
                # Decode URL-encoded email
                import urllib.parse
                return urllib.parse.unquote(cookie['value'])
            elif cookie['name'] == 'EMAIL':
                # Remove quotes if present
                email = cookie['value'].strip('"')
                return urllib.parse.unquote(email)
        return None