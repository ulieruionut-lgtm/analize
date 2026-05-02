"""Modele Pydantic și descrieri tabele (pentru documentație)."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

# --- Reține: tabelele reale sunt create din sql/001_schema.sql ---
# Pacient
class PacientBase(BaseModel):
    cnp: str
    nume: str
    prenume: Optional[str] = None


class PacientCreate(PacientBase):
    pass


class Pacient(PacientBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


# Buletin analize
class BuletinBase(BaseModel):
    data_buletin: Optional[datetime] = None
    laborator: Optional[str] = None
    fisier_original: Optional[str] = None


class BuletinCreate(BuletinBase):
    pacient_id: int


class Buletin(BuletinBase):
    id: int
    pacient_id: int
    created_at: datetime
    class Config:
        from_attributes = True


# Rezultat analiză
class RezultatAnalizaBase(BaseModel):
    analiza_standard_id: int
    valoare: Optional[float] = None
    valoare_text: Optional[str] = None
    unitate: Optional[str] = None
    interval_min: Optional[float] = None
    interval_max: Optional[float] = None
    flag: Optional[str] = None  # H, L, etc.


class RezultatAnalizaCreate(RezultatAnalizaBase):
    buletin_id: int


class RezultatAnaliza(RezultatAnalizaBase):
    id: int
    buletin_id: int
    created_at: datetime
    class Config:
        from_attributes = True


# Răspuns API
class RezultatParsat(BaseModel):
    analiza_standard_id: Optional[int] = None
    denumire_raw: Optional[str] = None
    valoare: Optional[float] = None
    valoare_text: Optional[str] = None
    unitate: Optional[str] = None
    interval_min: Optional[float] = None
    interval_max: Optional[float] = None
    flag: Optional[str] = None
    categorie: Optional[str] = None   # sectiunea din buletin (ex: Hemoleucograma, Biochimie)
    ordine: Optional[int] = None      # pozitia in PDF (pentru sortare in ordinea originala)
    # Microbiologie / meta (serializată JSON în coloana rezultat_meta la salvare)
    organism_raw: Optional[str] = None
    rezultat_tip: Optional[str] = None  # ex. "microbiology"
    needs_review: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    ocr_confidence: Optional[float] = None
    # Completare din buletin anterior (aceeași dată clinică); meta la salvare în rezultat_meta
    gap_fill_source_buletin_id: Optional[int] = None


class PatientParsed(BaseModel):
    cnp: str
    nume: str
    prenume: Optional[str] = None
    rezultate: list[RezultatParsat] = []


# --- Modele pentru validare endpoint-uri POST ---

class AdaugaAnalizaStdBody(BaseModel):
    denumire: str = Field(..., min_length=2, max_length=255)
    cod: str = Field(..., min_length=1, max_length=64)
    categorie: Optional[str] = Field(None, max_length=128)
    unitate: Optional[str] = Field(None, max_length=64)


class AdaugaRezultatBody(BaseModel):
    denumire_raw: str = Field(..., min_length=1, max_length=255)
    valoare: float
    unitate: Optional[str] = Field(None, max_length=64)
    flag: Optional[str] = Field(None, max_length=16)
    analiza_standard_id: Optional[int] = None


class AprobaAliasBody(BaseModel):
    analiza_standard_id: int
    denumire_raw: Optional[str] = Field(None, max_length=255)
    necunoscuta_id: Optional[int] = None


class AprobaAliasBulkBody(BaseModel):
    analiza_standard_id: int
    necunoscuta_ids: Optional[list[int]] = None
    ids: Optional[list[int]] = None


class SugestiiLlmNecunoscuteBody(BaseModel):
    limit: int = Field(default=120, ge=1, le=250)
    ids: Optional[list[int]] = None


class ActualizeazaPacientBody(BaseModel):
    nume: str = Field(..., min_length=2, max_length=128)
    prenume: Optional[str] = Field(None, max_length=128)
