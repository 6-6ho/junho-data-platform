# Check for Administrator privileges
if (!([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Detect WSL IP
Write-Host "Detecting WSL IP Address..." -ForegroundColor Cyan
try {
    $wsl_output = (wsl hostname -I).Trim()
    $wsl_ip = $wsl_output.Split(' ')[0] # Use first IP if multiple
} catch {
    Write-Host "Error: Failed to get WSL IP. Ensure WSL is running." -ForegroundColor Red
    pause
    exit
}

if ([string]::IsNullOrWhiteSpace($wsl_ip)) {
    Write-Host "Error: WSL IP is empty. Ensure WSL is running." -ForegroundColor Red
    pause
    exit
}

Write-Host "WSL IP: $wsl_ip" -ForegroundColor Green

# Ports to forward
# 5432: Postgres (Critical for Desktop connection)
# 3000: Frontend
# 8000: Backend API
# 9092: Kafka (Broker)
# 9090: Prometheus
# 3002: Grafana
# 9100: Node Exporter
# 8080: cAdvisor / Airflow Webserver
$ports = @(5432, 3000, 8000, 9092, 9090, 3002, 9100, 8080)

foreach ($port in $ports) {
    Write-Host "Configuring Port $port..." -ForegroundColor Yellow
    
    # 1. Delete existing portproxy (to avoid stale config)
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 | Out-Null

    # 2. Add new portproxy
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wsl_ip
    
    # 3. Add Firewall Rule (Delete existing first to avoid duplicates)
    Remove-NetFirewallRule -DisplayName "JunhoPlatform Port $port" -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "JunhoPlatform Port $port" -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow | Out-Null
    
    Write-Host "  [OK] Forwarded $port -> $wsl_ip:$port" -ForegroundColor Green
}

Write-Host "`nAll ports configured successfully! 🚀" -ForegroundColor Green
Write-Host "You can now connect to these services from other devices using this Laptop's LAN IP."
pause
