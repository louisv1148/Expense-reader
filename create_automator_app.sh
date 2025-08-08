#!/bin/bash
# This script creates an Automator application for Expense Reader

echo "🤖 Creating Automator Application for Expense Reader..."

# Create the AppleScript that will run our Flask app
APPLESCRIPT_CONTENT='
tell application "Terminal"
    activate
    do script "cd '"'"'/Users/lvc/Expense-reader'"'"' && source venv/bin/activate && echo '"'"'🧾 Starting Expense Reader...'"'"' && echo '"'"'🌐 Opening browser in 3 seconds...'"'"' && (sleep 3 && open http://127.0.0.1:8080) & python app.py"
end tell
'

echo "📝 AppleScript created"
echo ""
echo "🔧 To create your desktop app:"
echo ""
echo "1. Open Automator (⌘+Space, then type 'Automator')"
echo "2. Choose 'Application' when prompted"
echo "3. Search for 'Run AppleScript' in the actions"
echo "4. Drag 'Run AppleScript' to the workflow area"
echo "5. Replace the default script with this:"
echo ""
echo "----------------------------------------"
echo "$APPLESCRIPT_CONTENT"
echo "----------------------------------------"
echo ""
echo "6. Save the application as 'Expense Reader' on your Desktop"
echo "7. You can then move it to Applications folder"
echo ""
echo "✅ Your desktop app will:"
echo "   - Open Terminal automatically"
echo "   - Start Flask server"
echo "   - Open browser after 3 seconds"
echo "   - Work exactly like the command line version"
echo ""