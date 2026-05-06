#!/bin/bash

# Script de deployment pentru VPS Ubuntu/Debian
# Rulează ca root sau cu sudo

echo "🚀 Începem deployment-ul aplicației Analize Medicale..."

# 1. Update sistem
echo "📦 Actualizare sistem..."
apt update && apt upgrade -y

# 2. Instalează Docker
echo "🐳 Instalare Docker..."
apt install -y docker.io curl
systemctl start docker
systemctl enable docker

# 3. Instalează Git (dacă nu e)
echo "📥 Instalare Git..."
apt install -y git

# 4. Clonează repository (înlocuiește cu URL-ul tău GitHub)
echo "📂 Clonează codul sursă..."
# git clone https://github.com/user/repo.git /app
# cd /app

# Sau presupunem că fișierele sunt încărcate în /app
cd /app

# 5. Construiește imaginea Docker
echo "🏗️ Construire container..."
docker build -t analize-app .

# 6. Rulează containerul
echo "▶️ Pornire aplicație..."
docker run -d -p 80:8000 --name analize-container --restart unless-stopped analize-app

# 7. Verifică status
echo "✅ Verificare status..."
docker ps

echo ""
echo "🎉 Aplicația este acum online la http://IP-ul-server-ului"
echo "Pentru HTTPS, instalează Nginx + Certbot:"
echo "apt install -y nginx certbot python3-certbot-nginx"
echo "certbot --nginx -d domeniul-tau.com"

# Opțional: Instalează PostgreSQL dacă vrei DB extern
# echo "🗄️ Instalare PostgreSQL..."
# apt install -y postgresql postgresql-contrib
# systemctl start postgresql
# systemctl enable postgresql
# sudo -u postgres createuser --interactive --pwprompt app_user
# sudo -u postgres createdb -O app_user analize_db

echo "Deployment complet! Accesează aplicația în browser."