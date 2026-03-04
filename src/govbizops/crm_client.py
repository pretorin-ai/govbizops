"""
CRM client for posting SAM.gov opportunities to Pretorin CRM
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from .database import Opportunity

logger = logging.getLogger(__name__)


class CRMClient:
    """Client for interacting with Pretorin CRM API"""

    def __init__(self, base_url: str, api_key: str):
        """
        Initialize CRM client

        Args:
            base_url: Base URL of the CRM API (e.g., http://localhost:8000)
            api_key: CRM API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def login(self) -> bool:
        """
        Validate API key by making a test request

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/auth/me")
            response.raise_for_status()
            logger.info("Successfully authenticated with CRM API key")
            return True

        except Exception as e:
            logger.error(f"API key authentication failed: {e}")
            return False

    def import_opportunities(
        self, opportunities: List[Dict[str, Any]], auto_create_contacts: bool = True
    ) -> Dict[str, Any]:
        """
        Import SAM.gov opportunities to CRM

        Args:
            opportunities: List of opportunity dictionaries from SAM.gov
            auto_create_contacts: Whether to automatically create contacts from point-of-contact info

        Returns:
            Response dictionary with import results
        """
        if not self.login():
            raise Exception("Failed to authenticate with CRM API key")

        transformed_opps = []
        for opp in opportunities:
            transformed = {
                "noticeId": opp.get("noticeId"),
                "title": opp.get("title"),
                "solicitationNumber": opp.get("solicitationNumber"),
                "description": opp.get("description"),
                "responseDeadLine": opp.get("responseDeadLine"),
                "postedDate": opp.get("postedDate"),
                "naicsCode": opp.get("naicsCode"),
                "uiLink": opp.get("uiLink"),
                "pointOfContact": opp.get("pointOfContact", []),
                "source": "SAM.gov",
                "notes": "",
            }
            transformed_opps.append(transformed)

        payload = {
            "opportunities": transformed_opps,
            "auto_create_contacts": auto_create_contacts,
        }

        try:
            response = self.session.post(
                f"{self.base_url}/contracts/import/samgov", json=payload
            )
            response.raise_for_status()

            result = response.json()
            logger.info(
                f"Import complete: {result['contracts_created']} contracts created, "
                f"{result['contracts_skipped']} skipped, "
                f"{result['contacts_created']} contacts created"
            )

            if result.get("errors"):
                logger.warning(f"Errors during import: {result['errors']}")

            return result

        except Exception as e:
            logger.error(f"Failed to import opportunities: {e}")
            raise

    def push_collected_opportunities(
        self,
        db_session: Session,
        auto_create_contacts: bool = True,
    ) -> Dict[str, Any]:
        """
        Push all collected opportunities from database to CRM

        Args:
            db_session: SQLAlchemy session to query opportunities
            auto_create_contacts: Whether to automatically create contacts

        Returns:
            Response dictionary with import results
        """
        try:
            all_opps = db_session.query(Opportunity).all()
            opportunities = [opp.to_dict() for opp in all_opps]

            logger.info(f"Pushing {len(opportunities)} opportunities to CRM")
            return self.import_opportunities(opportunities, auto_create_contacts)

        except Exception as e:
            logger.error(f"Failed to push opportunities: {e}")
            raise


def push_to_crm(
    crm_url: str,
    crm_api_key: str,
    db_session: Session,
    auto_create_contacts: bool = True,
) -> Dict[str, Any]:
    """
    Convenience function to push opportunities to CRM

    Args:
        crm_url: Base URL of the CRM API
        crm_api_key: CRM API key for authentication
        db_session: SQLAlchemy session to query opportunities
        auto_create_contacts: Whether to auto-create contacts

    Returns:
        Import results dictionary
    """
    client = CRMClient(crm_url, crm_api_key)
    return client.push_collected_opportunities(db_session, auto_create_contacts)


if __name__ == "__main__":
    import os
    from .database import get_engine, get_session, init_db

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    crm_url = os.getenv("CRM_URL", "http://localhost:8000")
    crm_api_key = os.getenv("CRM_API_KEY")

    if not crm_api_key:
        print("ERROR: CRM_API_KEY environment variable is required")
        print("\nTo get your API key:")
        print("1. Log in to your CRM at http://localhost:5173")
        print("2. Go to Settings")
        print("3. Click 'Generate API Key'")
        print("4. Copy the key and set it: export CRM_API_KEY=crm_...")
        exit(1)

    engine = get_engine()
    init_db(engine)
    SessionFactory = get_session(engine)
    session = SessionFactory()

    try:
        result = push_to_crm(
            crm_url=crm_url,
            crm_api_key=crm_api_key,
            db_session=session,
            auto_create_contacts=True,
        )

        print("\n" + "=" * 50)
        print("CRM IMPORT RESULTS")
        print("=" * 50)
        print(f"Contracts created: {result['contracts_created']}")
        print(f"Contracts skipped: {result['contracts_skipped']}")
        print(f"Contacts created:  {result['contacts_created']}")

        if result.get("errors"):
            print(f"\nErrors ({len(result['errors'])}):")
            for error in result["errors"][:5]:
                print(f"  - {error}")
            if len(result["errors"]) > 5:
                print(f"  ... and {len(result['errors']) - 5} more")

        print("=" * 50)

    except Exception as e:
        print(f"Failed to push opportunities to CRM: {e}")
        exit(1)
    finally:
        session.close()
