"""
Daraz scraper implementation.
Scrapes product data from Daraz e-commerce platform.
"""

from typing import Optional, List, Any
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
import re
import json

from .base_scraper import BaseScraper
from ..core.models import Product, ScrapingResult
from ..utils.logger import logger


class DarazScraper(BaseScraper):
    """
    Scraper for Daraz e-commerce platform.
    Handles product listings, search results, and category pages.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize Daraz scraper."""
        super().__init__(*args, **kwargs)
        self.base_url = "https://www.daraz.pk"
    
    def get_source_name(self) -> str:
        """Get source name."""
        return "daraz"
    
    def scrape(self, url: str, **kwargs) -> ScrapingResult:
        """
        Scrape Daraz products from URL.
        
        Args:
            url: Daraz search or category URL
            **kwargs: Additional arguments
            
        Returns:
            ScrapingResult with scraped products
        """
        logger.info(f"Starting Daraz scrape: {url}")
        
        # Reset result
        self.result = ScrapingResult(source=self.get_source_name())
        
        # Scrape with pagination
        return self.scrape_with_pagination(url)
    
    def extract_product_list(self, soup: BeautifulSoup) -> List[Any]:
        """
        Extract product elements from Daraz listing page.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            List of product elements
        """
        product_elements = []
        
        # Daraz uses data-qa-locator for product items
        containers = soup.find_all('div', {'data-qa-locator': 'product-item'})
        if containers:
            product_elements.extend(containers)
        
        # Fallback: look for product grid items
        if not product_elements:
            grid = soup.find('div', class_='gridItem')
            if grid:
                product_elements = soup.find_all('div', class_=re.compile(r'gridItem'))
        
        # Another fallback: look for script tags with product data
        if not product_elements:
            script_tags = soup.find_all('script', type='application/ld+json')
            for script in script_tags:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') == 'ItemList':
                        # Create pseudo-elements from JSON data
                        product_elements = data.get('itemListElement', [])
                        break
                except (json.JSONDecodeError, AttributeError):
                    continue
        
        logger.debug(f"Extracted {len(product_elements)} product elements")
        return product_elements
    
    def parse_product(self, element: Any) -> Optional[Product]:
        """
        Parse product data from Daraz product element.
        
        Args:
            element: BeautifulSoup element or dict containing product
            
        Returns:
            Product object or None
        """
        try:
            # Handle JSON data
            if isinstance(element, dict):
                return self._parse_json_product(element)
            
            # Handle HTML element
            return self._parse_html_product(element)
            
        except Exception as e:
            logger.error(f"Error parsing Daraz product: {e}")
            return None

    def _parse_html_product(self, element: Any) -> Optional[Product]:
        """Parse product from HTML element."""

        try:
            # ---------- PRODUCT NAME ----------
            name_elem = element.select_one("a[title]")
            name = name_elem.get("title") if name_elem else None

            if not name:
                return None

            # ---------- PRODUCT URL ----------
            url = None
            if name_elem and name_elem.get("href"):
                href = name_elem["href"]
                url = urljoin(self.base_url, href)

            # ---------- PRICE ----------
            price = None
            currency = "PKR"

            price_elem = element.select_one("span.ooOxS")

            if price_elem:
                price_text = price_elem.get_text(strip=True)

                # Remove currency and commas
                price_text = price_text.replace("Rs.", "").replace(",", "").strip()

                try:
                    price = float(price_text)
                except ValueError:
                    price = None

            # ---------- IMAGE ----------
            image_url = None
            img_elem = element.select_one("img")
            if img_elem:
                image_url = img_elem.get("src") or img_elem.get("data-src")

            # ---------- SKU ----------
            sku = None
            if url:
                match = re.search(r"-i(\d+)", url)
                if match:
                    sku = match.group(1)

            return Product(
                name=name,
                price=price,
                currency=currency,
                url=url or "",
                image_url=image_url,
                sku=sku,
                availability="In Stock",
                source=self.get_source_name()
            )

        except Exception as e:
            logger.error(f"Error parsing Daraz product: {e}")
            return None

    def _parse_json_product(self, data: dict) -> Optional[Product]:
        """Parse product from JSON data."""
        item = data.get('item', {})
        
        name = item.get('name')
        if not name:
            return None
        
        # Extract price from offers
        price = None
        currency = "PKR"
        offers = item.get('offers', {})
        if offers:
            price_text = str(offers.get('price', ''))
            try:
                price = float(price_text)
            except ValueError:
                pass
            currency = offers.get('priceCurrency', 'PKR')
        
        # Extract rating
        rating = None
        aggregate_rating = item.get('aggregateRating', {})
        if aggregate_rating:
            rating_value = aggregate_rating.get('ratingValue')
            if rating_value:
                rating = float(rating_value)
        
        # Create Product object
        product = Product(
            name=name,
            price=price,
            currency=currency,
            rating=rating,
            url=item.get('url', ''),
            image_url=item.get('image', ''),
            source=self.get_source_name()
        )
        
        return product

    def get_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """
        Build next page URL manually for Daraz.
        """

        parsed = urlparse(current_url)
        params = parse_qs(parsed.query)

        # If page not present → assume page 1
        current_page = int(params.get("page", ["1"])[0])

        next_page = current_page + 1

        # Optional safety: stop if no products found
        products = self.extract_product_list(soup)
        if not products:
            logger.debug("No products found, stopping pagination.")
            return None

        params["page"] = [str(next_page)]

        new_query = "&".join(f"{k}={v[0]}" for k, v in params.items())

        next_url = parsed._replace(query=new_query).geturl()

        logger.debug(f"Built next page URL: {next_url}")

        return next_url