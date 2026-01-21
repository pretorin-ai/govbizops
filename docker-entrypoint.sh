#!/bin/bash
set -e

# Create data and logs directories if they don't exist
mkdir -p /app/data /app/logs

# Run the scheduled collector
# Use --notify flag if SLACK_WEBHOOK_URL is set
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    echo "Starting scheduled collector with Slack notifications (interval: ${SCHEDULE_INTERVAL:-120} minutes)"
    exec govbizops schedule --interval ${SCHEDULE_INTERVAL:-120} --notify
else
    echo "Starting scheduled collector (interval: ${SCHEDULE_INTERVAL:-120} minutes)"
    exec govbizops schedule --interval ${SCHEDULE_INTERVAL:-120}
fi

