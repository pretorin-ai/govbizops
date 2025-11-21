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
import random
import uuid
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

    # Push new opportunities to CRM if configured
    crm_url = os.getenv('CRM_URL')
    crm_api_key = os.getenv('CRM_API_KEY')
    
    if crm_url and crm_api_key and new_opportunities:
        logger.info(f"Pushing {len(new_opportunities)} new opportunities to CRM at {crm_url}")
        try:
            # Import CRM client
            try:
                from govbizops.crm_client import CRMClient
            except ImportError:
                from crm_client import CRMClient
            
            client = CRMClient(crm_url, crm_api_key)
            result = client.import_opportunities(new_opportunities, auto_create_contacts=True)
            
            logger.info("="*50)
            logger.info("CRM IMPORT RESULTS")
            logger.info("="*50)
            logger.info(f"Contracts created: {result['contracts_created']}")
            logger.info(f"Contracts skipped: {result['contracts_skipped']}")
            logger.info(f"Contacts created:  {result['contacts_created']}")
            
            if result.get('errors'):
                logger.warning(f"Errors ({len(result['errors'])}):")
                for error in result['errors'][:5]:
                    logger.warning(f"  - {error}")
                if len(result['errors']) > 5:
                    logger.warning(f"  ... and {len(result['errors']) - 5} more")
            
            logger.info("="*50)
        except Exception as e:
            logger.error(f"Failed to push opportunities to CRM: {e}")
            logger.exception("Full traceback:")
            # Don't fail the collection if CRM push fails
    elif new_opportunities and (not crm_url or not crm_api_key):
        logger.info("CRM_URL and/or CRM_API_KEY not configured, skipping CRM push")
        logger.info("Set CRM_URL and CRM_API_KEY environment variables to enable automatic CRM integration")

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


def run_crm_push(args):
    """Push collected opportunities to CRM"""
    # Import CRM client
    try:
        from govbizops.crm_client import push_to_crm
    except ImportError:
        from crm_client import push_to_crm

    # Get API key from args or environment
    crm_url = args.crm_url or os.getenv('CRM_URL', 'http://localhost:8000')
    crm_api_key = args.crm_api_key or os.getenv('CRM_API_KEY')

    if not crm_api_key:
        logger.error("CRM API key required. Set CRM_API_KEY environment variable")
        logger.error("or use --crm-api-key argument")
        logger.error("")
        logger.error("To get your API key:")
        logger.error("1. Log in to your CRM")
        logger.error("2. Go to Settings")
        logger.error("3. Click 'Generate API Key'")
        logger.error("4. Copy the key and set it: export CRM_API_KEY=crm_...")
        sys.exit(1)

    # Get opportunities file path
    storage_path = args.storage_path or os.path.join(get_data_dir(), 'opportunities.json')

    if not os.path.exists(storage_path):
        logger.error(f"No opportunities file found at {storage_path}")
        logger.error("Run 'govbizops collect' first to collect opportunities")
        sys.exit(1)

    logger.info(f"Pushing opportunities from {storage_path} to CRM at {crm_url}")

    try:
        result = push_to_crm(
            crm_url=crm_url,
            crm_api_key=crm_api_key,
            opportunities_file=storage_path,
            auto_create_contacts=not args.no_contacts
        )

        logger.info("="*50)
        logger.info("CRM IMPORT RESULTS")
        logger.info("="*50)
        logger.info(f"Contracts created: {result['contracts_created']}")
        logger.info(f"Contracts skipped: {result['contracts_skipped']}")
        logger.info(f"Contacts created:  {result['contracts_created']}")

        if result.get('errors'):
            logger.warning(f"Errors ({len(result['errors'])}):")
            for error in result['errors'][:5]:
                logger.warning(f"  - {error}")
            if len(result['errors']) > 5:
                logger.warning(f"  ... and {len(result['errors']) - 5} more")

        logger.info("="*50)

    except Exception as e:
        logger.error(f"Failed to push opportunities to CRM: {e}")
        sys.exit(1)


def generate_mock_opportunities(count: int = 3, naics_codes: List[str] = None) -> List[Dict[str, Any]]:
    """
    Generate mock SAM.gov opportunities for testing
    
    Args:
        count: Number of mock opportunities to generate
        naics_codes: List of NAICS codes to use (defaults to test codes)
        
    Returns:
        List of mock opportunity dictionaries
    """
    import random
    import uuid
    
    if naics_codes is None:
        naics_codes = ["541511", "541512"]
    
    mock_titles = [
        "IT Services and Support for Federal Agency",
        "Cloud Infrastructure Modernization Project",
        "Cybersecurity Assessment and Implementation",
        "Software Development and Maintenance Services",
        "Data Analytics and Business Intelligence Platform",
        "Network Infrastructure Upgrade and Support",
        "Enterprise Application Development",
        "IT Help Desk and Technical Support Services",
        "Database Administration and Management",
        "Web Application Development and Hosting"
    ]
    
    mock_descriptions = [
        "The contractor shall provide comprehensive IT services including system administration, help desk support, and technical assistance for federal agency operations.",
        "This solicitation seeks a qualified contractor to modernize cloud infrastructure, migrate legacy systems, and provide ongoing cloud management services.",
        "Services include cybersecurity risk assessment, implementation of security controls, penetration testing, and ongoing security monitoring.",
        "Development and maintenance of custom software applications, including requirements analysis, design, coding, testing, and deployment.",
        "Implementation of a data analytics platform to support business intelligence, reporting, and data visualization needs.",
        "Upgrade and support of network infrastructure including routers, switches, firewalls, and wireless access points.",
        "Development of enterprise-level applications using modern frameworks and technologies, with focus on scalability and security.",
        "24/7 help desk support services including ticket management, remote troubleshooting, and user training.",
        "Database administration services including performance tuning, backup and recovery, security management, and capacity planning.",
        "Development and hosting of web applications with responsive design, accessibility compliance, and integration capabilities."
    ]
    
    mock_contacts = [
        {"fullName": "John Smith", "email": "john.smith@agency.gov", "phone": "202-555-0101", "type": "Primary"},
        {"fullName": "Jane Doe", "email": "jane.doe@agency.gov", "phone": "202-555-0102", "type": "Secondary"},
        {"fullName": "Robert Johnson", "email": "robert.johnson@agency.gov", "phone": "202-555-0103", "type": "Primary"},
        {"fullName": "Sarah Williams", "email": "sarah.williams@agency.gov", "phone": "202-555-0104", "type": "Contracting Officer"},
    ]
    
    opportunities = []
    now = datetime.now()
    
    for i in range(count):
        # Generate unique notice ID
        notice_id = f"TEST-{uuid.uuid4().hex[:8].upper()}"
        
        # Random dates within the past week
        days_ago = random.randint(0, 7)
        posted_date = (now - timedelta(days=days_ago)).isoformat() + "Z"
        deadline_days = random.randint(14, 60)
        deadline = (now + timedelta(days=deadline_days)).isoformat() + "Z"
        
        # Random selection
        title = random.choice(mock_titles)
        description = random.choice(mock_descriptions)
        naics = random.choice(naics_codes)
        contact = random.choice(mock_contacts)
        solicitation_num = f"SOL-{now.year}-{random.randint(1000, 9999)}"
        
        opp = {
            "noticeId": notice_id,
            "title": title,
            "solicitationNumber": solicitation_num,
            "description": description,
            "responseDeadLine": deadline,
            "postedDate": posted_date,
            "naicsCode": naics,
            "uiLink": f"https://sam.gov/opp/{notice_id}/view",
            "pointOfContact": [contact],
            "type": "Solicitation"  # Important: must have "Solicitation" in type
        }
        
        opportunities.append(opp)
    
    return opportunities


def run_test_collector(args):
    """Run collector with mock/test data"""
    logger.info("="*60)
    logger.info("TEST MODE: Generating mock opportunities")
    logger.info("="*60)
    
    # Parse NAICS codes
    if args.naics_codes:
        naics_codes = args.naics_codes.split(',')
    elif os.getenv('NAICS_CODES'):
        naics_codes = os.getenv('NAICS_CODES').split(',')
    else:
        naics_codes = ["541511", "541512"]
    
    # Generate mock opportunities
    count = args.count if hasattr(args, 'count') else 3
    logger.info(f"Generating {count} mock opportunities with NAICS codes: {', '.join(naics_codes)}")
    
    mock_opportunities = generate_mock_opportunities(count=count, naics_codes=naics_codes)
    
    # Initialize collector (API key not needed for test mode, but required by constructor)
    # Use a dummy key for test mode
    api_key = os.environ.get('SAM_GOV_API_KEY', 'TEST_MODE_DUMMY_KEY')
    storage_path = args.storage_path or os.path.join(get_data_dir(), 'opportunities.json')
    
    collector = OpportunityCollector(
        api_key=api_key,
        naics_codes=naics_codes,
        storage_path=storage_path
    )
    
    # Manually add mock opportunities as if they were collected
    new_opportunities = []
    for opp in mock_opportunities:
        notice_id = opp.get("noticeId")
        if notice_id and notice_id not in collector.opportunities:
            collector.opportunities[notice_id] = {
                "collected_date": datetime.now().isoformat(),
                "data": opp
            }
            new_opportunities.append(opp)
    
    if new_opportunities:
        collector._save_opportunities()
        logger.info(f"✓ Stored {len(new_opportunities)} mock opportunities")
    else:
        logger.info("No new opportunities (all duplicates)")
        return 0
    
    # Get summary
    summary = collector.get_summary()
    logger.info(f"Total opportunities in database: {summary['total_opportunities']}")
    
    # Push to CRM if configured
    crm_url = os.getenv('CRM_URL')
    crm_api_key = os.getenv('CRM_API_KEY')
    
    if crm_url and crm_api_key and new_opportunities:
        logger.info(f"Pushing {len(new_opportunities)} mock opportunities to CRM at {crm_url}")
        try:
            try:
                from govbizops.crm_client import CRMClient
            except ImportError:
                from crm_client import CRMClient
            
            client = CRMClient(crm_url, crm_api_key)
            result = client.import_opportunities(new_opportunities, auto_create_contacts=True)
            
            logger.info("="*50)
            logger.info("CRM IMPORT RESULTS")
            logger.info("="*50)
            logger.info(f"Contracts created: {result['contracts_created']}")
            logger.info(f"Contracts skipped: {result['contracts_skipped']}")
            logger.info(f"Contacts created:  {result['contacts_created']}")
            
            if result.get('errors'):
                logger.warning(f"Errors ({len(result['errors'])}):")
                for error in result['errors'][:5]:
                    logger.warning(f"  - {error}")
                if len(result['errors']) > 5:
                    logger.warning(f"  ... and {len(result['errors']) - 5} more")
            
            logger.info("="*50)
        except Exception as e:
            logger.error(f"Failed to push opportunities to CRM: {e}")
            logger.exception("Full traceback:")
    elif new_opportunities and (not crm_url or not crm_api_key):
        logger.info("CRM_URL and/or CRM_API_KEY not configured, skipping CRM push")
        logger.info("Set CRM_URL and CRM_API_KEY environment variables to test CRM integration")
    
    # Send Slack notification if enabled
    notify_enabled = hasattr(args, 'notify') and args.notify
    if notify_enabled and new_opportunities:
        logger.info("Sending Slack notification for mock opportunities")
        send_slack_notification(new_opportunities)
    
    logger.info("="*60)
    logger.info("TEST MODE: Complete")
    logger.info("="*60)
    
    return len(new_opportunities)


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

    # CRM push mode
    crm_parser = subparsers.add_parser('push-crm', help='Push collected opportunities to Pretorin CRM')
    crm_parser.add_argument('--crm-url', type=str, default=None,
                          help='CRM base URL (default: from CRM_URL env var or http://localhost:8000)')
    crm_parser.add_argument('--crm-api-key', type=str, default=None,
                          help='CRM API key (default: from CRM_API_KEY env var)')
    crm_parser.add_argument('--storage-path', type=str, default=None,
                          help='Path to opportunities JSON file')
    crm_parser.add_argument('--no-contacts', action='store_true',
                          help='Do not auto-create contacts from point-of-contact info')

    # Diagnostic mode
    diag_parser = subparsers.add_parser('diagnose', help='Run diagnostic tests')
    
    # Test mode - generate mock opportunities
    test_parser = subparsers.add_parser('test', help='Generate mock opportunities for testing (no SAM.gov API calls)')
    test_parser.add_argument('--count', type=int, default=3,
                           help='Number of mock opportunities to generate (default: 3)')
    test_parser.add_argument('--naics-codes', type=str,
                           help='Comma-separated NAICS codes (default from NAICS_CODES env var or 541511,541512)')
    test_parser.add_argument('--storage-path', type=str, default=None,
                           help='Path to store opportunities')
    test_parser.add_argument('--notify', action='store_true',
                           help='Send Slack notifications for mock opportunities (requires SLACK_WEBHOOK_URL)')
    
    args = parser.parse_args()

    # Debug environment loading
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"SAM_GOV_API_KEY loaded: {bool(os.environ.get('SAM_GOV_API_KEY'))}")
    logger.info(f"SLACK_WEBHOOK_URL loaded: {bool(os.environ.get('SLACK_WEBHOOK_URL'))}")
    if os.environ.get('SLACK_WEBHOOK_URL'):
        logger.info(f"SLACK_WEBHOOK_URL value: {os.environ.get('SLACK_WEBHOOK_URL')[:50]}...")

    # Ensure required environment variables (except for test mode)
    if args.mode != 'test' and not os.environ.get('SAM_GOV_API_KEY'):
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
    elif args.mode == 'push-crm':
        run_crm_push(args)
    elif args.mode == 'test':
        run_test_collector(args)
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
        print("  # Generate mock opportunities for testing (no SAM.gov API calls)")
        print("  govbizops test --count 5")
        print("  ")
        print("  # Run web viewer")
        print("  govbizops viewer --port 5000")
        print("  ")
        print("  # Push collected opportunities to CRM")
        print("  govbizops push-crm")


if __name__ == '__main__':
    main()