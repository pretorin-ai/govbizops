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
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file in current working directory
load_dotenv(override=False)

# Add the parent directory to Python path for local runs
if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
log_dir = os.path.join(os.getcwd(), 'logs')
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

# Import govbizops components
try:
    # Try package imports first (for installed package)
    from govbizops.client import SAMGovClient
    from govbizops.collector import OpportunityCollector
except ImportError:
    # Fall back to direct imports (for script usage)
    from client import SAMGovClient
    from collector import OpportunityCollector


def get_data_dir():
    """Get data directory"""
    return os.path.join(os.getcwd(), 'data')


def send_slack_notification(opportunities: List[Dict[str, Any]]) -> bool:
    """
    Send Slack notification for new opportunities

    Args:
        opportunities: List of new opportunity dictionaries

    Returns:
        True if notification sent successfully, False otherwise
    """
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')

    logger.info(f"send_slack_notification called with {len(opportunities) if opportunities else 0} opportunities")
    logger.info(f"SLACK_WEBHOOK_URL configured: {bool(webhook_url)}")

    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not configured, skipping notification")
        logger.warning("Set SLACK_WEBHOOK_URL in your .env file to enable notifications")
        return False

    if not opportunities:
        logger.info("No opportunities to notify about")
        return True

    try:
        # Create message blocks for Slack
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔔 {len(opportunities)} New Contract Opportunit{'y' if len(opportunities) == 1 else 'ies'} Found",
                    "emoji": True
                }
            },
            {
                "type": "divider"
            }
        ]

        # Add up to 5 opportunities to avoid message size limits
        for opp in opportunities[:5]:
            title = opp.get('title', 'Untitled')
            notice_id = opp.get('noticeId', 'N/A')
            posted_date = opp.get('postedDate', 'N/A')
            deadline = opp.get('responseDeadLine', 'N/A')
            naics = opp.get('naicsCode', 'N/A')
            ui_link = opp.get('uiLink', '')

            # Format deadline
            if deadline and deadline != 'N/A':
                try:
                    deadline = deadline[:10]  # Just the date part
                except:
                    pass

            # Create opportunity block
            opp_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n"
                            f"📋 Notice ID: `{notice_id}`\n"
                            f"📅 Posted: {posted_date[:10] if posted_date != 'N/A' else 'N/A'}\n"
                            f"⏰ Deadline: {deadline}\n"
                            f"🏢 NAICS: {naics}"
                }
            }

            if ui_link:
                opp_block["accessory"] = {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View on SAM.gov",
                        "emoji": True
                    },
                    "url": ui_link,
                    "action_id": f"view_{notice_id}"
                }

            blocks.append(opp_block)
            blocks.append({"type": "divider"})

        # Add footer if there are more opportunities
        if len(opportunities) > 5:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_...and {len(opportunities) - 5} more opportunities_"
                    }
                ]
            })

        # Send to Slack
        payload = {
            "blocks": blocks,
            "text": f"{len(opportunities)} new contract opportunities found"  # Fallback text
        }

        logger.info(f"Sending POST request to Slack webhook...")
        logger.debug(f"Payload has {len(blocks)} blocks")

        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )

        logger.info(f"Slack API response status: {response.status_code}")

        if response.status_code == 200:
            logger.info(f"✓ Slack notification sent successfully for {len(opportunities)} opportunities")
            return True
        else:
            logger.error(f"✗ Slack notification failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"✗ Failed to send Slack notification: {e}")
        logger.exception("Full traceback:")
        return False


def run_collector(args):
    """Run the opportunity collector"""
    logger.info("Starting opportunity collector")
    
    # Parse NAICS codes - from args, env var, or defaults
    if args.naics_codes:
        naics_codes = args.naics_codes.split(',')
    elif os.getenv('NAICS_CODES'):
        naics_codes = os.getenv('NAICS_CODES').split(',')
    else:
        naics_codes = ["541511", "541512"]  # Default IT services codes
    
    # Validate limits
    if len(naics_codes) > SAMGovClient.MAX_NAICS_CODES:
        logger.warning(f"⚠️  WARNING: You requested {len(naics_codes)} NAICS codes, but maximum {SAMGovClient.MAX_NAICS_CODES} are allowed per collection.")
        naics_codes = naics_codes[:SAMGovClient.MAX_NAICS_CODES]
        logger.info(f"   Using first {len(naics_codes)} codes: {', '.join(naics_codes)}")

    if args.days_back and args.days_back > SAMGovClient.MAX_DAYS_RANGE:
        logger.warning(f"⚠️  WARNING: You requested {args.days_back} days, but maximum {SAMGovClient.MAX_DAYS_RANGE} days are allowed per collection.")
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

    # Send Slack notification if enabled and there are new opportunities
    notify_enabled = hasattr(args, 'notify') and args.notify
    logger.info(f"Slack notifications enabled: {notify_enabled}")

    if notify_enabled and new_opportunities:
        logger.info("Sending Slack notification for new opportunities")
        send_slack_notification(new_opportunities)
    elif notify_enabled and not new_opportunities:
        logger.info("Slack notifications enabled but no new opportunities to report")
    elif not notify_enabled:
        logger.info("Slack notifications not enabled (use --notify flag to enable)")

    return len(new_opportunities)


def run_viewer(args):
    """Run the simple web viewer"""
    logger.info(f"Starting web viewer on port {args.port}")

    # Import Flask app from simple_viewer
    try:
        from govbizops import simple_viewer
    except ImportError:
        import simple_viewer

    simple_viewer.app.run(host='0.0.0.0', port=args.port, debug=args.debug)


def run_scheduled_collector(args):
    """Run collector on a schedule"""
    logger.info(f"Starting scheduled collector (interval: {args.interval} minutes)")
    logger.info(f"Limits: Max {SAMGovClient.MAX_NAICS_CODES} NAICS codes, {SAMGovClient.MAX_DAYS_RANGE} days range, {SAMGovClient.MAX_DAILY_COLLECTIONS} collections per day")
    if hasattr(args, 'notify') and args.notify:
        logger.info("Slack notifications enabled for new opportunities")
    
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
                                help=f'Comma-separated NAICS codes (max 50, default from NAICS_CODES env var or 541511,541512)')
    collector_parser.add_argument('--days-back', type=int, default=1,
                                help=f'Number of days to look back (max 90, default: 1)')
    collector_parser.add_argument('--storage-path', type=str, default=None,
                                help='Path to store opportunities')
    collector_parser.add_argument('--notify', action='store_true',
                                help='Send Slack notifications for new opportunities (requires SLACK_WEBHOOK_URL)')
    
    # Scheduled collector mode
    scheduled_parser = subparsers.add_parser('schedule', help='Run collector on schedule')
    scheduled_parser.add_argument('--interval', type=int, default=60,
                                help='Collection interval in minutes (default: 60)')
    scheduled_parser.add_argument('--naics-codes', type=str,
                                help=f'Comma-separated NAICS codes (max 50, default from NAICS_CODES env var or 541511,541512)')
    scheduled_parser.add_argument('--storage-path', type=str, default=None,
                                help='Path to store opportunities')
    scheduled_parser.add_argument('--notify', action='store_true',
                                help='Send Slack notifications for new opportunities (requires SLACK_WEBHOOK_URL)')
    
    # Viewer mode
    viewer_parser = subparsers.add_parser('viewer', help='Run web viewer')
    viewer_parser.add_argument('--port', type=int, default=5000,
                             help='Port to run viewer on (default: 5000)')
    viewer_parser.add_argument('--debug', action='store_true',
                             help='Run in debug mode')

    # Diagnostic mode
    diag_parser = subparsers.add_parser('diagnose', help='Run diagnostic tests')
    
    args = parser.parse_args()

    # Debug environment loading
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"SAM_GOV_API_KEY loaded: {bool(os.environ.get('SAM_GOV_API_KEY'))}")
    logger.info(f"SLACK_WEBHOOK_URL loaded: {bool(os.environ.get('SLACK_WEBHOOK_URL'))}")
    if os.environ.get('SLACK_WEBHOOK_URL'):
        logger.info(f"SLACK_WEBHOOK_URL value: {os.environ.get('SLACK_WEBHOOK_URL')[:50]}...")

    # Ensure required environment variables
    if not os.environ.get('SAM_GOV_API_KEY'):
        logger.error("SAM_GOV_API_KEY environment variable is required")
        sys.exit(1)
    
    # Create data and logs directories
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
    elif args.mode == 'diagnose':
        # Import and run diagnostic
        try:
            from govbizops import diagnose_browser
        except ImportError:
            import diagnose_browser
        import asyncio
        success = asyncio.run(diagnose_browser.test_browser())
        sys.exit(0 if success else 1)
    else:
        parser.print_help()
        
        # Show examples
        print("\nExamples:")
        print("  # Collect daily opportunities")
        print("  govbizops collect --naics-codes 541511,541512")
        print("  ")
        print("  # Run scheduled collection every 2 hours")
        print("  govbizops schedule --interval 120")
        print("  ")
        print("  # Run web viewer")
        print("  govbizops viewer --port 5000")


if __name__ == '__main__':
    main()