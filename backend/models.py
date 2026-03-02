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


class PatientParsed(BaseModel):
    cnp: str
    nume: str
    prenume: Optional[str] = None
    rezultate: list[RezultatParsat] = []
