"""
Data models for e-commerce products using Pydantic for validation.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field, validator


class Product(BaseModel):
    """
    Product data model representing a scraped e-commerce product.
    
    Attributes:
        name: Product name/title
        price: Current price (numeric value)
        currency: Currency code (e.g., USD, PKR)
        rating: Product rating (0-5)
        num_reviews: Number of customer reviews
        availability: Stock availability status
        url: Product page URL
        image_url: Main product image URL
        category: Product category
        brand: Product brand/manufacturer
        sku: Stock keeping unit / product ID
        description: Product description
        scraped_at: Timestamp when data was scraped
        source: Source website (amazon, daraz, etc.)
    """
    
    name: str = Field(..., min_length=1, description="Product name")
    price: Optional[float] = Field(None, ge=0, description="Product price")
    currency: Optional[str] = Field(None, max_length=10, description="Currency code")
    rating: Optional[float] = Field(None, ge=0, le=5, description="Product rating")
    num_reviews: Optional[int] = Field(None, ge=0, description="Number of reviews")
    availability: Optional[str] = Field(None, description="Availability status")
    url: str = Field(..., description="Product URL")
    image_url: Optional[str] = Field(None, description="Product image URL")
    category: Optional[str] = Field(None, description="Product category")
    brand: Optional[str] = Field(None, description="Product brand")
    sku: Optional[str] = Field(None, description="Product SKU/ID")
    description: Optional[str] = Field(None, description="Product description")
    scraped_at: datetime = Field(default_factory=datetime.now, description="Scrape timestamp")
    source: str = Field(..., description="Source website")
    
    @validator('price', 'rating')
    def round_decimal_fields(cls, v):
        """Round decimal fields to 2 decimal places."""
        if v is not None:
            return round(v, 2)
        return v
    
    @validator('name', 'description')
    def clean_text_fields(cls, v):
        """Clean and normalize text fields."""
        if v:
            return ' '.join(v.split())
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        validate_assignment = True


class ScrapingResult(BaseModel):
    """
    Container for scraping results.
    
    Attributes:
        products: List of scraped products
        total_scraped: Total number of products scraped
        successful: Number of successfully scraped products
        failed: Number of failed attempts
        source: Source website
        started_at: Scraping start time
        completed_at: Scraping completion time
        errors: List of error messages
    """
    
    products: List[Product] = Field(default_factory=list, description="Scraped products")
    total_scraped: int = Field(0, ge=0, description="Total products scraped")
    successful: int = Field(0, ge=0, description="Successful scrapes")
    failed: int = Field(0, ge=0, description="Failed scrapes")
    source: str = Field(..., description="Source website")
    started_at: datetime = Field(default_factory=datetime.now, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    errors: List[str] = Field(default_factory=list, description="Error messages")
    
    def add_product(self, product: Product) -> None:
        """Add a successfully scraped product."""
        self.products.append(product)
        self.successful += 1
        self.total_scraped += 1
    
    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.failed += 1
        self.total_scraped += 1
    
    def complete(self) -> None:
        """Mark the scraping as completed."""
        self.completed_at = datetime.now()
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_scraped == 0:
            return 0.0
        return round((self.successful / self.total_scraped) * 100, 2)
    
    @property
    def duration(self) -> Optional[float]:
        """Calculate scraping duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ScraperConfig(BaseModel):
    """
    Configuration model for scraper settings.
    
    Attributes:
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds
        rate_limit_delay: Delay between requests in seconds
        use_proxy: Whether to use proxy rotation
        max_products: Maximum products to scrape (0 = unlimited)
        pagination_limit: Maximum pages to scrape (0 = unlimited)
    """
    
    timeout: int = Field(30, ge=1, description="Request timeout")
    max_retries: int = Field(3, ge=0, description="Max retry attempts")
    retry_delay: int = Field(2, ge=0, description="Retry delay in seconds")
    rate_limit_delay: float = Field(1.0, ge=0, description="Rate limit delay")
    use_proxy: bool = Field(False, description="Enable proxy rotation")
    max_products: int = Field(0, ge=0, description="Max products to scrape")
    pagination_limit: int = Field(10, ge=0, description="Max pages to scrape")
    
    class Config:
        """Pydantic configuration."""
        validate_assignment = True
