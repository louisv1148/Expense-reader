#!/bin/bash
# Expense Reader Launcher
# This script starts the Flask app and opens browser automatically

# Always use the project directory (absolute path)
PROJECT_DIR="/Users/lvc/Expense-reader"
cd "$PROJECT_DIR"

echo "🧾 Starting Expense Reader..."
echo "📂 Working directory: $PROJECT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please make sure you're in the correct directory."
    read -p "Press Enter to exit..."
    exit 1
fi

# Check if required files exist
if [ ! -f "app.py" ]; then
    echo "❌ app.py not found!"
    echo "Please make sure you're in the correct directory."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "✅ All files found"
echo "🔧 Activating virtual environment..."

# Activate virtual environment
source venv/bin/activate

echo "🚀 Starting Flask server..."
echo "📱 Your browser will open automatically in 3 seconds..."
echo ""
echo "=" * 50
echo "📊 EXPENSE READER IS STARTING"
echo "=" * 50
echo "🔗 Web Interface: http://127.0.0.1:8080"
echo "📁 Upload and process your receipts"
echo "🛑 Press Ctrl+C to stop when done"
echo "=" * 50
echo ""

# Wait 3 seconds then open browser
sleep 3 &
SLEEP_PID=$!

# Start Flask server in background initially
python app.py &
FLASK_PID=$!

# Wait for the sleep to finish, then open browser
wait $SLEEP_PID
echo "🌐 Opening browser..."
open http://127.0.0.1:8080

# Bring Flask to foreground so Ctrl+C works
wait $FLASK_PID