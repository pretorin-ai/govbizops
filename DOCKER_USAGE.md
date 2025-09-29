# Docker Usage Guide for GovBizOps

This guide shows how to run all components of the GovBizOps library in Docker containers.

## Quick Start

1. **Setup environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Run the full stack**:
   ```bash
   docker-compose up -d
   ```

3. **View opportunities**:
   Open http://localhost:5000 in your browser

## Available Services

### Core Services (Always Running)

#### 1. Collector Service
Automatically collects opportunities every hour and analyzes them with AI.

```bash
# Default: Collect every 60 minutes with AI analysis
docker-compose up -d collector

# Custom interval (every 30 minutes)
docker-compose run --rm collector python main.py schedule --interval 30 --analyze
```

#### 2. Viewer Service  
Web interface to browse collected opportunities.

```bash
# Start web viewer on port 5000
docker-compose up -d viewer

# Custom port
docker-compose run --rm -p 8080:8080 viewer python main.py viewer --port 8080
```

### On-Demand Services

#### 3. Analyzer Service
Analyze specific opportunities in detail.

```bash
# Analyze all opportunities in the database
docker-compose run --rm analyzer

# Analyze specific URL
docker-compose run --rm analyzer python main.py analyze --url "https://sam.gov/opp/abc123/view"

# Analyze with custom settings
docker-compose run --rm analyzer python main.py analyze --opportunity-file /app/data/opportunities.json --max-analyze 20
```

## Individual Commands

### Collection Commands

```bash
# One-time collection (last 24 hours)
docker run --rm -e SAM_GOV_API_KEY=your_key --shm-size=1g govbizops python main.py collect

# Collect last 7 days with analysis
docker run --rm -e SAM_GOV_API_KEY=your_key -e OPENAI_API_KEY=your_key --shm-size=1g govbizops \
  python main.py collect --days-back 7 --analyze

# Collect specific NAICS codes
docker run --rm -e SAM_GOV_API_KEY=your_key --shm-size=1g govbizops \
  python main.py collect --naics-codes "541511,541512,541513"

# Scheduled collection every 2 hours
docker run --rm -e SAM_GOV_API_KEY=your_key --shm-size=1g govbizops \
  python main.py schedule --interval 120 --analyze
```

### Analysis Commands

```bash
# Analyze specific opportunity by URL
docker run --rm -e SAM_GOV_API_KEY=your_key -e OPENAI_API_KEY=your_key --shm-size=1g govbizops \
  python main.py analyze --url "https://sam.gov/opp/abc123/view"

# Analyze all opportunities in a file
docker run --rm -v $(pwd)/data:/app/data -e SAM_GOV_API_KEY=your_key --shm-size=1g govbizops \
  python main.py analyze --opportunity-file /app/data/opportunities.json

# Batch analysis with limit
docker run --rm -v $(pwd)/data:/app/data -e SAM_GOV_API_KEY=your_key --shm-size=1g govbizops \
  python main.py analyze --opportunity-file /app/data/opportunities.json --max-analyze 10
```

### Viewer Commands

```bash
# Start web viewer
docker run --rm -p 5000:5000 -v $(pwd)/data:/app/data govbizops \
  python main.py viewer

# Viewer on custom port
docker run --rm -p 8080:8080 -v $(pwd)/data:/app/data govbizops \
  python main.py viewer --port 8080
```

### Diagnostic Commands

```bash
# Test browser functionality
docker run --rm --shm-size=1g govbizops python main.py diagnose

# Test with troubleshooting flags
docker run --rm --shm-size=1g --cap-add=SYS_ADMIN govbizops python main.py diagnose
```

## Environment Variables

Set these in your `.env` file or pass directly to Docker:

```bash
# Required
SAM_GOV_API_KEY=your_sam_gov_api_key

# Optional
OPENAI_API_KEY=your_openai_api_key
DB_PASSWORD=your_db_password
NAICS_CODES=541511,541512,541513
COLLECTION_INTERVAL=60
MAX_ANALYZE=5
```

## Volume Mounts

The container uses these directories:

- `/app/data` - Stored opportunities and analysis results
- `/app/logs` - Application logs

Mount them to persist data:

```bash
docker run -v $(pwd)/data:/app/data -v $(pwd)/logs:/app/logs govbizops [command]
```

## Production Deployment Examples

### Basic Production Setup

```bash
# Create environment file
cat > .env << EOF
SAM_GOV_API_KEY=your_real_api_key
OPENAI_API_KEY=your_real_openai_key
DB_PASSWORD=secure_password_123
EOF

# Start core services
docker-compose up -d collector viewer

# Monitor logs
docker-compose logs -f
```

### High-Volume Setup with Database

```bash
# Start with database and caching
docker-compose --profile database --profile cache up -d

# Scale analyzer for batch processing
docker-compose up -d --scale analyzer=3
```

### Custom NAICS Codes Setup

```bash
# Run collector for specific industry codes
docker-compose run --rm collector python main.py schedule \
  --interval 30 \
  --naics-codes "334111,334112,334118,541330,541511,541512" \
  --analyze \
  --max-analyze 10
```

## Service Profiles

Use profiles to run optional services:

```bash
# Run with Redis caching
docker-compose --profile cache up -d

# Run with PostgreSQL database
docker-compose --profile database up -d

# Run with nginx load balancer
docker-compose --profile loadbalancer up -d

# Run all optional services
docker-compose --profile cache --profile database --profile loadbalancer up -d
```

## Monitoring and Maintenance

### Health Checks

```bash
# Check service health
docker-compose ps

# View health check logs
docker inspect govbizops_collector_1 | grep -A 10 "Health"
```

### Log Management

```bash
# View logs
docker-compose logs collector
docker-compose logs viewer
docker-compose logs analyzer

# Follow logs in real-time
docker-compose logs -f collector

# Rotate logs (Linux)
docker-compose logs --no-color collector > collector.log 2>&1
```

### Data Management

```bash
# Backup data
tar -czf govbizops-backup-$(date +%Y%m%d).tar.gz data/

# Clean old logs
find logs/ -name "*.log" -mtime +30 -delete

# Archive old analysis files
find data/ -name "analysis_*.json" -mtime +90 -exec mv {} archive/ \;
```

### Performance Monitoring

```bash
# Monitor resource usage
docker stats

# Monitor specific services
docker stats govbizops_collector_1 govbizops_viewer_1

# Check disk usage
du -sh data/ logs/
```

## Scaling

### Horizontal Scaling

```bash
# Run multiple collector instances (different NAICS codes)
docker-compose run -d collector python main.py schedule --naics-codes "541511" --interval 60
docker-compose run -d collector python main.py schedule --naics-codes "541512" --interval 60

# Run multiple analyzer instances
docker-compose up -d --scale analyzer=3

# Load balance viewers
docker-compose up -d --scale viewer=2 nginx
```

### Resource Limits

Adjust in docker-compose.yml:

```yaml
collector:
  mem_limit: 4g    # Increase for large-scale collection
  cpus: 2.0        # More CPU for analysis
  
analyzer:
  mem_limit: 3g    # More memory for web scraping
  cpus: 1.5
```

## Troubleshooting

### Common Issues

**Browser fails to start:**
```bash
# Add shared memory and capabilities
docker run --shm-size=1g --cap-add=SYS_ADMIN govbizops python main.py diagnose
```

**Out of memory:**
```bash
# Increase memory limits
docker-compose up -d --scale collector=1 --scale analyzer=1
```

**Network timeouts:**
```bash
# Increase timeout in browser settings (modify main.py if needed)
# Or reduce concurrent operations
```

**Permission issues:**
```bash
# Fix data directory permissions
sudo chown -R 1000:1000 data/ logs/
```

### Debug Mode

Enable debug logging:

```bash
# Run with debug output
docker-compose run --rm collector python main.py collect --debug

# Check browser diagnostic
docker run --rm --shm-size=1g govbizops python diagnose_browser.py
```

This setup provides a complete, scalable solution for running GovBizOps in production server environments!