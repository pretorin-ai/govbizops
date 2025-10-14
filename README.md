# 🏛️ GovBizOps

[![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![SAM.gov](https://img.shields.io/badge/SAM.gov-API-FF6B35?style=for-the-badge&logo=government&logoColor=white)](https://sam.gov)
[![OpenAI](https://img.shields.io/badge/OpenAI-Enabled-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)

> 🚀 **A comprehensive Python library and Docker-based system for collecting, analyzing, and managing government contract opportunities from SAM.gov.**

---

## ✨ Features

| Feature | Description | Status |
|---------|-------------|--------|
| 🔌 **API Integration** | Fetch contract opportunities from SAM.gov API | ✅ Ready |
| 🎯 **Smart Filtering** | Filter opportunities by NAICS codes with intelligent OR logic | ✅ Ready |
| 💾 **Data Management** | Maintain a running list of collected opportunities with duplicate prevention | ✅ Ready |
| 📁 **Local Storage** | Store opportunities locally in JSON format with metadata | ✅ Ready |
| 🔍 **Advanced Querying** | Query stored opportunities by date range, NAICS code, or custom filters | ✅ Ready |
| 🕷️ **Web Scraping** | Automatic fallback to web scraping when API data is incomplete | ✅ Ready |
| 📄 **Document Extraction** | Extract and list all attached documents (RFPs, SOWs, etc.) | ✅ Ready |
| 🤖 **AI Analysis** | AI-powered solicitation analysis and response generation (OpenAI integration) | ✅ Ready |
| 🌐 **Web Interface** | Built-in Flask web viewer for browsing opportunities | ✅ Ready |
| 🐳 **Docker Support** | Complete Docker containerization with docker-compose orchestration | ✅ Ready |
| ⏰ **Scheduled Collection** | Automated daily/hourly opportunity collection | ✅ Ready |
| 💻 **Command Line Interface** | Full CLI with multiple operation modes | ✅ Ready |
| 🚀 **Production Ready** | Server deployment guides and monitoring capabilities | ✅ Ready |

## 🚀 Installation

### 🐳 Option 1: Docker (Recommended)

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

### 🐍 Option 2: Native Installation

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

## ⚙️ Setup

### 1. 🔑 Get a SAM.gov API Key
   - Visit [SAM.gov](https://sam.gov/)
   - Create an account or sign in
   - Navigate to your Account Details page
   - Generate a Public API Key

### 2. 🔧 Configure Environment
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and add your API keys
   SAM_GOV_API_KEY=your_api_key_here
   OPENAI_API_KEY=your_openai_key_here  # Optional, for AI analysis
   ```

## 🐳 Docker Usage

### ⚡ Quick Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View opportunities in browser
open http://localhost:5000
```

### 🛠️ Available Services

| Service | Description | Port |
|---------|-------------|------|
| 🔄 **Collector** | Automatically collects opportunities every hour | - |
| 🌐 **Viewer** | Web interface for browsing opportunities | `5000` |
| 🤖 **Analyzer** | On-demand analysis service | - |

### 🔧 Individual Docker Commands

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

## 💻 Command Line Interface

The library includes a comprehensive CLI through `main.py` with multiple operation modes:

### 📥 Collection Commands

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

### 🔍 Analysis Commands

```bash
# Analyze specific opportunity by URL
python main.py analyze --url "https://sam.gov/opp/abc123/view"

# Analyze all opportunities in a file
python main.py analyze --opportunity-file opportunities.json

# Analyze with custom settings
python main.py analyze --opportunity-file opportunities.json --max-analyze 20
```

### 🌐 Web Interface

```bash
# Start web viewer on port 5000
python main.py viewer

# Custom port
python main.py viewer --port 8080
```

### 🔧 Diagnostic Commands

```bash
# Test browser functionality
python main.py diagnose
```

## 🚀 Quick Start

### 💻 Using the Command Line Interface

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

### 🐍 Using the Python Library

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

## 📚 Usage Examples

### 🔌 Basic API Client Usage

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

### 📅 Daily Collection Script

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

### 🔍 Query Stored Opportunities

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

### ⏰ Automated Daily Collection

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

## 📋 NAICS Codes Reference

### 🖥️ Common IT-related NAICS codes:
| Code | Description | Activity Level |
|------|-------------|----------------|
| `541519` | Other Computer Related Services | 🔥 **Most Active** |
| `513210` | Software Publishers | ⚡ High |
| `541511` | Custom Computer Programming Services | ⚡ High |
| `541512` | Computer Systems Design Services | ⚡ High |
| `541513` | Computer Facilities Management Services | 📈 Medium |
| `611430` | Professional and Management Development Training | 📈 Medium |
| `334111` | Electronic Computer Manufacturing | 📊 Low |

> 🔍 **Find more NAICS codes at [NAICS Association](https://www.naics.com/search/)**

> ⚠️ **Important Note:** The SAM.gov API treats multiple NAICS codes as an AND condition (opportunities must match ALL codes) rather than OR (opportunities matching ANY code). The library handles this by querying each NAICS code separately and combining the results.

## 📊 API Response Format

Each opportunity contains fields such as:

| Field | Type | Description |
|-------|------|-------------|
| `noticeId` | String | Unique identifier |
| `title` | String | Opportunity title |
| `solicitationNumber` | String | Solicitation number |
| `postedDate` | DateTime | When the opportunity was posted |
| `responseDeadLine` | DateTime | Submission deadline |
| `naicsCode` | Array | Applicable NAICS codes |
| `type` | String | Opportunity type |
| `organizationHierarchy` | Object | Issuing organization details |

## 🌐 Web Interface

The library includes a built-in Flask web viewer for displaying and analyzing collected opportunities.

### 🚀 Running the Web Viewer

1. **💻 Using the CLI**:
   ```bash
   python main.py viewer
   ```

2. **🐳 Using Docker**:
   ```bash
   docker-compose up -d viewer
   ```

3. **🌐 Open your browser** to http://localhost:5000

### ✨ Features

| Feature | Description | Status |
|---------|-------------|--------|
| 🔍 **Browse Opportunities** | View all collected opportunities in a clean, searchable interface | ✅ Ready |
| 🏷️ **Filter by NAICS** | Filter opportunities by NAICS codes | ✅ Ready |
| 📅 **Date Range Filtering** | Filter by posted date or collection date | ✅ Ready |
| 🤖 **AI Analysis** | Analyze individual opportunities with AI (requires OpenAI API key) | ✅ Ready |
| 🔗 **Document Links** | Direct links to SAM.gov opportunity pages | ✅ Ready |
| 📤 **Export Options** | Export filtered results to JSON | ✅ Ready |

The viewer automatically loads opportunities from the configured storage file and provides real-time analysis capabilities.

## 🤖 Solicitation Analyzer

The library includes a powerful solicitation analyzer that can fetch detailed descriptions and generate AI responses.

### ✨ Features

| Feature | Description | Status |
|---------|-------------|--------|
| 🕷️ **Automatic Web Scraping** | Fallback to web scraping when API data is incomplete | ✅ Ready |
| 📄 **Document Extraction** | Finds and lists all attached documents (RFPs, SOWs, etc.) | ✅ Ready |
| 🤖 **AI Response Generation** | Uses OpenAI to generate professional solicitation responses | ✅ Ready |

### 💻 Usage

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

### 🔗 Analyzing by URL

You can also analyze directly from a SAM.gov URL:

```python
sam_url = "https://sam.gov/opp/7a7c8b4c48104106bee6f9356ccfa460/view"
result = analyzer.analyze_by_url(sam_url)
```

### 🕷️ Web Scraping Notes

- The analyzer uses Playwright to handle JavaScript-rendered content
- Automatically converts workspace URLs to public URLs
- Extracts both descriptions and document attachments
- Requires Playwright browsers to be installed (see Installation section)

## 🚀 Production Deployment

### 🐳 Docker Compose Deployment

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

### 🖥️ Server Deployment

For server deployment, see the comprehensive [DEPLOYMENT.md](DEPLOYMENT.md) guide which covers:

| Platform | Description | Status |
|----------|-------------|--------|
| 🐧 **Ubuntu/Debian** | Native server setup with system dependencies | ✅ Ready |
| 🔴 **CentOS/RHEL** | Enterprise Linux setup | ✅ Ready |
| 🐳 **Docker Production** | Optimized container deployment | ✅ Ready |
| 📈 **Scaling** | Horizontal scaling and load balancing | ✅ Ready |
| 📊 **Monitoring** | Health checks and performance monitoring | ✅ Ready |
| 🔒 **Security** | Best practices for production environments | ✅ Ready |

### ⚙️ Environment Variables

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

## 🛠️ Development

Run the example script to test the library:

```bash
python example.py
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

### 🎯 How to Contribute

1. 🍴 Fork the repository
2. 🌿 Create a feature branch (`git checkout -b feature/amazing-feature`)
3. 💾 Commit your changes (`git commit -m 'Add some amazing feature'`)
4. 📤 Push to the branch (`git push origin feature/amazing-feature`)
5. 🔄 Open a Pull Request

## 🔧 Troubleshooting

### 🚨 Common Issues & Solutions

| Issue | Solution | Status |
|-------|----------|--------|
| 🐳 **Browser fails to launch in Docker** | Increase shared memory and add capabilities | ✅ Fixed |
| 📚 **"error while loading shared libraries"** | Test system dependencies and rebuild if needed | ✅ Fixed |
| ⏱️ **Timeout errors on server** | Use server mode for optimizations | ✅ Fixed |
| 💾 **Memory issues with multiple scraping** | Limit concurrent operations | ✅ Fixed |
| 🚦 **API rate limiting** | Reduce collection frequency | ✅ Fixed |

#### 🔧 Detailed Solutions

**🐳 Browser fails to launch in Docker**
```bash
# Solution: Increase shared memory and add capabilities
docker run --shm-size=1g --cap-add=SYS_ADMIN govbizops

# Or in docker-compose.yml:
# shm_size: 1g
# cap_add:
#   - SYS_ADMIN
```

**📚 "error while loading shared libraries"**
```bash
# Test system dependencies
docker run --rm govbizops python main.py diagnose

# If dependencies missing, rebuild with additional packages
```

**⏱️ Timeout errors on server**
```python
# Increase timeout values for server environments
scraper = SAMWebScraper(server_mode=True)
# Server mode automatically applies optimizations
```

**💾 Memory issues with multiple scraping operations**
```bash
# Limit concurrent operations
export GOVBIZOPS_MAX_CONCURRENT=2

# Monitor memory usage
docker stats govbizops
```

**🚦 API rate limiting**
```bash
# Reduce collection frequency
python main.py schedule --interval 120  # Every 2 hours instead of 1

# Or collect fewer opportunities per run
python main.py collect --max-analyze 5
```

### 🧪 Testing Your Setup

Run the diagnostic script to test browser functionality:

```bash
# Using CLI
python main.py diagnose

# In Docker
docker run --rm --shm-size=1g govbizops python main.py diagnose

# Native installation
python diagnose_browser.py
```

### 💻 Resource Requirements

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| 🧠 **RAM** | 1GB | 2GB | For browser operations |
| ⚡ **CPU** | 1 core | 2 cores | For concurrent operations |
| 💾 **Storage** | 500MB | 1GB | Browsers + dependencies |
| 🌐 **Network** | Stable | High-speed | API calls and web scraping |

## 📁 Project Structure

```
🏛️ govbizops/
├── 📦 __init__.py              # Package initialization
├── 🔌 client.py                # SAM.gov API client
├── 📥 collector.py             # Opportunity collection logic
├── 🕷️ sam_scraper.py           # Web scraping functionality
├── 🤖 solicitation_analyzer.py # AI analysis and response generation
├── 💻 main.py                  # Command-line interface
├── 🌐 simple_viewer.py         # Flask web interface
├── 📚 example.py               # Usage examples
├── 🔧 diagnose_browser.py      # Browser diagnostic tool
├── ⚙️ setup_playwright.py      # Playwright setup script
├── 📋 requirements.txt         # Python dependencies
├── ⚙️ setup.py                 # Package configuration
├── 🐳 Dockerfile               # Docker image definition
├── 🐳 docker-compose.yml       # Multi-service orchestration
├── 📁 templates/               # Web interface templates
│   ├── 🌐 simple_viewer.html
│   └── 📊 analysis_view.html
├── 📖 README.md                # This file
├── 🐳 DOCKER_USAGE.md          # Detailed Docker usage guide
└── 🚀 DEPLOYMENT.md            # Production deployment guide
```

## ⚠️ Disclaimer

> **This library is not affiliated with or endorsed by SAM.gov or the U.S. Government.**

### 📋 SAM.gov Terms of Use Compliance

When using this library to access SAM.gov data, you must comply with the [SAM.gov Terms of Use](https://sam.gov/about/terms-of-use). Here are the key requirements:

#### 🔒 **Data Access & API Usage**
- ✅ **Primary API Access**: This library primarily uses official SAM.gov APIs for data collection
- ✅ **API Key Management**: Users must maintain their own SAM.gov API keys and update them every 90 days
- ✅ **Public Data Only**: Only accesses publicly available contract opportunity data
- ✅ **Exception-Based Web Scraping**: Uses web scraping only as a fallback when API description URLs fail, accessing only public view pages (no login required)
- ⚠️ **Data Collection Scope**: The library can collect large amounts of data - users should configure appropriate collection parameters and intervals to comply with SAM.gov terms

#### 🚫 **Prohibited Activities**
- ❌ **No Unauthorized Access**: Users must only access data they are authorized to view
- ❌ **No Data Sharing**: Don't share API keys or system account credentials
- ❌ **No Malicious Activity**: No uploading of viruses or attempts to damage the system
- ❌ **No Login-Based Scraping**: Never use SAM.gov login credentials for automated data collection
- ⚠️ **Bulk Data Collection**: While the library can collect large amounts of data, users must ensure their usage complies with SAM.gov terms and doesn't constitute prohibited bulk data mining

#### 📊 **Data Usage Guidelines**
- **D&B Data Restrictions**: Some entity data is provided by Dun & Bradstreet with usage restrictions
- **Sensitive Information**: Never enter classified or sensitive information in public fields
- **Attribution**: When sharing data, properly attribute sources as required
- **Compliance**: Users are responsible for ensuring their use complies with all applicable terms
- **Web Scraping Scope**: Limited to public opportunity view pages only, no access to restricted or login-required content
- **Collection Limits**: Consider using smaller date ranges, fewer NAICS codes, and longer intervals to avoid potential bulk data mining concerns

#### 🔐 **Security Requirements**
- **Account Security**: Keep your SAM.gov credentials secure and don't share them
- **Data Protection**: Protect any downloaded data according to government security standards
- **Monitoring**: SAM.gov monitors API usage and may revoke access for violations
- **Reporting**: Report any security incidents or unauthorized access immediately

> **⚠️ Important**: By using this library, you agree to comply with all [SAM.gov Terms of Use](https://sam.gov/about/terms-of-use). Violations may result in loss of access to SAM.gov services.

## News
- **Coming Soon:** updated user interface and integration into other Pretorin tools

---

<div align="center">

**Made with ❤️ for the government contracting community**

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/yourusername/govbizops)
[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)

</div> 
