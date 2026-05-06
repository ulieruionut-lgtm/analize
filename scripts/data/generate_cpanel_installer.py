#!/usr/bin/env python3
"""
Generator pachet deployment cPanel pentru aplicație Python FastAPI.
Creează fișiere PHP pentru instalare și configurare pe hosting tradițional.
"""
import os
import shutil
import zipfile
from pathlib import Path

DEPLOY_DIR = Path("deployment_cpanel")
ROOT = Path(__file__).parent

def create_php_installer():
    """Creează fișierul installer.php pentru setup automat."""
    
    installer_php = """<?php
/**
 * INSTALLER AUTOMAT - Analize Medicale
 * Pentru Romarg Hosting / cPanel cu PHP 7+ și MySQL
 */

header('Content-Type: text/html; charset=utf-8');
?>
<!DOCTYPE html>
<html lang="ro">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Installer - Analize Medicale</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 40px auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 40px;
        }
        h1 { color: #667eea; margin-bottom: 10px; }
        h2 { color: #764ba2; margin: 30px 0 15px; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        .success { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }
        .info { background: #d1ecf1; border: 1px solid #bee5eb; color: #0c5460; padding: 15px; border-radius: 5px; margin: 15px 0; }
        input, select { width: 100%; padding: 10px; margin: 8px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { 
            background: #667eea; 
            color: white; 
            padding: 12px 30px; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 16px;
            margin-top: 20px;
        }
        button:hover { background: #764ba2; }
        .step { background: #f8f9fa; padding: 15px; margin: 15px 0; border-left: 4px solid #667eea; }
        code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
        pre { background: #2d2d2d; color: #f8f8f2; padding: 15px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
<div class="container">
    <h1>🏥 Installer Analize Medicale</h1>
    <p>Configurare automată pentru Romarg Hosting / cPanel</p>

<?php
// Verificări sistem
$checks = [
    'PHP Version' => version_compare(PHP_VERSION, '7.4.0', '>='),
    'PDO MySQL' => extension_loaded('pdo_mysql'),
    'JSON' => extension_loaded('json'),
    'Fileinfo' => extension_loaded('fileinfo'),
    'Directory writable' => is_writable(__DIR__),
];

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    
    if ($_POST['action'] === 'test_db') {
        // Test conexiune MySQL
        try {
            $host = $_POST['db_host'];
            $name = $_POST['db_name'];
            $user = $_POST['db_user'];
            $pass = $_POST['db_pass'];
            
            $pdo = new PDO("mysql:host=$host;dbname=$name;charset=utf8mb4", $user, $pass);
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            
            echo '<div class="success">✓ Conexiune MySQL reușită!</div>';
            
            // Salvează configurația
            $env_content = "DATABASE_URL=mysql://$user:$pass@$host:3306/$name\\n";
            $env_content .= "OCR_LANG=ron\\n";
            $env_content .= "PDF_TEXT_MIN_CHARS=200\\n";
            file_put_contents('.env', $env_content);
            
            echo '<div class="info">✓ Fișier .env creat cu succes!</div>';
            
        } catch (PDOException $e) {
            echo '<div class="error">✗ Eroare conexiune: ' . htmlspecialchars($e->getMessage()) . '</div>';
        }
    }
    
    if ($_POST['action'] === 'create_tables') {
        // Creează tabelele MySQL
        try {
            // Citește .env
            $env = parse_ini_file('.env');
            preg_match('/mysql:\\\\/\\\\/(.+):(.+)@(.+):(\\\\d+)\\\\/(.+)/', $env['DATABASE_URL'], $matches);
            
            $pdo = new PDO(
                "mysql:host={$matches[3]};dbname={$matches[5]};charset=utf8mb4",
                $matches[1],
                $matches[2]
            );
            $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            
            // Citește și execută schema MySQL
            $sql = file_get_contents('sql/schema_mysql.sql');
            $pdo->exec($sql);
            
            echo '<div class="success">✓ Tabele create cu succes!</div>';
            echo '<div class="info">Următorul pas: Instalare Python și dependințe pe server</div>';
            
        } catch (Exception $e) {
            echo '<div class="error">✗ Eroare creare tabele: ' . htmlspecialchars($e->getMessage()) . '</div>';
        }
    }
}

// Afișare verificări sistem
echo '<h2>1. Verificări Sistem</h2>';
foreach ($checks as $check => $status) {
    $icon = $status ? '✓' : '✗';
    $class = $status ? 'success' : 'error';
    echo "<div class='$class'>$icon $check</div>";
}

// Formular configurare database
echo '<h2>2. Configurare MySQL Database</h2>';
echo '<div class="warning">⚠ Creează mai întâi baza de date MySQL în cPanel → MySQL Databases</div>';
?>

<form method="POST">
    <input type="hidden" name="action" value="test_db">
    
    <label>Host MySQL (de obicei: localhost)</label>
    <input type="text" name="db_host" value="localhost" required>
    
    <label>Nume Database</label>
    <input type="text" name="db_name" placeholder="ex: cpanel_analize" required>
    
    <label>Username MySQL</label>
    <input type="text" name="db_user" placeholder="ex: cpanel_user" required>
    
    <label>Parolă MySQL</label>
    <input type="password" name="db_pass" required>
    
    <button type="submit">Test Conexiune & Salvează Config</button>
</form>

<?php if (file_exists('.env')): ?>
<h2>3. Creare Tabele Database</h2>
<form method="POST">
    <input type="hidden" name="action" value="create_tables">
    <button type="submit">Creează Tabelele MySQL</button>
</form>
<?php endif; ?>

<h2>4. Instalare Python & Aplicație</h2>
<div class="warning">
    <strong>⚠ IMPORTANT:</strong> Romarg Hosting are Python preinstalat, dar aplicația FastAPI necesită acces SSH.
</div>

<div class="step">
    <strong>Opțiuni deployment:</strong>
    <ul style="margin-left: 20px; margin-top: 10px;">
        <li><strong>Opțiunea A (Recomandată):</strong> Railway.app / Render.com (gratuit, Python complet)</li>
        <li><strong>Opțiunea B:</strong> SSH pe Romarg (dacă ai acces SSH)</li>
        <li><strong>Opțiunea C:</strong> VPS separat pentru Python + MySQL pe Romarg</li>
    </ul>
</div>

<h2>5. Comenzi SSH (dacă ai acces)</h2>
<pre>
# Conectare SSH
ssh username@server.romarg.ro

# Instalare dependințe
cd ~/public_html
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Pornire aplicație (background)
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

# Configurare .htaccess pentru redirect PHP → Python
</pre>

<h2>Contact & Suport</h2>
<div class="info">
    <p><strong>Romarg Hosting PHP 7 + MySQL:</strong> Database OK ✓</p>
    <p><strong>Python FastAPI:</strong> Necesită SSH sau platformă separată</p>
    <p><strong>Recomandare:</strong> Folosește Railway.app (gratuit) + MySQL pe Romarg</p>
</div>

</div>
</body>
</html>
"""
    
    (DEPLOY_DIR / "installer.php").write_text(installer_php, encoding='utf-8')
    print("OK - installer.php creat")


def create_htaccess():
    """Creează .htaccess pentru proxy la aplicația Python."""
    
    htaccess = """# .htaccess pentru Analize Medicale
# Redirect trafic către aplicația Python (dacă rulează pe port 8000)

<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteBase /
    
    # Nu rewrite pentru installer.php
    RewriteCond %{REQUEST_URI} !^/installer\\.php$
    
    # Redirect la Python app (localhost:8000)
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteRule ^(.*)$ http://localhost:8000/$1 [P,L]
</IfModule>

# Security headers
<IfModule mod_headers.c>
    Header set X-Content-Type-Options "nosniff"
    Header set X-Frame-Options "SAMEORIGIN"
    Header set X-XSS-Protection "1; mode=block"
</IfModule>

# PHP settings
php_value upload_max_filesize 20M
php_value post_max_size 20M
php_value max_execution_time 300
"""
    
    (DEPLOY_DIR / ".htaccess").write_text(htaccess, encoding='utf-8')
    print("OK - .htaccess creat")


def create_instructions():
    """Creează fișierul cu instrucțiuni de deployment."""
    
    instructions = """═══════════════════════════════════════════════════════════════════════════
  📋 INSTRUCȚIUNI DEPLOYMENT CPANEL - ROMARG HOSTING
═══════════════════════════════════════════════════════════════════════════

IMPORTANT: Romarg Hosting folosește PHP 7 + MySQL.
Aplicația ta folosește Python + FastAPI.

╔════════════════════════════════════════════════════════════════════════╗
║  VARIANTĂ RECOMANDATĂ: Arhitectură Hibridă                             ║
╚════════════════════════════════════════════════════════════════════════╝

  🌐 Railway.app (gratuit) → Aplicația Python FastAPI
  💾 Romarg MySQL → Baza de date (accesibilă de pe Railway)

AVANTAJE:
  ✓ Python complet funcțional (Railway)
  ✓ Folosești MySQL-ul de pe Romarg (inclus în pachet)
  ✓ Totul gratuit pentru început
  ✓ HTTPS automat
  ✓ Deployment simplu

───────────────────────────────────────────────────────────────────────────
  PAȘI DEPLOYMENT
───────────────────────────────────────────────────────────────────────────

═══ PARTEA 1: MySQL pe Romarg (5 minute) ═══

1. LOGIN CPANEL
   → Accesează: https://cpanel.romarg.ro
   → Username: contul tău Romarg
   → Password: parola cPanel

2. CREEAZĂ DATABASE MYSQL
   a) Mergi la: "MySQL® Databases"
   
   b) Creează database:
      Nume: cpanel_analize (sau alt nume)
      → Click "Create Database"
   
   c) Creează user MySQL:
      Username: cpanel_user
      Password: [generează parolă puternică]
      → Click "Create User"
   
   d) Adaugă user la database:
      User: cpanel_user
      Database: cpanel_analize
      Privilegii: ALL PRIVILEGES
      → Click "Add"

3. NOTEAZĂ DATELE:
   ✓ Host: cpanel.mysql.romarg.ro (sau localhost)
   ✓ Database: cpanel_analize
   ✓ User: cpanel_user
   ✓ Password: [parola ta]
   ✓ Port: 3306

4. PERMITE ACCES REMOTE (IMPORTANT!)
   a) În cPanel → "Remote MySQL"
   b) Adaugă: %.railway.internal
   c) Adaugă: %.render.com
   d) Adaugă: % (toate IP-urile - doar pentru început)

5. UPLOAD & RULEAZĂ INSTALLER
   a) File Manager → public_html
   b) Upload deployment_cpanel.zip
   c) Extract arhiva
   d) Accesează: http://your-domain.ro/installer.php
   e) Completează datele MySQL
   f) Click "Test Conexiune & Salvează Config"
   g) Click "Creează Tabelele MySQL"

═══ PARTEA 2: Python FastAPI pe Railway (5 minute) ═══

6. INSTALARE RAILWAY CLI (pe calculatorul tău)
   
   Windows:
   > npm install -g @railway/cli
   
   Sau download de la: https://railway.app

7. DEPLOYMENT RAILWAY
   
   a) Deschide terminal în: D:\\Ionut analize
   
   b) Login Railway:
      > railway login
   
   c) Creează proiect:
      > railway init --name analize-medicale
   
   d) Configurează DATABASE_URL în Railway:
      > railway variables set DATABASE_URL="mysql://cpanel_user:PAROLA@cpanel.mysql.romarg.ro:3306/cpanel_analize"
      
      ⚠ Înlocuiește PAROLA cu parola ta MySQL!
   
   e) Deploy:
      > railway up
   
   f) Obține URL-ul:
      > railway domain
      → Salvează URL-ul (ex: https://analize-xxx.railway.app)

8. TEST APLICAȚIE
   
   a) Accesează: https://analize-xxx.railway.app/health
      Răspuns așteptat: {"status": "ok", "database": "connected"}
   
   b) Accesează: https://analize-xxx.railway.app
      → Ar trebui să vezi interfața aplicației

═══ VARIANTA 2: Doar pe Romarg (dacă ai SSH) ═══

Dacă ai acces SSH pe Romarg:

1. Conectare SSH:
   > ssh user@server.romarg.ro

2. Instalare dependințe:
   > cd ~/public_html
   > python3 -m venv venv
   > source venv/bin/activate
   > pip install -r requirements.txt

3. Configurare .env:
   > nano .env
   
   DATABASE_URL=mysql://cpanel_user:PAROLA@localhost:3306/cpanel_analize
   OCR_LANG=ron

4. Pornire aplicație:
   > nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 &

5. Configurare port în cPanel (Advanced → Application Manager)

───────────────────────────────────────────────────────────────────────────
  🆘 TROUBLESHOOTING
───────────────────────────────────────────────────────────────────────────

EROARE: "Can't connect to MySQL server"
  → Verifică: Remote MySQL este activat în cPanel
  → Adaugă %.railway.internal în whitelist
  → Verifică username/password

EROARE: "Access denied for user"
  → Verifică: user-ul are ALL PRIVILEGES pe database
  → Username format corect: cpanel_user (fără prefix)

EROARE: "Tesseract not found" (pe Railway)
  → Railway: Dockerfile include Tesseract automat ✓
  → Romarg SSH: apt install tesseract-ocr tesseract-ocr-ron

───────────────────────────────────────────────────────────────────────────
  📊 COMPARAȚIE VARIANTE
───────────────────────────────────────────────────────────────────────────

| Criterii        | Railway+Romarg | Doar Romarg SSH |
|-----------------|----------------|-----------------|
| Dificultate     | ⭐⭐ (ușor)    | ⭐⭐⭐⭐ (mediu) |
| Python complet  | ✓ DA           | ⚠ Depinde SSH   |
| MySQL          | ✓ Romarg       | ✓ Romarg        |
| Tesseract OCR   | ✓ Automat      | Manual install  |
| HTTPS           | ✓ Automat      | Manual certbot  |
| Cost            | Gratuit        | Inclus în pachet|
| Recomandare     | ✅ DA          | Dacă ai SSH     |

───────────────────────────────────────────────────────────────────────────
  ✅ VERIFICARE FINALĂ
───────────────────────────────────────────────────────────────────────────

□ MySQL creat pe Romarg
□ Remote MySQL activat
□ Tabele create (via installer.php)
□ Railway CLI instalat
□ Aplicația deployed pe Railway
□ DATABASE_URL configurat în Railway
□ /health returnează status: ok
□ Interfața se încarcă corect
□ Upload PDF funcționează

───────────────────────────────────────────────────────────────────────────
  📞 SUPORT
───────────────────────────────────────────────────────────────────────────

Romarg Hosting: https://romarg.ro/contact
Railway Support: https://railway.app/help
Documentație: Citește DEPLOYMENT_GUIDE.md

═══════════════════════════════════════════════════════════════════════════
  Succes cu deployment-ul! 🚀
═══════════════════════════════════════════════════════════════════════════
"""
    
    (ROOT / "INSTRUCTIUNI_CPANEL.txt").write_text(instructions, encoding='utf-8')
    print("OK - INSTRUCTIUNI_CPANEL.txt creat")


def create_zip():
    """Creează arhiva ZIP pentru upload."""
    
    zip_path = ROOT / f"{DEPLOY_DIR.name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    
    print(f"\n-> Creez arhiva {zip_path.name}...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(DEPLOY_DIR):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(DEPLOY_DIR.parent)
                zipf.write(file_path, arcname)
                print(f"  + {arcname}")
    
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"OK - Arhiva creata: {zip_path.name} ({size_mb:.2f} MB)")


def main():
    print("\n" + "="*75)
    print("  GENERATOR PACHET DEPLOYMENT CPANEL")
    print("="*75 + "\n")
    
    if not DEPLOY_DIR.exists():
        print(f"X Directorul {DEPLOY_DIR} nu exista!")
        print("  Ruleaza mai intai: CREATOR_PACHET_CPANEL.bat")
        return
    
    print("-> Generez fisiere PHP pentru instalare...\n")
    
    create_php_installer()
    create_htaccess()
    create_instructions()
    create_zip()
    
    print("\n" + "="*75)
    print("  OK - PACHET DEPLOYMENT PREGATIT CU SUCCES!")
    print("="*75)
    print(f"\nFisiere generate:")
    print(f"  • {DEPLOY_DIR.name}.zip - Pentru upload pe cPanel")
    print(f"  • INSTRUCTIUNI_CPANEL.txt - Pasi deployment\n")
    print("Citeste INSTRUCTIUNI_CPANEL.txt pentru pasii urmatori!")
    print("="*75 + "\n")


if __name__ == "__main__":
    main()
