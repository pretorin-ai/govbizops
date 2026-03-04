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
from typing import Dict, List, NoReturn, Optional
from dotenv import load_dotenv

# Load environment variables from .env file in current working directory
load_dotenv(override=False)

# Configure logging
log_dir: str = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "govbizops.log")),
        logging.StreamHandler(),
    ],
)
logger: logging.Logger = logging.getLogger(__name__)

from govbizops.client import SAMGovClient
from govbizops.collector import OpportunityCollector
from govbizops.database import get_engine, get_session, init_db


def _init_db_session():
    """Initialize the database and return a session."""
    engine = get_engine()
    init_db(engine)
    SessionFactory = get_session(engine)
    return SessionFactory()


def send_slack_notification(opportunities: List[Dict[str, str]]) -> bool:
    """
    Send Slack notification for new opportunities

    Args:
        opportunities: List of new opportunity dictionaries

    Returns:
        True if notification sent successfully, False otherwise
    """
    webhook_url: Optional[str] = os.environ.get("SLACK_WEBHOOK_URL")

    logger.info(
        f"send_slack_notification called with {len(opportunities) if opportunities else 0} opportunities"
    )
    logger.info(f"SLACK_WEBHOOK_URL configured: {bool(webhook_url)}")

    if not webhook_url:
        logger.warning("SLACK_WEBHOOK_URL not configured, skipping notification")
        logger.warning(
            "Set SLACK_WEBHOOK_URL in your .env file to enable notifications"
        )
        return False

    if not opportunities:
        logger.info("No opportunities to notify about")
        return True

    try:
        # Create message blocks for Slack
        blocks: List[Dict[str, object]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🔔 {len(opportunities)} New Contract Opportunit{'y' if len(opportunities) == 1 else 'ies'} Found",
                    "emoji": True,
                },
            },
            {"type": "divider"},
        ]

        # Add up to 5 opportunities to avoid message size limits
        for opp in opportunities[:5]:
            title: str = opp.get("title", "Untitled")
            notice_id: str = opp.get("noticeId", "N/A")
            posted_date: str = opp.get("postedDate", "N/A")
            deadline: str = opp.get("responseDeadLine", "N/A")
            naics: str = opp.get("naicsCode", "N/A")
            ui_link: str = opp.get("uiLink", "")

            # Format deadline to just the date part
            if deadline and deadline != "N/A":
                deadline = deadline[:10]

            # Create opportunity block
            opp_block: Dict[str, object] = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n"
                    f"📋 Notice ID: `{notice_id}`\n"
                    f"📅 Posted: {posted_date[:10] if posted_date != 'N/A' else 'N/A'}\n"
                    f"⏰ Deadline: {deadline}\n"
                    f"🏢 NAICS: {naics}",
                },
            }

            if ui_link:
                opp_block["accessory"] = {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View on SAM.gov",
                        "emoji": True,
                    },
                    "url": ui_link,
                    "action_id": f"view_{notice_id}",
                }

            blocks.append(opp_block)
            blocks.append({"type": "divider"})

        # Add footer if there are more opportunities
        if len(opportunities) > 5:
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"_...and {len(opportunities) - 5} more opportunities_",
                        }
                    ],
                }
            )

        # Send to Slack
        payload: Dict[str, object] = {
            "blocks": blocks,
            "text": f"{len(opportunities)} new contract opportunities found",  # Fallback text
        }

        logger.info(f"Sending POST request to Slack webhook...")
        logger.debug(f"Payload has {len(blocks)} blocks")

        response: requests.Response = requests.post(webhook_url, json=payload, timeout=10)

        logger.info(f"Slack API response status: {response.status_code}")

        if response.status_code == 200:
            logger.info(
                f"✓ Slack notification sent successfully for {len(opportunities)} opportunities"
            )
            return True
        else:
            logger.error(
                f"✗ Slack notification failed: {response.status_code} - {response.text}"
            )
            return False

    except Exception as e:
        logger.error(f"✗ Failed to send Slack notification: {e}")
        logger.exception("Full traceback:")
        return False


def run_collector(args: argparse.Namespace) -> int:
    """Run the opportunity collector"""
    logger.info("Starting opportunity collector")

    # Parse NAICS codes - from args, env var, or defaults
    naics_codes: List[str]
    if args.naics_codes:
        naics_codes = args.naics_codes.split(",")
    elif os.getenv("NAICS_CODES"):
        naics_env: str = os.getenv("NAICS_CODES", "")
        naics_codes = naics_env.split(",")
    else:
        naics_codes = ["541511", "541512"]  # Default IT services codes

    # Validate limits
    if len(naics_codes) > SAMGovClient.MAX_NAICS_CODES:
        logger.warning(
            f"⚠️  WARNING: You requested {len(naics_codes)} NAICS codes, but maximum {SAMGovClient.MAX_NAICS_CODES} are allowed per collection."
        )
        naics_codes = naics_codes[: SAMGovClient.MAX_NAICS_CODES]
        logger.info(
            f"   Using first {len(naics_codes)} codes: {', '.join(naics_codes)}"
        )

    if args.days_back and args.days_back > SAMGovClient.MAX_DAYS_RANGE:
        logger.warning(
            f"⚠️  WARNING: You requested {args.days_back} days, but maximum {SAMGovClient.MAX_DAYS_RANGE} days are allowed per collection."
        )
        args.days_back = SAMGovClient.MAX_DAYS_RANGE
        logger.info(f"   Using maximum allowed range: {args.days_back} days")

    # Initialize database session
    db_session = _init_db_session()

    try:
        collector: OpportunityCollector = OpportunityCollector(
            api_key=os.environ["SAM_GOV_API_KEY"],
            naics_codes=naics_codes,
            db_session=db_session,
        )

        new_opportunities: List[Dict[str, str]]
        if args.days_back:
            logger.info(f"Collecting opportunities from the past {args.days_back} days")
            new_opportunities = collector.collect_daily_opportunities(
                days_back=args.days_back
            )
        else:
            logger.info("Collecting daily opportunities")
            new_opportunities = collector.collect_daily_opportunities()

        logger.info(f"Collected {len(new_opportunities)} new opportunities")

        # Get summary
        summary: Dict[str, object] = collector.get_summary()
        logger.info(f"Total opportunities in database: {summary['total_opportunities']}")

        # Send Slack notification if enabled and there are new opportunities
        notify_enabled: bool = hasattr(args, "notify") and args.notify
        logger.info(f"Slack notifications enabled: {notify_enabled}")

        if notify_enabled and new_opportunities:
            logger.info("Sending Slack notification for new opportunities")
            send_slack_notification(new_opportunities)
        elif notify_enabled and not new_opportunities:
            logger.info("Slack notifications enabled but no new opportunities to report")
        elif not notify_enabled:
            logger.info("Slack notifications not enabled (use --notify flag to enable)")

        return len(new_opportunities)
    finally:
        db_session.close()


def run_viewer(args: argparse.Namespace) -> None:
    """Run the simple web viewer"""
    logger.info(f"Starting web viewer on port {args.port}")

    from govbizops import simple_viewer

    host: str = "127.0.0.1" if args.debug else "0.0.0.0"
    simple_viewer.app.run(host=host, port=args.port, debug=args.debug)


def run_crm_push(args: argparse.Namespace) -> None:
    """Push collected opportunities to CRM"""
    from govbizops.crm_client import push_to_crm

    # Get API key from args or environment
    crm_url: str = args.crm_url or os.getenv("CRM_URL", "http://localhost:8000")
    crm_api_key: Optional[str] = args.crm_api_key or os.getenv("CRM_API_KEY")

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

    # Initialize database session
    db_session = _init_db_session()

    logger.info(f"Pushing opportunities from database to CRM at {crm_url}")

    try:
        result: Dict[str, object] = push_to_crm(
            crm_url=crm_url,
            crm_api_key=crm_api_key,
            db_session=db_session,
            auto_create_contacts=not args.no_contacts,
        )

        logger.info("=" * 50)
        logger.info("CRM IMPORT RESULTS")
        logger.info("=" * 50)
        logger.info(f"Contracts created: {result['contracts_created']}")
        logger.info(f"Contracts skipped: {result['contracts_skipped']}")
        logger.info(f"Contacts created:  {result['contacts_created']}")

        if result.get("errors"):
            logger.warning(f"Errors ({len(result['errors'])}):")
            for error in result["errors"][:5]:
                logger.warning(f"  - {error}")
            if len(result["errors"]) > 5:
                logger.warning(f"  ... and {len(result['errors']) - 5} more")

        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"Failed to push opportunities to CRM: {e}")
        sys.exit(1)
    finally:
        db_session.close()


def run_scheduled_collector(args: argparse.Namespace) -> None:
    """Run collector on a schedule"""
    logger.info(f"Starting scheduled collector (interval: {args.interval} minutes)")
    logger.info(
        f"Limits: Max {SAMGovClient.MAX_NAICS_CODES} NAICS codes, {SAMGovClient.MAX_DAYS_RANGE} days range, {SAMGovClient.MAX_DAILY_COLLECTIONS} collections per day"
    )
    if hasattr(args, "notify") and args.notify:
        logger.info("Slack notifications enabled for new opportunities")

    while True:
        try:
            logger.info("Running scheduled collection")
            collected: int = run_collector(args)

            next_run: datetime = datetime.now() + timedelta(minutes=args.interval)
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


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="GovBizOps - Government Contract Opportunity Management"
    )
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(dest="mode", help="Operation mode")

    # Collector mode
    collector_parser: argparse.ArgumentParser = subparsers.add_parser("collect", help="Collect opportunities")
    collector_parser.add_argument(
        "--naics-codes",
        type=str,
        help=f"Comma-separated NAICS codes (max 50, default from NAICS_CODES env var or 541511,541512)",
    )
    collector_parser.add_argument(
        "--days-back",
        type=int,
        default=1,
        help=f"Number of days to look back (max 90, default: 1)",
    )
    collector_parser.add_argument(
        "--notify",
        action="store_true",
        help="Send Slack notifications for new opportunities (requires SLACK_WEBHOOK_URL)",
    )

    # Scheduled collector mode
    scheduled_parser: argparse.ArgumentParser = subparsers.add_parser(
        "schedule", help="Run collector on schedule"
    )
    scheduled_parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Collection interval in minutes (default: 60)",
    )
    scheduled_parser.add_argument(
        "--naics-codes",
        type=str,
        help=f"Comma-separated NAICS codes (max 50, default from NAICS_CODES env var or 541511,541512)",
    )
    scheduled_parser.add_argument(
        "--notify",
        action="store_true",
        help="Send Slack notifications for new opportunities (requires SLACK_WEBHOOK_URL)",
    )

    # Viewer mode
    viewer_parser: argparse.ArgumentParser = subparsers.add_parser("viewer", help="Run web viewer")
    viewer_parser.add_argument(
        "--port", type=int, default=5000, help="Port to run viewer on (default: 5000)"
    )
    viewer_parser.add_argument("--debug", action="store_true", help="Run in debug mode")

    # CRM push mode
    crm_parser: argparse.ArgumentParser = subparsers.add_parser(
        "push-crm", help="Push collected opportunities to Pretorin CRM"
    )
    crm_parser.add_argument(
        "--crm-url",
        type=str,
        default=None,
        help="CRM base URL (default: from CRM_URL env var or http://localhost:8000)",
    )
    crm_parser.add_argument(
        "--crm-api-key",
        type=str,
        default=None,
        help="CRM API key (default: from CRM_API_KEY env var)",
    )
    crm_parser.add_argument(
        "--no-contacts",
        action="store_true",
        help="Do not auto-create contacts from point-of-contact info",
    )

    # Diagnostic mode
    diag_parser: argparse.ArgumentParser = subparsers.add_parser("diagnose", help="Run diagnostic tests")

    args: argparse.Namespace = parser.parse_args()

    # Debug environment loading
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"SAM_GOV_API_KEY loaded: {bool(os.environ.get('SAM_GOV_API_KEY'))}")
    logger.info(
        f"SLACK_WEBHOOK_URL loaded: {bool(os.environ.get('SLACK_WEBHOOK_URL'))}"
    )

    # Ensure required environment variables
    if not os.environ.get("SAM_GOV_API_KEY"):
        logger.error("SAM_GOV_API_KEY environment variable is required")
        sys.exit(1)

    # Create logs directory
    logs_dir: str = os.path.join(os.getcwd(), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Route to appropriate function
    if args.mode == "collect":
        run_collector(args)
    elif args.mode == "schedule":
        run_scheduled_collector(args)
    elif args.mode == "viewer":
        run_viewer(args)
    elif args.mode == "push-crm":
        run_crm_push(args)
    elif args.mode == "diagnose":
        from govbizops import diagnose_browser
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
        print("  ")
        print("  # Push collected opportunities to CRM")
        print("  govbizops push-crm")


if __name__ == "__main__":
    main()
