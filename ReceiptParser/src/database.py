import os
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey, Numeric, DateTime
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

# --- Konfiguracja Silnika Bazy Danych ---

# Zakładamy, że ten plik (database.py) znajduje się w folderze 'src'.
# Chcemy, żeby baza danych 'receipts.db' była w folderze 'data' na tym samym poziomie co 'src'.
# Budujemy ścieżkę w sposób niezależny od systemu operacyjnego.
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(project_root, "data", "receipts.db")
DATABASE_URL = f"sqlite:///{db_path}"

# Tworzymy silnik SQLAlchemy. `echo=True` wyświetli generowane zapytania SQL - przydatne do debugowania.
engine = create_engine(DATABASE_URL, echo=False)

# Baza dla naszych modeli deklaratywnych
Base = declarative_base()

# --- Modele Danych (Tabele) ---

class Sklep(Base):
    __tablename__ = 'sklepy'
    sklep_id = Column(Integer, primary_key=True)
    nazwa_sklepu = Column(String, nullable=False, unique=True)
    lokalizacja = Column(String)
    
    paragony = relationship("Paragon", back_populates="sklep")

class KategoriaProduktu(Base):
    __tablename__ = 'kategorie_produktow'
    kategoria_id = Column(Integer, primary_key=True)
    nazwa_kategorii = Column(String, nullable=False, unique=True)
    
    produkty = relationship("Produkt", back_populates="kategoria")

class Produkt(Base):
    __tablename__ = 'produkty'
    produkt_id = Column(Integer, primary_key=True)
    znormalizowana_nazwa = Column(String, nullable=False, unique=True)
    kategoria_id = Column(Integer, ForeignKey('kategorie_produktow.kategoria_id'))
    
    kategoria = relationship("KategoriaProduktu", back_populates="produkty")
    aliasy = relationship("AliasProduktu", back_populates="produkt")
    pozycje_paragonu = relationship("PozycjaParagonu", back_populates="produkt")
    stan_magazynowy = relationship("StanMagazynowy", back_populates="produkt", cascade="all, delete-orphan")

class AliasProduktu(Base):
    __tablename__ = 'aliasy_produktow'
    alias_id = Column(Integer, primary_key=True)
    nazwa_z_paragonu = Column(String, nullable=False, unique=True)
    produkt_id = Column(Integer, ForeignKey('produkty.produkt_id'), nullable=False)
    
    produkt = relationship("Produkt", back_populates="aliasy")

class Paragon(Base):
    __tablename__ = 'paragony'
    paragon_id = Column(Integer, primary_key=True)
    sklep_id = Column(Integer, ForeignKey('sklepy.sklep_id'))
    data_zakupu = Column(Date)
    suma_paragonu = Column(Numeric(10, 2))
    plik_zrodlowy = Column(String, nullable=False)
    
    sklep = relationship("Sklep", back_populates="paragony")
    pozycje = relationship("PozycjaParagonu", back_populates="paragon", cascade="all, delete-orphan")

class PozycjaParagonu(Base):
    __tablename__ = 'pozycje_paragonu'
    pozycja_id = Column(Integer, primary_key=True)
    paragon_id = Column(Integer, ForeignKey('paragony.paragon_id'), nullable=False)
    # produkt_id może być pusty, jeśli nie uda się go znormalizować od razu
    produkt_id = Column(Integer, ForeignKey('produkty.produkt_id')) 
    nazwa_z_paragonu_raw = Column(String, nullable=False)
    ilosc = Column(Numeric(10, 2), default=1.0)
    jednostka_miary = Column(String)
    cena_jednostkowa = Column(Numeric(10, 2))
    cena_calkowita = Column(Numeric(10, 2), nullable=False)
    rabat = Column(Numeric(10, 2))
    cena_po_rabacie = Column(Numeric(10, 2))
    
    paragon = relationship("Paragon", back_populates="pozycje")
    produkt = relationship("Produkt", back_populates="pozycje_paragonu")

class StanMagazynowy(Base):
    """Tabela do śledzenia stanu magazynowego produktów (ilość, data ważności)"""
    __tablename__ = 'stan_magazynowy'
    stan_id = Column(Integer, primary_key=True)
    produkt_id = Column(Integer, ForeignKey('produkty.produkt_id'), nullable=False)
    ilosc = Column(Numeric(10, 2), nullable=False, default=0.0)
    jednostka_miary = Column(String)  # np. 'szt', 'kg', 'l'
    data_waznosci = Column(Date)  # Data ważności produktu
    data_dodania = Column(DateTime, default=datetime.now)  # Kiedy produkt został dodany do magazynu
    pozycja_paragonu_id = Column(Integer, ForeignKey('pozycje_paragonu.pozycja_id'), nullable=True)  # Opcjonalne powiązanie z paragonem
    
    produkt = relationship("Produkt", back_populates="stan_magazynowy")
    pozycja_paragonu = relationship("PozycjaParagonu")

# --- Funkcja Inicjalizująca ---

def init_db():
    """
    Tworzy wszystkie zdefiniowane tabele w bazie danych, jeśli jeszcze nie istnieją.
    Upewnia się również, że folder 'data' istnieje.
    """
    data_dir = os.path.dirname(db_path)
    if not os.path.exists(data_dir):
        print(f"Tworzenie folderu na bazę danych: {data_dir}")
        os.makedirs(data_dir)
        
    print("Tworzenie tabel w bazie danych...")
    Base.metadata.create_all(bind=engine)
    print("Tabele zostały utworzone (jeśli nie istniały).")

# --- Uruchomienie Inicjalizacji ---

if __name__ == '__main__':
    print("Uruchomiono skrypt 'database.py' w celu inicjalizacji bazy danych.")
    init_db()
    print("Proces inicjalizacji zakończony.")