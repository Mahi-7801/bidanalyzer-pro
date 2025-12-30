# Quick Start Guide - Deploy to Render

## ⚡ Fast Track (5 Minutes)

### 1️⃣ Push to GitHub

```bash
cd "c:\Users\ameer\Downloads\Bidanalyzer Pro"

# Initialize and commit
git init
git add .
git commit -m "Initial commit - ready for deployment"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/bidanalyzer-pro.git
git branch -M main
git push -u origin main
```

### 2️⃣ Deploy on Render

1. **Go to**: https://dashboard.render.com/
2. **Click**: "New +" → "Blueprint"
3. **Connect**: Your GitHub repository
4. **Deploy**: Render will detect `render.yaml` and create 2 services

### 3️⃣ Add API Key

1. **Go to**: Your backend service (`bidanalyzer-api`)
2. **Navigate**: "Environment" tab
3. **Add variable**:
   - Key: `GEMINI_API_KEY`
   - Value: [Your Gemini API Key from https://makersuite.google.com/app/apikey]
4. **Save**

### 4️⃣ Update Frontend

After backend deploys successfully:

1. **Copy** backend URL (e.g., `https://bidanalyzer-api.onrender.com`)
2. **Edit** `src/App.jsx` line ~22:
   ```javascript
   const API_BASE_URL = import.meta.env.PROD 
     ? 'https://bidanalyzer-api.onrender.com'  // ← Your backend URL here
     : 'http://localhost:8000';
   ```
3. **Commit and push**:
   ```bash
   git add src/App.jsx
   git commit -m "Update API URL for production"
   git push
   ```

### 5️⃣ Done! 🎉

Your app is now live! Access it at:
- **Frontend**: `https://bidanalyzer-frontend.onrender.com`
- **Backend**: `https://bidanalyzer-api.onrender.com`

---

## 🔍 Troubleshooting

### Build Fails?
- Check logs in Render dashboard
- Verify `requirements.txt` and `package.json` are correct
- Ensure Python 3.11+ and Node 18+ in render.yaml

### API Not Working?
- Verify `GEMINI_API_KEY` is set in backend environment
- Check CORS settings in `server.py`
- Open browser console and check for errors

### PDF Generation Fails?
- html2image requires Chrome (included in Render's Python runtime)
- Check backend logs for specific errors

### Free Tier Spin Down?
- Render free tier spins down after 15min inactivity
- First request after spin-down takes ~30-60 seconds
- Upgrade to paid tier ($7/month) for always-on

---

## 📚 Full Documentation

For detailed instructions, see:
- **DEPLOYMENT.md** - Complete deployment guide
- **README.md** - Project overview and local setup

---

## 🆘 Need Help?

Common issues and solutions:
1. **"Application failed to respond"** → Check PORT env variable in server.py
2. **CORS errors** → Verify backend URL in frontend
3. **API quota exceeded** → Check usage in Google AI Studio
4. **Build timeout** → Contact Render support or optimize dependencies

---

**Happy Deploying! 🚀**
