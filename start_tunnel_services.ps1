# Start All Services + ngrok Tunnel Script (Single Terminal)
Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Starting Chat Application Services..." -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

$root = "d:\SLIIIT\Research\Dev\chatApp"
$processes = @()

# Helper to set PYTHONPATH for the session
$env:PYTHONPATH = $root

# 1. Prompt Filter Engine (Port 3003)
Write-Host "[PFE]         Starting Prompt Filter Engine (Port 3003)..." -ForegroundColor Yellow
$processes += Start-Process python -ArgumentList "server.py" `
    -WorkingDirectory "$root\prompt_filter_engine" `
    -NoNewWindow -PassThru

Start-Sleep -Seconds 2

# 2. Prompt Enrichment Service (Port 3004)
Write-Host "[ENRICHMENT]  Starting Prompt Enrichment Service (Port 3004)..." -ForegroundColor Yellow
$processes += Start-Process python -ArgumentList "-m uvicorn main:app --port 3004 --reload" `
    -WorkingDirectory "$root\prompt_enrichment_service" `
    -NoNewWindow -PassThru

Start-Sleep -Seconds 2

# 3. MCP Server (Port 3001)
Write-Host "[MCP]         Starting MCP Server (Port 3001)..." -ForegroundColor Magenta
$processes += Start-Process node -ArgumentList "src/index.js" `
    -WorkingDirectory "$root\mcp-server" `
    -NoNewWindow -PassThru

Start-Sleep -Seconds 2

# 4. Chat Logger Backend (Port 3005)
Write-Host "[LOGGER]      Starting Chat Logger Backend (Port 3005)..." -ForegroundColor Green
$processes += Start-Process node -ArgumentList "src/server.js" `
    -WorkingDirectory "$root\chat-logger-backend" `
    -NoNewWindow -PassThru

Start-Sleep -Seconds 2

# 5. Web Client (Dev Server)
Write-Host "[WEB]         Starting Web Client..." -ForegroundColor Cyan
$processes += Start-Process node -ArgumentList "node_modules/vite/bin/vite.js" `
    -WorkingDirectory "$root\web-client" `
    -NoNewWindow -PassThru

Start-Sleep -Seconds 3

# 6. ngrok Tunnel (Port 3001)
Write-Host "[NGROK]       Starting ngrok tunnel (Port 3001)..." -ForegroundColor Yellow
$processes += Start-Process ngrok -ArgumentList "http 3001 --response-header-add `"X-Accel-Buffering:no`"" `
    -NoNewWindow -PassThru

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Local endpoints:" -ForegroundColor White
Write-Host "  PFE:        http://localhost:3003"
Write-Host "  Enrichment: http://localhost:3004"
Write-Host "  MCP (SSE):  http://localhost:3001/sse  <- Claude Desktop"
Write-Host "  MCP (HTTP): http://localhost:3001/mcp  <- ChatGPT"
Write-Host "  Logger:     http://localhost:3005"
Write-Host "  Web Client: http://localhost:3002"
Write-Host ""
Write-Host "Press Ctrl+C to stop all services." -ForegroundColor Red
Write-Host ""

# Keep the script running and wait for Ctrl+C
try {
    while ($true) {
        # Check if any process has exited unexpectedly
        foreach ($proc in $processes) {
            if ($proc.HasExited) {
                Write-Host "[WARNING] Process $($proc.ProcessName) (PID: $($proc.Id)) has exited with code $($proc.ExitCode)" -ForegroundColor Red
            }
        }
        Start-Sleep -Seconds 5
    }
}
finally {
    # Cleanup: kill all child processes on exit
    Write-Host ""
    Write-Host "Stopping all services..." -ForegroundColor Red
    foreach ($proc in $processes) {
        if (-not $proc.HasExited) {
            Write-Host "  Stopping $($proc.ProcessName) (PID: $($proc.Id))..." -ForegroundColor Yellow
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host "All services stopped." -ForegroundColor Green
}
