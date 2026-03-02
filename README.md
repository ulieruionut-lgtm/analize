# 🏥 Analize Medicale - Sistem de Management PDF

Aplicație web pentru procesarea, stocarea și vizualizarea analizelor medicale din fișiere PDF.

## ✨ Funcționalități

- **📤 Upload PDF**: Procesare automată analize medicale (text sau scanate cu OCR)
- **🔍 Extragere inteligentă**: CNP, nume, analize, valori, unități, intervale de referință
- **📊 Vizualizare evoluție**: Tabel pivotant cu evoluția analizelor în timp
- **🔗 Normalizare**: Mapare automată denumiri analize din diverse laboratoare
- **👨‍⚕️ Interfață medic**: Căutare rapidă pacient după CNP/nume
- **🤖 Auto-learning**: Sistem de învățare pentru analize necunoscute

## 🚀 Quick Start (Local)

### Cerințe
- Python 3.11+
- Tesseract OCR (pentru PDF-uri scanate)

### Instalare

#### Windows (Simplu)
```bash
# Dublu-click pe:
PORNESTE_APLICATIA.bat
```

#### Manual
```bash
# 1. Clonează repo
git clone https://github.com/USERNAME/analize-medicale.git
cd analize-medicale

# 2. Crează virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 3. Instalează dependințe
pip install -r requirements.txt

# 4. Instalează Tesseract OCR
# Windows: winget install UB-Mannheim.TesseractOCR
# Linux: apt install tesseract-ocr tesseract-ocr-ron
# Mac: brew install tesseract tesseract-lang

# 5. Pornește aplicația
cd backend
uvicorn main:app --reload
```

Aplicația va rula pe: **http://localhost:8000**

## 📦 Deployment Online

Aplicația suportă:
- ✅ **SQLite** (local)
- ✅ **PostgreSQL** (recomandat producție)
- ✅ **MySQL** (compatibil hosting PHP)

### Deployment rapid (gratuit)

**Railway.app** (recomandat):
```bash
railway login
railway init
railway up
```

**Render.com**:
- Connect GitHub repo
- Select Docker
- Deploy automat

Vezi ghidul complet: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

## 🏗️ Arhitectură

```
Backend:    Python 3.11 + FastAPI
Frontend:   HTML + CSS + JavaScript (vanilla)
Database:   SQLite / PostgreSQL / MySQL
OCR:        Tesseract + PyMuPDF
PDF Parse:  pdfplumber + regex
```

## 📁 Structura Proiect

```
analize-medicale/
├── backend/
│   ├── main.py              # FastAPI app + interfață HTML
│   ├── pdf_processor.py     # Extragere text/OCR
│   ├── parser.py            # Parse CNP, nume, analize
│   ├── normalizer.py        # Normalizare denumiri
│   ├── database.py          # CRUD + conexiuni DB
│   ├── models.py            # Modele Pydantic
│   └── config.py            # Configurare env
├── sql/
│   ├── schema_sqlite.sql    # Schema SQLite
│   ├── schema_mysql.sql     # Schema MySQL
│   └── seed_sqlite.sql      # Date inițiale
├── requirements.txt         # Dependințe Python
├── Dockerfile               # Container pentru deployment
├── .env.example             # Template configurare
└── DEPLOYMENT_GUIDE.md      # Ghid deployment complet
```

## 🔧 Configurare

Creează fișier `.env` (vezi `.env.example`):

```bash
# SQLite (local)
DATABASE_URL=sqlite

# PostgreSQL
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# MySQL
DATABASE_URL=mysql://user:pass@host:3306/dbname
```

## 📊 Baza de Date

### Tabele principale:
- `pacienti` - Date pacienți (CNP, nume)
- `buletine` - Buletine de analize încărcate
- `analiza_standard` - Analize standardizate
- `analiza_alias` - Mapări denumiri laboratoare
- `rezultate_analize` - Valori analize
- `analiza_necunoscuta` - Analize nemapate (auto-learning)

### Migrații:
```bash
python run_migrations.py
```

## 🧪 Testare

```bash
# Test conexiune DB
python test_database.py

# Test server
curl http://localhost:8000/health
```

## 📖 Utilizare

### 1. Upload PDF
- Click pe "Upload PDF"
- Selectează fișier PDF cu analize
- Așteaptă procesarea (OCR pentru PDF-uri scanate)

### 2. Vizualizare Pacient
- Click pe "Pacient"
- Caută după CNP sau nume
- Vezi tabel cu evoluția analizelor

### 3. Analize Necunoscute
- Click pe "Analize necunoscute"
- Asociază analizele noi cu numele standard
- Sistemul învață automat pentru viitor

## 🎨 Screenshots

### Dashboard Upload
![Upload](docs/screenshots/upload.png)

### Tabel Evoluție Analize
![Evolutie](docs/screenshots/evolutie.png)

## 🛠️ Tehnologii

- **Backend**: FastAPI, Uvicorn
- **OCR**: Tesseract, PyMuPDF, Pillow
- **PDF**: pdfplumber
- **Database**: SQLite / PostgreSQL / MySQL (pymysql, psycopg2)
- **Config**: Pydantic, python-dotenv

## 📝 Roadmap

- [x] Upload & procesare PDF
- [x] OCR pentru PDF-uri scanate
- [x] Extragere CNP, nume, analize
- [x] Normalizare denumiri analize
- [x] Interfață vizualizare evoluție
- [x] Auto-learning analize necunoscute
- [x] Suport MySQL pentru deployment
- [ ] Autentificare utilizatori
- [ ] Grafice evoluție analize
- [ ] Export Excel/PDF rapoarte
- [ ] API REST complet documentat
- [ ] Notificări valori anormale
- [ ] Integrare laborator (API)

## 🤝 Contribuții

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## 📄 Licență

MIT License - vezi [LICENSE](LICENSE)

## 👨‍💻 Autor

Dezvoltat pentru medici și clinici din România 🇷🇴

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/USERNAME/analize-medicale/issues)
- **Email**: support@example.com
- **Docs**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

**Made with ❤️ in Romania**
