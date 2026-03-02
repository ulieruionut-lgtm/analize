<?php
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
            $env_content = "DATABASE_URL=mysql://$user:$pass@$host:3306/$name\n";
            $env_content .= "OCR_LANG=ron\n";
            $env_content .= "PDF_TEXT_MIN_CHARS=200\n";
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
            preg_match('/mysql:\\/\\/(.+):(.+)@(.+):(\\d+)\\/(.+)/', $env['DATABASE_URL'], $matches);
            
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
