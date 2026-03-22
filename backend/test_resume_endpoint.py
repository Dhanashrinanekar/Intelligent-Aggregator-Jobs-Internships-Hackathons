#!/usr/bin/env python3
"""
Quick test to verify the resume upload endpoint
Run this to check if everything is working
"""
import sys
sys.path.insert(0, '.')

print("🧪 Testing Resume Upload Endpoint...")
print("=" * 60)

# Test 1: Import checks
print("\n1️⃣  Checking imports...")
try:
    from app.routes.resume import router
    print("   ✅ Resume router imported")
except Exception as e:
    print(f"   ❌ Error importing resume router: {e}")
    sys.exit(1)

try:
    from app.main import app
    print("   ✅ FastAPI app imported")
except Exception as e:
    print(f"   ❌ Error importing app: {e}")
    sys.exit(1)

try:
    from app.services.resume_parser import ResumeParser
    print("   ✅ ResumeParser imported")
except Exception as e:
    print(f"   ❌ Error importing ResumeParser: {e}")
    sys.exit(1)

# Test 2: Check routes
print("\n2️⃣  Checking registered routes...")
resume_routes = [r.path for r in router.routes if hasattr(r, 'path')]
print(f"   Resume routes: {resume_routes}")
if '/upload-resume' in resume_routes:
    print("   ✅ /upload-resume endpoint is registered")
else:
    print("   ❌ /upload-resume endpoint NOT found")
    sys.exit(1)

# Test 3: Check dependencies
print("\n3️⃣  Checking dependencies...")
try:
    import sklearn
    print(f"   ✅ scikit-learn available (version {sklearn.__version__})")
except:
    print("   ❌ scikit-learn not installed")
    sys.exit(1)

try:
    import PyPDF2
    print(f"   ✅ PyPDF2 available")
except:
    print("   ❌ PyPDF2 not installed")
    sys.exit(1)

try:
    from docx import Document
    print(f"   ✅ python-docx available")
except:
    print("   ❌ python-docx not installed")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ All checks passed!")
print("=" * 60)
print("\n🚀 The resume endpoint is ready!")
print("\nYou can now start the server with:")
print("   python -m uvicorn app.main:app --reload")
