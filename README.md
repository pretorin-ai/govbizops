# GovBizOps

[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

A Python library for collecting, analyzing, and managing government contract opportunities from SAM.gov.

## Features

- **SAM.gov API Integration** - Fetch contract opportunities with official API
- **Smart Filtering** - Filter by NAICS codes with intelligent OR logic
- **Data Management** - Store opportunities locally with duplicate prevention
- **Web Scraping Fallback** - Extract complete data when API is incomplete
- **AI Analysis** - Generate solicitation responses with OpenAI (optional)
- **Web Interface** - Browse and analyze opportunities in your browser
- **Docker Support** - Full containerization and orchestration
- **CLI & Python API** - Use via command line or import as a library

## Quick Start

```bash
# Install the package
git clone https://github.com/yourusername/govbizops.git
cd govbizops
pip install -e .
govbizops-setup  # Install Playwright browsers for web scraping

# Set your API key (get one from SAM.gov)
export SAM_GOV_API_KEY="your_key_here"

# Collect opportunities (uses default NAICS codes from config)
govbizops collect

# Or specify your industry's NAICS codes
govbizops collect --naics-codes "123456,234567,345678"

# Start web viewer to browse collected opportunities
govbizops viewer
# Open http://localhost:5000 in your browser

# Analyze a specific opportunity with AI
govbizops analyze --url "https://sam.gov/opp/abc123/view"
```

## Installation

```bash
git clone https://github.com/pretorin-ai/govbizops.git
cd govbizops
pip install -e .
govbizops-setup  # Install Playwright browsers for web scraping
```

**Requirements:**
- Python 3.8+
- SAM.gov API Key (free - [get one here](https://sam.gov/))
- Optional: OpenAI API Key (for AI analysis features)

## Configuration

**Get a SAM.gov API Key**
1. Sign up at [SAM.gov](https://sam.gov/)
2. Navigate to Account Details → Generate Public API Key

**Set Environment Variables**
```bash
export SAM_GOV_API_KEY="your_api_key_here"
export OPENAI_API_KEY="your_openai_key"  # Optional, for AI features
```

Or create a `.env` file:
```bash
SAM_GOV_API_KEY=your_api_key_here
OPENAI_API_KEY=your_openai_key
```

## Usage

### Command Line Interface

**Collect Opportunities**
```bash
govbizops collect                                        # Past 24 hours (uses defaults)
govbizops collect --days-back 7                          # Past week
govbizops collect --naics-codes "123456,234567,345678"   # Your industry codes (max 3)
govbizops collect --naics-codes "123456,234567" --days-back 3  # Past 3 days
```

**Web Viewer**
```bash
govbizops viewer                 # Start on port 5000
govbizops viewer --port 8080     # Custom port
```

**AI Analysis**
```bash
govbizops analyze --url "https://sam.gov/opp/abc123/view"
govbizops analyze --opportunity-file opportunities.json
```

**Scheduled Collection**
```bash
govbizops schedule --interval 120  # Every 2 hours
```

### Python Library

```python
from govbizops import OpportunityCollector

# Initialize collector with your industry's NAICS codes
collector = OpportunityCollector(
    api_key="your_api_key_here",
    naics_codes=[
        "123456",  # Your primary NAICS code
        "234567",  # Related NAICS code
        "345678"   # Additional NAICS code
    ],
    storage_path="opportunities.json"
)

# Collect new opportunities from the past day
new_opps = collector.collect_daily_opportunities()
print(f"Found {len(new_opps)} new opportunities")

# Query stored data
recent = collector.get_opportunities_by_date_range(start_date, end_date)
by_naics = collector.get_opportunities_by_naics("123456")
all_opps = collector.get_all_opportunities()
```

**AI Analysis**
```python
from govbizops import SolicitationAnalyzer

analyzer = SolicitationAnalyzer(api_key="your_api_key")
result = analyzer.analyze_by_url("https://sam.gov/opp/abc123/view")

print(result["detailed_description"])
print(result["ai_response"])
```

## NAICS Codes

NAICS codes are used to filter contract opportunities by industry. You can specify up to 3 codes per collection.

**How to find your industry's NAICS codes:**
1. Visit [NAICS.com](https://www.naics.com/search/) or [Census.gov NAICS](https://www.census.gov/naics/)
2. Search for your industry (e.g., "construction", "engineering", "consulting", "IT services")
3. Note the 6-digit codes that match your services
4. Use up to 3 codes in your collection command

**Example usage:**
```bash
# Specify your industry's NAICS codes (max 3)
govbizops collect --naics-codes "123456,234567,345678"

# Collect from multiple related codes over past week
govbizops collect --naics-codes "123456,234567" --days-back 7
```

**Note:** The library uses OR logic - it will find opportunities matching ANY of your specified codes (not all of them).

## Docker Deployment

For automated/production deployments, use Docker Compose:

```bash
# Set up environment
cp .env.example .env
# Edit .env and configure:
#   - SAM_GOV_API_KEY (required)
#   - NAICS_CODES (your industry codes, e.g., "123456,234567,345678")
#   - COLLECTION_INTERVAL (minutes, default: 60)
#   - MAX_ANALYZE (max opportunities to analyze, default: 5)

# Start automated services
docker-compose up -d

# Services:
# - Collector: Runs on schedule to collect new opportunities (uses NAICS_CODES from .env)
# - Viewer: Web interface at http://localhost:5000
```

**Run One-off Commands**
```bash
# Collect opportunities on demand
docker-compose run --rm collector govbizops collect --days-back 7

# Collect with specific NAICS codes (overrides .env)
docker-compose run --rm collector govbizops collect --naics-codes "123456,234567"

# Analyze specific opportunity
docker-compose run --rm collector govbizops analyze --url "https://sam.gov/opp/abc/view"
```

See [DOCKER_USAGE.md](DOCKER_USAGE.md) for detailed Docker documentation.

## Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for production setup, scaling, and monitoring.

## Troubleshooting

```bash
# Test browser setup
govbizops diagnose

# Docker browser issues - add shared memory
docker run --shm-size=1g govbizops

# Reduce API rate limit issues
govbizops schedule --interval 120
```

## Project Structure

```
govbizops/
├── client.py                # SAM.gov API client
├── collector.py             # Opportunity collection
├── sam_scraper.py           # Web scraping
├── solicitation_analyzer.py # AI analysis
├── main.py                  # CLI interface
├── simple_viewer.py         # Web interface
└── templates/               # Web UI templates
```

## Contributing

Contributions welcome! Please submit a Pull Request.

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push and open a Pull Request

## License & Compliance

This library is licensed under the MIT License. See [LICENSE](LICENSE) for details.

**SAM.gov Terms of Use**

By using this library, you agree to comply with [SAM.gov Terms of Use](https://sam.gov/about/terms-of-use):

- Uses official SAM.gov APIs for data collection
- Web scraping only as fallback for public data when API is incomplete
- You must maintain your own API key (renewed every 90 days)
- Only accesses publicly available contract opportunities
- Configure appropriate intervals to avoid bulk data mining concerns
- Keep credentials secure and don't share API keys

This library is not affiliated with or endorsed by SAM.gov or the U.S. Government.

---

**Made for the government contracting community** 
