# BidAnalyzer Pro - Quick Setup Script for Windows
# Run this in PowerShell

Write-Host "🚀 BidAnalyzer Pro - Deployment Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if Git is initialized
if (-not (Test-Path ".git")) {
    Write-Host "📦 Initializing Git repository..." -ForegroundColor Yellow
    git init
    Write-Host "✅ Git initialized" -ForegroundColor Green
} else {
    Write-Host "✅ Git already initialized" -ForegroundColor Green
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host ""
    Write-Host "⚙️  Creating .env file..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ .env file created from template" -ForegroundColor Green
    Write-Host "⚠️  IMPORTANT: Edit .env and add your GEMINI_API_KEY" -ForegroundColor Red
} else {
    Write-Host "✅ .env file already exists" -ForegroundColor Green
}

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
    Write-Host ""
    Write-Host "📦 Installing Node dependencies..." -ForegroundColor Yellow
    npm install
    Write-Host "✅ Node dependencies installed" -ForegroundColor Green
} else {
    Write-Host "✅ Node dependencies already installed" -ForegroundColor Green
}

# Check if Python packages are installed
Write-Host ""
Write-Host "🐍 Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt
Write-Host "✅ Python dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "✨ Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env and add your GEMINI_API_KEY" -ForegroundColor White
Write-Host "2. Run the backend: python server.py" -ForegroundColor White
Write-Host "3. Run the frontend (in new terminal): npm run dev" -ForegroundColor White
Write-Host ""
Write-Host "For deployment to Render, see DEPLOYMENT.md" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Cyan
