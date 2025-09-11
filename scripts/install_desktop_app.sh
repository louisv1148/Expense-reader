#!/bin/bash

echo "📦 Installing Expense Reader Desktop App..."
echo ""

# Check if the app exists
if [ ! -d "dist/Expense Reader.app" ]; then
    echo "❌ Desktop app not found! Please run the build process first."
    exit 1
fi

# Create Applications shortcut (optional)
echo "🔗 Creating shortcut to Applications folder..."
if [ ! -L "/Applications/Expense Reader.app" ]; then
    ln -sf "$(pwd)/dist/Expense Reader.app" "/Applications/Expense Reader.app"
    echo "✅ Shortcut created in Applications folder"
else
    echo "ℹ️  Shortcut already exists in Applications folder"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "📱 How to use your Desktop App:"
echo "   1. Double-click 'Expense Reader.app' in Applications or"
echo "   2. Double-click the app in the 'dist' folder"
echo "   3. The app will start Flask server automatically"
echo "   4. Your browser will open to the web interface"
echo "   5. Process your monthly receipts!"
echo "   6. Press Ctrl+C in the terminal to stop (or just close the app)"
echo ""
echo "💡 Pro tip: Pin the app to your Dock for easy monthly access!"
echo ""