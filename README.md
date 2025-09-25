# GovBizOps

A Python library for collecting and managing government contract opportunities.

## Features

- Fetch contract opportunities from SAM.gov API
- Filter opportunities by NAICS codes
- Maintain a running list of collected opportunities
- Prevent duplicate entries
- Store opportunities locally in JSON format
- Query stored opportunities by date range or NAICS code

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/govbizops.git
cd govbizops

# Install the package
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

## Setup

1. **Get a SAM.gov API Key**
   - Visit [SAM.gov](https://sam.gov/)
   - Create an account or sign in
   - Navigate to your Account Details page
   - Generate a Public API Key

2. **Configure Environment**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and add your API key
   SAM_GOV_API_KEY=your_api_key_here
   ```

## Quick Start

```python
from govbizops import OpportunityCollector

# Define NAICS codes to track
naics_codes = [
    "541511",  # Custom Computer Programming Services
    "541512",  # Computer Systems Design Services
]

# Initialize collector
collector = OpportunityCollector(
    api_key="your_api_key_here",
    naics_codes=naics_codes,
    storage_path="opportunities.json"
)

# Collect opportunities from the past day
new_opportunities = collector.collect_daily_opportunities()
print(f"Found {len(new_opportunities)} new opportunities")

# Get summary statistics
summary = collector.get_summary()
print(f"Total opportunities: {summary['total_opportunities']}")
```

## Usage Examples

### Basic API Client Usage

```python
from govbizops import SAMGovClient
from datetime import datetime, timedelta

# Initialize client
client = SAMGovClient(api_key="your_api_key_here")

# Search opportunities from the past week
end_date = datetime.now()
start_date = end_date - timedelta(days=7)

opportunities = client.get_all_opportunities(
    posted_from=start_date,
    posted_to=end_date,
    naics_codes=["541511", "541512"]
)

for opp in opportunities:
    print(f"{opp['noticeId']}: {opp['title']}")
```

### Daily Collection Script

```python
from govbizops import OpportunityCollector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize collector
collector = OpportunityCollector(
    api_key=os.getenv("SAM_GOV_API_KEY"),
    naics_codes=["541511", "541512", "541513", "541519"],
    storage_path="federal_opportunities.json"
)

# Collect daily opportunities
new_opps = collector.collect_daily_opportunities()

# Display new opportunities
for opp in new_opps:
    print(f"\nTitle: {opp['title']}")
    print(f"Notice ID: {opp['noticeId']}")
    print(f"Posted: {opp['postedDate']}")
    print(f"Response Deadline: {opp['responseDeadLine']}")
```

### Query Stored Opportunities

```python
from datetime import datetime, timedelta

# Get opportunities from the past 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

recent_opps = collector.get_opportunities_by_date_range(start_date, end_date)

# Get opportunities for a specific NAICS code
it_services_opps = collector.get_opportunities_by_naics("541511")

# Get all stored opportunities
all_opps = collector.get_all_opportunities()
```

### Automated Daily Collection

Create a script for automated daily collection (e.g., `daily_collection.py`):

```python
#!/usr/bin/env python3
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from govbizops import OpportunityCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"collection_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler()
    ]
)

load_dotenv()

# Your NAICS codes
NAICS_CODES = [
    "541511",  # Custom Computer Programming Services
    "541512",  # Computer Systems Design Services
    "541513",  # Computer Facilities Management Services
    "541519",  # Other Computer Related Services
    "541611",  # Administrative Management Consulting
    "541618",  # Other Management Consulting Services
]

def main():
    collector = OpportunityCollector(
        api_key=os.getenv("SAM_GOV_API_KEY"),
        naics_codes=NAICS_CODES,
        storage_path="opportunities_database.json"
    )
    
    logging.info("Starting daily opportunity collection")
    new_opportunities = collector.collect_daily_opportunities()
    
    if new_opportunities:
        logging.info(f"Collected {len(new_opportunities)} new opportunities")
        
        # Send notifications, update database, etc.
        for opp in new_opportunities:
            logging.info(f"New: {opp['noticeId']} - {opp['title']}")
    else:
        logging.info("No new opportunities found today")
    
    # Log summary
    summary = collector.get_summary()
    logging.info(f"Total opportunities in database: {summary['total_opportunities']}")

if __name__ == "__main__":
    main()
```

Schedule this script to run daily using cron (Linux/Mac) or Task Scheduler (Windows).

## NAICS Codes Reference

Common IT-related NAICS codes:
- `541519` - Other Computer Related Services (most active for IT opportunities)
- `513210` - Software Publishers
- `541511` - Custom Computer Programming Services
- `541512` - Computer Systems Design Services
- `541513` - Computer Facilities Management Services
- `611430` - Professional and Management Development Training
- `334111` - Electronic Computer Manufacturing

Find more NAICS codes at [NAICS Association](https://www.naics.com/search/).

**Important Note:** The SAM.gov API treats multiple NAICS codes as an AND condition (opportunities must match ALL codes) rather than OR (opportunities matching ANY code). The library handles this by querying each NAICS code separately and combining the results.

## API Response Format

Each opportunity contains fields such as:
- `noticeId` - Unique identifier
- `title` - Opportunity title
- `solicitationNumber` - Solicitation number
- `postedDate` - When the opportunity was posted
- `responseDeadLine` - Submission deadline
- `naicsCode` - Applicable NAICS codes
- `type` - Opportunity type
- `organizationHierarchy` - Issuing organization details

## Development

Run the example script to test the library:

```bash
python example.py
```

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This library is not affiliated with or endorsed by SAM.gov or the U.S. Government. 
