#!/bin/bash

# BidAnalyzer Pro - Quick Setup Script
# This script helps you prepare the project for deployment

echo "🚀 BidAnalyzer Pro - Deployment Setup"
echo "======================================"
echo ""

# Check if Git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Initializing Git repository..."
    git init
    echo "✅ Git initialized"
else
    echo "✅ Git already initialized"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created from template"
    echo "⚠️  IMPORTANT: Edit .env and add your GEMINI_API_KEY"
else
    echo "✅ .env file already exists"
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo ""
    echo "📦 Installing Node dependencies..."
    npm install
    echo "✅ Node dependencies installed"
else
    echo "✅ Node dependencies already installed"
fi

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo ""
    echo "🐍 Creating Python virtual environment..."
    python -m venv venv
    echo "✅ Virtual environment created"
fi

echo ""
echo "======================================"
echo "✨ Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your GEMINI_API_KEY"
echo "2. Run the backend: python server.py"
echo "3. Run the frontend: npm run dev"
echo ""
echo "For deployment to Render, see DEPLOYMENT.md"
echo "======================================"
