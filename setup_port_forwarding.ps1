# Check for Administrator privileges
$currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (!$currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting Administrator privileges..." -ForegroundColor Yellow
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Detect WSL IP with improved reliability
Write-Host "Detecting WSL IP Address..." -ForegroundColor Cyan
try {
    # Get raw output from WSL
    $wsl_output = (wsl hostname -I)
    
    if ([string]::IsNullOrWhiteSpace($wsl_output)) {
        throw "WSL returned empty IP. Is WSL running?"
    }

    # Take the first IP if multiple are returned (e.g. "172.17.0.2 192.168.1.5")
    $wsl_ip = $wsl_output.Trim().Split(" ")[0]
    
    if ([string]::IsNullOrWhiteSpace($wsl_ip)) {
        throw "Failed to parse IP from output: $wsl_output"
    }

    Write-Host "Found WSL IP: $wsl_ip" -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Please ensure WSL is running (wsl --distribution start)" -ForegroundColor Yellow
    pause
    exit
}

# Ports to forward
$ports = @(5432, 3000, 8000, 9092, 9090, 3002, 9100, 8080)

foreach ($port in $ports) {
    Write-Host "Configuring Port $port..." -ForegroundColor Yellow
    
    # 1. Reset PortProxy
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 | Out-Null
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$wsl_ip
    
    # 2. Configure Firewall
    # Remove old rule if exists
    Remove-NetFirewallRule -DisplayName "JunhoPlatform Port $port" -ErrorAction SilentlyContinue
    
    # Add new rule
    try {
        New-NetFirewallRule -DisplayName "JunhoPlatform Port $port" -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow -Profile Any | Out-Null
        Write-Host "  [OK] Forwarded $port -> $wsl_ip:$port (Firewall Allowed)" -ForegroundColor Green
    } catch {
        Write-Host "  [Warning] Firewall rule creation failed. Run as Administrator?" -ForegroundColor Red
    }
}

Write-Host "`nAll ports configured successfully! 🚀" -ForegroundColor Green
Write-Host "You can now connect to these services from other devices using this Laptop's LAN IP."
pause
