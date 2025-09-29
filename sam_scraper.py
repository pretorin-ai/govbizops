"""
SAM.gov web scraper for fetching full solicitation descriptions
Uses Playwright to handle JavaScript-rendered content
"""

import logging
import re
import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SAMWebScraper:
    """Scrapes solicitation details from SAM.gov web pages"""
    
    def __init__(self, headless: bool = True, server_mode: bool = False):
        """
        Initialize the SAM.gov scraper
        
        Args:
            headless: Whether to run browser in headless mode
            server_mode: Enable additional optimizations for server environments
        """
        self.headless = headless
        self.server_mode = server_mode
        self.browser: Optional[Browser] = None
        self.playwright = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.stop()
        
    async def start(self):
        """Start the browser"""
        if not self.playwright:
            self.playwright = await async_playwright().start()
            
            # Browser arguments optimized for server environments
            browser_args = [
                '--disable-dev-shm-usage',  # Helps with Docker/WSL
                '--disable-setuid-sandbox',
                '--no-sandbox',  # Required in some Docker environments
            ]
            
            if self.server_mode:
                # Additional server optimizations
                browser_args.extend([
                    '--disable-gpu',  # No GPU in most servers
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-blink-features=AutomationControlled',
                    '--window-size=1920,1080',  # Fixed size for consistency
                    '--start-maximized',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                ])
            
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=browser_args
            )
            logger.info(f"Browser started successfully (server_mode={self.server_mode})")
    
    async def stop(self):
        """Stop the browser"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            logger.info("Browser stopped")
    
    async def scrape_opportunity(self, url: str) -> Dict[str, Any]:
        """
        Scrape opportunity details from SAM.gov URL
        
        Args:
            url: The SAM.gov opportunity URL
            
        Returns:
            Dictionary with scraped data
        """
        if not self.browser:
            await self.start()
            
        page = await self.browser.new_page()
        result = {
            'url': url,
            'success': False,
            'description': None,
            'attachments': [],
            'error': None
        }
        
        try:
            logger.info(f"Navigating to: {url}")
            
            # Navigate to the page
            await page.goto(url, wait_until='networkidle', timeout=30000)
            
            # Wait for the main content to load
            # SAM.gov uses various selectors, try multiple approaches
            content_selectors = [
                '[data-test="opportunity-description"]',
                '.opportunity-description',
                '[class*="description-content"]',
                'div[class*="Description"]',
                'section[aria-label*="Description"]'
            ]
            
            content_found = False
            for selector in content_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    content_found = True
                    logger.info(f"Found content with selector: {selector}")
                    break
                except:
                    continue
            
            if not content_found:
                # Fallback: wait for any text content
                await page.wait_for_load_state('domcontentloaded')
                await asyncio.sleep(3)  # Give React time to render
            
            # Get the page content
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract description - try multiple approaches
            description_text = None
            
            # Method 1: Look for description sections
            description_patterns = [
                {'name': 'div', 'attrs': {'data-test': re.compile('description')}},
                {'name': 'div', 'class': re.compile('description', re.I)},
                {'name': 'section', 'attrs': {'aria-label': re.compile('description', re.I)}},
                {'name': 'div', 'class': re.compile('opportunity-content', re.I)}
            ]
            
            for pattern in description_patterns:
                elements = soup.find_all(**pattern)
                for elem in elements:
                    text = elem.get_text(strip=True, separator='\n')
                    if text and len(text) > 100:  # Meaningful content
                        description_text = text
                        logger.info(f"Found description using pattern: {pattern}")
                        break
                if description_text:
                    break
            
            # Method 2: If no description found, look for main content area
            if not description_text:
                main_content = soup.find('main') or soup.find('div', {'role': 'main'})
                if main_content:
                    # Remove navigation and header elements
                    for tag in main_content.find_all(['nav', 'header', 'footer']):
                        tag.decompose()
                    
                    text = main_content.get_text(strip=True, separator='\n')
                    if text and len(text) > 200:
                        description_text = text
                        logger.info("Found description in main content area")
            
            # Extract attachments/documents
            attachment_links = []
            
            # Look for attachment sections
            attachment_patterns = [
                {'name': 'a', 'href': re.compile(r'\.pdf|\.doc|\.xlsx|\.zip', re.I)},
                {'name': 'a', 'attrs': {'aria-label': re.compile('download|attachment', re.I)}},
                {'name': 'div', 'class': re.compile('attachment|document', re.I)}
            ]
            
            for pattern in attachment_patterns:
                elements = soup.find_all(**pattern)
                for elem in elements:
                    if elem.name == 'a':
                        href = elem.get('href', '')
                        text = elem.get_text(strip=True)
                        if href and text:
                            attachment_links.append({
                                'name': text,
                                'url': href if href.startswith('http') else f"https://sam.gov{href}"
                            })
                    else:
                        # Look for links within the element
                        links = elem.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            text = link.get_text(strip=True)
                            if href and text:
                                attachment_links.append({
                                    'name': text,
                                    'url': href if href.startswith('http') else f"https://sam.gov{href}"
                                })
            
            # Remove duplicates
            seen = set()
            unique_attachments = []
            for att in attachment_links:
                key = (att['name'], att['url'])
                if key not in seen:
                    seen.add(key)
                    unique_attachments.append(att)
            
            result['success'] = True
            result['description'] = description_text
            result['attachments'] = unique_attachments
            
            logger.info(f"Successfully scraped opportunity. Description length: {len(description_text) if description_text else 0}")
            logger.info(f"Found {len(unique_attachments)} attachments")
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            result['error'] = str(e)
            
        finally:
            await page.close()
            
        return result
    
    def scrape_sync(self, url: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for scraping
        
        Args:
            url: The SAM.gov opportunity URL
            
        Returns:
            Dictionary with scraped data
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.scrape_opportunity(url))
        finally:
            loop.close()


# Convenience function for one-off scraping
def scrape_sam_opportunity(url: str, headless: bool = True, server_mode: bool = None) -> Dict[str, Any]:
    """
    Scrape a single SAM.gov opportunity
    
    Args:
        url: The SAM.gov opportunity URL
        headless: Whether to run browser in headless mode
        server_mode: Enable server optimizations (auto-detected if None)
        
    Returns:
        Dictionary with scraped data
    """
    # Auto-detect server mode if not specified
    if server_mode is None:
        import os
        # Common server environment indicators
        server_mode = any([
            os.environ.get('KUBERNETES_SERVICE_HOST'),
            os.environ.get('DOCKER_CONTAINER'),
            os.path.exists('/.dockerenv'),
            not os.environ.get('DISPLAY'),  # No display in servers
        ])
        if server_mode:
            logger.info("Auto-detected server environment")
    
    async def _scrape():
        async with SAMWebScraper(headless=headless, server_mode=server_mode) as scraper:
            return await scraper.scrape_opportunity(url)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_scrape())
    finally:
        loop.close()