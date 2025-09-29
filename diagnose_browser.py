#!/usr/bin/env python3
"""
Diagnostic script to test browser functionality in server environments
"""

import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def test_browser():
    """Test if browser can launch and render a simple page"""
    
    print("Browser Diagnostic Test")
    print("=" * 50)
    
    # Environment info
    print(f"Python version: {sys.version}")
    print(f"Running in Docker: {os.path.exists('/.dockerenv')}")
    print(f"DISPLAY env: {os.environ.get('DISPLAY', 'Not set')}")
    print(f"User: {os.environ.get('USER', 'Unknown')}")
    
    # Test browser launch
    print("\n1. Testing browser launch...")
    try:
        playwright = await async_playwright().start()
        
        # Server-optimized args
        browser_args = [
            '--disable-dev-shm-usage',
            '--disable-setuid-sandbox',
            '--no-sandbox',
            '--disable-gpu',
            '--disable-web-security',
            '--window-size=1920,1080',
        ]
        
        browser = await playwright.chromium.launch(
            headless=True,
            args=browser_args
        )
        print("✓ Browser launched successfully")
        
        # Test page creation
        print("\n2. Testing page creation...")
        page = await browser.new_page()
        print("✓ Page created successfully")
        
        # Test navigation to a simple page
        print("\n3. Testing navigation...")
        await page.goto("https://example.com", timeout=30000)
        title = await page.title()
        print(f"✓ Successfully navigated to example.com")
        print(f"  Page title: {title}")
        
        # Test JavaScript execution
        print("\n4. Testing JavaScript execution...")
        result = await page.evaluate("() => window.navigator.userAgent")
        print(f"✓ JavaScript executed successfully")
        print(f"  User Agent: {result[:60]}...")
        
        # Test SAM.gov access (basic)
        print("\n5. Testing SAM.gov access...")
        try:
            await page.goto("https://sam.gov", timeout=30000)
            sam_title = await page.title()
            print(f"✓ Successfully accessed sam.gov")
            print(f"  SAM.gov title: {sam_title}")
        except Exception as e:
            print(f"✗ Failed to access sam.gov: {e}")
        
        await browser.close()
        await playwright.stop()
        
        print("\n" + "=" * 50)
        print("✓ All tests passed! Browser should work correctly.")
        return True
        
    except Exception as e:
        print(f"\n✗ Browser test failed: {e}")
        
        # Common troubleshooting
        print("\nTroubleshooting:")
        print("1. Increase shared memory: --shm-size=1g")
        print("2. Add capabilities: --cap-add=SYS_ADMIN")
        print("3. Check system dependencies in Dockerfile")
        print("4. Try running as root: --user root")
        
        return False

def check_system_deps():
    """Check if required system dependencies are available"""
    
    print("\nSystem Dependencies Check")
    print("-" * 30)
    
    import subprocess
    
    deps_to_check = [
        'chromium',
        'chromium-browser', 
        'google-chrome',
        'google-chrome-stable'
    ]
    
    found_browser = False
    for dep in deps_to_check:
        try:
            result = subprocess.run(['which', dep], capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ Found: {dep} at {result.stdout.strip()}")
                found_browser = True
        except:
            pass
    
    if not found_browser:
        print("✗ No browser binary found in PATH")
        print("  Playwright will download its own browser")
    
    # Check shared memory
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if 'Shmem:' in line:
                    print(f"✓ Shared memory info: {line.strip()}")
                    break
    except:
        print("? Could not check shared memory")

if __name__ == "__main__":
    check_system_deps()
    
    # Run async test
    try:
        success = asyncio.run(test_browser())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted")
        sys.exit(1)