# Script PowerShell pentru deployment DigitalOcean
# Rulează în PowerShell ca Administrator

param(
    [Parameter(Mandatory=$true)]
    [string]$DoToken,
    
    [string]$Region = "nyc1",
    [string]$Size = "s-1vcpu-1gb",
    [string]$Image = "ubuntu-22-04-x64",
    [string]$Name = "analize-app"
)

# 1. Instalează OpenSSH dacă nu e
if (!(Get-Command ssh -ErrorAction SilentlyContinue)) {
    Write-Host "Instalez OpenSSH..."
    Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0
}

# 2. Creează droplet-ul
Write-Host "Creez droplet-ul pe DigitalOcean..."
$body = @{
    name = $Name
    region = $Region
    size = $Size
    image = $Image
    ssh_keys = @()  # Poți adăuga SSH key ID dacă ai
} | ConvertTo-Json

$headers = @{
    "Authorization" = "Bearer $DoToken"
    "Content-Type" = "application/json"
}

$response = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/droplets" -Method Post -Headers $headers -Body $body
$dropletId = $response.droplet.id
$ip = $null

Write-Host "Droplet creat cu ID: $dropletId. Aștept IP-ul..."

# 3. Așteaptă până droplet-ul e activ și obține IP-ul
do {
    Start-Sleep -Seconds 10
    $status = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/droplets/$dropletId" -Headers $headers
    $ip = $status.droplet.networks.v4 | Where-Object { $_.type -eq "public" } | Select-Object -ExpandProperty ip_address
} while (!$ip)

Write-Host "Droplet activ la IP: $ip"

# 4. Așteaptă SSH să fie disponibil
Write-Host "Aștept SSH să fie disponibil..."
do {
    Start-Sleep -Seconds 5
    $test = Test-NetConnection -ComputerName $ip -Port 22
} while (!$test.TcpTestSucceeded)

# 5. Generează cheie SSH dacă nu există
$sshKeyPath = "$env:USERPROFILE\.ssh\do_key"
if (!(Test-Path $sshKeyPath)) {
    Write-Host "Generez cheie SSH..."
    ssh-keygen -t rsa -b 4096 -f $sshKeyPath -N ""
}

# 6. Adaugă cheia SSH la droplet (opțional, pentru acces fără parolă)
# (Presupunem că ai adăugat cheia în DO dashboard sau o adaugi manual)

# 7. Conectează-te și deployează
Write-Host "Conectez la server și deployez..."
$deployScript = @"
#!/bin/bash
apt update && apt upgrade -y
apt install -y docker.io curl git
systemctl start docker
systemctl enable docker

# Clonează repo (înlocuiește cu URL-ul tău GitHub)
git clone https://github.com/USERNAME/analize-medicale.git /app
cd /app

# Construiește și rulează
docker build -t analize-app .
docker run -d -p 80:8000 --name analize-container --restart unless-stopped analize-app

echo "Deployment complet! Accesează la http://$ip"
"@

# Salvează scriptul pe server și rulează-l
$deployScript | ssh -o StrictHostKeyChecking=no root@$ip "cat > /tmp/deploy.sh && chmod +x /tmp/deploy.sh && /tmp/deploy.sh"

Write-Host "🎉 Deployment complet! Aplicația e online la http://$ip"
Write-Host "Pentru HTTPS: apt install -y nginx certbot python3-certbot-nginx && certbot --nginx -d domeniul-tau.com"