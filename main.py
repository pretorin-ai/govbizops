#!/usr/bin/env python3
"""
Main entry point for govbizops container with multiple modes
"""

import argparse
import os
import sys
import time
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the parent directory to Python path for local runs
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
# Determine if running in Docker or locally
if os.path.exists('/app'):
    log_dir = '/app/logs'
else:
    log_dir = os.path.join(os.getcwd(), 'logs')

# Create log directory if it doesn't exist
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'govbizops.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import govbizops components - do this after path fix
if __name__ == '__main__':
    # Import here for script usage
    from client import SAMGovClient
    from collector import OpportunityCollector
    from solicitation_analyzer import SolicitationAnalyzer
else:
    # Import normally for module usage
    from govbizops import OpportunityCollector, SolicitationAnalyzer


def get_data_dir():
    """Get appropriate data directory based on environment"""
    return '/app/data' if os.path.exists('/app') else os.path.join(os.getcwd(), 'data')


def run_collector(args):
    """Run the opportunity collector"""
    logger.info("Starting opportunity collector")
    
    # Parse NAICS codes
    naics_codes = args.naics_codes.split(',') if args.naics_codes else ["541511", "541512","541690"]
    
    # Compliance warnings
    from client import SAMGovClient
    if len(naics_codes) > SAMGovClient.MAX_NAICS_CODES:
        logger.warning(f"⚠️  COMPLIANCE WARNING: You requested {len(naics_codes)} NAICS codes, but maximum {SAMGovClient.MAX_NAICS_CODES} are allowed per collection.")
        logger.warning("   This helps prevent bulk data mining and ensures SAM.gov terms compliance.")
        naics_codes = naics_codes[:SAMGovClient.MAX_NAICS_CODES]
        logger.info(f"   Using first {len(naics_codes)} codes: {', '.join(naics_codes)}")
    
    if args.days_back and args.days_back > SAMGovClient.MAX_DAYS_RANGE:
        logger.warning(f"⚠️  COMPLIANCE WARNING: You requested {args.days_back} days, but maximum {SAMGovClient.MAX_DAYS_RANGE} days are allowed per collection.")
        logger.warning("   This helps prevent bulk data mining and ensures SAM.gov terms compliance.")
        args.days_back = SAMGovClient.MAX_DAYS_RANGE
        logger.info(f"   Using maximum allowed range: {args.days_back} days")
    
    # Initialize collector
    storage_path = args.storage_path or os.path.join(get_data_dir(), 'opportunities.json')
    collector = OpportunityCollector(
        api_key=os.environ['SAM_GOV_API_KEY'],
        naics_codes=naics_codes,
        storage_path=storage_path
    )
    
    if args.days_back:
        logger.info(f"Collecting opportunities from the past {args.days_back} days")
        new_opportunities = collector.collect_daily_opportunities(days_back=args.days_back)
    else:
        logger.info("Collecting daily opportunities")
        new_opportunities = collector.collect_daily_opportunities()
    
    logger.info(f"Collected {len(new_opportunities)} new opportunities")
    
    # Get summary
    summary = collector.get_summary()
    logger.info(f"Total opportunities in database: {summary['total_opportunities']}")
    
    # If analysis requested, analyze new opportunities
    if args.analyze and new_opportunities:
        logger.info("Analyzing new opportunities with AI")
        analyzer = SolicitationAnalyzer(os.environ['SAM_GOV_API_KEY'])
        
        for opp in new_opportunities[:args.max_analyze]:
            try:
                logger.info(f"Analyzing: {opp.get('title', 'Unknown')}")
                result = analyzer.analyze_solicitation(opp)
                
                # Save analysis result
                analysis_file = os.path.join(get_data_dir(), f"analysis_{opp['noticeId']}.json")
                with open(analysis_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                logger.info(f"Analysis saved to {analysis_file}")
                
            except Exception as e:
                logger.error(f"Failed to analyze {opp.get('noticeId')}: {e}")
    
    return len(new_opportunities)


def run_viewer(args):
    """Run the simple web viewer"""
    logger.info(f"Starting web viewer on port {args.port}")
    
    # Import Flask app from simple_viewer
    try:
        import simple_viewer
        simple_viewer.app.run(host='0.0.0.0', port=args.port, debug=args.debug)
    except ImportError:
        logger.error("simple_viewer.py not found. Make sure it exists in the package.")
        sys.exit(1)


def run_analyzer(args):
    """Run the solicitation analyzer on specific opportunities"""
    logger.info("Starting solicitation analyzer")
    
    analyzer = SolicitationAnalyzer(os.environ['SAM_GOV_API_KEY'])
    
    if args.url:
        # Analyze by URL
        logger.info(f"Analyzing URL: {args.url}")
        result = analyzer.analyze_by_url(args.url)
        
        # Save result
        output_file = args.output or os.path.join(get_data_dir(), f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f"Analysis saved to {output_file}")
        
    elif args.opportunity_file:
        # Analyze from opportunity file
        logger.info(f"Analyzing opportunities from: {args.opportunity_file}")
        
        with open(args.opportunity_file, 'r') as f:
            opportunities = json.load(f)
        
        # Handle different file formats
        if isinstance(opportunities, dict):
            # If it's the collector format with IDs as keys
            opportunities = [data['data'] for data in opportunities.values()]
        
        for i, opp in enumerate(opportunities[:args.max_analyze]):
            try:
                logger.info(f"Analyzing {i+1}/{len(opportunities)}: {opp.get('title', 'Unknown')}")
                result = analyzer.analyze_solicitation(opp)
                
                # Save individual analysis
                output_file = os.path.join(get_data_dir(), f"analysis_{opp.get('noticeId', i)}.json")
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2)
                
                logger.info(f"Analysis saved to {output_file}")
                
            except Exception as e:
                logger.error(f"Failed to analyze opportunity {i}: {e}")


def run_scheduled_collector(args):
    """Run collector on a schedule"""
    # Enforce minimum 24-hour interval for compliance
    from client import SAMGovClient
    min_interval = 1440  # 24 hours in minutes
    
    if args.interval < min_interval:
        logger.warning(f"⚠️  COMPLIANCE WARNING: Minimum interval is {min_interval} minutes (24 hours) to prevent bulk data mining.")
        logger.warning("   This ensures SAM.gov terms compliance and prevents excessive API usage.")
        args.interval = min_interval
        logger.info(f"   Using minimum allowed interval: {args.interval} minutes (24 hours)")
    
    logger.info(f"Starting scheduled collector (interval: {args.interval} minutes)")
    logger.info(f"Compliance: Max {SAMGovClient.MAX_NAICS_CODES} NAICS codes, {SAMGovClient.MAX_DAYS_RANGE} days range, {SAMGovClient.MAX_DAILY_COLLECTIONS} collection per day")
    
    while True:
        try:
            logger.info("Running scheduled collection")
            collected = run_collector(args)
            
            next_run = datetime.now() + timedelta(minutes=args.interval)
            logger.info(f"Collected {collected} opportunities. Next run at {next_run}")
            
            # Sleep until next interval
            time.sleep(args.interval * 60)
            
        except KeyboardInterrupt:
            logger.info("Scheduled collector stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in scheduled collector: {e}")
            logger.info(f"Retrying in {args.interval} minutes")
            time.sleep(args.interval * 60)


def main():
    parser = argparse.ArgumentParser(description='GovBizOps - Government Contract Opportunity Management')
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')
    
    # Collector mode
    collector_parser = subparsers.add_parser('collect', help='Collect opportunities')
    collector_parser.add_argument('--naics-codes', type=str, 
                                help=f'Comma-separated NAICS codes (max 3, default: 541511,541512)')
    collector_parser.add_argument('--days-back', type=int, default=1,
                                help=f'Number of days to look back (max 7, default: 1)')
    collector_parser.add_argument('--storage-path', type=str, default=None,
                                help='Path to store opportunities')
    collector_parser.add_argument('--analyze', action='store_true',
                                help='Analyze new opportunities with AI')
    collector_parser.add_argument('--max-analyze', type=int, default=10,
                                help='Maximum opportunities to analyze (default: 10)')
    
    # Scheduled collector mode
    scheduled_parser = subparsers.add_parser('schedule', help='Run collector on schedule')
    scheduled_parser.add_argument('--interval', type=int, default=1440,
                                help='Collection interval in minutes (min 1440=24h, default: 1440)')
    scheduled_parser.add_argument('--naics-codes', type=str,
                                help=f'Comma-separated NAICS codes (max 3, default: 541511,541512)')
    scheduled_parser.add_argument('--storage-path', type=str, default=None,
                                help='Path to store opportunities')
    scheduled_parser.add_argument('--analyze', action='store_true',
                                help='Analyze new opportunities with AI')
    scheduled_parser.add_argument('--max-analyze', type=int, default=5,
                                help='Maximum opportunities to analyze per run (default: 5)')
    
    # Viewer mode
    viewer_parser = subparsers.add_parser('viewer', help='Run web viewer')
    viewer_parser.add_argument('--port', type=int, default=5000,
                             help='Port to run viewer on (default: 5000)')
    viewer_parser.add_argument('--debug', action='store_true',
                             help='Run in debug mode')
    
    # Analyzer mode
    analyzer_parser = subparsers.add_parser('analyze', help='Analyze specific opportunities')
    analyzer_parser.add_argument('--url', type=str,
                                help='SAM.gov opportunity URL to analyze')
    analyzer_parser.add_argument('--opportunity-file', type=str,
                                help='JSON file containing opportunities to analyze')
    analyzer_parser.add_argument('--output', type=str,
                                help='Output file for analysis results')
    analyzer_parser.add_argument('--max-analyze', type=int, default=50,
                                help='Maximum opportunities to analyze (default: 50)')
    
    # Diagnostic mode
    diag_parser = subparsers.add_parser('diagnose', help='Run diagnostic tests')
    
    args = parser.parse_args()
    
    # Ensure required environment variables
    if not os.environ.get('SAM_GOV_API_KEY'):
        logger.error("SAM_GOV_API_KEY environment variable is required")
        sys.exit(1)
    
    # Create data and logs directories
    # Use local directories when not in Docker
    if os.path.exists('/app'):
        data_dir = '/app/data'
        logs_dir = '/app/logs'
    else:
        data_dir = os.path.join(os.getcwd(), 'data')
        logs_dir = os.path.join(os.getcwd(), 'logs')
    
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)
    
    # Route to appropriate function
    if args.mode == 'collect':
        run_collector(args)
    elif args.mode == 'schedule':
        run_scheduled_collector(args)
    elif args.mode == 'viewer':
        run_viewer(args)
    elif args.mode == 'analyze':
        run_analyzer(args)
    elif args.mode == 'diagnose':
        # Import and run diagnostic
        import diagnose_browser
        import asyncio
        success = asyncio.run(diagnose_browser.test_browser())
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        
        # Show examples
        print("\nExamples:")
        print("  # Collect daily opportunities")
        print("  python main.py collect --naics-codes 541511,541512")
        print("  ")
        print("  # Run scheduled collection every 2 hours with analysis")
        print("  python main.py schedule --interval 120 --analyze")
        print("  ")
        print("  # Run web viewer")
        print("  python main.py viewer --port 5000")
        print("  ")
        print("  # Analyze specific opportunity")
        print("  python main.py analyze --url https://sam.gov/opp/abc123/view")
        print("  ")
        print("  # Analyze all opportunities in file")
        print("  python main.py analyze --opportunity-file opportunities.json")


if __name__ == '__main__':
    main()