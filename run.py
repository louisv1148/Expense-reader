#!/usr/bin/env python3
"""
Main entry point for the Expense Reader application
"""

if __name__ == '__main__':
    from app.main import app
    app.run(debug=True, host='127.0.0.1', port=8080)