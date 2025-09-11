#!/usr/bin/env python3
"""
Expense Reader Desktop App
A simple desktop launcher for the Flask expense reader
"""

import os
import sys
import threading
import time
import webbrowser
import signal
import atexit

# Add current directory to Python path to import our modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import our Flask app
from app import app

class ExpenseReaderApp:
    def __init__(self):
        self.flask_thread = None
        self.server_running = False
        self.port = 8080
        
    def start_server(self):
        """Start the Flask server in a separate thread"""
        if not self.server_running:
            print("🧾 Starting Expense Reader Desktop App...")
            print("📂 Launching server...")
            
            # Start Flask in a separate thread
            self.flask_thread = threading.Thread(target=self.run_flask, daemon=True)
            self.flask_thread.start()
            
            # Wait for server to start
            time.sleep(3)
            
            if self.server_running:
                print(f"✅ Server running at http://127.0.0.1:{self.port}")
                print("🌐 Opening browser...")
                self.open_browser()
                print("\n" + "="*50)
                print("📊 EXPENSE READER IS NOW RUNNING")
                print("="*50)
                print(f"🔗 Web Interface: http://127.0.0.1:{self.port}")
                print("📱 Use your browser to upload and process receipts")
                print("🛑 Press Ctrl+C to stop the server")
                print("="*50)
                print("\nServer output:")
    
    def run_flask(self):
        """Run the Flask application"""
        try:
            self.server_running = True
            # Configure Flask to run without debug mode for production
            app.run(host='127.0.0.1', port=self.port, debug=False, use_reloader=False)
        except Exception as e:
            print(f"❌ Flask server error: {e}")
            self.server_running = False
    
    def open_browser(self):
        """Open the web interface in default browser"""
        try:
            webbrowser.open(f"http://127.0.0.1:{self.port}")
        except Exception as e:
            print(f"⚠️  Could not auto-open browser: {e}")
            print(f"Please manually open: http://127.0.0.1:{self.port}")
    
    def run(self):
        """Start the desktop application"""
        try:
            self.start_server()
            
            # Keep the main thread alive
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down Expense Reader...")
            print("👋 Thanks for using Expense Reader!")
            
def main():
    """Main entry point for the desktop application"""
    
    # Change to the correct directory
    os.chdir(current_dir)
    
    # Check if required files exist
    required_files = ['app.py', 'database.py', 'templates/index.html']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("❌ Error: Missing required files:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nPlease run this from the Expense Reader directory.")
        input("Press Enter to exit...")
        return 1
    
    # Create and run the desktop app
    desktop_app = ExpenseReaderApp()
    desktop_app.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())