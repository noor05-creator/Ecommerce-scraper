# Universal E-commerce Product Scraper

A professional, production-ready web scraping system for extracting product data from e-commerce platforms like Amazon, Daraz, and Shopify stores. Built with Python, this modular and scalable scraper is perfect for freelance projects and commercial use.

## 🚀 Features

- **Multi-Platform Support**: Scrape from Amazon, Daraz, and easily add new platforms
- **Adapter Pattern**: Clean, extensible architecture for adding new scrapers
- **Automatic Pagination**: Handles multi-page scraping automatically
- **Multiple Export Formats**: CSV, JSON, and SQLite database storage
- **Robust Error Handling**: Retry logic with exponential backoff
- **Proxy Support**: Built-in proxy rotation (configurable)
- **Smart Rate Limiting**: Respectful scraping with configurable delays
- **User Agent Rotation**: Randomized user agents for better success rates
- **Comprehensive Logging**: Detailed logs with file and console output
- **CLI Interface**: Easy-to-use command-line interface
- **Docker Support**: Containerized deployment ready
- **Type Safety**: Full type hints and Pydantic validation

## 📋 Requirements

- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)

## 🛠️ Installation

### 1. Clone or Download the Project

```bash
cd ecommerce-scraper
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment (Optional)

```bash
cp .env.example .env
# Edit .env with your settings
```

## 📁 Project Structure

```
ecommerce-scraper/
├── config/
│   └── config.yaml              # Configuration settings
├── data/
│   ├── output/                  # Exported CSV/JSON files
│   └── products.db              # SQLite database
├── logs/                        # Log files
├── src/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration loader
│   │   └── models.py            # Data models (Pydantic)
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── base_scraper.py      # Abstract base scraper
│   │   ├── amazon_scraper.py    # Amazon implementation
│   │   ├── daraz_scraper.py     # Daraz implementation
│   │   └── scraper_factory.py   # Scraper factory (Adapter pattern)
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── csv_exporter.py      # CSV export
│   │   ├── json_exporter.py     # JSON export
│   │   └── database.py          # SQLite storage
│   └── utils/
│       ├── __init__.py
│       ├── logger.py            # Logging system
│       ├── proxy_manager.py     # Proxy rotation
│       ├── retry_handler.py     # Retry logic
│       └── user_agent.py        # User agent management
├── tests/                       # Unit tests (optional)
├── .env.example                 # Environment variables template
├── .gitignore                   # Git ignore file
├── Dockerfile                   # Docker configuration
├── main.py                      # CLI entry point
├── README.md                    # This file
└── requirements.txt             # Python dependencies
```

## 🎯 Usage

### Basic Usage

```bash
# Scrape Amazon search results
python main.py "https://www.amazon.com/s?k=laptop"

# Scrape Daraz category
python main.py "https://www.daraz.pk/smartphones/"
```

### Advanced Usage

```bash
# Export to specific formats
python main.py "URL" --format csv json

# Custom output filename
python main.py "URL" --output my_products

# Limit number of pages
python main.py "URL" --max-pages 5

# Disable database storage
python main.py "URL" --no-database

# Verbose output
python main.py "URL" --verbose

# List supported websites
python main.py --list-sources
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `url` | URL to scrape (required) |
| `-f, --format` | Output format: csv, json (default: both) |
| `-o, --output` | Custom output filename |
| `-d, --database` | Enable database storage |
| `--no-database` | Disable database storage |
| `--max-pages` | Maximum pages to scrape |
| `-v, --verbose` | Enable verbose logging |
| `-l, --list-sources` | List supported websites |
| `--version` | Show version |

## 📊 Data Schema

### Product Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Product name/title |
| `price` | float | Product price |
| `currency` | string | Currency code (USD, PKR, etc.) |
| `rating` | float | Product rating (0-5) |
| `num_reviews` | int | Number of reviews |
| `availability` | string | Stock status |
| `url` | string | Product URL |
| `image_url` | string | Product image URL |
| `category` | string | Product category |
| `brand` | string | Product brand |
| `sku` | string | Product SKU/ID |
| `description` | string | Product description |
| `source` | string | Source website |
| `scraped_at` | datetime | Scrape timestamp |

## ⚙️ Configuration

### config.yaml

Edit `config/config.yaml` to customize:

- Scraping behavior (timeouts, retries, delays)
- Output settings (formats, directories)
- Database settings
- Logging configuration
- Proxy settings
- Website-specific settings

### Environment Variables

Create `.env` file from `.env.example`:

```bash
# Proxy Configuration
PROXY_ENABLED=false
PROXY_LIST=http://proxy1.com:8080,http://proxy2.com:8080

# Scraping Configuration
REQUEST_TIMEOUT=30
MAX_RETRIES=3
RETRY_DELAY=2

# Output Configuration
OUTPUT_DIR=data/output
LOG_DIR=logs

# Debug Mode
DEBUG=false
LOG_LEVEL=INFO
```

## 🔌 Adding New Scrapers

To add support for a new e-commerce platform:

1. **Create Scraper Class**

```python
# src/scrapers/shopify_scraper.py
from .base_scraper import BaseScraper

class ShopifyScraper(BaseScraper):
    def get_source_name(self) -> str:
        return "shopify"
    
    def scrape(self, url: str, **kwargs):
        # Implementation
        pass
    
    # Implement other abstract methods
```

2. **Register in Factory**

```python
# src/scrapers/scraper_factory.py
from .shopify_scraper import ShopifyScraper

ScraperFactory.SCRAPER_MAP['shopify'] = ShopifyScraper
```

## 🐳 Docker Deployment

### Build Image

```bash
docker build -t ecommerce-scraper .
```

### Run Container

```bash
docker run -v $(pwd)/data:/app/data ecommerce-scraper "https://www.amazon.com/s?k=laptop"
```

## 📝 Logging

Logs are stored in the `logs/` directory with the following features:

- **Console Output**: Colored, formatted output
- **File Output**: Detailed logs with rotation
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Automatic Rotation**: 10MB file size limit, 5 backup files

View logs:

```bash
# Latest log file
tail -f logs/scraper_$(date +%Y%m%d).log
```

## 🧪 Testing

Run tests (when implemented):

```bash
pytest tests/ -v --cov=src
```

## 🔒 Best Practices

### Ethical Scraping

1. **Respect robots.txt**: Check website's robots.txt file
2. **Rate Limiting**: Use appropriate delays between requests
3. **User Agent**: Use realistic user agents
4. **Terms of Service**: Comply with website terms
5. **Personal Use**: Ensure scraping is for legitimate purposes

### Performance

- Use pagination limits for large datasets
- Enable database storage for data persistence
- Monitor log files for errors
- Adjust rate limits based on website response

### Security

- Use proxies for privacy (when needed)
- Rotate user agents
- Don't hardcode credentials
- Use environment variables for sensitive data

## 🤝 Contributing

This is a freelance-ready project. To extend functionality:

1. Follow the existing code structure
2. Add comprehensive docstrings
3. Include type hints
4. Write unit tests
5. Update documentation

## 📄 License

This project is provided as-is for freelance and commercial use. Please ensure compliance with website terms of service and applicable laws.

## 🆘 Troubleshooting

### Common Issues

**Issue**: "No products found"
- **Solution**: Website structure may have changed. Update selectors in scraper.

**Issue**: "Request timeout"
- **Solution**: Increase `REQUEST_TIMEOUT` in config or .env

**Issue**: "Too many requests"
- **Solution**: Increase `RATE_LIMIT_DELAY` in config

**Issue**: "Import errors"
- **Solution**: Ensure virtual environment is activated and dependencies installed

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Via environment variable
DEBUG=true python main.py "URL"

# Via command line
python main.py "URL" --verbose
```

## 📧 Support

For issues or questions about this project:

1. Check the logs in `logs/` directory
2. Review the configuration in `config/config.yaml`
3. Enable verbose mode for detailed output
4. Check that your Python version is 3.8+

## 🎓 Architecture Overview

This scraper uses professional software design patterns:

- **Adapter Pattern**: ScraperFactory creates appropriate scrapers
- **Template Method**: BaseScraper defines scraping workflow
- **Singleton Pattern**: Logger and ConfigLoader
- **Strategy Pattern**: Different export strategies (CSV, JSON, DB)
- **Dependency Injection**: Configurable components

## 📈 Roadmap

Potential enhancements:

- [ ] Add more e-commerce platforms
- [ ] Implement async scraping
- [ ] Add GUI interface
- [ ] Cloud deployment support
- [ ] API endpoint
- [ ] Web dashboard
- [ ] Scheduled scraping
- [ ] Email notifications

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Status**: Production Ready ✅
