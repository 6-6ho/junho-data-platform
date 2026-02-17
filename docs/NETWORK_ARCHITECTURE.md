# Network Architecture & Connectivity Guide

## 📡 Overview
Junho Data Platform is a distributed system running on two physical nodes (Laptop & Desktop).
They communicate via **WSL2 Port Forwarding** and **Windows Firewall Rules**.

## 💻 Laptop Node (Main Control)
- **IP**: 192.168.219.xxx (Dynamic)
- **Role**: Trade Pipeline, Web Server (Nginx), API, Monitor (Grafana)
- **Services Exposed to Desktop**:
  - ` Postgres (5432)`: Desktop Spark/Airflow connects here to save data.

| Service | Container Port | Host Port | Description |
|---------|---------------|-----------|-------------|
| **Postgres** | `5432` | `5432` | Main Database (Required by Desktop) |
| **Frontend** | `80` | `3000` | Web Access (Nginx) |
| **API** | `8000` | `8000` | Backend API (Internal) |
| **Grafana** | `3000` | `3002` | Monitoring UI |

---

## 🖥️ Desktop Node (Storage & Batch)
- **IP**: 192.168.219.108 (Static)
- **Role**: Shop Pipeline, Spark Cluster, Airflow, Metrics Exporters
- **Services Exposed to Laptop**:

| Service | Container Port | Host Port | Required For |
|---------|---------------|-----------|--------------|
| **Shop Web** | `80` | `3001` | Laptop Nginx (`shop.6-6ho.com`) |
| **Airflow** | `8080` | `8080` | Laptop Tunnel (`airflow.6-6ho.com`) |
| **Spark UI** | `8080` | `8081` | Laptop API (Pipeline Status) |
| **Node Exp** | `9100` | `9100` | Laptop Prometheus (Metrics) |
| **cAdvisor** | `8080` | `8085` | Laptop Prometheus (Metrics) |

---

## 🛠️ Connectivity Setup (Must Run on Host Windows)

### 1. Laptop Setup (Run once)
Allows Desktop to access Postgres.
```powershell
./setup_port_forwarding.ps1
```

### 2. Desktop Setup (Run once)
Allows Laptop to access Shop, Spark, Airflow, and Metrics.
**Run this in PowerShell (Admin):**

```powershell
$WSL_IP = (wsl hostname -I).Trim().Split(" ")[0]
$ports = @(3001, 8080, 8081, 9100, 8085)

foreach ($port in $ports) {
    netsh interface portproxy delete v4tov4 listenport=$port listenaddress=0.0.0.0
    netsh interface portproxy add v4tov4 listenport=$port listenaddress=0.0.0.0 connectport=$port connectaddress=$WSL_IP
    Remove-NetFirewallRule -DisplayName "JDP Port $port" -ErrorAction SilentlyContinue
    New-NetFirewallRule -DisplayName "JDP Port $port" -Direction Inbound -LocalPort $port -Protocol TCP -Action Allow -Profile Any
}
```
