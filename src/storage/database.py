"""
SQLite database storage for scraped products.
"""

import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..core.models import Product, ScrapingResult
from ..core.config import config
from ..utils.logger import logger


class DatabaseStorage:
    """
    SQLite database storage for products.
    Provides persistent storage with querying capabilities.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize database storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path or config.get('database.path', 'data/products.db'))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.connection = None
        self.enabled = config.get('database.enabled', True)
        
        if self.enabled:
            self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize database and create tables if they don't exist."""
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row
            
            self._create_tables()
            
            logger.info(f"Database initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            self.enabled = False
            raise
    
    def _create_tables(self) -> None:
        """Create database tables."""
        cursor = self.connection.cursor()
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL,
                currency TEXT,
                rating REAL,
                num_reviews INTEGER,
                availability TEXT,
                url TEXT,
                image_url TEXT,
                category TEXT,
                brand TEXT,
                sku TEXT,
                description TEXT,
                source TEXT NOT NULL,
                scraped_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source ON products(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sku ON products(sku)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_at ON products(scraped_at)')
        
        # Scraping sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraping_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                total_scraped INTEGER,
                successful INTEGER,
                failed INTEGER,
                success_rate REAL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.connection.commit()
        logger.debug("Database tables created/verified")
    
    def save_product(self, product: Product) -> Optional[int]:
        """
        Save a single product to database.
        
        Args:
            product: Product object
            
        Returns:
            Product ID or None
        """
        if not self.enabled:
            return None
        
        try:
            cursor = self.connection.cursor()
            
            cursor.execute('''
                INSERT INTO products (
                    name, price, currency, rating, num_reviews,
                    availability, url, image_url, category, brand,
                    sku, description, source, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product.name,
                product.price,
                product.currency,
                product.rating,
                product.num_reviews,
                product.availability,
                product.url,
                product.image_url,
                product.category,
                product.brand,
                product.sku,
                product.description,
                product.source,
                product.scraped_at
            ))
            
            self.connection.commit()
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"Error saving product: {e}")
            return None
    
    def save_products(self, products: List[Product]) -> int:
        """
        Save multiple products to database.
        
        Args:
            products: List of Product objects
            
        Returns:
            Number of products saved
        """
        if not self.enabled or not products:
            return 0
        
        saved_count = 0
        
        try:
            for product in products:
                if self.save_product(product):
                    saved_count += 1
            
            logger.info(f"Saved {saved_count}/{len(products)} products to database")
            
        except Exception as e:
            logger.error(f"Error saving products: {e}")
        
        return saved_count
    
    def save_scraping_result(self, result: ScrapingResult) -> Optional[int]:
        """
        Save scraping session result.
        
        Args:
            result: ScrapingResult object
            
        Returns:
            Session ID or None
        """
        if not self.enabled:
            return None
        
        try:
            # Save products
            self.save_products(result.products)
            
            # Save session metadata
            cursor = self.connection.cursor()
            
            cursor.execute('''
                INSERT INTO scraping_sessions (
                    source, total_scraped, successful, failed,
                    success_rate, started_at, completed_at, duration
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.source,
                result.total_scraped,
                result.successful,
                result.failed,
                result.success_rate,
                result.started_at,
                result.completed_at,
                result.duration
            ))
            
            self.connection.commit()
            logger.info(f"Saved scraping session to database")
            
            return cursor.lastrowid
            
        except Exception as e:
            logger.error(f"Error saving scraping result: {e}")
            return None
    
    def get_products_by_source(self, source: str, limit: int = None) -> List[dict]:
        """
        Get products by source.
        
        Args:
            source: Source name
            limit: Maximum number of products
            
        Returns:
            List of product dictionaries
        """
        if not self.enabled:
            return []
        
        try:
            cursor = self.connection.cursor()
            
            query = 'SELECT * FROM products WHERE source = ? ORDER BY scraped_at DESC'
            if limit:
                query += f' LIMIT {limit}'
            
            cursor.execute(query, (source,))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error fetching products: {e}")
            return []
    
    def get_recent_products(self, hours: int = 24, limit: int = 100) -> List[dict]:
        """
        Get recent products within specified hours.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of products
            
        Returns:
            List of product dictionaries
        """
        if not self.enabled:
            return []
        
        try:
            cursor = self.connection.cursor()
            
            cursor.execute('''
                SELECT * FROM products 
                WHERE scraped_at >= datetime('now', '-{} hours')
                ORDER BY scraped_at DESC
                LIMIT ?
            '''.format(hours), (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error fetching recent products: {e}")
            return []
    
    def get_statistics(self) -> dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        if not self.enabled:
            return {}
        
        try:
            cursor = self.connection.cursor()
            
            # Total products
            cursor.execute('SELECT COUNT(*) FROM products')
            total_products = cursor.fetchone()[0]
            
            # Products by source
            cursor.execute('''
                SELECT source, COUNT(*) as count 
                FROM products 
                GROUP BY source
            ''')
            by_source = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Recent scraping sessions
            cursor.execute('''
                SELECT COUNT(*) FROM scraping_sessions 
                WHERE created_at >= datetime('now', '-24 hours')
            ''')
            recent_sessions = cursor.fetchone()[0]
            
            return {
                'total_products': total_products,
                'products_by_source': by_source,
                'recent_sessions_24h': recent_sessions
            }
            
        except Exception as e:
            logger.error(f"Error fetching statistics: {e}")
            return {}
    
    def close(self) -> None:
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.debug("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
