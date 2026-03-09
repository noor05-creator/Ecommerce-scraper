"""
Amazon scraper implementation.
Scrapes product data from Amazon product listings.
"""

from typing import Optional, List, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re

from .base_scraper import BaseScraper
from ..core.models import Product, ScrapingResult
from ..utils.logger import logger


class AmazonScraper(BaseScraper):
    """
    Scraper for Amazon e-commerce platform.
    Handles product listings, search results, and category pages.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize Amazon scraper."""
        super().__init__(*args, **kwargs)
        self.base_url = "https://www.amazon.com"
    
    def get_source_name(self) -> str:
        """Get source name."""
        return "amazon"
    
    def scrape(self, url: str, **kwargs) -> ScrapingResult:
        """
        Scrape Amazon products from URL.
        
        Args:
            url: Amazon search or category URL
            **kwargs: Additional arguments
            
        Returns:
            ScrapingResult with scraped products
        """
        logger.info(f"Starting Amazon scrape: {url}")
        
        # Reset result
        self.result = ScrapingResult(source=self.get_source_name())
        
        # Scrape with pagination
        return self.scrape_with_pagination(url)
    
    def extract_product_list(self, soup: BeautifulSoup) -> List[Any]:
        """
        Extract product elements from Amazon search/listing page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of product elements
        """
        # Amazon uses different containers for products
        product_elements = []
        
        # Try main search results container
        containers = soup.find_all('div', {'data-component-type': 's-search-result'})
        if containers:
            product_elements.extend(containers)
        
        # Try alternate selectors
        if not product_elements:
            containers = soup.find_all('div', class_=re.compile(r's-result-item'))
            product_elements.extend([c for c in containers if c.get('data-asin')])
        
        logger.debug(f"Extracted {len(product_elements)} product elements")
        return product_elements

    def parse_product(self, element: Any) -> Optional[Product]:
        try:
            asin = element.get('data-asin', '')
            if not asin:
                return None

            # ---------- TITLE ----------
            h2_elem = element.find('h2')
            name = None
            if h2_elem:
                span = h2_elem.find('span')
                if span:
                    name = span.get_text(strip=True)

            if not name:
                return None

            # ---------- PRICE ----------
            price = None
            currency = "USD"

            price_whole = element.select_one(".a-price-whole")
            price_fraction = element.select_one(".a-price-fraction")
            price_symbol = element.select_one(".a-price-symbol")

            if price_whole:
                whole = price_whole.get_text(strip=True).replace(",", "")
                fraction = price_fraction.get_text(strip=True) if price_fraction else "00"
                try:
                    price = float(f"{whole}.{fraction}")
                except:
                    pass

            if price_symbol:
                currency = self._get_currency_code(price_symbol.get_text(strip=True))

            # ---------- RATING ----------
            rating = None
            rating_elem = element.select_one(".a-icon-alt")
            if rating_elem:
                match = re.search(r'(\d+\.?\d*)', rating_elem.get_text())
                if match:
                    rating = float(match.group(1))

            # ---------- REVIEWS ----------
            num_reviews = None
            reviews_elem = element.select_one("span.a-size-base.s-underline-text")
            if reviews_elem:
                text = reviews_elem.get_text(strip=True).replace(",", "")
                if text.isdigit():
                    num_reviews = int(text)

            # ---------- URL ----------
            a_tag = element.select_one("h2 a")
            url = urljoin(self.base_url, a_tag['href']) if a_tag else None

            # ---------- IMAGE ----------
            img_elem = element.select_one("img.s-image")
            image_url = img_elem.get("src") if img_elem else None

            # ---------- AVAILABILITY ----------
            availability = "In Stock"
            if element.find(string=re.compile(r'Out of stock|Currently unavailable', re.I)):
                availability = "Out of Stock"

            return Product(
                name=name,
                price=price,
                currency=currency,
                rating=rating,
                num_reviews=num_reviews,
                availability=availability,
                url=url or f"{self.base_url}/dp/{asin}",
                image_url=image_url,
                sku=asin,
                source=self.get_source_name()
            )

        except Exception as e:
            logger.error(f"Error parsing Amazon product: {e}")
            return None
    
    def get_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """
        Get next page URL from Amazon pagination.
        
        Args:
            soup: BeautifulSoup object
            current_url: Current page URL
            
        Returns:
            Next page URL or None
        """
        # Look for "Next" pagination link
        next_link = soup.find('a', class_='s-pagination-next')
        
        if next_link and next_link.get('href'):
            next_url = urljoin(self.base_url, next_link['href'])
            logger.debug(f"Found next page: {next_url}")
            return next_url
        
        logger.debug("No next page found")
        return None
    
    def _get_currency_code(self, symbol: str) -> str:
        """
        Convert currency symbol to code.
        
        Args:
            symbol: Currency symbol
            
        Returns:
            Currency code
        """
        currency_map = {
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
            '¥': 'JPY',
            '₹': 'INR',
            'Rs': 'PKR'
        }
        return currency_map.get(symbol, 'USD')
