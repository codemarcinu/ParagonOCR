"""
Skrypt migracyjny do aktualizacji schematu bazy danych.
Dodaje brakujące kolumny do istniejących tabel.
"""
import os
import sqlite3
from pathlib import Path

# Ścieżka do bazy danych (taka sama jak w database.py)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(project_root, "data", "receipts.db")


def migrate_add_zamrozone_column():
    """
    Dodaje kolumnę 'zamrozone' do tabeli 'stan_magazynowy' jeśli nie istnieje.
    """
    if not os.path.exists(db_path):
        print(f"Baza danych nie istnieje: {db_path}")
        print("Uruchom najpierw init_db() aby utworzyć bazę danych.")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Sprawdź czy kolumna już istnieje
        cursor.execute("PRAGMA table_info(stan_magazynowy)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'zamrozone' in columns:
            print("Kolumna 'zamrozone' już istnieje w tabeli 'stan_magazynowy'.")
            return True
        
        # Dodaj kolumnę
        print("Dodawanie kolumny 'zamrozone' do tabeli 'stan_magazynowy'...")
        cursor.execute("""
            ALTER TABLE stan_magazynowy 
            ADD COLUMN zamrozone BOOLEAN NOT NULL DEFAULT 0
        """)
        
        conn.commit()
        print("✅ Kolumna 'zamrozone' została pomyślnie dodana.")
        return True
        
    except sqlite3.Error as e:
        conn.rollback()
        print(f"❌ Błąd podczas migracji: {e}")
        return False
    finally:
        conn.close()


def migrate_all():
    """
    Wykonuje wszystkie migracje.
    """
    print("=== Migracja bazy danych ===")
    print(f"Baza danych: {db_path}")
    print()
    
    success = True
    success = migrate_add_zamrozone_column() and success
    
    print()
    if success:
        print("✅ Wszystkie migracje zakończone pomyślnie.")
    else:
        print("❌ Niektóre migracje zakończyły się błędem.")
    
    return success


if __name__ == '__main__':
    migrate_all()







