# Check for Administrator privileges
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (!$currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Detect WSL IP
Write-Host "Detecting WSL IP Address..." -ForegroundColor Cyan
try {
    $wsl_output = (wsl hostname -I)
    if ([string]::IsNullOrWhiteSpace($wsl_output)) { throw "WSL returned empty IP" }
    $wsl_ip = $wsl_output.Trim().Split(" ")[0]
    if ([string]::IsNullOrWhiteSpace($wsl_ip)) { throw "Failed to parse IP" }
    Write-Host "Found WSL IP: $wsl_ip" -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    pause
    exit
}

# Desktop Ports to Open
# 3001: Shop Frontend
# 8080: Airflow Web
# 8081: Spark Master Web UI
# 9100: Node Exporter
# 8085: cAdvisor
$ports = @(3001, 8080, 8081, 9100, 8085)

foreach ($port in $ports) {
    Write-Host "Configuring Port $port..." -ForegroundColor Yellow
    
    # Port Forwarding
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 | Out-Null
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wsl_ip
    
    # Firewall
    Remove-NetFirewallRule -DisplayName "JDP Desktop Port $port" -ErrorAction SilentlyContinue
    try {
        New-NetFirewallRule -DisplayName "JDP Desktop Port $port" -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow -Profile Any | Out-Null
        Write-Host "  [OK] Forwarded $port -> $wsl_ip:$port" -ForegroundColor Green
    } catch {
        Write-Host "  [Warning] Firewall rule failed" -ForegroundColor Red
    }
}

Write-Host "`nDesktop Network Configured! 🚀" -ForegroundColor Green
pause
