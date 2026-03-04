"""
Opportunity collector for tracking government contract opportunities
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from .client import SAMGovClient
from .database import Opportunity

logger = logging.getLogger(__name__)


class OpportunityCollector:
    """Collects and stores government contract opportunities"""

    def __init__(
        self,
        api_key: str,
        naics_codes: List[str],
        db_session: Session,
    ):
        """
        Initialize opportunity collector

        Args:
            api_key: SAM.gov API key
            naics_codes: List of NAICS codes to track
            db_session: SQLAlchemy session for database operations
        """
        if len(naics_codes) > SAMGovClient.MAX_NAICS_CODES:
            raise ValueError(
                f"Maximum {SAMGovClient.MAX_NAICS_CODES} NAICS codes allowed. Got {len(naics_codes)}."
            )

        self.client = SAMGovClient(api_key)
        self.naics_codes = naics_codes
        self.db_session = db_session

        logger.info(
            f"Initialized collector with {len(naics_codes)} NAICS codes: {', '.join(naics_codes)}"
        )

    def _opportunity_exists(self, notice_id: str) -> bool:
        """Check if an opportunity already exists in the database."""
        return (
            self.db_session.query(Opportunity)
            .filter(Opportunity.notice_id == notice_id)
            .first()
            is not None
        )

    def collect_daily_opportunities(self, days_back: int = 1) -> List[Dict[str, Any]]:
        """
        Collect opportunities from the past N days

        Args:
            days_back: Number of days to look back (default: 1 for daily)

        Returns:
            List of new opportunities collected
        """
        if days_back > SAMGovClient.MAX_DAYS_RANGE:
            raise ValueError(
                f"Maximum {SAMGovClient.MAX_DAYS_RANGE} days range allowed. Got {days_back} days."
            )

        posted_to = datetime.now()
        posted_from = posted_to - timedelta(days=days_back)

        logger.info(f"Collecting opportunities from {posted_from} to {posted_to}")
        logger.info(f"NAICS codes: {', '.join(self.naics_codes)}")
        logger.info(
            f"Compliance: Max {SAMGovClient.MAX_NAICS_CODES} NAICS codes, {SAMGovClient.MAX_DAYS_RANGE} days range, {SAMGovClient.MAX_DAILY_COLLECTIONS} collection per day"
        )

        try:
            all_opportunities_dict = {}
            total_fetched = 0

            for naics_code in self.naics_codes:
                logger.info(f"Fetching opportunities for NAICS code: {naics_code}")
                opportunities = self.client.get_all_opportunities(
                    posted_from=posted_from,
                    posted_to=posted_to,
                    naics_codes=[naics_code],
                )

                logger.info(
                    f"  Found {len(opportunities)} opportunities for NAICS {naics_code}"
                )
                total_fetched += len(opportunities)

                for opp in opportunities:
                    notice_id = opp.get("noticeId")
                    if notice_id:
                        all_opportunities_dict[notice_id] = opp

            opportunities = list(all_opportunities_dict.values())
            logger.info(
                f"Total fetched: {total_fetched}, Unique after deduplication: {len(opportunities)}"
            )

            new_opportunities = []
            already_collected = 0
            non_solicitation = 0

            for opp in opportunities:
                notice_id = opp.get("noticeId")
                opp_type = opp.get("type", "")

                if self._opportunity_exists(notice_id):
                    already_collected += 1
                    continue

                if "Solicitation" in opp_type:
                    db_opp = Opportunity.from_api_response(opp)
                    self.db_session.add(db_opp)
                    new_opportunities.append(opp)
                else:
                    non_solicitation += 1

            logger.info(
                f"Already collected: {already_collected}, Non-solicitation types: {non_solicitation}, New solicitations: {len(new_opportunities)}"
            )

            if new_opportunities:
                self.db_session.commit()
                logger.info(f"Collected {len(new_opportunities)} new opportunities")
            else:
                logger.info("No new opportunities found")

            return new_opportunities

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Error collecting opportunities: {e}")
            raise

    def get_opportunities_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Get opportunities within a date range

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of opportunities in date range
        """
        results = (
            self.db_session.query(Opportunity)
            .filter(
                Opportunity.collected_date >= start_date,
                Opportunity.collected_date <= end_date,
            )
            .all()
        )
        return [opp.to_dict() for opp in results]

    def get_opportunities_by_naics(self, naics_code: str) -> List[Dict[str, Any]]:
        """
        Get opportunities for a specific NAICS code

        Args:
            naics_code: NAICS code to filter by

        Returns:
            List of opportunities for the NAICS code
        """
        results = (
            self.db_session.query(Opportunity)
            .filter(Opportunity.naics_code.contains(naics_code))
            .all()
        )
        return [opp.to_dict() for opp in results]

    def get_all_opportunities(self) -> List[Dict[str, Any]]:
        """Get all stored opportunities"""
        results = self.db_session.query(Opportunity).all()
        return [opp.to_dict() for opp in results]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of collected opportunities"""
        all_opps = self.db_session.query(Opportunity).all()
        total = len(all_opps)

        if total == 0:
            return {"total_opportunities": 0, "naics_breakdown": {}, "date_range": None}

        naics_count: Dict[str, int] = {}
        dates = []

        for opp in all_opps:
            naics_codes = (opp.naics_code or "").split(",")
            for code in naics_codes:
                if code:
                    naics_count[code] = naics_count.get(code, 0) + 1
            dates.append(opp.collected_date)

        return {
            "total_opportunities": total,
            "naics_breakdown": naics_count,
            "date_range": {
                "earliest": min(dates).isoformat(),
                "latest": max(dates).isoformat(),
            },
        }
