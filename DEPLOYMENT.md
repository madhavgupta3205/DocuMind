# Deployment Guide for DocuMind AI

## Prerequisites

- GitHub account (already set up ✓)
- Render.com account (free)
- Vercel account (free)
- MongoDB Atlas account (free)
- Groq API key (free)

---

## 1. MongoDB Atlas Setup (5 minutes)

1. **Create Cluster:**
   - Go to https://cloud.mongodb.com
   - Sign up / Log in
   - Create FREE cluster (M0)
   - Choose AWS / Region closest to you
   - Cluster name: `documind-cluster`

2. **Database Access:**
   - Database Access → Add New Database User
   - Username: `documind_user`
   - Password: Generate secure password (save it!)
   - Built-in Role: `Atlas admin`

3. **Network Access:**
   - Network Access → Add IP Address
   - Choose: `0.0.0.0/0` (Allow access from anywhere)
   - Confirm

4. **Get Connection String:**
   - Clusters → Connect → Connect your application
   - Driver: Python, Version: 3.11 or later
   - Copy connection string:
   ```
   mongodb+srv://documind_user:<password>@documind-cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
   - Replace `<password>` with your actual password
   - Save this for later!

---

## 2. Groq API Key (2 minutes)

1. Go to https://console.groq.com
2. Sign up / Log in with GitHub
3. API Keys → Create API Key
4. Copy the key (starts with `gsk_...`)
5. Save for later!

---

## 3. Deploy Backend to Render.com (10 minutes)

1. **Create Account:**
   - Go to https://render.com
   - Sign up with GitHub
   - Authorize Render to access your repositories

2. **Create Web Service:**
   - Dashboard → New → Web Service
   - Connect Repository: `madhavgupta3205/DocuMind`
   - Name: `documind-backend`
   - Region: Oregon (US West) - Closest to free tier
   - Branch: `main`
   - Root Directory: `.` (leave as is)
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

3. **Add Disk for ChromaDB:**
   - Advanced → Add Disk
   - Name: `chroma-storage`
   - Mount Path: `/opt/render/project/src/chroma_db`
   - Size: 1 GB

4. **Environment Variables:**
   Click "Advanced" → "Add Environment Variable" for each:
   
   ```
   MONGODB_URL = mongodb+srv://documind_user:<password>@....mongodb.net/documind_ai
   GROQ_API_KEY = gsk_your_groq_api_key_here
   JWT_SECRET_KEY = (click "Generate" - Render will create random string)
   ALLOWED_ORIGINS = https://documind.vercel.app
   ```

5. **Deploy:**
   - Click "Create Web Service"
   - Wait 5-10 minutes for build
   - Once deployed, copy your backend URL:
   ```
   https://documind-backend.onrender.com
   ```

6. **Test Backend:**
   - Visit: https://documind-backend.onrender.com/
   - Should see: `{"name":"DocuMind AI","version":"2.0.0","status":"running"}`
   - Visit: https://documind-backend.onrender.com/api/docs
   - Should see Swagger API documentation

---

## 4. Deploy Frontend to Vercel (5 minutes)

1. **Create Account:**
   - Go to https://vercel.com
   - Sign up with GitHub
   - Authorize Vercel

2. **Import Project:**
   - Dashboard → Add New → Project
   - Import Git Repository: `madhavgupta3205/DocuMind`
   - Select repository
   - Configure Project:
     - Framework Preset: `Vite`
     - Root Directory: `frontend`
     - Build Command: `npm run build` (auto-detected)
     - Output Directory: `dist` (auto-detected)

3. **Environment Variables (IMPORTANT!):**
   Add this environment variable in Vercel dashboard:
   
   **Key:** `VITE_API_URL`
   **Value:** `https://documind-backend.onrender.com` (or your Render backend URL)
   
   ⚠️ **Note:** This is set in Vercel's dashboard, NOT in your code!
   - The backend URL is public-facing (users need it)
   - But it's protected by JWT authentication
   - Never commit API keys or secrets to GitHub!

4. **Deploy:**
   - Click "Deploy"
   - Wait 2-3 minutes
   - Your app will be live at:
   ```
   https://documind.vercel.app
   ```
   (Or custom Vercel URL like: https://documind-madhavs-projects.vercel.app)

5. **Update Backend CORS:**
   - Copy your Vercel URL
   - Go back to Render dashboard
   - Your service → Environment
   - Edit `ALLOWED_ORIGINS`:
   ```
   https://your-vercel-url.vercel.app
   ```
   - Save changes (will auto-redeploy)

---

## 5. Test Your Deployed App (5 minutes)

1. **Visit Your Frontend:**
   - Go to your Vercel URL
   - Should see DocuMind AI login page

2. **Create Account:**
   - Sign up with email/password
   - Should redirect to chat interface

3. **Upload Document:**
   - Click "Manage Documents"
   - Upload a PDF/TXT file
   - Wait for processing (30-60 seconds)

4. **Test Query:**
   - Type a question about your document
   - Should get AI response with streaming

5. **Test Document Selector:**
   - Upload another document
   - Use dropdown to select specific document
   - Ask questions - responses should be filtered

---

## 6. Security Best Practices ✅

**What's Safe to Expose:**
- ✅ Backend URL (public-facing, protected by JWT auth)
- ✅ Frontend URL (public website)
- ✅ MongoDB connection string in Render env vars (encrypted)

**What to NEVER Commit to GitHub:**
- ❌ `.env` files with secrets
- ❌ JWT_SECRET_KEY
- ❌ GROQ_API_KEY
- ❌ MongoDB passwords in plain text
- ❌ API tokens or credentials

**How to Handle Secrets:**
1. Set environment variables in Render/Vercel dashboards
2. Use `.gitignore` to exclude `.env` files
3. Use "Generate" button in Render for JWT secrets
4. Rotate keys periodically

---

## 🎉 Deployment Complete!

Your app is now live at:
- **Frontend:** https://documind.vercel.app
- **Backend:** https://documind-backend.onrender.com
- **Database:** MongoDB Atlas (Free M0 cluster)
- **Vector DB:** ChromaDB (1GB persistent disk on Render)

---

## 📊 Resource Limits (Free Tier)

| Service | Limit | Your Usage |
|---------|-------|------------|
| Render | 750 hours/month, 512MB RAM | ~24/7 uptime |
| Vercel | 100GB bandwidth | ~1,000 users/month |
| MongoDB Atlas | 512MB storage | ~50MB for 100 chats |
| ChromaDB Disk | 1GB storage | ~250MB for 50 documents |

---

## ⚠️ Important Notes

1. **Cold Starts:** Render free tier sleeps after 15 min inactivity
   - First request takes ~30 seconds to wake up
   - Subsequent requests are instant

2. **Storage Persistence:**
   - ChromaDB data persists across deploys
   - Uploads folder is temporary (deleted on redeploy)
   - Documents are stored in ChromaDB (persistent)

3. **Environment Variables:**
   - Never commit `.env` file to GitHub
   - Set them in Render/Vercel dashboards
   - JWT_SECRET_KEY should be random

4. **CORS:**
   - Update `ALLOWED_ORIGINS` if you change Vercel domain
   - Add custom domain URLs when ready

---

## 🔧 Troubleshooting

**Backend not responding:**
- Check Render logs: Dashboard → Your Service → Logs
- Verify environment variables are set
- Test MongoDB connection string

**Frontend can't connect:**
- Check CORS settings in backend
- Verify `VITE_API_URL` in Vercel
- Check browser console for errors

**Upload failing:**
- Check file size (max 50MB)
- Verify Groq API key is valid
- Check Render logs for errors

**Queries not working:**
- Ensure documents uploaded successfully
- Check ChromaDB disk is mounted
- Verify Groq API credits available

---

## 🚀 Next Steps

1. **Custom Domain:** Add to Vercel (free)
2. **Analytics:** Add Vercel Analytics (free)
3. **Monitoring:** Set up Render health checks
4. **Backups:** Export MongoDB data periodically

---

Need help? Check the logs or contact support! 🎯
