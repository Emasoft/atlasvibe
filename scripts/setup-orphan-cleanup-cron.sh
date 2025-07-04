#!/usr/bin/env bash
# Setup script for automated orphaned process cleanup

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/cleanup-orphaned-processes.sh"

echo "=== Setting up automated orphaned process cleanup ==="

# Check if cleanup script exists
if [ ! -f "$CLEANUP_SCRIPT" ]; then
    echo "ERROR: Cleanup script not found at $CLEANUP_SCRIPT"
    exit 1
fi

# Create a launchd plist for macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLIST_FILE="$HOME/Library/LaunchAgents/com.atlasvibe.cleanup-orphaned-processes.plist"

    cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.atlasvibe.cleanup-orphaned-processes</string>
    <key>ProgramArguments</key>
    <array>
        <string>$CLEANUP_SCRIPT</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer> <!-- Run every hour -->
    <key>StandardOutPath</key>
    <string>$HOME/.atlasvibe/cleanup-orphaned.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.atlasvibe/cleanup-orphaned-error.log</string>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
EOF

    # Create log directory
    mkdir -p "$HOME/.atlasvibe"

    # Load the launch agent
    launchctl unload "$PLIST_FILE" 2>/dev/null || true
    launchctl load "$PLIST_FILE"

    echo "✓ LaunchAgent installed at: $PLIST_FILE"
    echo "✓ Cleanup will run every hour"
    echo ""
    echo "To check status: launchctl list | grep atlasvibe"
    echo "To stop: launchctl unload $PLIST_FILE"
    echo "To start: launchctl load $PLIST_FILE"

else
    # Linux/Unix cron setup
    CRON_JOB="0 * * * * $CLEANUP_SCRIPT >> $HOME/.atlasvibe/cleanup-orphaned.log 2>&1"

    # Check if cron job already exists
    if crontab -l 2>/dev/null | grep -q "cleanup-orphaned-processes.sh"; then
        echo "Cron job already exists"
    else
        # Add cron job
        (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
        echo "✓ Cron job added to run hourly"
    fi

    # Create log directory
    mkdir -p "$HOME/.atlasvibe"

    echo ""
    echo "To check cron jobs: crontab -l"
    echo "To remove: crontab -e (and delete the line)"
fi

echo ""
echo "=== Setup complete ==="
echo "Logs will be written to: $HOME/.atlasvibe/cleanup-orphaned.log"
