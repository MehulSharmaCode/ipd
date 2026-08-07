"""
Crawler & Scheme Ingestion Package — myScheme.gov.in Integration
"""
from app.services.crawler.fetcher import MySchemeApiFetcher
from app.services.crawler.parser import MySchemeParser
from app.services.crawler.normalizer import MySchemeNormalizer
from app.services.crawler.rule_extractor import extract_rules_from_text
from app.services.crawler.scheduler import MySchemeIngestionScheduler

__all__ = [
    "MySchemeApiFetcher",
    "MySchemeParser",
    "MySchemeNormalizer",
    "extract_rules_from_text",
    "MySchemeIngestionScheduler",
]
