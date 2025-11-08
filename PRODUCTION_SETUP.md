# Production Deployment Guide - Pinecone + Railway/Render

## 🎯 Architecture Overview

**Production Stack:**
- **Vector Database:** Pinecone (1GB free, persistent, production-grade)
- **Backend:** Railway or Render (both support Pinecone)
- **Frontend:** Vercel
- **Database:** MongoDB Atlas
- **LLM:** Groq API

**Why This Stack:**
- ✅ Fully managed, no infrastructure maintenance
- ✅ All free tiers (no credit card for most)
- ✅ Production-grade performance and reliability
- ✅ Auto-scaling and global CDN
- ✅ Persistent vector storage with backups

---

## 📋 Prerequisites

- GitHub account with DocuMind repository
- Email addresses for account signups
- 30 minutes setup time

---

## Step 1: MongoDB Atlas (5 minutes)

1. **Create Account & Cluster:**
   ```
   URL: https://cloud.mongodb.com
   - Sign up with Google/GitHub
   - Create FREE M0 cluster
   - Choose: AWS, us-east-1 (or closest region)
   - Name: documind-cluster
   ```

2. **Database Access:**
   ```
   Security → Database Access → Add New User
   - Username: documind_user
   - Password: <generate strong password>
   - Role: Atlas admin
   - Click "Add User"
   ```

3. **Network Access:**
   ```
   Security → Network Access → Add IP Address
   - Select: "Allow access from anywhere" (0.0.0.0/0)
   - Confirm
   ```

4. **Get Connection String:**
   ```
   - Click "Connect" on your cluster
   - Choose "Connect your application"
   - Driver: Python, Version: 3.12 or later
   - Copy connection string:
     mongodb+srv://documind_user:<password>@cluster0.xxxxx.mongodb.net/
   - Replace <password> with your actual password
   - Save this for later!
   ```

---

## Step 2: Groq API Key (2 minutes)

1. **Get API Key:**
   ```
   URL: https://console.groq.com
   - Sign up with Google/GitHub
   - Go to "API Keys" section
   - Click "Create API Key"
   - Name: "DocuMind Production"
   - Copy the key (starts with gsk_...)
   - Save this for later!
   ```

---

## Step 3: Pinecone Setup (5 minutes)

1. **Create Account:**
   ```
   URL: https://www.pinecone.io
   - Sign up (free tier, no credit card)
   - Verify email
   ```

2. **Create API Key:**
   ```
   Dashboard → API Keys → Create API Key
   - Name: "DocuMind"
   - Copy the key
   - Save this for later!
   ```

3. **Index Setup:**
   ```
   The app will auto-create the index on first run, but you can verify:
   - Index name: documind
   - Dimensions: 384
   - Metric: cosine
   - Cloud: AWS
   - Region: us-east-1
   ```

---

## Step 4: Deploy Backend to Railway (10 minutes)

**Why Railway:** $5/month credit (~500 hours), simpler than Render, good performance

1. **Create Account:**
   ```
   URL: https://railway.app
   - Sign up with GitHub
   - You'll get $5 credit automatically
   ```

2. **Deploy from GitHub:**
   ```
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your DocuMind repository
   - Railway detects Python automatically
   ```

3. **Set Environment Variables:**
   ```
   Project → Variables tab → Add these:

   MONGODB_URL=mongodb+srv://documind_user:<password>@cluster0.xxxxx.mongodb.net/
   DATABASE_NAME=documind_ai
   GROQ_API_KEY=gsk_your_groq_key_here
   JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-characters-random
   
   # Pinecone Configuration (Production Vector DB)
   USE_PINECONE=true
   PINECONE_API_KEY=your_pinecone_api_key_here
   PINECONE_INDEX_NAME=documind
   PINECONE_NAMESPACE=documents
   
   # CORS (update after deploying frontend)
   FRONTEND_URL=https://your-app.vercel.app
   ALLOWED_ORIGINS=https://your-app.vercel.app
   ```

4. **Generate JWT Secret:**
   ```bash
   # Run locally to generate a secure key:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

5. **Deploy & Get URL:**
   ```
   - Railway builds automatically (2-3 minutes)
   - Check "Deployments" tab for status
   - Once deployed, go to "Settings" → "Generate Domain"
   - Copy the URL: https://documind-production.up.railway.app
   - Save this for later!
   ```

6. **Verify Deployment:**
   ```
   Visit: https://your-railway-url.railway.app/docs
   - Should see FastAPI Swagger UI
   - Test the /health endpoint
   ```

---

## Step 5: Deploy Frontend to Vercel (5 minutes)

1. **Create Account:**
   ```
   URL: https://vercel.com
   - Sign up with GitHub
   ```

2. **Import Project:**
   ```
   - Click "New Project"
   - Import your DocuMind GitHub repository
   - Framework Preset: Vite
   - Root Directory: ./frontend
   ```

3. **Configure Build Settings:**
   ```
   Build Command: npm run build
   Output Directory: dist
   Install Command: npm install
   ```

4. **Set Environment Variable:**
   ```
   Project Settings → Environment Variables
   
   Variable: VITE_API_URL
   Value: https://your-railway-url.railway.app
   Environment: Production, Preview, Development
   ```

5. **Deploy:**
   ```
   - Click "Deploy"
   - Wait 2-3 minutes
   - Copy the deployment URL: https://documind.vercel.app
   ```

6. **Update Backend CORS:**
   ```
   Go back to Railway:
   - Update FRONTEND_URL variable with Vercel URL
   - Update ALLOWED_ORIGINS variable
   - Redeploy will happen automatically
   ```

---

## Step 6: Testing (5 minutes)

1. **Create Account:**
   ```
   - Visit your Vercel URL
   - Click "Sign Up"
   - Create account: test@example.com / password123
   ```

2. **Upload Document:**
   ```
   - Click "Manage Documents" button
   - Upload a PDF (test with < 5MB)
   - Wait for processing (should see chunk count)
   ```

3. **Test Query:**
   ```
   - Type a question about your document
   - Should see streaming response
   - Verify document selector dropdown shows your document
   ```

4. **Check Pinecone:**
   ```
   - Go to Pinecone dashboard
   - Select "documind" index
   - Should see vectors stored
   - Check stats for storage usage
   ```

---

## 🔍 Troubleshooting

### Backend Issues:

**"Module not found" errors:**
```bash
# Check railway.json has correct build command:
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  }
}
```

**Pinecone connection fails:**
```
- Verify PINECONE_API_KEY is correct
- Check USE_PINECONE=true (not "True" or "1")
- Ensure index region is us-east-1
- Check Pinecone dashboard for index status
```

**MongoDB connection fails:**
```
- Check password has no special characters (or URL-encode them)
- Verify IP whitelist includes 0.0.0.0/0
- Test connection string format
```

**CORS errors:**
```
- Update ALLOWED_ORIGINS with exact Vercel URL
- Include https:// prefix
- Redeploy backend after changes
```

### Frontend Issues:

**API calls fail:**
```
- Check VITE_API_URL in Vercel environment variables
- Verify backend is running (visit /docs endpoint)
- Check browser console for CORS errors
```

**Build fails:**
```
- Ensure Root Directory is set to "frontend"
- Check package.json has all dependencies
- Verify Node version (should use latest)
```

---

## 📊 Resource Usage (Free Tier Limits)

| Service | Limit | Your Usage (10-50 docs) |
|---------|-------|------------------------|
| Pinecone | 1GB storage, 100K vectors | ~250MB, ~10K vectors |
| Railway | $5 credit (~500 hrs) | 24/7 = ~20 days/month |
| Vercel | 100GB bandwidth | ~1GB for 1000 users |
| MongoDB Atlas | 512MB storage | ~50MB for 100 chats |
| Groq | 30 req/min free | ~10 queries/min avg |

**Cost After Free Tier:**
- Railway: $5/month for 24/7 uptime
- Pinecone: Free tier sufficient for most use
- Vercel: Free tier covers most hobby projects
- MongoDB: Free tier usually sufficient

---

## 🔒 Security Best Practices

1. **Never commit .env files:**
   ```bash
   # Already in .gitignore:
   .env
   .env.*
   frontend/.env*
   ```

2. **Use strong JWT secret:**
   ```bash
   # Generate:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Rotate API keys regularly:**
   - Groq: Every 90 days
   - Pinecone: Every 90 days
   - MongoDB: Every 90 days

4. **Monitor logs:**
   ```
   Railway: Deployments → View Logs
   Vercel: Deployments → Function Logs
   Pinecone: Dashboard → Monitoring
   ```

---

## 🚀 Performance Optimization

1. **Pinecone Index Settings:**
   ```
   - Use cosine similarity for semantic search
   - Enable metadata filtering for multi-tenancy
   - Monitor query latency in dashboard
   ```

2. **Railway Optimization:**
   ```
   - Use NIXPACKS builder (auto-optimized)
   - Enable automatic deploys from main branch
   - Monitor memory usage in metrics
   ```

3. **Vercel Edge Functions:**
   ```
   - Already optimized with Vite
   - Uses edge network for fast global access
   - Automatic image optimization
   ```

---

## 📈 Scaling Path

**When Free Tier Isn't Enough:**

1. **Pinecone:** Upgrade to Standard ($70/mo for 10GB)
2. **Railway:** Add $5/month for continued service
3. **MongoDB:** M10 cluster ($57/mo for 10GB)
4. **Vercel:** Pro plan ($20/mo for better bandwidth)

**Alternative: Self-Hosted:**
- AWS EC2 + EBS volumes (~$20/mo)
- DigitalOcean Droplet + Spaces (~$18/mo)
- Requires more maintenance but cheaper at scale

---

## ✅ Post-Deployment Checklist

- [ ] MongoDB cluster is running
- [ ] Pinecone index is created and accessible
- [ ] Backend deployed on Railway/Render
- [ ] Frontend deployed on Vercel
- [ ] Environment variables set correctly
- [ ] CORS configured properly
- [ ] Test signup and login working
- [ ] Document upload successful
- [ ] Query returns results
- [ ] Document selector shows documents
- [ ] Vectors stored in Pinecone dashboard
- [ ] All API endpoints accessible

---

## 🎉 Success!

Your DocuMind AI is now production-ready with:
- ✅ Persistent vector storage (Pinecone)
- ✅ Scalable backend (Railway/Render)
- ✅ Fast global frontend (Vercel)
- ✅ Secure authentication (JWT)
- ✅ Enhanced RAG with LLM-powered retrieval
- ✅ Document management dashboard
- ✅ Multi-document query filtering

**Next Steps:**
1. Share your Vercel URL with users
2. Monitor usage in dashboards
3. Set up custom domain (optional)
4. Add analytics (optional)
5. Consider upgrading tiers as you grow

**Support:**
- GitHub Issues: Report bugs
- Pinecone Docs: https://docs.pinecone.io
- Railway Docs: https://docs.railway.app
- Vercel Docs: https://vercel.com/docs
