# Deployment Guide for Render.com

This guide will walk you through deploying BidAnalyzer Pro on Render with both frontend and backend services.

## Prerequisites

✅ GitHub account  
✅ Render account (free tier available)  
✅ Google Gemini API Key  
✅ Project pushed to GitHub repository  

---

## 🚀 Quick Deploy (Using Blueprint)

### Step 1: Prepare Your Repository

1. **Initialize Git** (if not already done):
```bash
cd "c:\Users\ameer\Downloads\Bidanalyzer Pro"
git init
git add .
git commit -m "Initial commit - ready for Render deployment"
```

2. **Create GitHub Repository**:
   - Go to https://github.com/new
   - Create a new repository (e.g., `bidanalyzer-pro`)
   - Don't initialize with README/License/gitignore

3. **Push to GitHub**:
```bash
git remote add origin https://github.com/YOUR_USERNAME/bidanalyzer-pro.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Render

1. **Go to Render Dashboard**: https://dashboard.render.com/

2. **Create New Blueprint**:
   - Click "New +" button
   - Select "Blueprint"
   
3. **Connect GitHub Repository**:
   - Connect your GitHub account (if first time)
   - Select your `bidanalyzer-pro` repository
   - Click "Connect"

4. **Render Auto-Detection**:
   - Render will detect `render.yaml`
   - It will show 2 services:
     - `bidanalyzer-api` (Backend)
     - `bidanalyzer-frontend` (Frontend)
   - Review the configuration
   - Click "Apply"

### Step 3: Configure Environment Variables

1. **Backend Service Configuration**:
   - Go to your `bidanalyzer-api` service
   - Navigate to "Environment" tab
   - Add environment variable:
     ```
     Key: GEMINI_API_KEY
     Value: <paste-your-gemini-api-key>
     ```
   - Click "Save Changes"

2. **Get Your API Key**:
   - Visit: https://makersuite.google.com/app/apikey
   - Create a new API key
   - Copy and paste into Render

### Step 4: Update Frontend API URL

1. **Wait for Backend to Deploy**:
   - Check deployment logs for backend service
   - Copy the backend URL (e.g., `https://bidanalyzer-api.onrender.com`)

2. **Update Frontend Code**:
   - Open `src/App.jsx`
   - Find the API URL configuration (around line 10-20)
   - Replace `http://localhost:8000` with your backend URL
   
   Example:
   ```javascript
   const API_URL = 'https://bidanalyzer-api.onrender.com';
   ```

3. **Push Update**:
```bash
git add src/App.jsx
git commit -m "Update API URL for production"
git push
```

4. Render will automatically redeploy the frontend!

---

## 🔄 Manual Deployment (Alternative Method)

If you prefer to deploy services separately:

### A. Deploy Backend First

1. **New Web Service**:
   - Dashboard → New → Web Service
   - Connect repository

2. **Configuration**:
   ```
   Name: bidanalyzer-api
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn server:app --host 0.0.0.0 --port $PORT
   ```

3. **Environment Variables**:
   - Add `GEMINI_API_KEY`

4. **Deploy**

### B. Deploy Frontend

1. **New Static Site**:
   - Dashboard → New → Static Site
   - Connect repository

2. **Configuration**:
   ```
   Name: bidanalyzer-frontend
   Build Command: npm install && npm run build
   Publish Directory: dist
   ```

3. **Auto-Deploy**: Enable on main branch

4. **Deploy**

---

## 📝 Post-Deployment Checklist

### Backend Service
- [ ] Service is live and shows "Live" status
- [ ] Health check endpoint responds (visit your-backend-url.onrender.com)
- [ ] Environment variable `GEMINI_API_KEY` is set
- [ ] No error logs in deployment logs

### Frontend Service
- [ ] Build completed successfully
- [ ] Site is accessible
- [ ] API calls work (test file upload)
- [ ] No CORS errors in browser console

---

## 🔍 Testing Your Deployment

1. **Visit Frontend URL**: `https://bidanalyzer-frontend.onrender.com`

2. **Test Upload**:
   - Click "Upload Document"
   - Select a PDF file
   - Wait for analysis
   - Verify results display correctly

3. **Test PDF Generation**:
   - Click "Download Report"
   - Verify PDF downloads successfully

4. **Test Translation** (if applicable):
   - Select a language
   - Click translate
   - Verify translation works

---

## ⚙️ Configuration Files Explained

### `render.yaml`
Blueprint configuration for both services. Render reads this to create services automatically.

### `requirements.txt`
Python dependencies for backend. Includes FastAPI, Gemini SDK, PDF tools, etc.

### `.env.example`
Template for environment variables. Copy to `.env` for local development.

---

## 🐛 Common Issues & Solutions

### Issue 1: "Application failed to respond"
**Solution**: Check if `PORT` environment variable is used correctly
```python
# In server.py (already configured)
uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
```

### Issue 2: CORS Errors
**Solution**: Verify backend CORS settings allow frontend domain
```python
# In server.py (already configured)
allow_origins=["*"]  # Or specify your frontend URL
```

### Issue 3: PDF Generation Fails
**Solution**: Ensure html2image can find browser. Render includes Chrome in Python runtime.

### Issue 4: Build Fails - Dependencies
**Solutions**:
- **Python**: Check `requirements.txt` versions
- **Node**: Ensure Node 18+ in render.yaml
- Check build logs for specific errors

### Issue 5: API Key Not Working
**Solutions**:
- Verify key is correct in Render dashboard
- Check API quota in Google AI Studio
- Ensure no extra spaces in environment variable

---

## 💰 Cost Estimation

### Free Tier (Render)
- **Backend**: Free for 750 hours/month
- **Frontend**: Free unlimited static hosting
- **Limitations**: 
  - Services spin down after 15min inactivity (free tier)
  - First request after spin-down takes ~30-60 seconds

### Paid Tier ($7/month per service)
- Always-on services
- No spin-down delays
- Better performance
- More resources

---

## 🔐 Security Best Practices

1. **Never commit `.env` file** - Already in `.gitignore`
2. **Use environment variables** for API keys
3. **Rotate API keys** periodically
4. **Monitor usage** in Google AI Studio
5. **Set up CORS** properly in production

---

## 📊 Monitoring

### Render Dashboard
- View logs in real-time
- Monitor resource usage
- Check deployment history
- Set up alerts

### Google AI Studio
- Monitor API usage
- Check quota limits
- Track errors

---

## 🚀 Next Steps

After deployment:

1. **Custom Domain** (Optional):
   - Add custom domain in Render settings
   - Update DNS records
   - Enable HTTPS (automatic)

2. **Performance Optimization**:
   - Enable caching
   - Compress assets
   - Optimize images

3. **Monitoring**:
   - Set up error tracking (e.g., Sentry)
   - Add analytics
   - Monitor API usage

4. **Scaling**:
   - Upgrade to paid tier for always-on
   - Add Redis for caching
   - Use CDN for assets

---

## 📞 Support

- **Render Docs**: https://render.com/docs
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Vite Docs**: https://vitejs.dev/
- **Google AI**: https://ai.google.dev/

---

**Happy Deploying! 🎉**
