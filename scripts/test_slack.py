#!/usr/bin/env python3
"""
Test script to verify Slack webhook configuration
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_slack_webhook():
    """Test the Slack webhook with a simple message"""
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')

    print("=== Slack Webhook Test ===\n")

    if not webhook_url:
        print("❌ ERROR: SLACK_WEBHOOK_URL not found in environment")
        print("   Please add it to your .env file:")
        print("   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
        return False

    print(f"✓ Webhook URL found: {webhook_url[:50]}...")
    print("\nSending test message to Slack...\n")

    # Simple test payload
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🧪 GovBizOps Test Message"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "This is a test message to verify your Slack webhook is working correctly.\n\nIf you see this message in Slack, your webhook is configured properly! ✓"
                }
            }
        ],
        "text": "GovBizOps Test Message"
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10
        )

        print(f"Response Status Code: {response.status_code}")

        if response.status_code == 200:
            print("✓ SUCCESS: Test message sent to Slack!")
            print("  Check your Slack channel for the test message.")
            return True
        else:
            print(f"❌ ERROR: Slack API returned error")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print("❌ ERROR: Request timed out")
        print("   Check your internet connection and webhook URL")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ ERROR: Request failed - {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error - {e}")
        return False

if __name__ == '__main__':
    success = test_slack_webhook()
    exit(0 if success else 1)
