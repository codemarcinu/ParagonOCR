import click
from sqlalchemy.orm import sessionmaker, Session, joinedload
from typing import Callable, Optional

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
from .security import (
    validate_file_path,
    validate_llm_model,
    sanitize_path,
    sanitize_log_message,
    sanitize_ocr_text,
)
import os
import inspect

# --- GŁÓWNA LOGIKA PRZETWARZANIA (NIEZALEŻNA OD UI) ---


def _call_log_callback(
    log_callback: Callable,
    message: str,
    progress: Optional[float] = None,
    status: Optional[str] = None,
):
    """
    Wywołuje log_callback z obsługą zarówno starego (tylko message) jak i nowego formatu.
    
    Args:
        log_callback: Funkcja callback do wywołania
        message: Wiadomość do zalogowania
        progress: Postęp 0-100 lub -1 dla indeterminate
        status: Tekst statusu
    """
    import inspect
    sig = inspect.signature(log_callback)
    # Sprawdź czy callback przyjmuje więcej niż jeden argument
    if len(sig.parameters) > 1:
        # Nowy format - przekazujemy tuple
        log_callback(message, progress, status)
    else:
        # Stary format - tylko message
        log_callback(message)


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
    # Krok 0: Walidacja wejściowa
    temp_image_path = None
    try:
        # Waliduj ścieżkę pliku
        validated_path = validate_file_path(
            file_path,
            allowed_extensions=['.png', '.jpg', '.jpeg', '.pdf']
        )
        file_path = str(validated_path)
        
        # Waliduj model LLM
        llm_model = validate_llm_model(llm_model)
        
        # Krok 1: Parsowanie multimodalne jest teraz domyślnym i jedynym potokiem
        processing_file_path = file_path

        # Obsługa PDF
        if file_path.lower().endswith(".pdf"):
            _call_log_callback(log_callback, f"INFO: Wykryto plik PDF. Konwertuję na obraz...", progress=-1, status="Konwertowanie PDF...")
            temp_image_path = convert_pdf_to_image(file_path)
            if not temp_image_path:
                raise Exception("Nie udało się skonwertować pliku PDF na obraz.")
            processing_file_path = temp_image_path
            _call_log_callback(log_callback, f"INFO: PDF skonwertowany tymczasowo do: {sanitize_path(processing_file_path)}")

        if llm_model == "mistral-ocr":
            _call_log_callback(log_callback, "INFO: Używam Mistral OCR do ekstrakcji tekstu...", progress=-1, status="OCR (Mistral)...")
            mistral_client = MistralOCRClient()
            ocr_markdown = mistral_client.process_image(processing_file_path)

            if not ocr_markdown:
                raise Exception("Mistral OCR nie zwrócił wyniku.")

            _call_log_callback(log_callback, "INFO: Mistral OCR zakończył pracę. Przesyłam tekst do LLM (Bielik)...", progress=30, status="Przetwarzanie przez LLM...")
            parsed_data = parse_receipt_from_text(ocr_markdown)

        else:
            # Krok 1.5: Detekcja sklepu (Strategy Pattern) + Hybrid OCR
            _call_log_callback(log_callback, "INFO: Analizuję tekst z OCR (Tesseract)...", progress=-1, status="OCR (Tesseract)...")
            full_ocr_text = extract_text_from_image(processing_file_path)
            # Sanityzuj tekst OCR przed logowaniem (usuń wrażliwe dane)
            sanitized_ocr = sanitize_ocr_text(full_ocr_text, max_length=200)
            _call_log_callback(log_callback, f"--- WYNIK OCR (Tesseract) ---\n{sanitized_ocr}\n-----------------------------")

            # Do detekcji sklepu używamy próbki, ale do LLM przekażemy całość
            header_sample = full_ocr_text[:1000]

            strategy = get_strategy_for_store(header_sample)
            _call_log_callback(log_callback, f"INFO: Wybrano strategię: {strategy.__class__.__name__}")

            system_prompt = strategy.get_system_prompt()

            _call_log_callback(log_callback, f"INFO: Używam modelu LLM '{llm_model}' do przetworzenia obrazu (wspaganego OCR).", progress=30, status="Przetwarzanie przez LLM...")
            parsed_data = parse_receipt_with_llm(
                processing_file_path,
                llm_model,
                system_prompt_override=system_prompt,
                ocr_text=full_ocr_text,
            )

        # Jeśli używamy Mistral OCR, strategia mogła nie zostać jeszcze wybrana (bo pominęliśmy Tesseract)
        # Ale potrzebujemy jej do post-processingu.
        # Spróbujmy wykryć strategię na podstawie tekstu z Mistral OCR jeśli jeszcze jej nie mamy.
        if "strategy" not in locals():
            # Używamy początku tekstu z Mistral OCR do detekcji
            header_sample = (
                ocr_markdown[:1000]
                if "ocr_markdown" in locals() and ocr_markdown
                else ""
            )
            strategy = get_strategy_for_store(header_sample)
            log_callback(
                f"INFO: Wybrano strategię (na podstawie Mistral OCR): {strategy.__class__.__name__}"
            )

        # Sprzątanie po PDF - zawsze wykonaj cleanup, nawet przy błędach
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.unlink(temp_image_path)
                _call_log_callback(log_callback, "INFO: Usunięto tymczasowy plik obrazu.")
            except Exception as e:
                _call_log_callback(log_callback, f"OSTRZEŻENIE: Nie udało się usunąć pliku tymczasowego: {e}")

        if not parsed_data:
            raise Exception("Parsowanie za pomocą LLM nie zwróciło danych.")

        # Krok 1.6: Post-processing (Strategy Pattern)
        _call_log_callback(log_callback, "INFO: Uruchamiam post-processing specyficzny dla sklepu...", progress=60, status="Post-processing...")
        parsed_data = strategy.post_process(parsed_data)

        _call_log_callback(log_callback, "INFO: Dane z paragonu zostały pomyślnie sparsowane przez LLM.", progress=70, status="Dane sparsowane")

        # Krok 1.7: Manualna weryfikacja przez użytkownika (jeśli dostępna)
        if review_callback:
            _call_log_callback(log_callback, "INFO: Oczekiwanie na weryfikację użytkownika...", progress=70, status="Oczekiwanie na weryfikację...")
            reviewed_data = review_callback(parsed_data)
            if not reviewed_data:
                _call_log_callback(log_callback, "INFO: Użytkownik odrzucił zmiany. Anulowanie zapisu.")
                return
            parsed_data = reviewed_data
            _call_log_callback(log_callback, "INFO: Użytkownik zatwierdził dane (ewentualnie po edycji).", progress=80, status="Zapisuję do bazy...")

    except Exception as e:
        # Cleanup pliku tymczasowego nawet przy błędzie
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.unlink(temp_image_path)
            except Exception:
                pass
        _call_log_callback(log_callback, f"BŁĄD KRYTYCZNY na etapie parsowania LLM: {sanitize_log_message(str(e))}")
        _call_log_callback(log_callback, "Upewnij się, że serwer Ollama działa i model jest dostępny.")
        return

    # Krok 2: Zapis do bazy (ta logika jest już dobra i pozostaje bez zmian)
    if parsed_data:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        try:
            save_to_database(
                session, parsed_data, file_path, log_callback, prompt_callback
            )
            session.commit()
            _call_log_callback(log_callback, "--- Sukces! Dane zostały zapisane w bazie danych. ---", progress=100, status="Gotowy")
        except Exception as e:
            session.rollback()
            _call_log_callback(log_callback, f"BŁĄD KRYTYCZNY podczas zapisu do bazy danych: {e}")
        finally:
            session.close()
    else:
        _call_log_callback(log_callback, "BŁĄD: Nie udało się uzyskać danych do zapisu.")


def save_to_database(
    session: Session,
    parsed_data: ParsedData,
    file_path: str,
    log_callback: Callable,
    prompt_callback: Callable,
):
    _call_log_callback(log_callback, "INFO: Rozpoczynam zapis do bazy danych...", progress=80, status="Zapisuję do bazy...")
    sklep_name = parsed_data["sklep_info"]["nazwa"]
    sklep = session.query(Sklep).filter_by(nazwa_sklepu=sklep_name).first()
    if not sklep:
        _call_log_callback(log_callback, f"INFO: Sklep '{sklep_name}' nie istnieje. Tworzę nowy wpis.")
        sklep = Sklep(
            nazwa_sklepu=sklep_name,
            lokalizacja=parsed_data["sklep_info"]["lokalizacja"],
        )
        session.add(sklep)
        session.flush()
    else:
        _call_log_callback(log_callback, f"INFO: Znaleziono istniejący sklep '{sklep_name}' w bazie danych.")

    paragon = Paragon(
        sklep_id=sklep.sklep_id,
        data_zakupu=parsed_data["paragon_info"]["data_zakupu"].date(),
        suma_paragonu=parsed_data["paragon_info"]["suma_calkowita"],
        plik_zrodlowy=file_path,
    )

    _call_log_callback(log_callback, "INFO: Przetwarzam pozycje z paragonu...", progress=85, status="Przetwarzam pozycje...")
    total_items = len(parsed_data["pozycje"])
    for idx, item_data in enumerate(parsed_data["pozycje"]):
        # Aktualizuj postęp dla każdej pozycji (85-95%)
        if total_items > 0:
            progress = 85 + int((idx / total_items) * 10)
            _call_log_callback(log_callback, f"INFO: Przetwarzam pozycję {idx + 1}/{total_items}...", progress=progress, status=f"Przetwarzam pozycję {idx + 1}/{total_items}...")
        # Logika rabatów została przeniesiona do strategies.py (LidlStrategy)
        # Tutaj zakładamy, że dane są już wyczyszczone przez strategy.post_process

        product_id = resolve_product(
            session, item_data["nazwa_raw"], log_callback, prompt_callback
        )

        # Jeśli resolve_product zwrócił None (np. dla śmieci OCR, PTU, POMIŃ), pomijamy dodawanie
        if product_id is None:
            _call_log_callback(log_callback, f"   -> Pominięto pozycję: {item_data['nazwa_raw']}")
            continue

        pozycja = PozycjaParagonu(
            produkt_id=product_id,
            nazwa_z_paragonu_raw=item_data["nazwa_raw"],
            ilosc=item_data["ilosc"],
            jednostka_miary=item_data["jednostka"],
            cena_jednostkowa=item_data["cena_jedn"],
            cena_calkowita=item_data["cena_calk"],
            rabat=(
                item_data["rabat"] if item_data["rabat"] else 0
            ),  # Domyślnie 0 dla bazy
            cena_po_rabacie=item_data["cena_po_rab"],
        )
        paragon.pozycje.append(pozycja)
        session.flush()  # Flush aby mieć pozycja.pozycja_id
        
        # Dodaj produkt do magazynu (StanMagazynowy)
        data_waznosci = item_data.get("data_waznosci")
        # data_waznosci może być już typu date lub None
        
        # Sprawdź czy już istnieje stan magazynowy dla tego produktu z tą samą datą ważności
        # (lub bez daty ważności, jeśli data_waznosci jest None)
        existing_stan = None
        if data_waznosci:
            existing_stan = session.query(StanMagazynowy).filter_by(
                produkt_id=product_id,
                data_waznosci=data_waznosci
            ).first()
        else:
            # Jeśli brak daty ważności, szukaj wpisu bez daty ważności dla tego produktu
            existing_stan = session.query(StanMagazynowy).filter_by(
                produkt_id=product_id,
                data_waznosci=None
            ).first()
        
        if existing_stan:
            # Jeśli istnieje, zwiększ ilość
            existing_stan.ilosc += item_data["ilosc"]
            existing_stan.pozycja_paragonu_id = pozycja.pozycja_id
            jednostka_str = item_data.get("jednostka") or "szt"
            _call_log_callback(log_callback, f"   -> Zaktualizowano stan magazynowy: +{item_data['ilosc']} {jednostka_str}")
        else:
            # Jeśli nie istnieje, utwórz nowy wpis
            stan = StanMagazynowy(
                produkt_id=product_id,
                ilosc=item_data["ilosc"],
                jednostka_miary=item_data.get("jednostka"),
                data_waznosci=data_waznosci,
                pozycja_paragonu_id=pozycja.pozycja_id
            )
            session.add(stan)
            jednostka_str = item_data.get("jednostka") or "szt"
            _call_log_callback(log_callback, f"   -> Dodano do magazynu: {item_data['ilosc']} {jednostka_str}")

    session.add(paragon)
    _call_log_callback(log_callback, f"INFO: Przygotowano do zapisu 1 paragon z {len(paragon.pozycje)} pozycjami.", progress=95, status="Kończenie zapisu...")


def resolve_product(
    session: Session, raw_name: str, log_callback: Callable, prompt_callback: Callable
) -> int | None:
    # 1. Sprawdź Aliasy w Bazie (Najszybsze i Najpewniejsze)
    alias = (
        session.query(AliasProduktu)
        .options(joinedload(AliasProduktu.produkt))
        .filter_by(nazwa_z_paragonu=raw_name)
        .first()
    )
    if alias:
        _call_log_callback(log_callback, f"   -> Znaleziono alias (DB) dla '{raw_name}': '{alias.produkt.znormalizowana_nazwa}'")
        return alias.produkt_id

    _call_log_callback(log_callback, f"  ?? Nieznany produkt: '{raw_name}'")

    # 2. Sprawdź Reguły Statyczne (Oszczędność LLM)
    suggested_name = find_static_match(raw_name)
    source = "Reguły Statyczne"

    if suggested_name:
        _call_log_callback(log_callback, f"   -> Sugestia (Słownik): '{suggested_name}'")
    else:
        # 3. Zapytaj LLM z przykładami uczenia (Ostatnia deska ratunku)
        _call_log_callback(log_callback, "   -> Słownik pusty. Pytam LLM z przykładami uczenia...")
        
        # Pobierz przykłady uczenia z bazy danych
        from .llm import get_learning_examples
        learning_examples = get_learning_examples(raw_name, session, max_examples=5, min_similarity=30)
        
        if learning_examples:
            _call_log_callback(log_callback, f"   -> Znaleziono {len(learning_examples)} podobnych przykładów uczenia")
        
        suggested_name = get_llm_suggestion(raw_name, learning_examples=learning_examples)
        source = "LLM (z uczeniem)"
        if suggested_name:
            _call_log_callback(log_callback, f"   -> Sugestia (LLM): '{suggested_name}'")
        else:
            _call_log_callback(log_callback, "   -> Nie udało się uzyskać sugestii LLM.")

    # Obsługa przypadku "POMIŃ" (czy to ze słownika, czy z LLM)
    if suggested_name == "POMIŃ":
        _call_log_callback(log_callback, "   -> System zasugerował pominięcie tej pozycji.")
        # Zwracamy None - pozycja zostanie pominięta
        return None

    # 4. Weryfikacja Użytkownika (Prompt)
    prompt_text = f"Nieznany produkt (Sugerowany przez {source}: {suggested_name or 'Brak'}). Do jakiego produktu go przypisać?"

    normalized_name = prompt_callback(prompt_text, suggested_name or "", raw_name)

    # Jeśli użytkownik nie podał nazwy lub podał "POMIŃ", pomijamy pozycję
    if not normalized_name or normalized_name.strip().upper() == "POMIŃ":
        _call_log_callback(log_callback, "   -> Pominięto przypisanie produktu dla tej pozycji.")
        return None

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

    _call_log_callback(log_callback, f"   -> Kategoria: {kategoria_nazwa} | {freeze_info}")

    # Pobierz lub utwórz kategorię w bazie
    kategoria = (
        session.query(KategoriaProduktu)
        .filter_by(nazwa_kategorii=kategoria_nazwa)
        .first()
    )
    if not kategoria:
        _call_log_callback(log_callback, f"   -> Tworzę nową kategorię: '{kategoria_nazwa}'")
        kategoria = KategoriaProduktu(nazwa_kategorii=kategoria_nazwa)
        session.add(kategoria)
        session.flush()

    if not product:
        _call_log_callback(log_callback, f"   -> Tworzę nowy produkt w bazie: '{normalized_name}'")
        product = Produkt(
            znormalizowana_nazwa=normalized_name, kategoria_id=kategoria.kategoria_id
        )
        session.add(product)
        session.flush()
    else:
        _call_log_callback(log_callback, f"   -> Znaleziono istniejący produkt: '{normalized_name}'")
        # Opcjonalnie: Aktualizuj kategorię jeśli brakuje (dla starszych wpisów)
        if product.kategoria_id is None:
            product.kategoria_id = kategoria.kategoria_id
            _call_log_callback(log_callback, f"   -> Zaktualizowano kategorię produktu na: '{kategoria_nazwa}'")

    _call_log_callback(log_callback, f"   -> Tworzę nowy alias: '{raw_name}' -> '{normalized_name}'")
    new_alias = AliasProduktu(nazwa_z_paragonu=raw_name, produkt_id=product.produkt_id)
    session.add(new_alias)
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
    return click.prompt(text, default=default_value)


@click.group()
def cli():
    """Proste narzędzie CLI do parsowania paragonów i zapisywania ich do bazy danych."""
    pass


@cli.command()
def init_db_command():
    """Inicjalizuje bazę danych i tworzy wszystkie tabele."""
    click.echo("Rozpoczynam inicjalizację bazy danych...")
    init_db()
    
    # Uruchom migracje po inicjalizacji
    from .migrate_db import migrate_all
    click.echo("Sprawdzam i aktualizuję schemat bazy danych...")
    migrate_all()
    
    click.secho("Baza danych została pomyślnie zainicjalizowana!", fg="green")


@cli.command()
def migrate():
    """Wykonuje migracje bazy danych (dodaje brakujące kolumny)."""
    from .migrate_db import migrate_all
    migrate_all()


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
    try:
        # Waliduj model przed rozpoczęciem
        validated_model = validate_llm_model(llm_model)
        # Sanityzuj ścieżkę przed wyświetleniem
        safe_path = sanitize_path(file_path)
        click.secho(f"--- Rozpoczynam przetwarzanie pliku: {safe_path} ---", bold=True)
        run_processing_pipeline(file_path, validated_model, cli_log_callback, cli_prompt_callback)
    except ValueError as e:
        click.secho(f"BŁĄD WALIDACJI: {e}", fg="red", bold=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--pytanie",
    "question",
    required=True,
    type=str,
    help="Pytanie do asystenta Bielik (np. 'co mam do jedzenia?', 'co mogę zrobić na obiad?')",
)
def bielik(question: str):
    """Zadaje pytanie asystentowi AI Bielik o jedzenie, produkty i gotowanie."""
    from .bielik import ask_bielik
    
    click.secho("🦅 Bielik - Asystent Kulinarny", fg="cyan", bold=True)
    click.echo(f"Pytanie: {question}\n")
    
    try:
        answer = ask_bielik(question)
        click.echo(answer)
    except Exception as e:
        click.secho(f"BŁĄD: {e}", fg="red", bold=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--zapytanie",
    "query",
    required=False,
    type=str,
    help="Opcjonalne zapytanie (np. 'obiad', 'kolacja', 'coś szybkiego')",
)
@click.option(
    "--max",
    "max_dishes",
    default=5,
    type=int,
    help="Maksymalna liczba potraw do zaproponowania (domyślnie: 5)",
)
def potrawy(query: Optional[str], max_dishes: int):
    """Proponuje potrawy na podstawie dostępnych produktów w magazynie."""
    from .bielik import get_dish_suggestions
    
    click.secho("🍳 Bielik - Propozycje Potraw", fg="cyan", bold=True)
    if query:
        click.echo(f"Zapytanie: {query}\n")
    
    try:
        suggestions = get_dish_suggestions(query, max_dishes)
        
        if not suggestions:
            click.secho("Nie znaleziono żadnych propozycji.", fg="yellow")
            return
        
        for i, potrawa in enumerate(suggestions, 1):
            click.secho(f"\n{i}. {potrawa.get('nazwa', 'Bez nazwy')}", fg="green", bold=True)
            click.echo(f"   {potrawa.get('opis', 'Brak opisu')}")
            
            skladniki = potrawa.get('skladniki', [])
            if skladniki:
                click.echo(f"   Składniki: {', '.join(skladniki)}")
            
            czas = potrawa.get('czas_przygotowania')
            if czas:
                click.echo(f"   ⏱️  {czas}")
            
            trudnosc = potrawa.get('trudnosc')
            if trudnosc:
                click.echo(f"   📊 Trudność: {trudnosc}")
                
    except Exception as e:
        click.secho(f"BŁĄD: {e}", fg="red", bold=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--potrawa",
    "dish_name",
    required=False,
    type=str,
    help="Nazwa potrawy, dla której generować listę zakupów",
)
@click.option(
    "--zapytanie",
    "query",
    required=False,
    type=str,
    help="Zapytanie użytkownika (np. 'co potrzebuję na obiad?')",
)
def lista_zakupow(dish_name: Optional[str], query: Optional[str]):
    """Generuje listę zakupów na podstawie potrawy lub zapytania."""
    from .bielik import get_shopping_list
    
    click.secho("🛒 Bielik - Lista Zakupów", fg="cyan", bold=True)
    
    if not dish_name and not query:
        click.secho("BŁĄD: Musisz podać --potrawa lub --zapytanie", fg="red", bold=True)
        raise click.Abort()
    
    try:
        shopping_list = get_shopping_list(dish_name, query)
        
        if dish_name:
            click.echo(f"Potrawa: {dish_name}\n")
        
        produkty = shopping_list.get('produkty', [])
        
        if not produkty:
            click.secho("✅ Masz wszystkie potrzebne produkty w magazynie!", fg="green")
        else:
            # Grupuj produkty według kategorii
            by_category = {}
            for produkt in produkty:
                kategoria = produkt.get('kategoria', 'Inne')
                if kategoria not in by_category:
                    by_category[kategoria] = []
                by_category[kategoria].append(produkt)
            
            for kategoria, produkty_kat in by_category.items():
                click.secho(f"\n📦 {kategoria}:", fg="yellow", bold=True)
                for produkt in produkty_kat:
                    nazwa = produkt.get('nazwa', '')
                    ilosc = produkt.get('ilosc', '')
                    priorytet = produkt.get('priorytet', 'średni')
                    
                    priorytet_emoji = {
                        'wysoki': '🔴',
                        'średni': '🟡',
                        'niski': '🟢'
                    }.get(priorytet, '🟡')
                    
                    click.echo(f"   {priorytet_emoji} {nazwa} - {ilosc}")
        
        uwagi = shopping_list.get('uwagi')
        if uwagi:
            click.secho(f"\n💡 Uwagi: {uwagi}", fg="blue")
            
    except Exception as e:
        click.secho(f"BŁĄD: {e}", fg="red", bold=True)
        raise click.Abort()


if __name__ == "__main__":
    cli.add_command(init_db_command, name="init-db")
    cli()