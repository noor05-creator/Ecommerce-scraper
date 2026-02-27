"""
Command-line interface for the Universal E-commerce Scraper.
"""

import argparse
import sys
from pathlib import Path
from colorama import Fore, Style

from src.scrapers import ScraperFactory
from src.storage import CSVExporter, JSONExporter, DatabaseStorage
from src.utils import logger
from src.core.config import config


def print_banner():
    """Print application banner."""
    banner = f"""
{Fore.CYAN}{'='*70}
{Fore.GREEN}       Universal E-commerce Product Scraper v1.0.0
{Fore.CYAN}{'='*70}{Style.RESET_ALL}
    """
    print(banner)


def print_result_summary(result):
    """Print scraping result summary."""
    print(f"\n{Fore.YELLOW}{'='*70}")
    print(f"{Fore.GREEN}Scraping Summary{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'='*70}{Style.RESET_ALL}")
    print(f"Source: {Fore.CYAN}{result.source}{Style.RESET_ALL}")
    print(f"Total Products Scraped: {Fore.GREEN}{result.total_scraped}{Style.RESET_ALL}")
    print(f"Successful: {Fore.GREEN}{result.successful}{Style.RESET_ALL}")
    print(f"Failed: {Fore.RED}{result.failed}{Style.RESET_ALL}")
    print(f"Success Rate: {Fore.CYAN}{result.success_rate}%{Style.RESET_ALL}")
    
    if result.duration:
        print(f"Duration: {Fore.CYAN}{result.duration:.2f} seconds{Style.RESET_ALL}")
    
    if result.errors:
        print(f"\n{Fore.RED}Errors ({len(result.errors)}):{Style.RESET_ALL}")
        for i, error in enumerate(result.errors[:5], 1):
            print(f"  {i}. {error}")
        if len(result.errors) > 5:
            print(f"  ... and {len(result.errors) - 5} more")
    
    print(f"{Fore.YELLOW}{'='*70}{Style.RESET_ALL}\n")


def export_data(result, args):
    """Export scraped data to specified formats."""
    exported_files = []
    
    # CSV export
    if 'csv' in args.format:
        try:
            csv_exporter = CSVExporter()
            csv_file = csv_exporter.export_result(result, args.output)
            if csv_file:
                exported_files.append(('CSV', csv_file))
                logger.info(f"CSV export successful: {csv_file}")
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
    
    # JSON export
    if 'json' in args.format:
        try:
            json_exporter = JSONExporter()
            json_file = json_exporter.export_result(result, args.output)
            if json_file:
                exported_files.append(('JSON', json_file))
                logger.info(f"JSON export successful: {json_file}")
        except Exception as e:
            logger.error(f"JSON export failed: {e}")
    
    # Database storage
    if args.database or config.get('database.enabled', True):
        try:
            with DatabaseStorage() as db:
                db.save_scraping_result(result)
                logger.info("Data saved to database")
                exported_files.append(('Database', str(db.db_path)))
        except Exception as e:
            logger.error(f"Database storage failed: {e}")
    
    # Print export summary
    if exported_files:
        print(f"\n{Fore.GREEN}Exported Files:{Style.RESET_ALL}")
        for format_name, filepath in exported_files:
            print(f"  {Fore.CYAN}{format_name}:{Style.RESET_ALL} {filepath}")
    
    return exported_files


def main():
    """Main CLI entry point."""
    print_banner()
    
    parser = argparse.ArgumentParser(
        description='Universal E-commerce Product Scraper',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape Amazon search results
  python main.py https://www.amazon.com/s?k=laptop
  
  # Scrape Daraz category
  python main.py https://www.daraz.pk/smartphones/ --format csv json
  
  # Scrape with custom output name
  python main.py https://www.amazon.com/s?k=headphones --output headphones_data
  
  # Scrape without database storage
  python main.py https://www.daraz.pk/laptops/ --no-database
  
  # List supported websites
  python main.py --list-sources
        """
    )
    
    parser.add_argument(
        'url',
        nargs='?',
        help='URL to scrape (product listing, search results, or category page)'
    )
    
    parser.add_argument(
        '-f', '--format',
        nargs='+',
        choices=['csv', 'json'],
        default=['csv', 'json'],
        help='Output format(s) (default: csv json)'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        help='Output filename (without extension)'
    )
    
    parser.add_argument(
        '-d', '--database',
        action='store_true',
        help='Save to database (enabled by default)'
    )
    
    parser.add_argument(
        '--no-database',
        action='store_true',
        help='Disable database storage'
    )
    
    parser.add_argument(
        '-l', '--list-sources',
        action='store_true',
        help='List supported e-commerce websites'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        help='Maximum number of pages to scrape (overrides config)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version=f"%(prog)s {config.get('app.version', '1.0.0')}"
    )
    
    args = parser.parse_args()
    
    # Set verbose mode
    if args.verbose:
        logger._logger.setLevel('DEBUG')
    
    # List supported sources
    if args.list_sources:
        sources = ScraperFactory.get_supported_domains()
        print(f"\n{Fore.GREEN}Supported E-commerce Websites:{Style.RESET_ALL}")
        for source in sources:
            print(f"  • {Fore.CYAN}{source}{Style.RESET_ALL}")
        print()
        return 0
    
    # Validate URL
    if not args.url:
        parser.print_help()
        print(f"\n{Fore.RED}Error: URL is required{Style.RESET_ALL}")
        return 1
    
    try:
        # Create scraper
        print(f"\n{Fore.CYAN}Initializing scraper...{Style.RESET_ALL}")
        scraper = ScraperFactory.create_scraper(args.url)
        
        if not scraper:
            print(f"{Fore.RED}Error: Unsupported website{Style.RESET_ALL}")
            print(f"Use --list-sources to see supported websites")
            return 1
        
        # Override pagination limit if specified
        if args.max_pages:
            scraper.scraper_config.pagination_limit = args.max_pages
            logger.info(f"Pagination limit set to {args.max_pages} pages")
        
        # Scrape
        print(f"{Fore.GREEN}Starting scrape: {args.url}{Style.RESET_ALL}\n")
        
        with scraper:
            result = scraper.scrape(args.url)
        
        # Print summary
        print_result_summary(result)
        
        # Export data
        if result.successful > 0:
            export_data(result, args)
            print(f"\n{Fore.GREEN}✓ Scraping completed successfully!{Style.RESET_ALL}\n")
            return 0
        else:
            print(f"\n{Fore.RED}✗ No products were scraped successfully{Style.RESET_ALL}\n")
            return 1
    
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Scraping interrupted by user{Style.RESET_ALL}\n")
        return 130
    
    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"\n{Fore.RED}Error: {str(e)}{Style.RESET_ALL}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
