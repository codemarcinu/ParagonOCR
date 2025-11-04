
import click
from sqlalchemy.orm import sessionmaker, Session, joinedload
from typing import Callable

# Lokalne importy z naszego projektu
from .ocr import extract_text_from_file
from .database import engine, init_db, Sklep, Paragon, PozycjaParagonu, Produkt, AliasProduktu
from .parsers import BaseParser, ParsedData
from .parsers.lidl_parser import LidlParser
from .llm import get_llm_suggestion, parse_receipt_with_llm

# --- GŁÓWNA LOGIKA PRZETWARZANIA (NIEZALEŻNA OD UI) ---

def run_processing_pipeline(
    file_path: str,
    llm_model: str | None,
    log_callback: Callable[[str], None],
    prompt_callback: Callable[[str, str, str], str]
) -> None:
    """
    Uruchamia pełny potok przetwarzania paragonu, od odczytu po zapis do bazy.
    Funkcja jest niezależna od UI i przyjmuje callbacki do komunikacji z użytkownikiem.
    """
    try:
        if llm_model:
            log_callback(f"INFO: Używam modelu LLM '{llm_model}' do przetworzenia obrazu.")
            parsed_data = parse_receipt_with_llm(file_path, llm_model)
            if not parsed_data:
                raise Exception("Parsowanie za pomocą LLM nie zwróciło danych.")
            log_callback("INFO: Dane z paragonu zostały pomyślnie sparsowane przez LLM.")
        else:
            log_callback("INFO: Używam klasycznego OCR (Tesseract) i parserów regex.")
            raw_text = extract_text_from_file(file_path)
            if not raw_text.strip():
                raise Exception("OCR nie zwrócił żadnego tekstu.")

            parser = get_parser(raw_text, log_callback)
            parsed_data = parser.parse(raw_text)
            log_callback("INFO: Dane z paragonu zostały pomyślnie sparsowane.")

    except Exception as e:
        log_callback(f"BŁĄD KRYTYCZNY na etapie OCR/Parsowania: {e}")
        return

    if parsed_data:
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        try:
            save_to_database(session, parsed_data, file_path, log_callback, prompt_callback)
            session.commit()
            log_callback("--- Sukces! Dane zostały zapisane w bazie danych. ---")
        except Exception as e:
            session.rollback()
            log_callback(f"BŁĄD KRYTYCZNY podczas zapisu do bazy danych: {e}")
        finally:
            session.close()
    else:
        log_callback("BŁĄD: Nie udało się uzyskać danych do zapisu.")

def get_parser(raw_text: str, log_callback: Callable) -> BaseParser:
    text_lower = raw_text.lower()
    if 'lidl' in text_lower:
        log_callback("INFO: Wykryto sklep Lidl, używam dedykowanego parsera.")
        return LidlParser()
    else:
        raise ValueError("Nie udało się zidentyfikować sklepu na podstawie tekstu paragonu.")

def save_to_database(session: Session, parsed_data: ParsedData, file_path: str, log_callback: Callable, prompt_callback: Callable):
    log_callback("INFO: Rozpoczynam zapis do bazy danych...")
    sklep_name = parsed_data['sklep_info']['nazwa']
    sklep = session.query(Sklep).filter_by(nazwa_sklepu=sklep_name).first()
    if not sklep:
        log_callback(f"INFO: Sklep '{sklep_name}' nie istnieje. Tworzę nowy wpis.")
        sklep = Sklep(nazwa_sklepu=sklep_name, lokalizacja=parsed_data['sklep_info']['lokalizacja'])
        session.add(sklep)
        session.flush()
    else:
        log_callback(f"INFO: Znaleziono istniejący sklep '{sklep_name}' w bazie danych.")

    paragon = Paragon(
        sklep_id=sklep.sklep_id,
        data_zakupu=parsed_data['paragon_info']['data_zakupu'].date(),
        suma_paragonu=parsed_data['paragon_info']['suma_calkowita'],
        plik_zrodlowy=file_path
    )

    log_callback("INFO: Przetwarzam pozycje z paragonu...")
    for item_data in parsed_data['pozycje']:
        product_id = resolve_product(session, item_data['nazwa_raw'], log_callback, prompt_callback)
        pozycja = PozycjaParagonu(
            produkt_id=product_id,
            nazwa_z_paragonu_raw=item_data['nazwa_raw'],
            ilosc=item_data['ilosc'],
            jednostka_miary=item_data['jednostka'],
            cena_jednostkowa=item_data['cena_jedn'],
            cena_calkowita=item_data['cena_calk'],
            rabat=item_data['rabat'] if item_data['rabat'] else None,
            cena_po_rabacie=item_data['cena_po_rab']
        )
        paragon.pozycje.append(pozycja)

    session.add(paragon)
    log_callback(f"INFO: Przygotowano do zapisu 1 paragon z {len(paragon.pozycje)} pozycjami.")

def resolve_product(session: Session, raw_name: str, log_callback: Callable, prompt_callback: Callable) -> int:
    alias = session.query(AliasProduktu).options(joinedload(AliasProduktu.produkt)).filter_by(nazwa_z_paragonu=raw_name).first()
    if alias:
        log_callback(f"   -> Znaleziono alias dla '{raw_name}': '{alias.produkt.znormalizowana_nazwa}'")
        return alias.produkt_id

    log_callback(f"  ?? Nieznany produkt: '{raw_name}'")
    suggested_name = get_llm_suggestion(raw_name)
    if suggested_name:
        log_callback(f"   -> Sugestia LLM: '{suggested_name}'")
    else:
        log_callback("   -> Nie udało się uzyskać sugestii LLM.")

    prompt_text = "Do jakiego produktu go przypisać?"
    normalized_name = prompt_callback(prompt_text, suggested_name or "", raw_name)

    if not normalized_name:
        log_callback("   -> Pominięto przypisanie produktu dla tej pozycji.")
        return None

    product = session.query(Produkt).filter_by(znormalizowana_nazwa=normalized_name).first()
    if not product:
        log_callback(f"   -> Tworzę nowy produkt w bazie: '{normalized_name}'")
        product = Produkt(znormalizowana_nazwa=normalized_name, kategoria_id=None)
        session.add(product)
        session.flush()
    else:
        log_callback(f"   -> Znaleziono istniejący produkt: '{normalized_name}'")

    log_callback(f"   -> Tworzę nowy alias: '{raw_name}' -> '{normalized_name}'")
    new_alias = AliasProduktu(nazwa_z_paragonu=raw_name, produkt_id=product.produkt_id)
    session.add(new_alias)
    return product.produkt_id

# --- WARSTWA INTERFEJSU KONSOLOWEGO (CLI) ---

def cli_log_callback(message: str):
    """Callback do logowania dla trybu CLI."""
    # Używa secho dla kolorowania, jeśli to błąd/sukces
    if message.startswith("BŁĄD"):
        click.secho(message, fg='red')
    elif message.startswith("--- Sukces!"):
        click.secho(message, fg='green', bold=True)
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
    click.secho("Baza danych została pomyślnie zainicjalizowana!", fg='green')

@cli.command()
@click.option('--file', 'file_path', required=True, type=click.Path(exists=True, dir_okay=False, resolve_path=True), help="Ścieżka do pliku z paragonem (PDF, PNG, JPG).")
@click.option('--llm', 'llm_model', type=str, help='Użyj modelu LLM (np. llava) do parsowania obrazu.')
def process(file_path: str, llm_model: str = None):
    """Przetwarza plik z paragonem, parsuje go i zapisuje do bazy danych."""
    click.secho(f"--- Rozpoczynam przetwarzanie pliku: {file_path} ---", bold=True)
    run_processing_pipeline(file_path, llm_model, cli_log_callback, cli_prompt_callback)

if __name__ == '__main__':
    cli.add_command(init_db_command, name='init-db')
    cli()
