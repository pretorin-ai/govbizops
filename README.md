# GovBizOps

A comprehensive Python library and Docker-based system for collecting, analyzing, and managing government contract opportunities from SAM.gov.

## Features

- **API Integration**: Fetch contract opportunities from SAM.gov API
- **Smart Filtering**: Filter opportunities by NAICS codes with intelligent OR logic
- **Data Management**: Maintain a running list of collected opportunities with duplicate prevention
- **Local Storage**: Store opportunities locally in JSON format with metadata
- **Advanced Querying**: Query stored opportunities by date range, NAICS code, or custom filters
- **Web Scraping**: Automatic fallback to web scraping when API data is incomplete
- **Document Extraction**: Extract and list all attached documents (RFPs, SOWs, etc.)
- **AI Analysis**: AI-powered solicitation analysis and response generation (OpenAI integration)
- **Web Interface**: Built-in Flask web viewer for browsing opportunities
- **Docker Support**: Complete Docker containerization with docker-compose orchestration
- **Scheduled Collection**: Automated daily/hourly opportunity collection
- **Command Line Interface**: Full CLI with multiple operation modes
- **Production Ready**: Server deployment guides and monitoring capabilities

## Installation

### Option 1: Docker (Recommended)

The easiest way to get started is with Docker:

```bash
# Clone the repository
git clone https://github.com/yourusername/govbizops.git
cd govbizops

# Create environment file
cp .env.example .env
# Edit .env with your API keys

# Run with Docker Compose
docker-compose up -d
```

### Option 2: Native Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/govbizops.git
cd govbizops

# Install the package
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt

# IMPORTANT: Install Playwright browsers for web scraping
python -m playwright install chromium
# Or use the included setup script after installation:
govbizops-setup
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
   
   # Edit .env and add your API keys
   SAM_GOV_API_KEY=your_api_key_here
   OPENAI_API_KEY=your_openai_key_here  # Optional, for AI analysis
   ```

## Docker Usage

### Quick Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View opportunities in browser
open http://localhost:5000
```

### Available Services

- **Collector**: Automatically collects opportunities every hour
- **Viewer**: Web interface at http://localhost:5000
- **Analyzer**: On-demand analysis service

### Individual Docker Commands

```bash
# One-time collection
docker run --rm -e SAM_GOV_API_KEY=your_key --shm-size=1g govbizops python main.py collect

# Run web viewer
docker run --rm -p 5000:5000 -v $(pwd)/data:/app/data govbizops python main.py viewer

# Analyze specific opportunity
docker run --rm -e SAM_GOV_API_KEY=your_key -e OPENAI_API_KEY=your_key --shm-size=1g govbizops \
  python main.py analyze --url "https://sam.gov/opp/abc123/view"
```

For detailed Docker usage, see [DOCKER_USAGE.md](DOCKER_USAGE.md).

## Command Line Interface

The library includes a comprehensive CLI through `main.py` with multiple operation modes:

### Collection Commands

```bash
# Collect opportunities from the past day
python main.py collect

# Collect from the past 7 days with AI analysis
python main.py collect --days-back 7 --analyze

# Collect specific NAICS codes
python main.py collect --naics-codes "541511,541512,541513"

# Scheduled collection every 2 hours
python main.py schedule --interval 120 --analyze
```

### Analysis Commands

```bash
# Analyze specific opportunity by URL
python main.py analyze --url "https://sam.gov/opp/abc123/view"

# Analyze all opportunities in a file
python main.py analyze --opportunity-file opportunities.json

# Analyze with custom settings
python main.py analyze --opportunity-file opportunities.json --max-analyze 20
```

### Web Interface

```bash
# Start web viewer on port 5000
python main.py viewer

# Custom port
python main.py viewer --port 8080
```

### Diagnostic Commands

```bash
# Test browser functionality
python main.py diagnose
```

## Quick Start

### Using the Command Line Interface

```bash
# Set up environment
export SAM_GOV_API_KEY="your_api_key_here"
export OPENAI_API_KEY="your_openai_key_here"  # Optional

# Collect opportunities from the past day
python main.py collect

# View them in the web interface
python main.py viewer
# Open http://localhost:5000 in your browser
```

### Using the Python Library

```python
from govbizops import OpportunityCollector

# Define NAICS codes to track
naics_codes = [
    "541511",  # Custom Computer Programming Services
    "541512",  # Computer Systems Design Services
    "541519",  # Other Computer Related Services (most active)
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

## Web Interface

The library includes a built-in Flask web viewer for displaying and analyzing collected opportunities.

### Running the Web Viewer

1. **Using the CLI**:
   ```bash
   python main.py viewer
   ```

2. **Using Docker**:
   ```bash
   docker-compose up -d viewer
   ```

3. **Open your browser** to http://localhost:5000

### Features

- **Browse Opportunities**: View all collected opportunities in a clean, searchable interface
- **Filter by NAICS**: Filter opportunities by NAICS codes
- **Date Range Filtering**: Filter by posted date or collection date
- **AI Analysis**: Analyze individual opportunities with AI (requires OpenAI API key)
- **Document Links**: Direct links to SAM.gov opportunity pages
- **Export Options**: Export filtered results to JSON

The viewer automatically loads opportunities from the configured storage file and provides real-time analysis capabilities.

## Solicitation Analyzer

The library includes a powerful solicitation analyzer that can fetch detailed descriptions and generate AI responses.

### Features

- **Automatic fallback to web scraping**: When SAM.gov's API doesn't provide descriptions, the analyzer automatically scrapes the web page
- **Document extraction**: Finds and lists all attached documents (RFPs, SOWs, etc.)
- **AI response generation**: Uses OpenAI to generate professional solicitation responses

### Usage

```python
from govbizops import SolicitationAnalyzer
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize analyzer
analyzer = SolicitationAnalyzer(
    api_key=os.getenv("SAM_GOV_API_KEY")
)

# Analyze an opportunity
opportunity = {
    "noticeId": "abc123",
    "title": "IT Services RFP",
    "description": "https://api.sam.gov/...",  # API URL
    "uiLink": "https://sam.gov/opp/abc123/view"  # Web URL
}

result = analyzer.analyze_solicitation(opportunity)

# Access the results
print("Description:", result["detailed_description"])
print("Documents:", result["documents_info"])
print("AI Response:", result["ai_response"])
```

### Analyzing by URL

You can also analyze directly from a SAM.gov URL:

```python
sam_url = "https://sam.gov/opp/7a7c8b4c48104106bee6f9356ccfa460/view"
result = analyzer.analyze_by_url(sam_url)
```

### Web Scraping Notes

- The analyzer uses Playwright to handle JavaScript-rendered content
- Automatically converts workspace URLs to public URLs
- Extracts both descriptions and document attachments
- Requires Playwright browsers to be installed (see Installation section)

## Production Deployment

### Docker Compose Deployment

For production environments, use the included docker-compose setup:

```bash
# Create production environment file
cat > .env << EOF
SAM_GOV_API_KEY=your_production_api_key
OPENAI_API_KEY=your_production_openai_key
DB_PASSWORD=secure_database_password
EOF

# Start all services
docker-compose up -d

# Monitor logs
docker-compose logs -f
```

### Server Deployment

For server deployment, see the comprehensive [DEPLOYMENT.md](DEPLOYMENT.md) guide which covers:

- **Ubuntu/Debian Installation**: Native server setup with system dependencies
- **CentOS/RHEL Installation**: Enterprise Linux setup
- **Docker Production**: Optimized container deployment
- **Scaling**: Horizontal scaling and load balancing
- **Monitoring**: Health checks and performance monitoring
- **Security**: Best practices for production environments

### Environment Variables

```bash
# Required
SAM_GOV_API_KEY=your_sam_gov_api_key

# Optional but recommended
OPENAI_API_KEY=your_openai_api_key

# Server optimizations
GOVBIZOPS_SERVER_MODE=true
GOVBIZOPS_MAX_CONCURRENT=3
GOVBIZOPS_CACHE_DIR=/app/cache
```

## Development

Run the example script to test the library:

```bash
python example.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Troubleshooting

### Common Issues & Solutions

**Issue: Browser fails to launch in Docker**
```bash
# Solution: Increase shared memory and add capabilities
docker run --shm-size=1g --cap-add=SYS_ADMIN govbizops

# Or in docker-compose.yml:
# shm_size: 1g
# cap_add:
#   - SYS_ADMIN
```

**Issue: "error while loading shared libraries"**
```bash
# Test system dependencies
docker run --rm govbizops python main.py diagnose

# If dependencies missing, rebuild with additional packages
```

**Issue: Timeout errors on server**
```python
# Increase timeout values for server environments
scraper = SAMWebScraper(server_mode=True)
# Server mode automatically applies optimizations
```

**Issue: Memory issues with multiple scraping operations**
```bash
# Limit concurrent operations
export GOVBIZOPS_MAX_CONCURRENT=2

# Monitor memory usage
docker stats govbizops
```

**Issue: API rate limiting**
```bash
# Reduce collection frequency
python main.py schedule --interval 120  # Every 2 hours instead of 1

# Or collect fewer opportunities per run
python main.py collect --max-analyze 5
```

### Testing Your Setup

Run the diagnostic script to test browser functionality:

```bash
# Using CLI
python main.py diagnose

# In Docker
docker run --rm --shm-size=1g govbizops python main.py diagnose

# Native installation
python diagnose_browser.py
```

### Resource Requirements

- **Minimum**: 1GB RAM, 1 CPU core
- **Recommended**: 2GB RAM, 2 CPU cores
- **Storage**: ~500MB for browsers + dependencies
- **Network**: Stable internet connection for API calls and web scraping

## Project Structure

```
govbizops/
├── __init__.py              # Package initialization
├── client.py                # SAM.gov API client
├── collector.py             # Opportunity collection logic
├── sam_scraper.py           # Web scraping functionality
├── solicitation_analyzer.py # AI analysis and response generation
├── main.py                  # Command-line interface
├── simple_viewer.py         # Flask web interface
├── example.py               # Usage examples
├── diagnose_browser.py      # Browser diagnostic tool
├── setup_playwright.py      # Playwright setup script
├── requirements.txt         # Python dependencies
├── setup.py                 # Package configuration
├── Dockerfile               # Docker image definition
├── docker-compose.yml       # Multi-service orchestration
├── templates/               # Web interface templates
│   ├── simple_viewer.html
│   └── analysis_view.html
├── README.md                # This file
├── DOCKER_USAGE.md          # Detailed Docker usage guide
└── DEPLOYMENT.md            # Production deployment guide
```

## Disclaimer

This library is not affiliated with or endorsed by SAM.gov or the U.S. Government. 
