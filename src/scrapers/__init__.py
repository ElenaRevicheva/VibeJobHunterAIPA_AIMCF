"""
Job scrapers for various platforms
"""
from .base_scraper import BaseScraper
from .linkedin_scraper import LinkedInScraper
from .indeed_scraper import IndeedScraper

__all__ = ["BaseScraper", "LinkedInScraper", "IndeedScraper"]
