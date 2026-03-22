# Expired Jobs Cleanup Implementation

## Overview
Implemented automatic filtering and cleanup of expired jobs throughout the application. Users now only see jobs with valid timelines (application deadline hasn't passed).

---

## Changes Made

### 1. **Backend API Routes** 

#### File: `backend/app/routes/jobs.py`

**Modified 4 endpoints to filter expired jobs:**

1. **GET `/api/jobs/search`** - Job Search Endpoint
   - Added filter: `(Opportunity.application_end_date > now) OR (Opportunity.application_end_date == NULL)`
   - Only returns jobs with future deadlines or no deadline (indefinite)
   - Prevents expired jobs from appearing in search results

2. **GET `/api/jobs/{job_id}`** - Job Details Endpoint
   - Added expiry check before returning job details
   - Returns 404 "Job not found or has expired" if job has expired
   - Ensures users cannot access expired job details

3. **GET `/api/jobs/portals/list`** - Portal Listing Endpoint
   - Only returns portals that have active (non-expired) jobs
   - Cleans up portal list to show only relevant job sources

4. **GET `/api/jobs/stats/summary`** - Statistics Endpoint
   - Updated to count only active jobs in statistics
   - Provides accurate job counts and breakdowns by type/portal

#### File: `backend/app/routes/recommendations.py`

**Modified 1 endpoint:**

1. **GET `/api/recommendations`** - Recommendations Endpoint
   - Added expiry filter in database query
   - Only returns job recommendations with valid application deadlines
   - Ensures personalized matches are current and applicable

---

### 2. **Automatic Cleanup Service**

#### File: `backend/app/scheduler/tasks.py`

**Added automatic cleanup task:**

- **New Function:** `cleanup_expired_jobs()`
  - Runs automatically every 24 hours
  - Removes:
    - Expired job opportunities
    - Related similarity scores
    - Related email notifications
    - Related job vectors
  - Prevents database bloat from old jobs
  - Logs all deletions for audit trail

- **Updated:** `start_scheduler()`
  - Now schedules cleanup task daily
  - Maintains three background tasks:
    1. Vectorization (hourly)
    2. Matching & Notifications (every 2 hours)
    3. **Expired Job Cleanup (daily - NEW)**

---

### 3. **Manual Cleanup Utility**

#### File: `backend/cleanup_expired_jobs.py` (NEW)

**Standalone cleanup script with these features:**

```bash
# View statistics about expired jobs
python cleanup_expired_jobs.py

# Manually clean up expired jobs
python cleanup_expired_jobs.py --cleanup
```

**Features:**
- Shows comprehensive expiry statistics
- Displays which jobs are expiring soon
- Provides confirmation before deletion
- Manual control over cleanup process
- Detailed logging of all removed records

---

## How It Works

### Job Expiry Timeline

```
Three States of a Job:
1. ACTIVE      → application_end_date > NOW  ✅ Visible to users
2. EXPIRED     → application_end_date < NOW  ❌ Hidden/Deleted
3. INDEFINITE  → application_end_date = NULL ✅ Always visible
```

### Data Cleanup Process

```
When a job expires:
1. Job becomes invisible in search/recommendations
2. Daily scheduler detects and marks for removal
3. All related data is cascade-deleted:
   - Similarity scores (user-job matches)
   - Email notifications (to avoid stale emails)
   - Job vectors (TF-IDF embeddings)
   - Job record itself
4. Database is cleaned and optimized
```

---

## API Changes Summary

| Endpoint | Change | Behavior |
|----------|--------|----------|
| `/jobs/search` | Filtered | Only shows active jobs |
| `/jobs/{id}` | Filtered | Returns 404 if expired |
| `/jobs/portals/list` | Filtered | Only active portals |
| `/jobs/stats/summary` | Filtered | Counts only active jobs |
| `/recommendations` | Filtered | Only active recommendations |

---

## Database Impact

### What Gets Deleted
- Opportunities with `application_end_date < NOW()`
- All related SimilarityScores
- All related EmailNotifications  
- All related JobVectors

### What's Preserved
- Jobs with `application_end_date = NULL` (indefinite)
- Jobs with `application_end_date > NOW()` (still active)
- User data remains untouched

---

## Frontend Changes

**Dashboard Page** (`frontend/dashboard.html`)
- No UI changes needed
- API filtering handles expired jobs automatically
- Users automatically see only valid jobs
- Search and filters work with active jobs only

---

## Usage Instructions

### Automatic Cleanup
The system automatically:
- Runs cleanup every 24 hours
- No manual action required
- Logs progress in server console
- Continues to function during application runtime

### Manual Cleanup (Optional)

```bash
# SSH into your server or local terminal
cd /path/to/backend

# Check expiry statistics
python cleanup_expired_jobs.py

# Manually cleanup (with confirmation)
python cleanup_expired_jobs.py --cleanup
```

### Example Output
```
📊 Job Expiry Statistics
============================================================
Total jobs in database:     15,432
Active jobs (not expired):  14,201 (92.0%)
Expired jobs:               1,231 (8.0%)
Jobs with no end date:      0 (0.0%)
============================================================

💡 To clean up expired jobs, run:
   python cleanup_expired_jobs.py --cleanup
```

---

## Monitoring & Logs

**Server console logs show:**
```
✅ [2026-03-21 10:30:15] No expired jobs to cleanup
```

Or if cleanup occurs:
```
🗑️  [2026-03-21 10:30:15] Starting cleanup of 245 expired jobs...
✅ [2026-03-21 10:30:18] Cleanup completed!
   • Expired jobs removed: 245
   • Related records deleted: 892
```

---

## Database Schema Requirements

Relies on existing columns in `opportunities` table:
- `application_end_date` (DateTime) - Job application deadline
- `id` (Primary Key)

No schema changes needed - uses existing fields!

---

## Performance Notes

- ✅ Filter applied at database query level (efficient)
- ✅ No additional API calls needed
- ✅ Cleanup runs in background (non-blocking)
- ✅ Cascading deletes handled automatically
- ✅ No impact on new job creation or user experience

---

## Troubleshooting

**Issue: Users still seeing expired jobs**
- Solution: Check if `application_end_date` is properly set in scrapers
- Verify database has correct timestamps
- Restart backend service

**Issue: Cleanup not running**
- Solution: Verify scheduler is started in main.py
- Check logs for scheduler errors
- Can manually run: `python cleanup_expired_jobs.py --cleanup`

**Issue: Want to keep expired jobs for history**
- Solution: Don't run cleanup script
- Jobs remain visible but filtered from UI
- Only delete if needed

---

## Summary

✅ **Expired jobs are now:**
- Automatically filtered from all API responses
- Removed daily from database (stored procedures)
- No longer visible to users through any interface
- Completely behind the scenes - users see only valid jobs

✅ **Users can only see:**
- Jobs with future application deadlines
- Jobs with no deadline (indefinite)
- Only active opportunities

✅ **System benefits:**
- Cleaner database over time
- Better search performance
- No stale job recommendations
- Automated maintenance with no manual work

---

## Files Modified
1. ✅ `backend/app/routes/jobs.py` - API filtering
2. ✅ `backend/app/routes/recommendations.py` - Recommendation filtering
3. ✅ `backend/app/scheduler/tasks.py` - Automatic cleanup
4. ✅ `backend/cleanup_expired_jobs.py` - New manual utility

**No database schema changes required!**
