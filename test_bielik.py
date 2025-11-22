#!/usr/bin/env python3
"""Prosty skrypt testowy do demonstracji asystenta Bielik."""

import sys
import os

# Dodaj ścieżkę do modułów
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ReceiptParser'))

from ReceiptParser.src.bielik import BielikAssistant, ask_bielik, get_dish_suggestions, get_shopping_list

def main():
    print("=" * 60)
    print("🦅 TEST ASYSTENTA BIELIK")
    print("=" * 60)
    
    # Test 1: Pytanie ogólne
    print("\n1. PYTANIE OGÓLNE:")
    print("-" * 60)
    question = "co mam do jedzenia?"
    print(f"Pytanie: {question}")
    answer = ask_bielik(question)
    print(f"Odpowiedź:\n{answer}")
    
    # Test 2: Propozycje potraw
    print("\n\n2. PROPOZYCJE POTRAW:")
    print("-" * 60)
    suggestions = get_dish_suggestions(query="obiad", max_dishes=3)
    for i, potrawa in enumerate(suggestions, 1):
        print(f"\n{i}. {potrawa.get('nazwa', 'Bez nazwy')}")
        print(f"   {potrawa.get('opis', 'Brak opisu')}")
        skladniki = potrawa.get('skladniki', [])
        if skladniki:
            print(f"   Składniki: {', '.join(skladniki)}")
    
    # Test 3: Lista zakupów
    print("\n\n3. LISTA ZAKUPÓW:")
    print("-" * 60)
    shopping_list = get_shopping_list(query="co potrzebuję na obiad?")
    produkty = shopping_list.get('produkty', [])
    if produkty:
        print("Produkty do zakupu:")
        for produkt in produkty:
            print(f"  - {produkt.get('nazwa')} - {produkt.get('ilosc')}")
    else:
        print("Masz wszystkie potrzebne produkty!")
    
    # Test 4: Użycie z context manager
    print("\n\n4. UŻYCIE Z CONTEXT MANAGER:")
    print("-" * 60)
    with BielikAssistant() as assistant:
        available = assistant.get_available_products()
        print(f"Dostępne produkty w magazynie: {len(available)}")
        for p in available[:5]:
            print(f"  - {p['nazwa']} ({p['kategoria']}) - {p['total_ilosc']}")
    
    print("\n" + "=" * 60)
    print("Test zakończony!")

if __name__ == "__main__":
    main()

