import sqlite3
import json
from datetime import datetime
import os

class ExpenseDatabase:
    def __init__(self, db_path="expenses.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS receipts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                ocr_text TEXT,
                restaurant_name TEXT,
                date TEXT,
                total_amount REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_receipt(self, filename, file_path, ocr_text, restaurant_name=None, date=None, total_amount=None):
        """Add a new receipt to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO receipts (filename, file_path, ocr_text, restaurant_name, date, total_amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (filename, file_path, ocr_text, restaurant_name, date, total_amount))
        
        receipt_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return receipt_id
    
    def get_all_receipts(self):
        """Get all receipts from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, file_path, ocr_text, restaurant_name, date, total_amount, reviewed
            FROM receipts ORDER BY created_at DESC
        ''')
        
        receipts = cursor.fetchall()
        conn.close()
        
        return [
            {
                'id': r[0],
                'filename': r[1],
                'file_path': r[2],
                'ocr_text': r[3],
                'restaurant_name': r[4],
                'date': r[5],
                'total_amount': r[6],
                'reviewed': bool(r[7])
            }
            for r in receipts
        ]
    
    def get_receipt(self, receipt_id):
        """Get a specific receipt by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, file_path, ocr_text, restaurant_name, date, total_amount, reviewed
            FROM receipts WHERE id = ?
        ''', (receipt_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'id': result[0],
                'filename': result[1],
                'file_path': result[2],
                'ocr_text': result[3],
                'restaurant_name': result[4],
                'date': result[5],
                'total_amount': result[6],
                'reviewed': bool(result[7])
            }
        return None
    
    def update_receipt(self, receipt_id, restaurant_name=None, date=None, total_amount=None):
        """Update receipt data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE receipts 
            SET restaurant_name = ?, date = ?, total_amount = ?, reviewed = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (restaurant_name, date, total_amount, receipt_id))
        
        conn.commit()
        conn.close()
    
    def get_training_examples(self, limit=5):
        """Get successfully corrected receipts as training examples"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ocr_text, restaurant_name, date, total_amount
            FROM receipts 
            WHERE reviewed = TRUE 
            AND restaurant_name IS NOT NULL 
            AND date IS NOT NULL 
            AND total_amount IS NOT NULL
            ORDER BY updated_at DESC
            LIMIT ?
        ''', (limit,))
        
        examples = cursor.fetchall()
        conn.close()
        
        return [
            {
                'ocr_text': e[0],
                'restaurant_name': e[1],
                'date': e[2],
                'total_amount': e[3]
            }
            for e in examples
        ]
    
    def export_to_csv(self):
        """Export all receipts to CSV format"""
        import pandas as pd
        
        receipts = self.get_all_receipts()
        if not receipts:
            return None
        
        df = pd.DataFrame(receipts)
        df = df[['filename', 'restaurant_name', 'date', 'total_amount', 'reviewed']]
        
        return df