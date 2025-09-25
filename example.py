"""
Example usage of the GovBizOps library
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

from govbizops import OpportunityCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Load environment variables
load_dotenv()

def main():
    # Get API key from environment
    api_key = os.getenv("SAM_GOV_API_KEY")
    if not api_key:
        print("Please set SAM_GOV_API_KEY in your environment or .env file")
        print("You can get an API key from: https://sam.gov/")
        return
    
    # Define NAICS codes to track
    # Example: IT services and software development
    # Note: These codes have been verified to have active opportunities
    naics_codes = [
        "541519",  # Other Computer Related Services (most active)
        "513210",  # Software Publishers
        "541511",  # Custom Computer Programming Services
        "541512",  # Computer Systems Design Services
    ]
    
    # Initialize collector
    collector = OpportunityCollector(
        api_key=api_key,
        naics_codes=naics_codes,
        storage_path="federal_opportunities.json"
    )
    
    print("Collecting daily opportunities...")
    
    # Collect opportunities from the past day
    new_opportunities = collector.collect_daily_opportunities(days_back=1)
    
    print(f"\nFound {len(new_opportunities)} new opportunities")
    
    # Display summary of new opportunities
    for opp in new_opportunities[:5]:  # Show first 5
        print(f"\n{'='*60}")
        print(f"Notice ID: {opp.get('noticeId')}")
        print(f"Title: {opp.get('title')}")
        print(f"Posted Date: {opp.get('postedDate')}")
        print(f"Response Deadline: {opp.get('responseDeadLine')}")
        print(f"NAICS: {opp.get('naicsCode')}")
        print(f"Type: {opp.get('type')}")
        
        # Show organization info
        org_info = opp.get('organizationHierarchy', [{}])[0]
        if org_info:
            print(f"Organization: {org_info.get('name')}")
            print(f"Department: {org_info.get('department')}")
    
    # Show overall summary
    print(f"\n{'='*60}")
    print("Overall Summary:")
    summary = collector.get_summary()
    print(f"Total opportunities in database: {summary['total_opportunities']}")
    print("\nNAICS breakdown:")
    for code, count in summary['naics_breakdown'].items():
        print(f"  {code}: {count} opportunities")
    
    if summary['date_range']:
        print(f"\nDate range: {summary['date_range']['earliest']} to {summary['date_range']['latest']}")


if __name__ == "__main__":
    main()