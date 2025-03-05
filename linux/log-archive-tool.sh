#!/bin/bash

# Default directory containing log files
LOG_DIR="/var/log/"

# Allow user to specify a directory as an argument
if [ -n "$1" ]; then
    LOG_DIR="$1"
fi

# Number of days after which logs should be archived
DAYS=2

# Archive file name with timestamp
ARCHIVE_FILE="${LOG_DIR%/}/logs-$(date +%Y-%m-%d).tar.gz"

# Find and archive log files older than specified days
find "$LOG_DIR" -type f -name "*.log" -mtime +$DAYS -print0 | tar -czvf "$ARCHIVE_FILE" --null -T -

# Optional: Remove archived log files
echo "Do you want to delete the archived logs? (y/n)"
read -r response
if [[ "$response" == "y" ]]; then
    find "$LOG_DIR" -type f -name "*.log" -mtime +$DAYS -delete
    echo "Archived log files deleted."
else
    echo "Archived log files retained."
fi

# Print archive details
echo "Logs archived to: $ARCHIVE_FILE"
