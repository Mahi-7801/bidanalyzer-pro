---
title: Bidanalyzer Pro
emoji: 📊
colorFrom: green
colorTo: red
sdk: docker
pinned: false
license: apache-2.0
short_description: AI-powered tender and bid document analyzer
---

# Bidanalyzer Pro

AI-powered tool to analyze and summarize tender / bid documents.

# BidAnalyzer Pro

A powerful document analysis tool that extracts and analyzes tender/bid documents using AI (Google Gemini) and generates professional PDF reports.

## 🚀 Features

- **AI-Powered Analysis**: Uses Google Gemini 2.5 Flash for intelligent document extraction
- **Multi-Language Support**: Translate reports to multiple languages (Hindi, Telugu, Tamil, Spanish, French, etc.)
- **PDF Generation**: Creates professional, branded PDF reports with custom templates
- **React Frontend**: Modern, responsive UI built with React & Vite
- **FastAPI Backend**: High-performance Python backend with async support

## 📋 Tech Stack

### Frontend
- React 19
- Vite
- Lucide React (icons)
- HTML2Canvas & jsPDF

### Backend
- FastAPI
- Google Generative AI (Gemini)
- PDFPlumber (text extraction)
- ReportLab (PDF generation)
- Deep Translator

## 🔧 Local Development

### Prerequisites
- Node.js 18+ 
- Python 3.11+
- Google Gemini API Key

### Setup

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd "Bidanalyzer Pro"
```

2. **Install Frontend Dependencies**
```bash
npm install
```

3. **Install Backend Dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure Environment Variables**
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

5. **Run Development Servers**

**Backend (Terminal 1):**
```bash
python server.py
# Runs on http://localhost:8000
```

**Frontend (Terminal 2):**
```bash
npm run dev
# Runs on http://localhost:5173
```

## 🌐 Deployment to Render

### Option 1: Using Render Blueprint (Recommended)

1. **Push to GitHub**
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-github-repo-url>
git push -u origin main
```

2. **Deploy on Render**
   - Go to [Render Dashboard](https://dashboard.render.com/)
   - Click "New" → "Blueprint"
   - Connect your GitHub repository
   - Render will automatically detect `render.yaml` and create both services

3. **Configure Environment Variables**
   - Go to your backend service settings
   - Add environment variable: `GEMINI_API_KEY=<your-key>`

4. **Update Frontend API URL**
   - After backend deploys, copy its URL (e.g., `https://bidanalyzer-api.onrender.com`)
   - Update the API URL in `src/App.jsx` (search for `localhost:8000`)
   - Redeploy frontend

### Option 2: Manual Deployment

#### Deploy Backend
1. Go to Render Dashboard → New → Web Service
2. Connect your repository
3. Configure:
   - **Name**: bidanalyzer-api
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
4. Add environment variable: `GEMINI_API_KEY`
5. Deploy

#### Deploy Frontend
1. Go to Render Dashboard → New → Static Site
2. Connect your repository
3. Configure:
   - **Name**: bidanalyzer-frontend
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`
4. Deploy

## 🔑 Environment Variables

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

## 📁 Project Structure

```
Bidanalyzer Pro/
├── src/                    # React frontend source
│   ├── App.jsx            # Main application component
│   ├── main.jsx           # React entry point
│   └── index.css          # Global styles
├── public/                # Static assets
├── server.py              # FastAPI backend
├── requirements.txt       # Python dependencies
├── package.json           # Node dependencies
├── render.yaml            # Render deployment config
├── vite.config.js         # Vite configuration
└── README.md              # This file
```

## 🎯 API Endpoints

- `POST /analyze` - Analyze uploaded document
- `POST /translate` - Translate analysis results
- `POST /generate-pdf` - Generate PDF report

## 🐛 Troubleshooting

### Common Issues

**1. CORS Errors**
- Ensure backend URL is correctly configured in frontend
- Check CORS settings in `server.py`

**2. PDF Generation Fails**
- Ensure Chrome/Chromium is installed on the server
- For Render, this is included in the Python runtime

**3. API Key Issues**
- Verify GEMINI_API_KEY is set in Render environment variables
- Check API quota limits in Google AI Studio

## 📝 License

MIT License - feel free to use this project for your own purposes!

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

---

**Made with ❤️ using React, FastAPI, and Google Gemini**
