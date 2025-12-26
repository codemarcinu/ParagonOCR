#!/usr/bin/env python3
"""Prosty skrypt do sprawdzenia zawartości bazy danych."""

import sys
import os

# Dodaj ścieżkę do modułów (scripts/ jest w głównym katalogu, ReceiptParser/ też)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ReceiptParser'))

from src.database import engine, Sklep, Paragon, PozycjaParagonu, Produkt, AliasProduktu
from sqlalchemy.orm import sessionmaker

SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

print("=" * 60)
print("SPRAWDZANIE ZAWARTOŚCI BAZY DANYCH")
print("=" * 60)

# Sprawdź sklepy
print("\n📦 SKLEPY:")
sklepy = session.query(Sklep).all()
if sklepy:
    for sklep in sklepy:
        print(f"  - {sklep.nazwa_sklepu} (ID: {sklep.sklep_id})")
        if sklep.lokalizacja:
            print(f"    Lokalizacja: {sklep.lokalizacja}")
else:
    print("  Brak sklepów w bazie")

# Sprawdź paragony
print("\n🧾 PARAGONY:")
paragony = session.query(Paragon).all()
if paragony:
    for paragon in paragony:
        print(f"  - Paragon ID: {paragon.paragon_id}")
        print(f"    Sklep: {paragon.sklep.nazwa_sklepu}")
        print(f"    Data: {paragon.data_zakupu}")
        print(f"    Suma: {paragon.suma_paragonu} PLN")
        print(f"    Plik: {paragon.plik_zrodlowy}")
        print(f"    Pozycji: {len(paragon.pozycje)}")
        for i, pozycja in enumerate(paragon.pozycje, 1):
            print(f"      {i}. {pozycja.nazwa_z_paragonu_raw} -> {pozycja.produkt.znormalizowana_nazwa}")
            print(f"         Ilość: {pozycja.ilosc} {pozycja.jednostka_miary or 'szt'}")
            print(f"         Cena: {pozycja.cena_jednostkowa} x {pozycja.ilosc} = {pozycja.cena_calkowita} PLN")
            if pozycja.rabat and pozycja.rabat > 0:
                print(f"         Rabat: {pozycja.rabat} PLN")
        print()
else:
    print("  Brak paragonów w bazie")

# Sprawdź produkty
print("\n🛒 PRODUKTY:")
produkty = session.query(Produkt).all()
if produkty:
    print(f"  Łącznie produktów: {len(produkty)}")
    for produkt in produkty[:10]:  # Pokaż pierwsze 10
        print(f"  - {produkt.znormalizowana_nazwa} (ID: {produkt.produkt_id})")
        if produkt.kategoria:
            print(f"    Kategoria: {produkt.kategoria.nazwa_kategorii}")
        aliases = session.query(AliasProduktu).filter_by(produkt_id=produkt.produkt_id).all()
        if aliases:
            print(f"    Aliasy: {', '.join([a.nazwa_z_paragonu for a in aliases[:3]])}")
            if len(aliases) > 3:
                print(f"    ... i {len(aliases) - 3} więcej")
    if len(produkty) > 10:
        print(f"  ... i {len(produkty) - 10} więcej produktów")
else:
    print("  Brak produktów w bazie")

# Sprawdź aliasy
print("\n🏷️  ALIASY:")
aliases = session.query(AliasProduktu).all()
if aliases:
    print(f"  Łącznie aliasów: {len(aliases)}")
    for alias in aliases[:10]:  # Pokaż pierwsze 10
        print(f"  - '{alias.nazwa_z_paragonu}' -> '{alias.produkt.znormalizowana_nazwa}'")
    if len(aliases) > 10:
        print(f"  ... i {len(aliases) - 10} więcej aliasów")
else:
    print("  Brak aliasów w bazie")

session.close()
print("\n" + "=" * 60)


