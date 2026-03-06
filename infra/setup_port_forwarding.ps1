# WSL Port Forwarding Setup for Desktop Node
# Run with: powershell.exe -ExecutionPolicy Bypass -File setup_port_forwarding.ps1

$WSL_IP = (wsl hostname -I).Trim().Split(" ")[0]
$ports = @(3001, 8080, 8081, 9101, 8086)

foreach ($port in $ports) {
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0 2>$null
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$WSL_IP
    Write-Host "  $port -> $WSL_IP"
}

Write-Host "`nPort forwarding configured!"
netsh interface portproxy show v4tov4
