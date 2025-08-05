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
                cuenta_contable TEXT DEFAULT 'Comidas con Clientes',
                pais TEXT DEFAULT 'MX',
                cc TEXT DEFAULT 'Alternativos',
                fx_rate REAL DEFAULT 1.0,
                markup_percent REAL DEFAULT 2.5,
                amount_mxn REAL,
                reembolso TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Create categories table for remembering user selections
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_type TEXT NOT NULL,
                category_value TEXT NOT NULL,
                usage_count INTEGER DEFAULT 1,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category_type, category_value)
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
            SELECT id, filename, file_path, ocr_text, restaurant_name, date, total_amount, reviewed,
                   cuenta_contable, pais, cc, fx_rate, markup_percent, amount_mxn, reembolso, detalle
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
                'reviewed': bool(r[7]),
                'cuenta_contable': r[8] if len(r) > 8 else 'Comidas con Clientes',
                'pais': r[9] if len(r) > 9 else 'MX',
                'cc': r[10] if len(r) > 10 else 'Alternativos',
                'fx_rate': r[11] if len(r) > 11 else 20.0,
                'markup_percent': r[12] if len(r) > 12 else 2.5,
                'amount_mxn': r[13] if len(r) > 13 else None,
                'reembolso': r[14] if len(r) > 14 else None,
                'detalle': r[15] if len(r) > 15 else None
            }
            for r in receipts
        ]
    
    def get_receipt(self, receipt_id):
        """Get a specific receipt by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, file_path, ocr_text, restaurant_name, date, total_amount, reviewed,
                   cuenta_contable, pais, cc, fx_rate, markup_percent, amount_mxn, reembolso, detalle
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
                'reviewed': bool(result[7]),
                'cuenta_contable': result[8] if len(result) > 8 else 'Comidas con Clientes',
                'pais': result[9] if len(result) > 9 else 'MX',
                'cc': result[10] if len(result) > 10 else 'Alternativos',
                'fx_rate': result[11] if len(result) > 11 else 20.0,
                'markup_percent': result[12] if len(result) > 12 else 2.5,
                'amount_mxn': result[13] if len(result) > 13 else None,
                'reembolso': result[14] if len(result) > 14 else None,
                'detalle': result[15] if len(result) > 15 else None
            }
        return None
    
    def update_receipt(self, receipt_id, restaurant_name=None, date=None, total_amount=None, 
                      cuenta_contable=None, cc=None, fx_rate=None, markup_percent=None, reembolso=None, detalle=None):
        """Update receipt data with all new fields"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Calculate USD amount (receipts are in MXN, convert to USD)
        amount_usd = None
        if total_amount and fx_rate:
            # total_amount is in MXN, divide by FX rate to get USD
            amount_usd = total_amount / fx_rate
            # Apply markup to USD amount
            amount_usd = amount_usd * (1 + (markup_percent or 2.5) / 100)
        
        cursor.execute('''
            UPDATE receipts 
            SET restaurant_name = ?, date = ?, total_amount = ?, cuenta_contable = ?, 
                cc = ?, fx_rate = ?, markup_percent = ?, amount_mxn = ?, reembolso = ?, detalle = ?,
                reviewed = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (restaurant_name, date, total_amount, cuenta_contable, cc, fx_rate, markup_percent, amount_usd, reembolso, detalle, receipt_id))
        
        conn.commit()
        conn.close()
        
        # Remember category selections (after closing the main connection)
        if cuenta_contable:
            self._remember_category('cuenta_contable', cuenta_contable)
        if cc:
            self._remember_category('cc', cc)
        if reembolso:
            self._remember_category('reembolso', reembolso)
    
    def _remember_category(self, category_type, category_value):
        """Remember a category selection for future use"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO categories (category_type, category_value, usage_count, last_used)
            VALUES (?, ?, COALESCE((SELECT usage_count FROM categories WHERE category_type = ? AND category_value = ?), 0) + 1, CURRENT_TIMESTAMP)
        ''', (category_type, category_value, category_type, category_value))
        
        conn.commit()
        conn.close()
    
    def get_remembered_categories(self, category_type):
        """Get previously used categories, ordered by usage frequency"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT category_value, usage_count FROM categories 
            WHERE category_type = ? 
            ORDER BY usage_count DESC, last_used DESC
        ''', (category_type,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [r[0] for r in results]
    
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