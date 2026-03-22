# Resume Upload Debugging Guide

## ✅ Changes Made

### Backend (app/routes/resume.py)
- ✅ Added comprehensive error logging
- ✅ Better error messages for each stage
- ✅ Proper JSON error responses
- ✅ Fixed sparse matrix issue with `.toarray()`
- ✅ Detailed console output for debugging

### Frontend (frontend/upload-resume.html)
- ✅ Better error message display
- ✅ Console logging for debugging
- ✅ Shows actual error details to users

## 🚀 How to Test

### Step 1: Start the Server
```powershell
cd c:\Users\dhana\Desktop\job-aggregator\backend
c:/Users/dhana/Desktop/job-aggregator/venv/Scripts/python.exe -m uvicorn app.main:app --reload
```

### Step 2: Monitor Terminal Output
When you upload a file, you should see detailed logs:
```
======================================================================
📁 RESUME UPLOAD STARTED
======================================================================
📂 Reading file: your_resume.pdf
✅ File size: 150.50 KB
📖 Extracting text...
✅ Text extracted: 5000 characters
🎯 Extracting skills...
✅ Skills found: ['Python', 'FastAPI', 'React', ...]
👤 Updating user record...
✅ User record updated
🔍 Starting job matching...
📊 Total jobs in database: 350
🚀 Processing matches...
✅ Prepared 350 job descriptions
🔢 Vectorizing 351 texts...
✅ Vectorizer output shape: (351, 251)
✅ Converted to dense: (351, 251)
⚙️  Calculating similarities...
✅ Matching complete!
✅ Found 50 job matches

📊 FINAL RESULTS:
   • Skills extracted: 15
   • Job matches found: 50
   • Resume saved as: user_1_20260321_120000_resume.pdf

✅ UPLOAD SUCCESSFUL
======================================================================
```

### Step 3: Check Browser Console
1. Open your browser (http://localhost:8000/upload-resume)
2. Press `F12` to open Developer Tools
3. Go to **Console** tab
4. Upload a resume
5. You should see:
   ```
   ✅ Resume uploaded successfully: {message: ..., skills_extracted: [...], matches_found: 50}
   ```

### Step 4: Check For Errors
If you see an error:
1. **Check terminal output** - detailed backend logs
2. **Check browser console** - error message and type
3. **Check Network tab** - response code and body

## 🧪 Quick Test with Sample Resume

Create a `test_resume.txt` file with basic content:
```
Skills: Python, JavaScript, React, FastAPI
Experience: 5 years as Software Engineer
Education: BS Computer Science
```

Then rename it to `test_resume.pdf` and try uploading.

## 🐛 If You Still Get Network Error

1. **Press F12** in browser
2. Go to **Network** tab
3. Upload resume
4. Find the `upload-resume` request
5. Click on it
6. Go to **Response** tab
7. Note the response - it will tell us exactly what failed

Then share:
- The response body
- The terminal logs
- The browser console errors

## 📋 File Locations

- **Backend endpoint:** `/api/resume/upload-resume`
- **Frontend page:** `/upload-resume`
- **Uploads saved:** `backend/uploads/resumes/`
- **Recommendations:** `/api/recommendations`

## ✨ Expected Flow

1. ✅ User logs in
2. ✅ Navigate to Upload Resume
3. ✅ Select PDF/DOCX file
4. ✅ Click "Upload & Process Resume"
5. ✅ Shows progress bar
6. ✅ Backend extracts text and skills
7. ✅ Backend matches with 350 jobs
8. ✅ Shows success with:
   - Extracted skills
   - Number of matches
9. ✅ Link to "View Recommendations"
10. ✅ Click link to see all matched jobs ranked by similarity

## 🚨 Common Issues

### "Network error" but no details in console
- Server might be down - check if uvicorn is running
- Token might be expired - try logging in again

### "File size exceeds 5MB"
- Make sure file is under 5MB
- PDF compression tools can help reduce size

### "Could not extract text from resume"
- PDF might be image-based (scanned document)
- Try a PDF with selectable text
- Or upload as DOCX file

### "0 job matches found"
- This is OK! Means no jobs matched,similarity threshold is 0.25 (25%)
- Try uploading a more detailed resume

## 📞 For Support

If error persists, provide:
1. The error message from browser console
2. The full terminal output
3. Steps to reproduce
