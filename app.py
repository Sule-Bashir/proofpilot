import os
import json
import sqlite3
import io
import numpy as np
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from groq import Groq

# OCR and image processing with EasyOCR
try:
    import easyocr
    from PIL import Image
    # Initialize EasyOCR reader (runs once at startup)
    reader = easyocr.Reader(['en'], gpu=False)
    OCR_AVAILABLE = True
    print("✅ EasyOCR initialized")
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️ OCR not available. Install: pip install easyocr opencv-python-headless")

# PDF processing
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PDF not available. Install: pip install pdfplumber")

app = FastAPI(
    title="ProofPilot API",
    description="AI-powered receipt processing agent with OCR",
    version="1.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
def init_db():
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor TEXT,
            amount REAL,
            currency TEXT,
            category TEXT,
            confidence REAL,
            status TEXT,
            filename TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Database initialized")

init_db()

# Initialize Groq client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("⚠️ WARNING: GROQ_API_KEY not set!")
    print("Run: export GROQ_API_KEY='gsk_your_key'")
    client = None
else:
    client = Groq(api_key=GROQ_API_KEY)
    print("✅ Groq client initialized")

# Response models
class ExpenseResponse(BaseModel):
    status: str
    vendor: str
    amount: float
    currency: str
    category: str
    confidence: float
    message: str
    filename: Optional[str] = None

class ExpenseListResponse(BaseModel):
    expenses: List[dict]
    count: int

def extract_text_from_file(content: bytes, filename: str) -> str:
    """Extract text from various file formats."""
    file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
    text = ""

    # Text files
    if file_extension in ['txt', 'csv', 'log']:
        try:
            text = content.decode('utf-8', errors='ignore')
        except:
            text = "Could not decode text file"

    # PDF files
    elif file_extension in ['pdf']:
        if PDF_AVAILABLE:
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                print(f"✅ PDF extracted {len(text)} characters")
            except Exception as e:
                print(f"❌ PDF error: {e}")
                text = "Could not extract text from PDF. It may be scanned or password protected."
        else:
            text = "PDF support not installed. Install: pip install pdfplumber"

    # Image files - using EasyOCR
    elif file_extension in ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'webp']:
        if OCR_AVAILABLE:
            try:
                image = Image.open(io.BytesIO(content))
                # Convert PIL image to numpy array
                img_array = np.array(image)
                # Use EasyOCR
                results = reader.readtext(img_array)
                # Combine all detected text
                text = ' '.join([res[1] for res in results])
                print(f"✅ OCR extracted {len(text)} characters from image")
            except Exception as e:
                print(f"❌ OCR error: {e}")
                text = "Could not extract text from image. Please upload a clearer photo."
        else:
            text = "OCR not installed. Please install: pip install easyocr opencv-python-headless"

    # Unknown format - try as text
    else:
        try:
            text = content.decode('utf-8', errors='ignore')
            if len(text.strip()) < 10:
                text = f"Unsupported file format: {file_extension}"
        except:
            text = f"Could not read file: {filename}"

    return text

@app.post("/process-receipt", response_model=ExpenseResponse)
async def process_receipt(file: UploadFile = File(...)):
    """Process a receipt file (text, image, or PDF)."""

    if not client:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY not set. Please set it and restart the server."
        )

    # Read file content
    content = await file.read()

    # Extract text based on file type
    text = extract_text_from_file(content, file.filename)

    # If text is empty or error message, return early
    if not text or len(text.strip()) < 5:
        return ExpenseResponse(
            status="needs_review",
            vendor="Unknown",
            amount=0.0,
            currency="NGN",
            category="Other",
            confidence=0.0,
            filename=file.filename,
            message=f"Could not extract text from {file.filename}. Please upload a clear image or text file."
        )

    # Build prompt for Groq
    prompt = f"""
    Extract information from this receipt and return ONLY valid JSON.

    Receipt text:
    {text[:1000]}

    Return JSON with these exact keys:
    - vendor: The store/business name (string)
    - amount: The total amount as a number (float, no currency symbol)
    - currency: The currency code (string, e.g., NGN, USD, EUR)
    - category: Choose ONE from [Food, Transport, Office Supplies, Utilities, Entertainment, Other]
    - confidence: Your confidence in the extraction (float between 0 and 1)

    Example output:
    {{"vendor":"ABC Supermarket","amount":24500.0,"currency":"NGN","category":"Office Supplies","confidence":0.95}}

    ONLY return the JSON. No other text.
    """

    try:
        # Call Groq API
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": "You are a receipt parsing assistant. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=300
        )

        # Parse response
        try:
            data = json.loads(response.choices[0].message.content)
            print(f"✅ Parsed: {data}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parse error: {e}")
            data = {
                "vendor": "Unknown",
                "amount": 0.0,
                "currency": "NGN",
                "category": "Other",
                "confidence": 0.5
            }

    except Exception as e:
        print(f"❌ Error calling Groq: {e}")
        data = {
            "vendor": "Unknown",
            "amount": 0.0,
            "currency": "NGN",
            "category": "Other",
            "confidence": 0.5
        }

    # Determine status based on confidence
    status = "auto_approved" if data.get("confidence", 0) > 0.8 else "needs_review"

    # Save to database
    try:
        conn = sqlite3.connect("expenses.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO expenses (vendor, amount, currency, category, confidence, status, filename, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("vendor", "Unknown"),
            data.get("amount", 0.0),
            data.get("currency", "NGN"),
            data.get("category", "Other"),
            data.get("confidence", 0.5),
            status,
            file.filename,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        print(f"✅ Saved expense: {data.get('vendor')} - {data.get('amount')} {data.get('currency')}")
    except Exception as e:
        print(f"❌ Error saving to database: {e}")

    # Return response
    return ExpenseResponse(
        status=status,
        vendor=data.get("vendor", "Unknown"),
        amount=float(data.get("amount", 0.0)),
        currency=data.get("currency", "NGN"),
        category=data.get("category", "Other"),
        confidence=float(data.get("confidence", 0.5)),
        filename=file.filename,
        message=f"Receipt processed from {file.filename}. Status: {status}"
    )

@app.get("/expenses", response_model=ExpenseListResponse)
async def get_expenses(limit: Optional[int] = 100):
    """Get all processed expenses."""
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, vendor, amount, currency, category, confidence, status, filename, created_at
        FROM expenses
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    expenses = []
    for row in rows:
        expenses.append({
            "id": row[0],
            "vendor": row[1],
            "amount": row[2],
            "currency": row[3],
            "category": row[4],
            "confidence": row[5],
            "status": row[6],
            "filename": row[7],
            "created_at": row[8]
        })

    return ExpenseListResponse(expenses=expenses, count=len(expenses))

@app.get("/stats")
async def get_stats():
    """Get statistics about processed expenses."""
    conn = sqlite3.connect("expenses.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM expenses")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM expenses WHERE status = 'auto_approved'")
    auto_approved = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM expenses WHERE status = 'needs_review'")
    needs_review = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(amount) FROM expenses")
    total_amount = cursor.fetchone()[0] or 0

    # Count by category
    cursor.execute("SELECT category, COUNT(*) FROM expenses GROUP BY category")
    categories = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    return {
        "total_expenses": total,
        "auto_approved": auto_approved,
        "needs_review": needs_review,
        "total_amount": total_amount,
        "currency": "NGN",
        "categories": categories
    }

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ProofPilot API",
        "version": "1.1.0",
        "description": "AI-powered expense processing agent with OCR",
        "features": {
            "ocr": OCR_AVAILABLE,
            "pdf": PDF_AVAILABLE
        },
        "endpoints": {
            "/": "This information",
            "/docs": "Interactive API documentation",
            "/process-receipt": "Upload a receipt (text, image, or PDF)",
            "/expenses": "View all processed expenses",
            "/stats": "View expense statistics"
        },
        "status": "ready" if client else "missing_api_key"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "database": "connected",
        "groq_api": "configured" if client else "missing",
        "ocr_available": OCR_AVAILABLE,
        "pdf_available": PDF_AVAILABLE,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/test-ocr")
async def test_ocr(file: UploadFile = File(...)):
    """Test OCR on a file."""
    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content))
        img_array = np.array(image)
        results = reader.readtext(img_array)
        text = ' '.join([res[1] for res in results])
        return {
            "ocr_text": text.strip(),
            "length": len(text),
            "success": len(text.strip()) > 0
        }
    except Exception as e:
        return {"error": str(e), "success": False}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
