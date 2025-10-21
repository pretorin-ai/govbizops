"""
Opportunity collector for tracking government contract opportunities
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

try:
    from .client import SAMGovClient
except ImportError:
    from client import SAMGovClient

logger = logging.getLogger(__name__)


class OpportunityCollector:
    """Collects and stores government contract opportunities"""
    
    def __init__(
        self,
        api_key: str,
        naics_codes: List[str],
        storage_path: str = "opportunities_data.json"
    ):
        """
        Initialize opportunity collector
        
        Args:
            api_key: SAM.gov API key
            naics_codes: List of NAICS codes to track
            storage_path: Path to store collected opportunities
        """
        # Validate NAICS codes for compliance
        if len(naics_codes) > SAMGovClient.MAX_NAICS_CODES:
            raise ValueError(f"Maximum {SAMGovClient.MAX_NAICS_CODES} NAICS codes allowed. Got {len(naics_codes)}.")
        
        self.client = SAMGovClient(api_key)
        self.naics_codes = naics_codes
        self.storage_path = Path(storage_path)
        self.opportunities = self._load_opportunities()
        
        logger.info(f"Initialized collector with {len(naics_codes)} NAICS codes: {', '.join(naics_codes)}")
    
    def _load_opportunities(self) -> Dict[str, Any]:
        """Load existing opportunities from storage"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading opportunities: {e}")
                return {}
        return {}
    
    def _save_opportunities(self):
        """Save opportunities to storage"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.opportunities, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving opportunities: {e}")
    
    def collect_daily_opportunities(
        self,
        days_back: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Collect opportunities from the past N days
        
        Args:
            days_back: Number of days to look back (default: 1 for daily)
            
        Returns:
            List of new opportunities collected
        """
        # Validate days_back for compliance
        if days_back > SAMGovClient.MAX_DAYS_RANGE:
            raise ValueError(f"Maximum {SAMGovClient.MAX_DAYS_RANGE} days range allowed. Got {days_back} days.")
        
        posted_to = datetime.now()
        posted_from = posted_to - timedelta(days=days_back)
        
        logger.info(f"Collecting opportunities from {posted_from} to {posted_to}")
        logger.info(f"NAICS codes: {', '.join(self.naics_codes)}")
        logger.info(f"Compliance: Max {SAMGovClient.MAX_NAICS_CODES} NAICS codes, {SAMGovClient.MAX_DAYS_RANGE} days range, {SAMGovClient.MAX_DAILY_COLLECTIONS} collection per day")
        
        try:
            # SAM.gov API treats multiple NAICS codes as AND, not OR
            # So we need to query each code separately
            all_opportunities_dict = {}
            total_fetched = 0

            for naics_code in self.naics_codes:
                logger.info(f"Fetching opportunities for NAICS code: {naics_code}")
                opportunities = self.client.get_all_opportunities(
                    posted_from=posted_from,
                    posted_to=posted_to,
                    naics_codes=[naics_code]
                )

                logger.info(f"  Found {len(opportunities)} opportunities for NAICS {naics_code}")
                total_fetched += len(opportunities)

                # Use notice ID as key to avoid duplicates
                for opp in opportunities:
                    notice_id = opp.get('noticeId')
                    if notice_id:
                        all_opportunities_dict[notice_id] = opp

            opportunities = list(all_opportunities_dict.values())
            logger.info(f"Total fetched: {total_fetched}, Unique after deduplication: {len(opportunities)}")

            # Filter and categorize
            new_opportunities = []
            already_collected = 0
            non_solicitation = 0

            for opp in opportunities:
                notice_id = opp.get("noticeId")
                opp_type = opp.get("type", "")

                if not notice_id:
                    continue

                if notice_id in self.opportunities:
                    already_collected += 1
                    continue

                # Only collect opportunities with "Solicitation" in the type
                if "Solicitation" in opp_type:
                    # Store opportunity with metadata
                    self.opportunities[notice_id] = {
                        "collected_date": datetime.now().isoformat(),
                        "data": opp
                    }
                    new_opportunities.append(opp)
                else:
                    non_solicitation += 1

            logger.info(f"Already collected: {already_collected}, Non-solicitation types: {non_solicitation}, New solicitations: {len(new_opportunities)}")
            
            if new_opportunities:
                self._save_opportunities()
                logger.info(f"Collected {len(new_opportunities)} new opportunities")
            else:
                logger.info("No new opportunities found")
            
            return new_opportunities
            
        except Exception as e:
            logger.error(f"Error collecting opportunities: {e}")
            raise
    
    def get_opportunities_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get opportunities within a date range
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            List of opportunities in date range
        """
        filtered_opportunities = []
        
        for notice_id, opp_data in self.opportunities.items():
            collected_date = datetime.fromisoformat(opp_data["collected_date"])
            if start_date <= collected_date <= end_date:
                filtered_opportunities.append(opp_data["data"])
        
        return filtered_opportunities
    
    def get_opportunities_by_naics(
        self,
        naics_code: str
    ) -> List[Dict[str, Any]]:
        """
        Get opportunities for a specific NAICS code
        
        Args:
            naics_code: NAICS code to filter by
            
        Returns:
            List of opportunities for the NAICS code
        """
        filtered_opportunities = []
        
        for notice_id, opp_data in self.opportunities.items():
            opp = opp_data["data"]
            # Check if NAICS code matches
            naics_list = opp.get("naicsCode", "").split(",")
            if naics_code in naics_list:
                filtered_opportunities.append(opp)
        
        return filtered_opportunities
    
    def get_all_opportunities(self) -> List[Dict[str, Any]]:
        """Get all stored opportunities"""
        return [opp_data["data"] for opp_data in self.opportunities.values()]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of collected opportunities"""
        total = len(self.opportunities)
        
        if total == 0:
            return {
                "total_opportunities": 0,
                "naics_breakdown": {},
                "date_range": None
            }
        
        # Calculate NAICS breakdown
        naics_count = {}
        dates = []
        
        for opp_data in self.opportunities.values():
            opp = opp_data["data"]
            naics_codes = opp.get("naicsCode", "").split(",")
            for code in naics_codes:
                if code:
                    naics_count[code] = naics_count.get(code, 0) + 1
            
            dates.append(datetime.fromisoformat(opp_data["collected_date"]))
        
        return {
            "total_opportunities": total,
            "naics_breakdown": naics_count,
            "date_range": {
                "earliest": min(dates).isoformat(),
                "latest": max(dates).isoformat()
            }
        }