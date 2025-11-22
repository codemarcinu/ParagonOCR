import click
from click.exceptions import Abort
from sqlalchemy.orm import sessionmaker, Session, joinedload
from typing import Callable

# Lokalne importy z naszego projektu
from .database import (
    engine,
    init_db,
    Sklep,
    Paragon,
    PozycjaParagonu,
    Produkt,
    AliasProduktu,
    KategoriaProduktu,
    StanMagazynowy,
)
from .knowledge_base import get_product_metadata
from .data_models import ParsedData
from .llm import get_llm_suggestion, parse_receipt_with_llm, parse_receipt_from_text
from .ocr import convert_pdf_to_image, extract_text_from_image
from .strategies import get_strategy_for_store
from .mistral_ocr import MistralOCRClient
from .normalization_rules import find_static_match
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
import os

# --- GŁÓWNA LOGIKA PRZETWARZANIA (NIEZALEŻNA OD UI) ---


def verify_math_consistency(parsed_data: ParsedData, log_callback: Callable) -> ParsedData:
    """
    Weryfikuje matematyczną spójność danych: czy ilość * cena_jedn == cena_calk.
    Jeśli nie, loguje ostrzeżenie i próbuje naprawić (może być ukryty rabat).
    """
    if not parsed_data or "pozycje" not in parsed_data:
        return parsed_data

    items = parsed_data["pozycje"]
    fixed_count = 0

    for item in items:
        try:
            # Konwersja na Decimal dla precyzji
            ilosc = Decimal(str(item.get("ilosc", 1.0)).replace(",", "."))
            cena_jedn = Decimal(str(item.get("cena_jedn", 0)).replace(",", "."))
            cena_calk = Decimal(str(item.get("cena_calk", 0)).replace(",", "."))
            rabat = Decimal(str(item.get("rabat", 0)).replace(",", "."))

            # Obliczona wartość (ilość * cena jednostkowa)
            obliczona = ilosc * cena_jedn

            # Pobierz cenę po rabacie (jeśli istnieje)
            cena_po_rab = Decimal(str(item.get("cena_po_rab", 0)).replace(",", "."))
            
            # Sprawdź zgodność matematyczną: ilość * cena_jedn powinna równać się cena_calk
            # (cena_calk to cena PRZED rabatem, jeśli jest rabat)
            # Tolerancja 0.01 PLN (błędy zaokrągleń)
            roznica = abs(obliczona - cena_calk)

            if roznica > Decimal("0.01"):
                nazwa = item.get("nazwa_raw", "Nieznany produkt")
                log_callback(
                    f"OSTRZEŻENIE: Niezgodność matematyczna dla '{nazwa}': "
                    f"{ilosc} * {cena_jedn} = {obliczona}, ale cena_calk = {cena_calk} (różnica: {roznica:.2f})"
                )

                # Jeśli cena_calk < obliczona, może to być błąd OCR - używamy obliczonej wartości
                if cena_calk < obliczona:
                    # Korekta: ustawiamy cena_calk na obliczoną wartość
                    log_callback(
                        f"  -> Korekta: ustawiam cena_calk na {obliczona:.2f} (było {cena_calk:.2f})"
                    )
                    item["cena_calk"] = str(obliczona)
                    # Jeśli nie ma rabatu, cena_po_rab = cena_calk
                    if rabat == 0:
                        if not item.get("cena_po_rab") or cena_po_rab == 0:
                            item["cena_po_rab"] = str(obliczona)
                    else:
                        # Jeśli jest rabat, przelicz cenę po rabacie
                        nowa_cena_po_rab = max(Decimal("0"), obliczona - rabat)
                        item["cena_po_rab"] = str(nowa_cena_po_rab)
                    fixed_count += 1
                else:
                    # Jeśli cena_calk > obliczona, może być błąd OCR w cenie jednostkowej
                    # lub może być ukryty rabat (ale tylko jeśli różnica jest znacząca)
                    if roznica > Decimal("1.00"):  # Różnica większa niż 1 PLN
                        log_callback(
                            f"  -> Korekta: ustawiam cena_calk na {obliczona:.2f} (było {cena_calk:.2f}) - prawdopodobny błąd OCR"
                        )
                        item["cena_calk"] = str(obliczona)
                        if rabat == 0:
                            if not item.get("cena_po_rab") or cena_po_rab == 0:
                                item["cena_po_rab"] = str(obliczona)
                        else:
                            nowa_cena_po_rab = max(Decimal("0"), obliczona - rabat)
                            item["cena_po_rab"] = str(nowa_cena_po_rab)
                        fixed_count += 1
                    # Jeśli różnica jest mała (< 1 PLN), ignorujemy - może być błąd zaokrąglenia
            
            # Walidacja: cena_po_rab nie może być ujemna
            final_cena_po_rab = Decimal(str(item.get("cena_po_rab", 0)).replace(",", "."))
            final_rabat = Decimal(str(item.get("rabat", 0)).replace(",", "."))
            final_cena_calk = Decimal(str(item.get("cena_calk", 0)).replace(",", "."))
            
            if final_cena_po_rab < 0:
                log_callback(
                    f"OSTRZEŻENIE: Ujemna cena po rabacie dla '{item.get('nazwa_raw', 'Nieznany')}': {final_cena_po_rab:.2f}. Korekta na 0."
                )
                item["cena_po_rab"] = "0.00"
                fixed_count += 1
            
            # Walidacja: rabat nie może być większy niż cena całkowita
            if final_rabat > final_cena_calk:
                log_callback(
                    f"OSTRZEŻENIE: Rabat ({final_rabat:.2f}) większy niż cena całkowita ({final_cena_calk:.2f}) dla '{item.get('nazwa_raw', 'Nieznany')}'. Korekta rabatu."
                )
                item["rabat"] = str(final_cena_calk)
                item["cena_po_rab"] = "0.00"
                fixed_count += 1

        except (ValueError, TypeError, InvalidOperation) as e:
            nazwa = item.get("nazwa_raw", "Nieznany produkt")
            log_callback(
                f"OSTRZEŻENIE: Nie udało się zweryfikować matematyki dla '{nazwa}': {e}"
            )
            continue

    if fixed_count > 0:
        log_callback(
            f"INFO: Naprawiono {fixed_count} pozycji z niezgodnościami matematycznymi."
        )

    return parsed_data


def run_processing_pipeline(
    file_path: str,
    llm_model: str,  # Teraz to jest parametr wymagany
    log_callback: Callable[[str], None],
    prompt_callback: Callable[[str, str, str], str],
    review_callback: Callable[[dict], dict | None] = None,
) -> None:
    """
    Uruchamia pełny potok przetwarzania paragonu, od odczytu po zapis do bazy.
    Funkcja jest niezależna od UI i przyjmuje callbacki do komunikacji z użytkownikiem.
    """
    # Krok 1: Parsowanie multimodalne jest teraz domyślnym i jedynym potokiem
    processing_file_path = file_path
    temp_image_path = None
    
    try:
        # Obsługa PDF
        if file_path.lower().endswith(".pdf"):
            log_callback(f"INFO: Wykryto plik PDF. Konwertuję na obraz...")
            temp_image_path = convert_pdf_to_image(file_path)
            if not temp_image_path:
                raise Exception("Nie udało się skonwertować pliku PDF na obraz.")
            processing_file_path = temp_image_path
            log_callback(
                f"INFO: PDF skonwertowany tymczasowo do: {processing_file_path}"
            )

        if llm_model == "mistral-ocr":
            log_callback("INFO: Używam Mistral OCR do ekstrakcji tekstu...")
            mistral_client = MistralOCRClient()
            ocr_markdown = mistral_client.process_image(processing_file_path)

            if not ocr_markdown:
                raise Exception("Mistral OCR nie zwrócił wyniku.")

            log_callback(
                "INFO: Mistral OCR zakończył pracę. Przesyłam tekst do LLM (Bielik)..."
            )
            
            # Detekcja strategii na podstawie tekstu z Mistral OCR
            header_sample = ocr_markdown[:1000] if ocr_markdown else ""
            strategy = get_strategy_for_store(header_sample)
            log_callback(f"INFO: Wybrano strategię (na podstawie Mistral OCR): {strategy.__class__.__name__}")
            system_prompt = strategy.get_system_prompt()
            
            parsed_data = parse_receipt_from_text(ocr_markdown, system_prompt_override=system_prompt)

        else:
            # Krok 1.5: Detekcja sklepu (Strategy Pattern) + Hybrid OCR
            log_callback("INFO: Analizuję tekst z OCR (Tesseract)...")
            full_ocr_text = extract_text_from_image(processing_file_path)
            log_callback(
                f"--- WYNIK OCR (Tesseract) ---\n{full_ocr_text}\n-----------------------------"
            )

            # Do detekcji sklepu używamy próbki, ale do LLM przekażemy całość
            header_sample = full_ocr_text[:1000]

            strategy = get_strategy_for_store(header_sample)
            log_callback(f"INFO: Wybrano strategię: {strategy.__class__.__name__}")

            system_prompt = strategy.get_system_prompt()

            log_callback(
                f"INFO: Używam modelu LLM '{llm_model}' do przetworzenia obrazu (wspaganego OCR)."
            )
            parsed_data = parse_receipt_with_llm(
                processing_file_path,
                llm_model,
                system_prompt_override=system_prompt,
                ocr_text=full_ocr_text,
            )

        # Strategia powinna być już wybrana wcześniej (dla Mistral OCR lub Tesseract)

        if not parsed_data:
            raise Exception("Parsowanie za pomocą LLM nie zwróciło danych.")

        # Krok 1.6: Post-processing (Strategy Pattern)
        log_callback("INFO: Uruchamiam post-processing specyficzny dla sklepu...")
        # Przekaż tekst OCR do post_process (jeśli dostępny)
        ocr_text_for_post_process = None
        if llm_model == "mistral-ocr":
            ocr_text_for_post_process = ocr_markdown
        else:
            ocr_text_for_post_process = full_ocr_text if 'full_ocr_text' in locals() else None
        parsed_data = strategy.post_process(parsed_data, ocr_text=ocr_text_for_post_process)

        # Krok 1.6.5: Matematyczna weryfikacja (sanity check)
        log_callback("INFO: Weryfikuję matematyczną spójność danych...")
        parsed_data = verify_math_consistency(parsed_data, log_callback)

        log_callback("INFO: Dane z paragonu zostały pomyślnie sparsowane przez LLM.")

        # Krok 1.7: Manualna weryfikacja przez użytkownika (jeśli dostępna)
        if review_callback:
            log_callback("INFO: Oczekiwanie na weryfikację użytkownika...")
            reviewed_data = review_callback(parsed_data)
            if not reviewed_data:
                log_callback("INFO: Użytkownik odrzucił zmiany. Anulowanie zapisu.")
                return
            parsed_data = reviewed_data
            log_callback("INFO: Użytkownik zatwierdził dane (ewentualnie po edycji).")

    except Exception as e:
        log_callback(f"BŁĄD KRYTYCZNY na etapie parsowania LLM: {e}")
        log_callback("Upewnij się, że serwer Ollama działa i model jest dostępny.")
        return
    finally:
        # Sprzątanie po PDF - zawsze wykonujemy, nawet w przypadku błędu
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
                log_callback("INFO: Usunięto tymczasowy plik obrazu.")
            except OSError as e:
                log_callback(f"OSTRZEŻENIE: Nie udało się usunąć tymczasowego pliku {temp_image_path}: {e}")

    # Krok 2: Zapis do bazy (ta logika jest już dobra i pozostaje bez zmian)
    if parsed_data:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        try:
            save_to_database(
                session, parsed_data, file_path, log_callback, prompt_callback
            )
            session.commit()
            log_callback("--- Sukces! Dane zostały zapisane w bazie danych. ---")
        except Exception as e:
            session.rollback()
            log_callback(f"BŁĄD KRYTYCZNY podczas zapisu do bazy danych: {e}")
        finally:
            session.close()
    else:
        log_callback("BŁĄD: Nie udało się uzyskać danych do zapisu.")


def save_to_database(
    session: Session,
    parsed_data: ParsedData,
    file_path: str,
    log_callback: Callable,
    prompt_callback: Callable,
):
    log_callback("INFO: Rozpoczynam zapis do bazy danych...")
    sklep_name = parsed_data["sklep_info"]["nazwa"]
    sklep = session.query(Sklep).filter_by(nazwa_sklepu=sklep_name).first()
    if not sklep:
        log_callback(f"INFO: Sklep '{sklep_name}' nie istnieje. Tworzę nowy wpis.")
        sklep = Sklep(
            nazwa_sklepu=sklep_name,
            lokalizacja=parsed_data["sklep_info"]["lokalizacja"],
        )
        session.add(sklep)
        session.flush()
    else:
        log_callback(
            f"INFO: Znaleziono istniejący sklep '{sklep_name}' w bazie danych."
        )

    # Walidacja danych przed zapisem
    data_zakupu = parsed_data["paragon_info"]["data_zakupu"]
    if not data_zakupu:
        raise ValueError("Brak daty zakupu w danych paragonu. Nie można zapisać do bazy.")
    
    # Konwersja datetime na date jeśli potrzeba
    if isinstance(data_zakupu, datetime):
        data_zakupu = data_zakupu.date()
    elif not isinstance(data_zakupu, date):
        raise ValueError(f"Nieprawidłowy format daty zakupu: {type(data_zakupu)}")

    paragon = Paragon(
        sklep_id=sklep.sklep_id,
        data_zakupu=data_zakupu,
        suma_paragonu=parsed_data["paragon_info"]["suma_calkowita"],
        plik_zrodlowy=file_path,
    )

    log_callback("INFO: Przetwarzam pozycje z paragonu...")
    
    # Optymalizacja N+1: Batch loading aliasów dla wszystkich pozycji
    raw_names = [item["nazwa_raw"] for item in parsed_data["pozycje"]]
    aliases = (
        session.query(AliasProduktu)
        .options(joinedload(AliasProduktu.produkt))
        .filter(AliasProduktu.nazwa_z_paragonu.in_(raw_names))
        .all()
    )
    alias_map = {a.nazwa_z_paragonu: a.produkt_id for a in aliases}
    log_callback(f"INFO: Załadowano {len(alias_map)} aliasów z bazy danych (batch loading).")
    
    for item_data in parsed_data["pozycje"]:
        # Logika rabatów została przeniesiona do strategies.py (LidlStrategy)
        # Tutaj zakładamy, że dane są już wyczyszczone przez strategy.post_process

        product_id = resolve_product(
            session, item_data["nazwa_raw"], log_callback, prompt_callback, alias_map=alias_map
        )

        # Jeśli resolve_product zwrócił None (np. dla śmieci OCR), pomijamy dodawanie
        # UWAGA: Produkt "POMIŃ" jest specjalnym produktem, który powinien być zapisany
        if product_id is None:
            log_callback(f"   -> Pominięto pozycję: {item_data['nazwa_raw']}")
            continue

        # Upewniamy się, że cena_po_rabacie jest zawsze wypełniona
        cena_calk = item_data["cena_calk"]
        cena_po_rab = item_data.get("cena_po_rab")
        
        # Konwersja na Decimal dla porównań
        try:
            cena_po_rab_decimal = Decimal(str(cena_po_rab).replace(",", ".")) if cena_po_rab else None
        except (ValueError, TypeError):
            cena_po_rab_decimal = None
        
        # Jeśli cena po rabacie nie została wyliczona (brak rabatu) lub jest ujemna, to jest równa cenie całkowitej
        if not cena_po_rab_decimal or cena_po_rab_decimal <= 0:
            cena_po_rab = cena_calk
        else:
            cena_po_rab = cena_po_rab_decimal

        pozycja = PozycjaParagonu(
            produkt_id=product_id,
            nazwa_z_paragonu_raw=item_data["nazwa_raw"],
            ilosc=item_data["ilosc"],
            jednostka_miary=item_data["jednostka"],
            cena_jednostkowa=item_data["cena_jedn"],
            cena_calkowita=cena_calk,
            rabat=(
                item_data["rabat"] if item_data["rabat"] else 0
            ),  # Domyślnie 0 dla bazy
            cena_po_rabacie=cena_po_rab,
        )
        paragon.pozycje.append(pozycja)
        session.flush()  # Flush, aby uzyskać pozycja_id
        
        # Dodaj stan magazynowy, jeśli podano datę ważności
        data_waznosci = item_data.get("data_waznosci")
        if data_waznosci:
            stan = StanMagazynowy(
                produkt_id=product_id,
                ilosc=item_data["ilosc"],
                jednostka_miary=item_data.get("jednostka", "szt"),
                data_waznosci=data_waznosci,
                pozycja_paragonu_id=pozycja.pozycja_id,
            )
            session.add(stan)
            log_callback(f"   -> Dodano do magazynu: {item_data['ilosc']} {item_data.get('jednostka', 'szt')} (ważność: {data_waznosci})")
        else:
            log_callback(f"   -> Uwaga: Brak daty ważności dla produktu '{item_data['nazwa_raw']}' - nie dodano do magazynu")

    session.add(paragon)
    log_callback(
        f"INFO: Przygotowano do zapisu 1 paragon z {len(paragon.pozycje)} pozycjami."
    )


def resolve_product(
    session: Session, raw_name: str, log_callback: Callable, prompt_callback: Callable, alias_map: dict = None
) -> int | None:
    # 1. Sprawdź Aliasy w Bazie (Najszybsze i Najpewniejsze)
    # Używamy cache jeśli dostępny (batch loading), w przeciwnym razie zapytanie do DB
    if alias_map is not None and raw_name in alias_map:
        product_id = alias_map[raw_name]
        # Pobierz nazwę produktu dla logowania
        produkt = session.query(Produkt).filter_by(produkt_id=product_id).first()
        if produkt:
            log_callback(
                f"   -> Znaleziono alias (cache) dla '{raw_name}': '{produkt.znormalizowana_nazwa}'"
            )
        return product_id
    
    # Fallback: zapytanie do bazy jeśli nie ma w cache
    alias = (
        session.query(AliasProduktu)
        .options(joinedload(AliasProduktu.produkt))
        .filter_by(nazwa_z_paragonu=raw_name)
        .first()
    )
    if alias:
        log_callback(
            f"   -> Znaleziono alias (DB) dla '{raw_name}': '{alias.produkt.znormalizowana_nazwa}'"
        )
        return alias.produkt_id

    log_callback(f"  ?? Nieznany produkt: '{raw_name}'")

    # 2. Sprawdź Reguły Statyczne (Oszczędność LLM)
    suggested_name = find_static_match(raw_name)
    source = "Reguły Statyczne"

    if suggested_name:
        log_callback(f"   -> Sugestia (Słownik): '{suggested_name}'")
    else:
        # 3. Zapytaj LLM (Ostatnia deska ratunku)
        log_callback("   -> Słownik pusty. Pytam LLM...")
        suggested_name = get_llm_suggestion(raw_name)
        source = "LLM"
        if suggested_name:
            # Dodatkowe czyszczenie na wypadek, gdyby LLM zwróciło coś z prefiksem
            from .llm import clean_llm_suggestion
            suggested_name = clean_llm_suggestion(suggested_name)
            log_callback(f"   -> Sugestia (LLM): '{suggested_name}'")
        else:
            log_callback("   -> Nie udało się uzyskać sugestii LLM.")

    # Obsługa przypadku "POMIŃ" (czy to ze słownika, czy z LLM)
    # "POMIŃ" to specjalny produkt, który powinien być zapisany, ale oznacza, że pozycja nie jest produktem spożywczym
    if suggested_name == "POMIŃ":
        log_callback("   -> System zasugerował oznaczenie jako 'POMIŃ' (pozycja nie jest produktem spożywczym).")
        # Kontynuujemy, aby zapisać tę pozycję z produktem "POMIŃ"

    # 4. Weryfikacja Użytkownika (Prompt)
    prompt_text = f"Nieznany produkt (Sugerowany przez {source}: {suggested_name or 'Brak'}). Do jakiego produktu go przypisać?"

    # Jeśli mamy sugestię ze słownika, możemy chcieć ją pominąć w pytaniu użytkownika (auto-akceptacja)
    # Ale dla bezpieczeństwa na początku zostawmy prompt.
    normalized_name = prompt_callback(prompt_text, suggested_name or "", raw_name)

    # Walidacja nazwy produktu
    if not normalized_name:
        log_callback("   -> Pominięto przypisanie produktu dla tej pozycji.")
        return None
    
    # Czyszczenie i walidacja nazwy
    normalized_name = normalized_name.strip()
    if not normalized_name or len(normalized_name) == 0:
        log_callback("   -> Pusta nazwa produktu, pomijam przypisanie.")
        return None
    
    # Sprawdzenie maksymalnej długości (np. 200 znaków)
    if len(normalized_name) > 200:
        log_callback(f"   -> OSTRZEŻENIE: Nazwa produktu jest za długa ({len(normalized_name)} znaków), obcinam do 200.")
        normalized_name = normalized_name[:200].strip()

    # ... Dalsza część kodu (Zapis do bazy Produkt/Alias) bez zmian ...
    product = (
        session.query(Produkt).filter_by(znormalizowana_nazwa=normalized_name).first()
    )

    # Pobierz metadane z bazy wiedzy
    metadata = get_product_metadata(normalized_name)
    kategoria_nazwa = metadata["kategoria"]
    can_freeze = metadata["can_freeze"]

    # Info dla usera
    freeze_info = "❄️ MOŻNA MROZIĆ" if can_freeze else "🚫 NIE MROZIĆ"
    if can_freeze is None:
        freeze_info = ""  # Brak danych

    log_callback(f"   -> Kategoria: {kategoria_nazwa} | {freeze_info}")

    # Pobierz lub utwórz kategorię w bazie
    kategoria = (
        session.query(KategoriaProduktu)
        .filter_by(nazwa_kategorii=kategoria_nazwa)
        .first()
    )
    if not kategoria:
        log_callback(f"   -> Tworzę nową kategorię: '{kategoria_nazwa}'")
        kategoria = KategoriaProduktu(nazwa_kategorii=kategoria_nazwa)
        session.add(kategoria)
        session.flush()

    if not product:
        log_callback(f"   -> Tworzę nowy produkt w bazie: '{normalized_name}'")
        product = Produkt(
            znormalizowana_nazwa=normalized_name, kategoria_id=kategoria.kategoria_id
        )
        session.add(product)
        session.flush()
    else:
        log_callback(f"   -> Znaleziono istniejący produkt: '{normalized_name}'")
        # Opcjonalnie: Aktualizuj kategorię jeśli brakuje (dla starszych wpisów)
        if product.kategoria_id is None:
            product.kategoria_id = kategoria.kategoria_id
            log_callback(
                f"   -> Zaktualizowano kategorię produktu na: '{kategoria_nazwa}'"
            )

    # Sprawdź, czy alias już istnieje (w bazie lub w sesji)
    existing_alias = (
        session.query(AliasProduktu)
        .filter_by(nazwa_z_paragonu=raw_name)
        .first()
    )
    if existing_alias:
        log_callback(f"   -> Alias '{raw_name}' już istnieje. Pomijam tworzenie nowego.")
        if existing_alias.produkt_id != product.produkt_id:
            log_callback(f"   -> OSTRZEŻENIE: Istniejący alias wskazuje na inny produkt (ID: {existing_alias.produkt_id}). Aktualizuję na {product.produkt_id}.")
            existing_alias.produkt_id = product.produkt_id
    else:
        # Sprawdź też w sesji (pending objects) - może alias został dodany wcześniej w tej samej sesji
        for obj in session.new:
            if isinstance(obj, AliasProduktu) and obj.nazwa_z_paragonu == raw_name:
                log_callback(f"   -> Alias '{raw_name}' jest już w sesji (pending). Pomijam tworzenie nowego.")
                return product.produkt_id
        
        log_callback(f"   -> Tworzę nowy alias: '{raw_name}' -> '{normalized_name}'")
        new_alias = AliasProduktu(nazwa_z_paragonu=raw_name, produkt_id=product.produkt_id)
        session.add(new_alias)
        session.flush()  # Flush, aby kolejne zapytania widziały nowy alias
    return product.produkt_id


# --- WARSTWA INTERFEJSU KONSOLOWEGO (CLI) ---


def cli_log_callback(message: str):
    """Callback do logowania dla trybu CLI."""
    if message.startswith("BŁĄD"):
        click.secho(message, fg="red")
    elif message.startswith("--- Sukces!"):
        click.secho(message, fg="green", bold=True)
    else:
        click.echo(message)


def cli_prompt_callback(prompt_text: str, default_value: str, raw_name: str) -> str:
    """Callback do zadawania pytań dla trybu CLI."""
    text = f"{prompt_text} (Enter by zaakceptować sugestię, zostaw puste by pominąć)"
    try:
        return click.prompt(text, default=default_value)
    except (Abort, EOFError, KeyboardInterrupt):
        # Jeśli nie ma interaktywnego terminala, używamy wartości domyślnej
        cli_log_callback(f"INFO: Brak interaktywnego terminala. Używam wartości domyślnej: '{default_value}'")
        return default_value


@click.group()
def cli():
    """Proste narzędzie CLI do parsowania paragonów i zapisywania ich do bazy danych."""
    pass


@cli.command()
def init_db_command():
    """Inicjalizuje bazę danych i tworzy wszystkie tabele."""
    click.echo("Rozpoczynam inicjalizację bazy danych...")
    init_db()
    click.secho("Baza danych została pomyślnie zainicjalizowana!", fg="green")


@cli.command()
@click.option(
    "--file",
    "file_path",
    required=True,
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Ścieżka do pliku z paragonem (PDF, PNG, JPG).",
)
@click.option(
    "--llm",
    "llm_model",
    required=True,
    type=str,
    help="Nazwa modelu LLM (np. llava:latest) do użycia.",
)
def process(file_path: str, llm_model: str):
    """Przetwarza plik z paragonem, parsuje go i zapisuje do bazy danych."""
    click.secho(f"--- Rozpoczynam przetwarzanie pliku: {file_path} ---", bold=True)
    run_processing_pipeline(file_path, llm_model, cli_log_callback, cli_prompt_callback)


if __name__ == "__main__":
    cli.add_command(init_db_command, name="init-db")
    cli()
