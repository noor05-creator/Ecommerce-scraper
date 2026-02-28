"""
Scraper factory for creating appropriate scraper based on URL.
Implements adapter pattern for different e-commerce websites.
"""

from typing import Optional
from urllib.parse import urlparse

from .base_scraper import BaseScraper
from .amazon_scraper import AmazonScraper
from .daraz_scraper import DarazScraper
from ..utils.logger import logger


class ScraperFactory:
    """
    Factory class for creating appropriate scraper based on URL.
    Implements adapter pattern to handle different e-commerce platforms.
    """
    
    # Mapping of domain patterns to scraper classes
    SCRAPER_MAP = {
        'amazon': AmazonScraper,
        'daraz': DarazScraper,
    }
    
    @classmethod
    def create_scraper(cls, url: str) -> Optional[BaseScraper]:
        """
        Create appropriate scraper based on URL.
        
        Args:
            url: URL to scrape
            
        Returns:
            Scraper instance or None if unsupported
        """
        domain = cls._extract_domain(url)
        
        if not domain:
            logger.error(f"Invalid URL: {url}")
            return None
        
        # Find matching scraper
        scraper_class = cls._get_scraper_class(domain)
        
        if scraper_class:
            logger.info(f"Using {scraper_class.__name__} for domain: {domain}")
            return scraper_class()
        
        logger.error(f"No scraper available for domain: {domain}")
        logger.info(f"Supported domains: {', '.join(cls.SCRAPER_MAP.keys())}")
        return None
    
    @classmethod
    def _extract_domain(cls, url: str) -> Optional[str]:
        """
        Extract domain from URL.
        
        Args:
            url: URL string
            
        Returns:
            Domain name or None
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            return domain
        except Exception as e:
            logger.error(f"Error parsing URL: {e}")
            return None
    
    @classmethod
    def _get_scraper_class(cls, domain: str) -> Optional[type]:
        """
        Get scraper class for domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Scraper class or None
        """
        # Check for exact match
        for key, scraper_class in cls.SCRAPER_MAP.items():
            if key in domain:
                return scraper_class
        
        return None
    
    @classmethod
    def register_scraper(cls, domain_pattern: str, scraper_class: type) -> None:
        """
        Register a new scraper for a domain pattern.
        
        Args:
            domain_pattern: Domain pattern (e.g., 'shopify')
            scraper_class: Scraper class to use
        """
        cls.SCRAPER_MAP[domain_pattern] = scraper_class
        logger.info(f"Registered {scraper_class.__name__} for pattern: {domain_pattern}")
    
    @classmethod
    def get_supported_domains(cls) -> list:
        """
        Get list of supported domain patterns.
        
        Returns:
            List of domain patterns
        """
        return list(cls.SCRAPER_MAP.keys())
