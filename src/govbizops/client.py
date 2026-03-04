"""
SAM.gov API client for fetching contract opportunities
"""

import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class SAMGovClient:
    """Client for interacting with SAM.gov Contract Opportunities API"""
    
    BASE_URL = "https://api.sam.gov/opportunities/v2/search"
    
    # Compliance limits
    MAX_NAICS_CODES = 50  # Maximum NAICS codes per collection
    MAX_DAYS_RANGE = 90   # Maximum days to collect at once
    RATE_LIMIT_DELAY = 2  # Seconds between API calls
    MAX_DAILY_COLLECTIONS = 100  # Maximum collections per day
    
    def __init__(self, api_key: str, use_alpha: bool = False):
        """
        Initialize SAM.gov API client
        
        Args:
            api_key: SAM.gov API key
            use_alpha: Use alpha API endpoint (default: False)
        """
        self.api_key = api_key
        if use_alpha:
            self.BASE_URL = "https://api-alpha.sam.gov/opportunities/v2/search"
        
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": api_key,
            "Accept": "application/json"
        })
        
        # Track daily collection count
        self._daily_collections = 0
        self._last_collection_date = None
    
    def _check_daily_limit(self):
        """Check if daily collection limit has been reached"""
        today = datetime.now().date()
        
        # Reset counter if it's a new day
        if self._last_collection_date != today:
            self._daily_collections = 0
            self._last_collection_date = today
        
        if self._daily_collections >= self.MAX_DAILY_COLLECTIONS:
            raise ValueError(f"Daily collection limit reached ({self.MAX_DAILY_COLLECTIONS} per day). Please try again tomorrow.")
        
        self._daily_collections += 1
    
    def _validate_naics_codes(self, naics_codes: Optional[List[str]]):
        """Validate NAICS codes against compliance limits"""
        if naics_codes and len(naics_codes) > self.MAX_NAICS_CODES:
            raise ValueError(f"Maximum {self.MAX_NAICS_CODES} NAICS codes allowed per collection. Got {len(naics_codes)}.")
    
    def _validate_date_range(self, posted_from: datetime, posted_to: datetime):
        """Validate date range against compliance limits"""
        days_diff = (posted_to - posted_from).days
        if days_diff > self.MAX_DAYS_RANGE:
            raise ValueError(f"Maximum {self.MAX_DAYS_RANGE} days range allowed per collection. Got {days_diff} days.")
    
    def search_opportunities(
        self,
        posted_from: datetime,
        posted_to: datetime,
        naics_codes: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search for contract opportunities
        
        Args:
            posted_from: Start date for posted date range
            posted_to: End date for posted date range
            naics_codes: List of NAICS codes to filter by
            limit: Number of results per page (max 1000)
            offset: Pagination offset
            **kwargs: Additional query parameters
            
        Returns:
            API response as dictionary
        """
        # Check daily collection limit
        self._check_daily_limit()
        
        # Validate inputs for compliance
        self._validate_naics_codes(naics_codes)
        self._validate_date_range(posted_from, posted_to)
        
        # Validate date range (max 1 year)
        if posted_to - posted_from > timedelta(days=365):
            raise ValueError("Date range cannot exceed 1 year")
        
        params = {
            "postedFrom": posted_from.strftime("%m/%d/%Y"),
            "postedTo": posted_to.strftime("%m/%d/%Y"),
            "limit": min(limit, 1000),
            "offset": offset
        }
        
        if naics_codes:
            params["ncode"] = ",".join(naics_codes)
        
        # Add any additional parameters
        params.update(kwargs)
        
        logger.info(f"API Request URL: {self.BASE_URL}")
        logger.info(f"API Request params: {params}")
        
        response = self.session.get(self.BASE_URL, params=params)
        
        # Log response details for debugging
        logger.info(f"API Response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"API Error Response: {response.text}")
            
        response.raise_for_status()
        
        result = response.json()
        logger.info(f"API Response: totalRecords={result.get('totalRecords', 0)}, returned={len(result.get('opportunitiesData', []))}")
        
        # Rate limiting delay
        time.sleep(self.RATE_LIMIT_DELAY)
        
        return result
    
    def get_all_opportunities(
        self,
        posted_from: datetime,
        posted_to: datetime,
        naics_codes: Optional[List[str]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Get all opportunities matching criteria (handles pagination)
        
        Args:
            posted_from: Start date for posted date range
            posted_to: End date for posted date range
            naics_codes: List of NAICS codes to filter by
            **kwargs: Additional query parameters
            
        Returns:
            List of all opportunities
        """
        # Validate inputs for compliance
        self._validate_naics_codes(naics_codes)
        self._validate_date_range(posted_from, posted_to)
        
        all_opportunities = []
        offset = 0
        limit = 500  # Reduced from 1000 to be more conservative
        
        while True:
            try:
                response = self.search_opportunities(
                    posted_from=posted_from,
                    posted_to=posted_to,
                    naics_codes=naics_codes,
                    limit=limit,
                    offset=offset,
                    **kwargs
                )
                
                opportunities = response.get("opportunitiesData", [])
                if not opportunities:
                    break
                
                all_opportunities.extend(opportunities)
                
                # Check if there are more results
                total_records = response.get("totalRecords", 0)
                if offset + limit >= total_records:
                    break
                
                offset += limit
                
                # Additional rate limiting for pagination
                time.sleep(self.RATE_LIMIT_DELAY)
                
            except Exception as e:
                logger.error(f"Error fetching opportunities at offset {offset}: {e}")
                break
        
        logger.info(f"Total opportunities collected: {len(all_opportunities)}")
        return all_opportunities