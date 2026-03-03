"""
Base scraper class providing common functionality for all scrapers.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import time
import requests
from bs4 import BeautifulSoup

from ..core.models import Product, ScrapingResult, ScraperConfig
from ..core.config import config
from ..utils.logger import logger
from ..utils.proxy_manager import ProxyManager
from ..utils.retry_handler import RetryHandler, retry_on_exception
from ..utils.user_agent import UserAgentManager

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


class BaseScraper(ABC):
    """
    Abstract base class for all e-commerce scrapers.
    Provides common functionality like request handling, pagination, and error handling.
    """
    
    def __init__(self, scraper_config: Optional[ScraperConfig] = None):
        """
        Initialize base scraper.
        
        Args:
            scraper_config: Custom scraper configuration
        """
        # Load configuration
        self.scraper_config = scraper_config or self._load_default_config()
        
        # Initialize utilities
        self.proxy_manager = ProxyManager()
        self.retry_handler = RetryHandler(
            max_retries=self.scraper_config.max_retries,
            retry_delay=self.scraper_config.retry_delay
        )
        self.ua_manager = UserAgentManager()
        
        # Session for connection pooling
        self.session = requests.Session()
        
        # Results container
        self.result = ScrapingResult(source=self.get_source_name())
        
        logger.info(f"Initialized {self.__class__.__name__}")
    
    def _load_default_config(self) -> ScraperConfig:
        """Load default scraper configuration from config file."""
        return ScraperConfig(
            timeout=config.get('scraping.timeout', 30),
            max_retries=config.get('scraping.max_retries', 3),
            retry_delay=config.get('scraping.retry_delay', 2),
            rate_limit_delay=config.get('scraping.rate_limit_delay', 1),
            use_proxy=config.get('proxy.enabled', False),
            max_products=config.get('scraping.max_products_per_page', 100),
            pagination_limit=config.get('scraping.pagination_limit', 10)
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """
        Get request headers with random user agent.
        
        Returns:
            Dictionary of HTTP headers
        """
        headers = config.get('headers', {})
        headers['User-Agent'] = self.ua_manager.get_user_agent()
        return headers
    
    @retry_on_exception(exceptions=(requests.RequestException,))
    @retry_on_exception(exceptions=(requests.RequestException,))
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """
        Make HTTP request with retry logic and error handling.
        Supports both requests (static pages) and Selenium (dynamic pages).
        """

        use_selenium = config.get('scraping.use_selenium', True)  # default ON

        # ---------- USE SELENIUM (for JS websites like Daraz) ----------
        if use_selenium:
            logger.info("Using Selenium to fetch page (JS rendering enabled)")

            options = Options()
            options.add_argument("--headless=new")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )

            try:
                driver.get(url)
                time.sleep(3)  # allow JS to load products

                html = driver.page_source

                # Create fake response object (so rest of code unchanged)
                response = requests.Response()
                response.status_code = 200
                response._content = html.encode("utf-8")

                return response

            finally:
                driver.quit()

        # ---------- NORMAL REQUESTS (for static sites) ----------
        request_kwargs = {
            'headers': self._get_headers(),
            'timeout': self.scraper_config.timeout,
            **kwargs
        }

        if self.scraper_config.use_proxy:
            proxy = self.proxy_manager.get_proxy()
            if proxy:
                request_kwargs['proxies'] = proxy

        logger.debug(f"Requesting {method} {url}")
        response = self.session.request(method, url, **request_kwargs)
        response.raise_for_status()

        time.sleep(self.scraper_config.rate_limit_delay)

        return response

    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """
        Parse HTML content into BeautifulSoup object.
        
        Args:
            html_content: HTML string
            
        Returns:
            BeautifulSoup object
        """
        return BeautifulSoup(html_content, 'lxml')
    
    @abstractmethod
    def get_source_name(self) -> str:
        """
        Get the name of the source website.
        
        Returns:
            Source name (e.g., 'amazon', 'daraz')
        """
        pass
    
    @abstractmethod
    def scrape(self, url: str, **kwargs) -> ScrapingResult:
        """
        Main scraping method to be implemented by each scraper.
        
        Args:
            url: URL to scrape
            **kwargs: Additional scraper-specific arguments
            
        Returns:
            ScrapingResult containing scraped products
        """
        pass
    
    @abstractmethod
    def parse_product(self, element: Any) -> Optional[Product]:
        """
        Parse a single product from HTML element.
        
        Args:
            element: HTML element containing product data
            
        Returns:
            Product object or None if parsing fails
        """
        pass
    
    @abstractmethod
    def extract_product_list(self, soup: BeautifulSoup) -> List[Any]:
        """
        Extract list of product elements from page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of HTML elements containing products
        """
        pass
    
    @abstractmethod
    def get_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """
        Extract URL of the next page for pagination.
        
        Args:
            soup: BeautifulSoup object of current page
            current_url: Current page URL
            
        Returns:
            URL of next page or None if no next page
        """
        pass
    
    def scrape_page(self, url: str) -> List[Product]:
        """
        Scrape all products from a single page.
        
        Args:
            url: Page URL to scrape
            
        Returns:
            List of scraped Product objects
        """
        products = []
        
        try:
            # Fetch page
            response = self._make_request(url)
            #print(response.text[:2000])
            soup = self._parse_html(response.text)
            
            # Extract product elements
            product_elements = self.extract_product_list(soup)
            logger.info(f"Found {len(product_elements)} products on page")
            
            # Parse each product
            for element in product_elements:
                try:
                    product = self.parse_product(element)
                    if product:
                        products.append(product)
                        self.result.add_product(product)
                    else:
                        self.result.add_error("Failed to parse product")
                except Exception as e:
                    logger.error(f"Error parsing product: {e}")
                    self.result.add_error(str(e))
            
        except Exception as e:
            logger.error(f"Error scraping page {url}: {e}")
            self.result.add_error(f"Page scraping failed: {str(e)}")
        
        return products
    
    def scrape_with_pagination(self, start_url: str) -> ScrapingResult:
        """
        Scrape multiple pages following pagination.
        
        Args:
            start_url: Starting URL
            
        Returns:
            ScrapingResult with all scraped products
        """
        current_url = start_url
        page_count = 0
        
        while current_url and (
            self.scraper_config.pagination_limit == 0 or 
            page_count < self.scraper_config.pagination_limit
        ):
            page_count += 1
            logger.info(f"Scraping page {page_count}: {current_url}")
            
            # Scrape current page
            self.scrape_page(current_url)
            
            # Get next page URL
            try:
                response = self._make_request(current_url)
                soup = self._parse_html(response.text)
                current_url = self.get_next_page_url(soup, current_url)
            except Exception as e:
                logger.error(f"Error getting next page: {e}")
                break
            
            if not current_url:
                logger.info("No more pages to scrape")
                break
        
        self.result.complete()
        return self.result
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.session.close()
        logger.debug(f"Closed session for {self.__class__.__name__}")
