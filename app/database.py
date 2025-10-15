import sqlite3
import json
from datetime import datetime
import os
from core.file_utils import format_receipt_filename

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
                detalle TEXT,
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
        
        # Create settings table for default values
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add display_filename column if it doesn't exist (migration)
        try:
            cursor.execute('ALTER TABLE receipts ADD COLUMN display_filename TEXT')
            conn.commit()
        except sqlite3.OperationalError:
            # Column already exists
            pass

        conn.commit()
        conn.close()
    
    def add_receipt(self, filename, file_path, ocr_text, restaurant_name=None, date=None, total_amount=None):
        """Add a new receipt to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get default FX rate and markup from settings
        default_fx_rate = self.get_default_setting('default_fx_rate', 20.0)
        default_markup = self.get_default_setting('default_markup_percent', 2.5)
        
        # Calculate USD amount if MXN amount is provided
        amount_usd = None
        if total_amount and total_amount > 0:
            # total_amount is in MXN, convert to USD with default rates
            amount_usd = total_amount / default_fx_rate
            amount_usd = amount_usd * (1 + default_markup / 100)
        
        cursor.execute('''
            INSERT INTO receipts (filename, file_path, ocr_text, restaurant_name, date, total_amount, 
                                fx_rate, markup_percent, amount_mxn)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (filename, file_path, ocr_text, restaurant_name, date, total_amount, 
              default_fx_rate, default_markup, amount_usd))
        
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
                   cuenta_contable, pais, cc, fx_rate, markup_percent, amount_mxn, reembolso, detalle, display_filename
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
                'detalle': r[15] if len(r) > 15 else None,
                'display_filename': r[16] if len(r) > 16 else None
            }
            for r in receipts
        ]
    
    def get_receipt(self, receipt_id):
        """Get a specific receipt by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, filename, file_path, ocr_text, restaurant_name, date, total_amount, reviewed,
                   cuenta_contable, pais, cc, fx_rate, markup_percent, amount_mxn, reembolso, detalle, display_filename
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
                'detalle': result[15] if len(result) > 15 else None,
                'display_filename': result[16] if len(result) > 16 else None
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

        # Generate display_filename
        display_filename = None
        if date and restaurant_name:
            formatted_name = format_receipt_filename(date, restaurant_name)
            if formatted_name:
                # Get all existing display filenames to check for duplicates
                cursor.execute('SELECT display_filename FROM receipts WHERE id != ? AND reviewed = TRUE', (receipt_id,))
                existing_filenames = {row[0].replace('.pdf', '') for row in cursor.fetchall() if row[0]}

                # Check if this formatted name already exists
                counter = 1
                test_name = formatted_name
                while test_name in existing_filenames:
                    counter += 1
                    test_name = f"{formatted_name}_{counter}"

                display_filename = f"{test_name}.pdf"

        cursor.execute('''
            UPDATE receipts
            SET restaurant_name = ?, date = ?, total_amount = ?, cuenta_contable = ?,
                cc = ?, fx_rate = ?, markup_percent = ?, amount_mxn = ?, reembolso = ?, detalle = ?,
                display_filename = ?, reviewed = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (restaurant_name, date, total_amount, cuenta_contable, cc, fx_rate, markup_percent, amount_usd, reembolso, detalle, display_filename, receipt_id))

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
            SELECT DISTINCT category_value, usage_count FROM categories 
            WHERE category_type = ? 
            ORDER BY usage_count DESC, last_used DESC
        ''', (category_type,))
        
        results = cursor.fetchall()
        conn.close()
        
        # Ensure uniqueness in case DISTINCT didn't fully handle it
        seen = set()
        unique_results = []
        for r in results:
            if r[0] not in seen:
                seen.add(r[0])
                unique_results.append(r[0])
        
        return unique_results
    
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
    
    def delete_receipt(self, receipt_id):
        """Delete a receipt from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if receipt exists
        cursor.execute('SELECT id FROM receipts WHERE id = ?', (receipt_id,))
        if not cursor.fetchone():
            conn.close()
            return False
        
        # Delete the receipt
        cursor.execute('DELETE FROM receipts WHERE id = ?', (receipt_id,))
        conn.commit()
        conn.close()
        return True
    
    def duplicate_receipt_with_cc_split(self, receipt_id, cost_centers):
        """Create duplicate receipts split across cost centers and delete original"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get original receipt
        cursor.execute('''
            SELECT filename, file_path, ocr_text, restaurant_name, date, total_amount, 
                   cuenta_contable, pais, fx_rate, markup_percent, amount_mxn, reembolso, detalle
            FROM receipts WHERE id = ?
        ''', (receipt_id,))
        
        receipt = cursor.fetchone()
        if not receipt:
            conn.close()
            return False
        
        # Calculate split amount
        split_amount = receipt[5] / len(cost_centers) if receipt[5] else 0
        split_amount_mxn = receipt[10] / len(cost_centers) if receipt[10] else 0
        
        # Create new receipts for each cost center
        for cc in cost_centers:
            cursor.execute('''
                INSERT INTO receipts (filename, file_path, ocr_text, restaurant_name, date, total_amount,
                                    cuenta_contable, pais, cc, fx_rate, markup_percent, amount_mxn, 
                                    reembolso, detalle, reviewed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)
            ''', (receipt[0], receipt[1], receipt[2], receipt[3], receipt[4], split_amount,
                  receipt[6], receipt[7], cc, receipt[8], receipt[9], split_amount_mxn,
                  receipt[11], receipt[12]))
        
        # Delete original receipt
        cursor.execute('DELETE FROM receipts WHERE id = ?', (receipt_id,))
        
        conn.commit()
        conn.close()
        return True
    
    def add_cost_center(self, cost_center_name):
        """Add a new cost center to the categories"""
        self._remember_category('cc', cost_center_name)
    
    def set_default_setting(self, key, value):
        """Set a default setting value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, str(value)))
        
        conn.commit()
        conn.close()
    
    def get_default_setting(self, key, default_value=None):
        """Get a default setting value"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            try:
                return float(result[0])
            except ValueError:
                return result[0]
        return default_value
    
    def update_all_fx_rates(self, new_fx_rate, markup_percent=2.5):
        """Update FX rate for all receipts and store as default for future receipts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Store as default for future receipts
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES ('default_fx_rate', ?, CURRENT_TIMESTAMP)
        ''', (new_fx_rate,))
        
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES ('default_markup_percent', ?, CURRENT_TIMESTAMP)
        ''', (markup_percent,))
        
        # Get all receipts with MXN amounts
        cursor.execute('SELECT id, total_amount FROM receipts WHERE total_amount IS NOT NULL')
        receipts = cursor.fetchall()
        
        updated_count = 0
        for receipt_id, total_amount_mxn in receipts:
            if total_amount_mxn and total_amount_mxn > 0:
                # Calculate new USD amount
                usd_base = total_amount_mxn / new_fx_rate
                usd_with_markup = usd_base * (1 + markup_percent / 100)
                
                # Update the receipt
                cursor.execute('''
                    UPDATE receipts 
                    SET fx_rate = ?, markup_percent = ?, amount_mxn = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (new_fx_rate, markup_percent, usd_with_markup, receipt_id))
                
                updated_count += 1
        
        conn.commit()
        conn.close()
        return updated_count
    
    def clear_all_receipts(self):
        """Delete all receipts from the database and their files"""
        import os
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all file paths before deleting
        cursor.execute('SELECT file_path FROM receipts WHERE file_path IS NOT NULL')
        file_paths = [row[0] for row in cursor.fetchall()]
        
        # Delete files
        deleted_files = 0
        for file_path in file_paths:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_files += 1
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
        
        # Delete all receipts from database
        cursor.execute('DELETE FROM receipts')
        deleted_records = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return deleted_records, deleted_files
    
    def export_to_csv(self):
        """Export all receipts to CSV format"""
        import pandas as pd
        
        receipts = self.get_all_receipts()
        if not receipts:
            return None
        
        df = pd.DataFrame(receipts)
        df = df[['filename', 'restaurant_name', 'date', 'total_amount', 'reviewed']]
        
        return df