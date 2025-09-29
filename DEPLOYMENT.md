# Server Deployment Guide

This guide covers deploying GovBizOps in server environments for web scraping SAM.gov opportunities.

## Docker Deployment (Recommended)

### Quick Start

```bash
# Build the Docker image
docker build -t govbizops .

# Run with environment variables
docker run --rm \
  -e SAM_GOV_API_KEY=your_api_key_here \
  -e OPENAI_API_KEY=your_openai_key_here \
  -v $(pwd)/data:/app/data \
  govbizops
```

### Production Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  govbizops:
    build: .
    environment:
      - SAM_GOV_API_KEY=${SAM_GOV_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    mem_limit: 2g
    cpus: 1.0
    
  # Optional: Redis for caching
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    
  # Optional: PostgreSQL for persistent storage
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=govbizops
      - POSTGRES_USER=govbizops
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

Run with:
```bash
docker-compose up -d
```

## Native Server Installation

### Ubuntu/Debian

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    wget \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils

# Install the package
pip3 install govbizops

# Install Playwright browsers
python3 -m playwright install chromium
```

### CentOS/RHEL/Amazon Linux

```bash
# Install system dependencies
sudo yum update -y
sudo yum install -y \
    python3 \
    python3-pip \
    wget \
    alsa-lib \
    atk \
    cups-libs \
    gtk3 \
    libX11 \
    libXcomposite \
    libXdamage \
    libXext \
    libXfixes \
    libXrandr \
    libgbm \
    libxcb \
    libxkbcommon \
    nspr \
    nss

# Install the package
pip3 install govbizops

# Install Playwright browsers
python3 -m playwright install chromium
```

## Server Optimizations

### Memory Considerations

- Minimum RAM: 1GB
- Recommended RAM: 2GB+
- Chromium uses ~100-300MB per browser instance

### CPU Considerations

- Web scraping is CPU-intensive during page rendering
- Recommend at least 1 CPU core per concurrent scraping operation
- Multiple instances can run in parallel for batch processing

### Environment Variables

```bash
# Required
export SAM_GOV_API_KEY="your_api_key"

# Optional but recommended
export OPENAI_API_KEY="your_openai_key"

# Server optimizations
export GOVBIZOPS_SERVER_MODE=true
export GOVBIZOPS_MAX_CONCURRENT=3
export GOVBIZOPS_CACHE_DIR="/app/cache"

# Browser optimizations
export PLAYWRIGHT_BROWSERS_PATH="/app/browsers"
```

## Usage Examples

### Basic Server Script

```python
#!/usr/bin/env python3
"""
Server-side opportunity analyzer
"""

import os
import logging
from govbizops import OpportunityCollector, SolicitationAnalyzer

# Configure logging for server
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/govbizops.log'),
        logging.StreamHandler()
    ]
)

def main():
    # Initialize components
    collector = OpportunityCollector(
        api_key=os.environ['SAM_GOV_API_KEY'],
        naics_codes=['541511', '541512']
    )
    
    analyzer = SolicitationAnalyzer(
        api_key=os.environ['SAM_GOV_API_KEY']
    )
    
    # Collect opportunities
    opportunities = collector.collect_daily_opportunities()
    
    # Analyze each with web scraping
    for opp in opportunities:
        try:
            result = analyzer.analyze_solicitation(opp)
            logging.info(f"Analyzed: {opp['title']}")
            
            # Save to database, send notifications, etc.
            
        except Exception as e:
            logging.error(f"Analysis failed for {opp['noticeId']}: {e}")

if __name__ == "__main__":
    main()
```

### Batch Processing

```python
import asyncio
from govbizops.sam_scraper import SAMWebScraper

async def batch_scrape(urls):
    """Scrape multiple URLs efficiently"""
    
    # Use server mode for optimizations
    async with SAMWebScraper(server_mode=True) as scraper:
        tasks = [scraper.scrape_opportunity(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results

# Usage
urls = [
    "https://sam.gov/opp/abc123/view",
    "https://sam.gov/opp/def456/view",
    # ... more URLs
]

results = asyncio.run(batch_scrape(urls))
```

### API Service

```python
from flask import Flask, jsonify, request
from govbizops import SolicitationAnalyzer

app = Flask(__name__)
analyzer = SolicitationAnalyzer(os.environ['SAM_GOV_API_KEY'])

@app.route('/analyze', methods=['POST'])
def analyze_opportunity():
    data = request.json
    
    try:
        result = analyzer.analyze_by_url(data['sam_url'])
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Performance Tuning

### Browser Pool

For high-throughput applications, consider implementing a browser pool:

```python
class BrowserPool:
    def __init__(self, size=3):
        self.pool = asyncio.Queue(maxsize=size)
        self.size = size
    
    async def start(self):
        for _ in range(self.size):
            scraper = SAMWebScraper(server_mode=True)
            await scraper.start()
            await self.pool.put(scraper)
    
    async def get_scraper(self):
        return await self.pool.get()
    
    async def return_scraper(self, scraper):
        await self.pool.put(scraper)
```

### Caching

Implement Redis caching to avoid re-scraping:

```python
import redis
import json

r = redis.Redis(host='redis', port=6379, db=0)

def cached_scrape(url):
    # Check cache first
    cached = r.get(f"scrape:{url}")
    if cached:
        return json.loads(cached)
    
    # Scrape and cache
    result = scrape_sam_opportunity(url, server_mode=True)
    r.setex(f"scrape:{url}", 3600, json.dumps(result))  # 1 hour cache
    
    return result
```

## Monitoring

### Health Check Endpoint

```python
@app.route('/health')
def health_check():
    try:
        # Test browser functionality
        test_result = scrape_sam_opportunity("https://sam.gov", server_mode=True)
        return jsonify({'status': 'healthy', 'browser': 'ok'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500
```

### Metrics

Monitor these key metrics:
- Memory usage (browser instances)
- CPU usage during scraping
- Scraping success rate
- Response times
- Queue depth (if using task queues)

## Troubleshooting

### Common Issues

1. **Browser launch fails**
   ```bash
   # Check dependencies
   ldd $(python3 -c "from playwright._impl._driver import compute_driver_executable; print(compute_driver_executable())")
   ```

2. **Memory issues**
   ```bash
   # Monitor memory usage
   docker stats govbizops
   ```

3. **Timeout errors**
   - Increase timeout values in scraper
   - Check network connectivity
   - Consider retry mechanisms

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger('playwright').setLevel(logging.DEBUG)
logging.getLogger('sam_scraper').setLevel(logging.DEBUG)
```

## Security Considerations

1. **API Keys**: Use environment variables or secret management
2. **Network**: Restrict outbound connections to SAM.gov only
3. **Container**: Run as non-root user (already configured in Dockerfile)
4. **Updates**: Regularly update Playwright browsers for security patches

## Scaling

For high-volume processing:

1. **Horizontal scaling**: Deploy multiple container instances
2. **Load balancing**: Use nginx or cloud load balancers
3. **Queue systems**: Use Redis/RabbitMQ for task queues
4. **Database**: Use PostgreSQL for persistent storage
5. **Monitoring**: Use Prometheus/Grafana for observability