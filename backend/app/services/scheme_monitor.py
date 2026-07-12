# backend/app/services/scheme_monitor.py
import requests
from bs4 import BeautifulSoup
import uuid
from typing import List

class SchemeMonitor:
    """
    Lightweight proactive monitoring service that simulates checking
    an external government portal for new or updated schemes.
    """

    MOCK_URL = "https://agricoop.nic.in/en/Agriculture"

    @staticmethod
    def scrape_latest_schemes() -> List[dict]:
        """
        Since real government portals have strict scraping policies and often block requests,
        this acts as a heuristic/mock approach that *could* scrape a live URL.
        """
        scraped_data = []
        try:
            # We add a small timeout to ensure this doesn't block heavily
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(SchemeMonitor.MOCK_URL, headers=headers, timeout=5)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # In a real environment, we'd search for specific divs/tables.
                # Here we simulate finding a block that looks like a new update.
                updates = soup.find_all('a', class_='latest-update') # Example selector
                for update in updates:
                    scraped_data.append({
                        "id": str(uuid.uuid4())[:8],
                        "title": update.text.strip(),
                        "url": update.get('href'),
                        "source": "AgriCoop Portal",
                        "status": "New"
                    })
        except Exception as e:
            print(f"⚠️ Scheme Monitor scraping failed/timeout: {str(e)}")
            
        # Provide guaranteed mock updates for the dashboard if scraping fails/finds nothing
        if not scraped_data:
            scraped_data = [
                {
                    "id": "SCH-PMKSY-2026",
                    "title": "Pradhan Mantri Krishi Sinchayee Yojana Guidelines Updated",
                    "url": "https://pmksy.gov.in/",
                    "source": "Ministry of Agriculture",
                    "status": "Updated",
                    "description": "The Ministry of Agriculture has released updated guidelines for the Pradhan Mantri Krishi Sinchayee Yojana (PMKSY) focusing on 'Per Drop More Crop'.",
                    "insights": ["Focus on micro-irrigation", "Increased subsidy for small farmers", "Simplified application process"]
                },
                {
                    "id": "SCH-NEW-001",
                    "title": "National Mission on Natural Farming Extended Subsidy",
                    "url": "https://naturalfarming.dac.gov.in/",
                    "source": "State Agriculture Portal",
                    "status": "New",
                    "description": "A new subsidy scheme has been announced to promote natural farming practices across the state. Farmers adopting organic methods are eligible for direct benefit transfers.",
                    "insights": ["100% organic certification support", "Input subsidy up to ₹31,000 per hectare", "Free training workshops at district level"]
                }
            ]
            
        return scraped_data
