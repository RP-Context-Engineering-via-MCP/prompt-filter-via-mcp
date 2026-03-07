# Start All Services + ngrok Tunnel Script
Write-Host "Starting Chat Application Services with ngrok Tunnel..." -ForegroundColor Green

$root = "d:\SLIIIT\Research\Dev\chatApp"

# 1. Start Prompt Filter Engine (Python/FastAPI)
# This loads the SLM and listens on port 3003
Write-Host "Launching Prompt Filter Engine (Port 3003)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {
    Write-Host '--- PROMPT FILTER ENGINE (PFE) ---' -ForegroundColor Yellow;
    cd '$root\prompt_filter_engine';
    `$env:PYTHONPATH='$root';
    python server.py;
}"

# Wait for Python to start initializing
Start-Sleep -Seconds 2

# 1.5 Start Prompt Enrichment Service (Python/FastAPI)
# Listens on port 3004
Write-Host "Launching Prompt Enrichment Service (Port 3004)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {
    Write-Host '--- PROMPT ENRICHMENT SERVICE ---' -ForegroundColor Yellow;
    cd '$root\prompt_enrichment_service';
    `$env:PYTHONPATH='$root';
    python -m uvicorn main:app --port 3004 --reload;
}"

Start-Sleep -Seconds 2

# 2. Start MCP Server (Node.js)
# Listens on port 3001 — exposes /sse (Claude Desktop) and /mcp (ChatGPT)
Write-Host "Launching MCP Server (Port 3001)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {
    Write-Host '--- MCP SERVER ---' -ForegroundColor Magenta;
    cd '$root\mcp-server';
    npm start;
}"

# 3. Start Chat Logger Backend (Node.js)
# Listens on port 3005
Write-Host "Launching Chat Logger Backend (Port 3005)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {
    Write-Host '--- CHAT LOGGER BACKEND ---' -ForegroundColor Green;
    cd '$root\chat-logger-backend';
    npm start;
}"

Start-Sleep -Seconds 2

# 4. Start Web Client (React/Vite)
# Listens on generic dev port (likely 5173)
Write-Host "Launching Web Client..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {
    Write-Host '--- WEB CLIENT ---' -ForegroundColor Cyan;
    cd '$root\web-client';
    npm run dev;
}"

Start-Sleep -Seconds 3

# 5. Start ngrok tunnel — exposes MCP Server port 3001 to the internet
Write-Host "Launching ngrok tunnel (Port 3001 -> public HTTPS)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {
    Write-Host '--- NGROK TUNNEL ---' -ForegroundColor Yellow;
    Write-Host 'Waiting for MCP Server to be ready...' -ForegroundColor Gray;
    Start-Sleep -Seconds 3;
    ngrok http 3001 --response-header-add 'X-Accel-Buffering:no';
}"

Write-Host ""
Write-Host "All services launched in separate windows." -ForegroundColor Green
Write-Host ""
Write-Host "Local endpoints:" -ForegroundColor White
Write-Host "  PFE:        http://localhost:3003/health"
Write-Host "  MCP (SSE):  http://localhost:3001/sse       <- Claude Desktop / web-client"
Write-Host "  MCP (HTTP): http://localhost:3001/mcp       <- ChatGPT"
Write-Host ""
Write-Host "Once ngrok starts, copy the public URL from the ngrok window." -ForegroundColor Yellow
Write-Host "Then add it to ChatGPT: Settings -> Connected apps -> Add MCP server" -ForegroundColor Yellow
Write-Host "  URL format: https://<ngrok-id>.ngrok-free.app/mcp" -ForegroundColor Cyan
