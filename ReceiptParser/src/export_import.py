"""
Moduł do eksportu i importu danych z bazy danych.

Obsługuje:
- CSV export (receipts, receipt_items, products, warehouse)
- Database backup/restore (.db, .zip, .sql)
- Multi-format import (CSV, JSON, Excel, SQLite backup)
"""
import os
import csv
import json
import zipfile
import shutil
import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional, Any
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine

from .database import (
    engine,
    Sklep,
    Paragon,
    PozycjaParagonu,
    Produkt,
    AliasProduktu,
    KategoriaProduktu,
    StanMagazynowy,
)
from .security import validate_file_path, sanitize_path, sanitize_log_message


class DataExporter:
    """Klasa do eksportu danych do CSV."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def export_receipts(
        self,
        output_path: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        store_filter: Optional[str] = None,
    ) -> bool:
        """
        Eksportuje paragony do CSV.
        
        Args:
            output_path: Ścieżka do pliku wyjściowego CSV
            date_from: Data początkowa (opcjonalna)
            date_to: Data końcowa (opcjonalna)
            store_filter: Filtr nazwy sklepu (opcjonalna)
        
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        try:
            # Waliduj ścieżkę wyjściową
            validated_path = validate_file_path(
                output_path,
                allowed_extensions=['.csv'],
                check_exists=False
            )
            output_path = str(validated_path)
            
            # Zapytanie do bazy
            query = self.session.query(Paragon).join(Sklep)
            
            if date_from:
                query = query.filter(Paragon.data_zakupu >= date_from)
            if date_to:
                query = query.filter(Paragon.data_zakupu <= date_to)
            if store_filter:
                query = query.filter(Sklep.nazwa_sklepu.ilike(f"%{store_filter}%"))
            
            receipts = query.all()
            
            # Zapisz do CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                # Nagłówek
                writer.writerow([
                    'paragon_id',
                    'sklep_nazwa',
                    'sklep_lokalizacja',
                    'data_zakupu',
                    'suma_paragonu',
                    'plik_zrodlowy',
                ])
                
                # Dane
                for receipt in receipts:
                    writer.writerow([
                        receipt.paragon_id,
                        receipt.sklep.nazwa_sklepu if receipt.sklep else '',
                        receipt.sklep.lokalizacja if receipt.sklep else '',
                        receipt.data_zakupu.isoformat() if receipt.data_zakupu else '',
                        str(receipt.suma_paragonu) if receipt.suma_paragonu else '',
                        receipt.plik_zrodlowy,
                    ])
            
            return True
        except Exception as e:
            print(f"BŁĄD podczas eksportu paragonów: {sanitize_log_message(str(e))}")
            return False
    
    def export_receipt_items(
        self,
        output_path: str,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        category_filter: Optional[str] = None,
    ) -> bool:
        """
        Eksportuje pozycje paragonów do CSV.
        
        Args:
            output_path: Ścieżka do pliku wyjściowego CSV
            date_from: Data początkowa (opcjonalna)
            date_to: Data końcowa (opcjonalna)
            category_filter: Filtr kategorii produktu (opcjonalna)
        
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        try:
            validated_path = validate_file_path(
                output_path,
                allowed_extensions=['.csv'],
                check_exists=False
            )
            output_path = str(validated_path)
            
            query = (
                self.session.query(PozycjaParagonu)
                .join(Paragon)
                .join(Produkt, isouter=True)
                .join(KategoriaProduktu, isouter=True)
            )
            
            if date_from:
                query = query.filter(Paragon.data_zakupu >= date_from)
            if date_to:
                query = query.filter(Paragon.data_zakupu <= date_to)
            if category_filter:
                query = query.filter(
                    KategoriaProduktu.nazwa_kategorii.ilike(f"%{category_filter}%")
                )
            
            items = query.all()
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([
                    'pozycja_id',
                    'paragon_id',
                    'produkt_nazwa',
                    'kategoria',
                    'nazwa_z_paragonu_raw',
                    'ilosc',
                    'jednostka_miary',
                    'cena_jednostkowa',
                    'cena_calkowita',
                    'rabat',
                    'cena_po_rabacie',
                ])
                
                for item in items:
                    writer.writerow([
                        item.pozycja_id,
                        item.paragon_id,
                        item.produkt.znormalizowana_nazwa if item.produkt else '',
                        item.produkt.kategoria.nazwa_kategorii if item.produkt and item.produkt.kategoria else '',
                        item.nazwa_z_paragonu_raw,
                        str(item.ilosc) if item.ilosc else '',
                        item.jednostka_miary or '',
                        str(item.cena_jednostkowa) if item.cena_jednostkowa else '',
                        str(item.cena_calkowita) if item.cena_calkowita else '',
                        str(item.rabat) if item.rabat else '',
                        str(item.cena_po_rabacie) if item.cena_po_rabacie else '',
                    ])
            
            return True
        except Exception as e:
            print(f"BŁĄD podczas eksportu pozycji: {sanitize_log_message(str(e))}")
            return False
    
    def export_products(self, output_path: str) -> bool:
        """Eksportuje produkty do CSV."""
        try:
            validated_path = validate_file_path(
                output_path,
                allowed_extensions=['.csv'],
                check_exists=False
            )
            output_path = str(validated_path)
            
            products = self.session.query(Produkt).all()
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([
                    'produkt_id',
                    'znormalizowana_nazwa',
                    'kategoria_nazwa',
                ])
                
                for product in products:
                    writer.writerow([
                        product.produkt_id,
                        product.znormalizowana_nazwa,
                        product.kategoria.nazwa_kategorii if product.kategoria else '',
                    ])
            
            return True
        except Exception as e:
            print(f"BŁĄD podczas eksportu produktów: {sanitize_log_message(str(e))}")
            return False
    
    def export_warehouse(self, output_path: str) -> bool:
        """Eksportuje stan magazynowy do CSV."""
        try:
            validated_path = validate_file_path(
                output_path,
                allowed_extensions=['.csv'],
                check_exists=False
            )
            output_path = str(validated_path)
            
            warehouse_items = self.session.query(StanMagazynowy).all()
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([
                    'stan_id',
                    'produkt_nazwa',
                    'ilosc',
                    'jednostka_miary',
                    'data_waznosci',
                    'data_dodania',
                    'zamrozone',
                ])
                
                for item in warehouse_items:
                    writer.writerow([
                        item.stan_id,
                        item.produkt.znormalizowana_nazwa if item.produkt else '',
                        str(item.ilosc) if item.ilosc else '',
                        item.jednostka_miary or '',
                        item.data_waznosci.isoformat() if item.data_waznosci else '',
                        item.data_dodania.isoformat() if item.data_dodania else '',
                        'TAK' if item.zamrozone else 'NIE',
                    ])
            
            return True
        except Exception as e:
            print(f"BŁĄD podczas eksportu magazynu: {sanitize_log_message(str(e))}")
            return False


class DatabaseBackup:
    """Klasa do tworzenia i przywracania backupów bazy danych."""
    
    @staticmethod
    def create_backup(backup_path: str, format: str = 'db') -> bool:
        """
        Tworzy backup bazy danych.
        
        Args:
            backup_path: Ścieżka do pliku backupu
            format: Format backupu ('db', 'zip', 'sql')
        
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        try:
            from .database import db_path
            
            if not os.path.exists(db_path):
                print(f"BŁĄD: Baza danych nie istnieje: {db_path}")
                return False
            
            # Waliduj ścieżkę wyjściową
            validated_path = validate_file_path(
                backup_path,
                allowed_extensions=['.db', '.zip', '.sql'],
                check_exists=False
            )
            backup_path = str(validated_path)
            
            if format == 'db':
                # Prosta kopia pliku
                shutil.copy2(db_path, backup_path)
            
            elif format == 'zip':
                # Kompresja do ZIP
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    zipf.write(db_path, os.path.basename(db_path))
            
            elif format == 'sql':
                # SQL dump
                conn = sqlite3.connect(db_path)
                with open(backup_path, 'w', encoding='utf-8') as f:
                    for line in conn.iterdump():
                        f.write(f'{line}\n')
                conn.close()
            
            else:
                print(f"BŁĄD: Nieobsługiwany format backupu: {format}")
                return False
            
            return True
        except Exception as e:
            print(f"BŁĄD podczas tworzenia backupu: {sanitize_log_message(str(e))}")
            return False
    
    @staticmethod
    def restore_backup(backup_path: str, validate_schema: bool = True) -> bool:
        """
        Przywraca backup bazy danych.
        
        Args:
            backup_path: Ścieżka do pliku backupu
            validate_schema: Czy walidować schemat przed przywróceniem
        
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        try:
            from .database import db_path, Base, engine
            
            # Waliduj ścieżkę backupu
            validated_path = validate_file_path(
                backup_path,
                allowed_extensions=['.db', '.zip', '.sql'],
                check_exists=True
            )
            backup_path = str(validated_path)
            
            # Sprawdź rozmiar pliku (max 500MB)
            file_size = os.path.getsize(backup_path)
            if file_size > 500 * 1024 * 1024:
                print("BŁĄD: Plik backupu jest za duży (max 500MB)")
                return False
            
            # Przygotuj tymczasową ścieżkę
            temp_db_path = db_path + '.tmp'
            
            # Rozpakuj/konwertuj backup
            if backup_path.endswith('.zip'):
                with zipfile.ZipFile(backup_path, 'r') as zipf:
                    # Znajdź plik .db w archiwum
                    db_files = [f for f in zipf.namelist() if f.endswith('.db')]
                    if not db_files:
                        print("BŁĄD: Brak pliku .db w archiwum ZIP")
                        return False
                    zipf.extract(db_files[0], os.path.dirname(temp_db_path))
                    extracted_path = os.path.join(os.path.dirname(temp_db_path), db_files[0])
                    shutil.move(extracted_path, temp_db_path)
            
            elif backup_path.endswith('.sql'):
                # Przywróć z SQL dump
                conn = sqlite3.connect(temp_db_path)
                with open(backup_path, 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                    conn.executescript(sql_script)
                conn.close()
            
            else:
                # Prosta kopia
                shutil.copy2(backup_path, temp_db_path)
            
            # Waliduj schemat jeśli wymagane
            if validate_schema:
                temp_engine = create_engine(f"sqlite:///{temp_db_path}")
                try:
                    # Sprawdź czy wszystkie tabele istnieją
                    with temp_engine.connect() as conn:
                        result = conn.execute(text(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ))
                        tables = {row[0] for row in result}
                        required_tables = {
                            'sklepy', 'paragony', 'pozycje_paragonu',
                            'produkty', 'aliasy_produktow', 'kategorie_produktow',
                            'stan_magazynowy'
                        }
                        if not required_tables.issubset(tables):
                            print("BŁĄD: Backup nie zawiera wszystkich wymaganych tabel")
                            os.remove(temp_db_path)
                            return False
                except Exception as e:
                    print(f"BŁĄD podczas walidacji schematu: {sanitize_log_message(str(e))}")
                    os.remove(temp_db_path)
                    return False
                finally:
                    temp_engine.dispose()
            
            # Utwórz backup obecnej bazy (jeśli istnieje)
            if os.path.exists(db_path):
                old_backup = db_path + '.old'
                shutil.copy2(db_path, old_backup)
            
            # Zastąp bazę danych
            shutil.move(temp_db_path, db_path)
            
            # Usuń stary backup jeśli wszystko się powiodło
            old_backup = db_path + '.old'
            if os.path.exists(old_backup):
                os.remove(old_backup)
            
            return True
        except Exception as e:
            print(f"BŁĄD podczas przywracania backupu: {sanitize_log_message(str(e))}")
            # Przywróć stary backup jeśli istnieje
            old_backup = db_path + '.old'
            if os.path.exists(old_backup):
                try:
                    shutil.move(old_backup, db_path)
                except Exception:
                    pass
            return False


class DataImporter:
    """Klasa do importu danych z różnych formatów."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def import_csv(
        self,
        csv_path: str,
        table: str,
        mode: str = 'merge'
    ) -> bool:
        """
        Importuje dane z CSV.
        
        Args:
            csv_path: Ścieżka do pliku CSV
            table: Nazwa tabeli ('receipts', 'products', 'warehouse')
            mode: Tryb importu ('merge' lub 'replace')
        
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        try:
            validated_path = validate_file_path(
                csv_path,
                allowed_extensions=['.csv'],
                check_exists=True
            )
            csv_path = str(validated_path)
            
            # Sprawdź rozmiar pliku (max 100MB)
            file_size = os.path.getsize(csv_path)
            if file_size > 100 * 1024 * 1024:
                print("BŁĄD: Plik CSV jest za duży (max 100MB)")
                return False
            
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=';')
                
                if table == 'products':
                    return self._import_products_csv(reader, mode)
                elif table == 'receipts':
                    return self._import_receipts_csv(reader, mode)
                else:
                    print(f"BŁĄD: Nieobsługiwana tabela: {table}")
                    return False
            
        except Exception as e:
            print(f"BŁĄD podczas importu CSV: {sanitize_log_message(str(e))}")
            return False
    
    def _import_products_csv(self, reader, mode: str) -> bool:
        """Importuje produkty z CSV."""
        try:
            for row in reader:
                # Waliduj dane
                if not row.get('znormalizowana_nazwa'):
                    continue
                
                # Znajdź lub utwórz kategorię
                kategoria_nazwa = row.get('kategoria_nazwa', 'Inne')
                kategoria = (
                    self.session.query(KategoriaProduktu)
                    .filter_by(nazwa_kategorii=kategoria_nazwa)
                    .first()
                )
                if not kategoria:
                    kategoria = KategoriaProduktu(nazwa_kategorii=kategoria_nazwa)
                    self.session.add(kategoria)
                    self.session.flush()
                
                # Znajdź lub utwórz produkt
                produkt_nazwa = row['znormalizowana_nazwa']
                produkt = (
                    self.session.query(Produkt)
                    .filter_by(znormalizowana_nazwa=produkt_nazwa)
                    .first()
                )
                
                if not produkt:
                    produkt = Produkt(
                        znormalizowana_nazwa=produkt_nazwa,
                        kategoria_id=kategoria.kategoria_id
                    )
                    self.session.add(produkt)
                elif mode == 'replace':
                    produkt.kategoria_id = kategoria.kategoria_id
            
            self.session.commit()
            return True
        except Exception as e:
            self.session.rollback()
            print(f"BŁĄD podczas importu produktów: {sanitize_log_message(str(e))}")
            return False
    
    def _import_receipts_csv(self, reader, mode: str) -> bool:
        """Importuje paragony z CSV (uproszczona wersja)."""
        # Implementacja importu paragonów jest bardziej złożona
        # i wymaga walidacji relacji między tabelami
        print("OSTRZEŻENIE: Import paragonów z CSV jest w trakcie implementacji")
        return False

