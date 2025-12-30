
import os
import json
import shutil
import time
import pdfplumber
from typing import Optional
from fastapi import FastAPI, File, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import google.generativeai as genai
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv
from html2image import Html2Image
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

from fastapi.staticfiles import StaticFiles

from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request

# 1. Setup & Config
load_dotenv()

app = FastAPI()

# Global Exception Handler for 422 Validation Errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"⚠️ Validation Error: {exc}")
    print(f"⚠️ Request Body: {exc.body}")
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(exc.errors()), "body": str(exc)}
    )

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logger Middleware to debug incoming requests
@app.middleware("http")
async def log_requests(request, call_next):
    print(f"Incoming Request: {request.method} {request.url.path}")
    response = await call_next(request)
    print(f"Response Status: {response.status_code}")
    return response

# Sanitize API Key (Remove potential newlines/spaces)
GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()

# Serve React Frontend Assets
if os.path.exists("dist"):
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "BidAnalyzer Pro API"}

# 2. Text Extraction
def extract_text_from_file_path(file_path: str):
    import pdfplumber
    text_content = ""
    try:
        if file_path.endswith('.txt'):
             with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                 return f.read()

        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages: return None
            # Limit to first 20 pages
            for i, page in enumerate(pdf.pages[:20]): 
                text = page.extract_text()
                if text: text_content += text + "\n"
        return text_content
    except Exception as e:
        print(f"Extraction Error: {e}")
        return None

# API ROUTES moved under /api
@app.post("/api/analyze")
async def analyze_document(
    file: UploadFile = File(...), 
    x_api_key: Optional[str] = Header(None)
):
    # Log that we hit the endpoint
    print(f"Analyzing file: {file.filename}")
    # 1. Determine API Key (Header > Env)
    api_key = (x_api_key or "").strip()
    if not api_key:
        api_key = GEMINI_API_KEY

    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key missing. Provide X-API-Key or configure server key."
        )

    # 2. Save Upload Temporarily
    temp_filename = f"temp_{file.filename}"
    try:
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        print(f"File saved to {temp_filename}")
        
        # 3. Hybrid Analysis
        content_text = extract_text_from_file_path(temp_filename)
        
        if content_text and len(content_text.strip()) > 50:
            print("Analyzing extracted text...")
            analysis_result = analyze_with_gemini_text(content_text, api_key)
        else:
            print("Analyzing file (upload)...")
            analysis_result = analyze_with_gemini_file(temp_filename, api_key)
        
        # Clean up
        try: os.remove(temp_filename)
        except: pass
        
        return analysis_result

    except Exception as e:
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except: pass
        # DIRECT ERROR RETURN
        print(f"Analysis Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# 3. Gemini Analysis (Hybrid Text/File)
def analyze_with_gemini_text(text: str, api_key: str):
    genai.configure(api_key=api_key)
    # Use 2.5 Flash as requested, using 'gemini-2.5-flash' alias which is usually safer than models/ path for genai lib
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """
You are a senior Tender Analyst AI specialized in Government & PSU procurement documents.
You must READ THE ENTIRE DOCUMENT CAREFULLY before extracting any data.

====================================
CRITICAL RULES (NON-NEGOTIABLE)
====================================

1. NO ASSUMPTIONS OR GUESSING
   - Extract only what is explicitly present in the document.
   - If a value is unclear or partially visible, state it clearly.

2. REFERENCE RESOLUTION (MANDATORY)
   When you see phrases like:
   - "Refer to Para X"
   - "As per Clause Y"
   - "See Annexure Z"

   You MUST:
   a) Search the ENTIRE document
   b) Try variations:
      - Para / Paragraph
      - Clause / Section
      - Annexure / Appendix / Schedule
   c) Search ALL locations:
      - NIT
      - GCC / SCC
      - Technical Specs
      - BOQ
      - Annexures
      - Tables, footnotes, headers

   If found:
   → Extract the ACTUAL VALUE from the referenced section

   If NOT found after exhaustive search:
   → Write exactly:
     "Referenced in <reference> but details not found in extracted text"

3. NEVER write "Not Specified" if a reference exists.
   Use "Not Specified" ONLY when:
   - No value
   - No reference
   - No implied criteria

4. CONFLICT RESOLUTION
   - If multiple values exist:
     Priority order:
     1) Special Conditions
     2) Technical Specifications
     3) NIT
     4) GCC
   - Mention conflicts clearly if unresolved.

5. NORMALIZATION RULES
   - Dates → DD-MM-YYYY
   - Time → HH:mm (24-hour)
   - Currency → Preserve original (₹ / Rs / INR / %)
   - DO NOT convert amounts unless explicitly stated.

====================================
ELIGIBILITY EXTRACTION (STRICT)
====================================

For ALL eligibility-related fields:
- Search referenced clauses deeply
- Extract COMPLETE criteria including:
  - Amount
  - Time period
  - Financial years
  - Nature of work
  - Quantity / value thresholds

If eligibility is split across clauses:
→ Merge into a single, complete requirement.

====================================
FIELDS TO EXTRACT (STRICT JSON)
====================================

Tender_Reference (String)
Issuing_Authority (String)
Project_Name (String)
Location (String)
Estimated_Value (String)
EMD_Amount (String)
Tender_Fee (String)

Important_Dates (Object)
- Extract ALL dates with exact labels as mentioned

Eligibility (Object with these keys):
  - Min_Turnover (String: Complete criteria with amount, period, financial years)
  - Experience_Required (String: Complete criteria with years, nature of work)
  - Other_Eligibility_Criteria (String: Any other qualifying conditions)

Scope_of_Work (String: MAX 200 characters)
- Use 2-3 bullet points OR one concise sentence
- Example: "• PSC sleepers for BG • Monoblock & curve types • RDSO spec compliance"

Contract_Period (String)

Payment_Terms (String: MAX 150 characters)
- 1-2 sentences only

Technical_Specifications (String: MAX 250 characters)
- KEY points only, not paragraphs
- Reference detailed clauses if needed

Submission_Method (String)
Contact_Details (String)

Required_Documents (Array)
- Extract EVERY required document
- Include certificates, affidavits, forms, annexures

Executive_Summary (String)
- 3–5 sentences
- Cover:
  - What is being procured
  - Value & duration
  - Key eligibility
  - Submission mode

====================================
OUTPUT RULES
====================================

- OUTPUT ONLY VALID JSON
- NO markdown
- NO explanations
- NO comments
- NO backticks
- Preserve exact wording from document wherever possible

Search the ENTIRE document before finalizing ANY field.
    """
    
    # Safety truncate
    safe_text = text[:100000]
    
    response = model.generate_content([prompt, safe_text])
    return clean_and_parse_json(response.text)

def analyze_with_gemini_file(file_path: str, api_key: str):
    genai.configure(api_key=api_key)
    sample_file = genai.upload_file(path=file_path, display_name="Tender_Doc")
    
    while sample_file.state.name == "PROCESSING":
        time.sleep(1)
        sample_file = genai.get_file(sample_file.name)
        
    if sample_file.state.name == "FAILED":
        raise ValueError("Gemini failed to process the file upload.")

    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """
You are a senior Tender Analyst AI specialized in Government & PSU procurement documents.
You must READ THE ENTIRE DOCUMENT CAREFULLY before extracting any data.

====================================
CRITICAL RULES (NON-NEGOTIABLE)
====================================

1. NO ASSUMPTIONS OR GUESSING
   - Extract only what is explicitly present in the document.
   - If a value is unclear or partially visible, state it clearly.

2. REFERENCE RESOLUTION (MANDATORY)
   When you see phrases like:
   - "Refer to Para X"
   - "As per Clause Y"
   - "See Annexure Z"

   You MUST:
   a) Search the ENTIRE document
   b) Try variations:
      - Para / Paragraph
      - Clause  / Section
      - Annexure / Appendix / Schedule
   c) Search ALL locations:
      - NIT
      - GCC / SCC
      - Technical Specs
      - BOQ
      - Annexures
      - Tables, footnotes, headers

   If found:
   → Extract the ACTUAL VALUE from the referenced section

   If NOT found after exhaustive search:
   → Write exactly:
     "Referenced in <reference> but details not found in extracted text"

3. NEVER write "Not Specified" if a reference exists.
   Use "Not Specified" ONLY when:
   - No value
   - No reference
   - No implied criteria

4. CONFLICT RESOLUTION
   - If multiple values exist:
     Priority order:
     1) Special Conditions
     2) Technical Specifications
     3) NIT
     4) GCC
   - Mention conflicts clearly if unresolved.

5. NORMALIZATION RULES
   - Dates → DD-MM-YYYY
   - Time → HH:mm (24-hour)
   - Currency → Preserve original (₹ / Rs / INR / %)
   - DO NOT convert amounts unless explicitly stated.

====================================
ELIGIBILITY EXTRACTION (STRICT)
====================================

For ALL eligibility-related fields:
- Search referenced clauses deeply
- Extract COMPLETE criteria including:
  - Amount
  - Time period
  - Financial years
  - Nature of work
  - Quantity / value thresholds

If eligibility is split across clauses:
→ Merge into a single, complete requirement.

====================================
FIELDS TO EXTRACT (STRICT JSON)
====================================

Tender_Reference (String)
Issuing_Authority (String)
Project_Name (String)
Location (String)
Estimated_Value (String)
EMD_Amount (String)
Tender_Fee (String)

Important_Dates (Object)
- Extract ALL dates with exact labels as mentioned

Eligibility (Object with these keys):
  - Min_Turnover (String: Complete criteria with amount, period, financial years)
  - Experience_Required (String: Complete criteria with years, nature of work)
  - Other_Eligibility_Criteria (String: Any other qualifying conditions)

Scope_of_Work (String: MAX 200 characters)
- Use 2-3 bullet points OR one concise sentence
- Example: "• PSC sleepers for BG • Monoblock & curve types • RDSO spec compliance"

Contract_Period (String)

Payment_Terms (String: MAX 150 characters)
- 1-2 sentences only

Technical_Specifications (String: MAX 250 characters)
- KEY points only, not paragraphs
- Reference detailed clauses if needed

Submission_Method (String)
Contact_Details (String)

Required_Documents (Array)
- Extract EVERY required document
- Include certificates, affidavits, forms, annexures

Executive_Summary (String)
- 3–5 sentences
- Cover:
  - What is being procured
  - Value & duration
  - Key eligibility
  - Submission mode

====================================
OUTPUT RULES
====================================

- OUTPUT ONLY VALID JSON
- NO markdown
- NO explanations
- NO comments
- NO backticks
- Preserve exact wording from document wherever possible

Search the ENTIRE document before finalizing ANY field.
    """
    
    response = model.generate_content([sample_file, prompt])
    return clean_and_parse_json(response.text)

def clean_and_parse_json(text):
    clean = text.strip()
    if clean.startswith("```json"): clean = clean[7:]
    if clean.endswith("```"): clean = clean[:-3]
    return json.loads(clean)

# Deprecated single function, kept as proxy if needed or removed.
# We will use the specific ones in the endpoint.

def extract_text_pypdf(file_path): 
    # Quick helper if the other one has issues
    import pdfplumber
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
    except:
        pass
    return text


# 4. Helper: PDF Generation

# 4. Helper: PDF Generation
def generate_pdf_report(data, filename="report.pdf", language='en'):
    # Use the template image if it exists
    bg_image_path = "Bidalert template.png"
    has_bg = os.path.exists(bg_image_path)
    
    doc = SimpleDocTemplate(
        filename, 
        pagesize=A4, 
        rightMargin=50, leftMargin=50, 
        topMargin=120 if has_bg else 30, # Push content down to avoid header
        bottomMargin=50
    )
    
    story = []
    styles = getSampleStyleSheet()

    # Define a background function
    def add_background(canvas, doc):
        if has_bg:
            # Draw image to fill the page or as a header/footer
            # Assuming A4 size: 595.27 x 841.89
            canvas.drawImage(bg_image_path, 0, 0, width=A4[0], height=A4[1])

    # Styles
    title_style = ParagraphStyle('CTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#667eea'), alignment=1, spaceAfter=20)
    sec_style = ParagraphStyle('SecHeader', parent=styles['Heading3'], fontSize=14, textColor=colors.white, backColor=colors.HexColor('#667eea'), borderPadding=6, spaceBefore=15, spaceAfter=10)
    norm_style = styles["Normal"]

    if not has_bg:
        story.append(Paragraph(f"Bid Analysis Report", title_style))
        story.append(Spacer(1, 12))

    # Exec Summary
    story.append(Paragraph(f"<b>EXECUTIVE SUMMARY</b>", sec_style))
    story.append(Paragraph(data.get("Executive_Summary", ""), norm_style))
    story.append(Spacer(1, 10))

    # Helper Table
    def make_table(d):
        tdata = []
        for k, v in d.items():
            if isinstance(v, list): v = ", ".join(str(x) for x in v)
            tdata.append([Paragraph(f"<b>{k}</b>", norm_style), Paragraph(str(v), norm_style)])
        t = Table(tdata, colWidths=[2.2*inch, 4.2*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#f8f9fa')),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
            ('BOX', (0,0), (-1,-1), 0.25, colors.grey),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ]))
        return t

    # Sections
    story.append(Paragraph("<b>BASIC INFORMATION</b>", sec_style))
    story.append(make_table({
        "Reference": data.get("Tender_Reference"),
        "Authority": data.get("Issuing_Authority"),
        "Project": data.get("Project_Name")
    }))

    story.append(Paragraph("<b>FINANCIALS</b>", sec_style))
    story.append(make_table({
        "Value": data.get("Estimated_Value"),
        "EMD": data.get("EMD_Amount"),
        "Fee": data.get("Tender_Fee")
    }))
    
    story.append(Paragraph("<b>DATES & ELIGIBILITY</b>", sec_style))
    story.append(make_table({
        "Submission": data.get("Bid_Submission_Deadline"),
        "Opening": data.get("Bid_Opening_Date"),
        "Turnover": data.get("Min_Turnover"),
        "Experience": data.get("Experience_Required"),
        "Documents": data.get("Required_Documents")
    }))

    doc.build(story, onFirstPage=add_background, onLaterPages=add_background)
    return filename

# Optimized Translation Helper
def recursive_translate(data, target_lang):
    translator = GoogleTranslator(source='auto', target=target_lang)
    
    # Process dictionary values in parallel to speed up
    if isinstance(data, dict):
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Create a map of future -> key
            future_to_key = {
                executor.submit(recursive_translate, v, target_lang): k 
                for k, v in data.items()
            }
            results = {}
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                try:
                    results[key] = future.result()
                except Exception as exc:
                    print(f'{key} translation generated an exception: {exc}')
                    results[key] = data[key] # Fallback to original
            return results

    elif isinstance(data, list):
         # Also parallelize list items if they are strings
         with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(recursive_translate, item, target_lang) for item in data]
            return [f.result() for f in futures]
            
    elif isinstance(data, str) and data.strip():
        try:
             # Limit length to avoid timeouts on large blocks
             return translator.translate(data[:4500])
        except:
             return data
    else:
        return data

@app.post("/api/translate")
async def translate_text(
    data: dict, # { "data": {...}, "target_lang": "hi" }
):
    try:
        input_data = data.get("data")
        target_lang = data.get("target_lang", "hi")
        
        if not input_data:
            return {"translated_data": None}
            
        # Standardize language codes if needed, though deep-translator takes names often too.
        # Minimal map for user convenience
        lang_map = {
            "Telugu": "te", "Hindi": "hi", "Tamil": "ta", "Spanish": "es", "French": "fr",
            "German": "de", "Russian": "ru", "Japanese": "ja", "Arabic": "ar"
        }
        code = lang_map.get(target_lang, target_lang.lower())
        
        translated_data = recursive_translate(input_data, code)
        
        return {"translated_data": translated_data}
    except Exception as e:
         print(f"Translation Error: {e}")
         raise HTTPException(status_code=500, detail=str(e))

import base64

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except:
        return ""


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "BidAnalyzer Pro API"}

@app.post("/api/ask")
async def ask_question(
    data: dict,
    x_api_key: Optional[str] = Header(None)
):
    try:
        question = data.get("question")
        context = data.get("context")
        
        if not question or not context:
             raise HTTPException(status_code=400, detail="Missing question or context")

        # Determine API Key (Header > Env)
        api_key = (x_api_key or "").strip()
        if not api_key:
            api_key = GEMINI_API_KEY

        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="Gemini API Key missing. Provide X-API-Key or configure server key."
            )

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
        You are a helpful expert assistant for a government tender document.
        Here is the JSON summary of the tender document:
        {context}
        
        Question: {question}
        
        Answer the question concisely based strictly on the provided context. If the answer is not in the context, say so.
        """
        
        response = model.generate_content(prompt)
        return {"answer": response.text}
        
    except Exception as e:
        print(f"Ask Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def generate_formatted_html(data):
    # Load Template
    bg_base64 = get_base64_image("Bidalert template.png")
    
    # Build background CSS rule
    if bg_base64:
        bg_rule = "background-image: url('data:image/png;base64," + bg_base64 + "');"
    else:
        bg_rule = "background-color: #ffffff;"
    
    # CSS - Split into parts to avoid f-string issues
    css_part1 = """
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, sans-serif; 
            margin: 0; padding: 0;
            background-color: #ffffff;
        }
        
        .page-container {
            position: relative;
            width: 1240px;
            min-height: 1754px; 
    """
    
    css_part2 = """
            background-size: 1240px 1754px;
            background-repeat: repeat-y;
            box-sizing: border-box;
            padding: 100px 80px 60px 80px; 
            display: flex;
            flex-direction: column;
        }

        h1 { 
            text-align: center; 
            color: #1a202c; 
            font-size: 3.5rem;
            margin: 0 0 40px 0; 
            font-weight: 900;
            text-transform: uppercase; 
            letter-spacing: 2px;
            text-shadow: 2px 2px 4px rgba(255,255,255,1);
        }
        
        .exec-summary { 
            background: rgba(255, 255, 255, 0.95); 
            padding: 30px 35px; 
            border-radius: 12px; 
            margin-bottom: 35px; 
            border-left: 8px solid #4c51bf; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.08);
        }
        .exec-summary h4 { color: #4c51bf; margin: 0 0 15px 0; font-size: 1.8rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; }
        .exec-summary p { font-size: 1.4rem; line-height: 1.6; color: #1a202c; font-weight: 500; margin: 0; }

        .section-header { 
            color: #2c5282; 
            font-size: 1.8rem; 
            font-weight: 800; 
            margin: 25px 0 15px 0; 
            border-bottom: 3px solid #aecdbf; 
            padding-bottom: 8px; 
            text-transform: uppercase;
            page-break-after: avoid;
        }
        
        table { 
            width: 100%; 
            border-collapse: separate; 
            border-spacing: 0; 
            margin-bottom: 20px; 
            font-size: 1.4rem; 
            border-radius: 8px; 
            overflow: hidden;
            page-break-inside: avoid;
        }
        th { background: #2d3748; color: white; padding: 18px 20px; text-align: left; font-weight: 700; width: 35%; border-bottom: 2px solid #ed8936; }
        td { background: rgba(255, 255, 255, 0.95); color: #000; padding: 18px 20px; border-bottom: 2px solid #e2e8f0; font-weight: 500; }
        tr:last-child td { border-bottom: none; }
        
        /* Force page break before certain sections if needed */
        .page-break-before {
            page-break-before: always;
            margin-top: 0;
        }
    </style>
    """
    
    # Combine CSS
    full_css = css_part1 + bg_rule + css_part2
    
    # Helper function to check if value should be shown
    def should_show_value(val):
        if not val or val is None:
            return False
        val_str = str(val).strip().lower()
        hide_values = ['not specified', 'n/a', 'null', 'undefined', 'none']
        return not any(hide in val_str for hide in hide_values)
    
    # Helper to build table rows (only if value is valid)
    def make_row(label, value):
        if should_show_value(value):
            return f"<tr><td>{label}</td><td>{value}</td></tr>"
        return ""
    
    # Build dates table dynamically (with filtering)
    dates_rows = ""
    if 'Important_Dates' in data and isinstance(data['Important_Dates'], dict):
        for date_label, date_value in data['Important_Dates'].items():
            if should_show_value(date_value):
                dates_rows += f"<tr><td>{date_label}</td><td>{date_value}</td></tr>"
    
    # Build HTML content
    html_content = f"""
    <html>
    <head>{full_css}</head>
    <body>
        <div class="page-container">
            <h1>Bid Analysis Report</h1>
            
            <div class="exec-summary">
                <h4>Executive Summary</h4>
                <p>{data.get('Executive_Summary', 'N/A')}</p>
            </div>

            <div class="section-header">Basic Information</div>
            <table>
                <tr><th>Field</th><th>Value</th></tr>
                {make_row('Tender Reference', data.get('Tender_Reference', ''))}
                {make_row('Issuing Authority', data.get('Issuing_Authority', ''))}
                {make_row('Project Name', data.get('Project_Name', ''))}
                {make_row('Location', data.get('Location', ''))}
            </table>

            <div class="section-header">Project Details</div>
            <table>
                <tr><th>Field</th><th>Value</th></tr>
                {make_row('Scope of Work', data.get('Scope_of_Work', ''))}
                {make_row('Contract Period', data.get('Contract_Period', ''))}
                {make_row('Technical Specifications', data.get('Technical_Specifications', ''))}
            </table>

            <div class="section-header">Financials</div>
            <table style="margin-bottom: 60px;">
                <tr><th>Field</th><th>Value</th></tr>
                {make_row('Estimated Value', data.get('Estimated_Value', ''))}
                {make_row('EMD Amount', data.get('EMD_Amount', ''))}
                {make_row('Tender Fee', data.get('Tender_Fee', ''))}
                {make_row('Payment Terms', data.get('Payment_Terms', ''))}
            </table>

            <div class="section-header">Important Dates</div>
            <table style="margin-bottom: 80px;">
                <tr><th>Field</th><th>Value</th></tr>
                {dates_rows}
            </table>

            <div class="section-header">Eligibility Criteria</div>
            <table style="margin-bottom: 60px;">
                <tr><th>Field</th><th>Value</th></tr>
                {make_row('Min Turnover', data.get('Eligibility', {}).get('Min_Turnover') if isinstance(data.get('Eligibility'), dict) else data.get('Min_Turnover', ''))}
                {make_row('Experience Required', data.get('Eligibility', {}).get('Experience_Required') if isinstance(data.get('Eligibility'), dict) else data.get('Experience_Required', ''))}
                {make_row('Other Criteria', data.get('Eligibility', {}).get('Other_Eligibility_Criteria', ''))}
                {make_row('Required Docs', str(data.get('Required_Documents', ''))[:400] + '...' if data.get('Required_Documents') else '')}
            </table>

            <div class="section-header">Submission Information</div>
            <table>
                <tr><th>Field</th><th>Value</th></tr>
                {make_row('Submission Method', data.get('Submission_Method', ''))}
                {make_row('Contact Details', data.get('Contact_Details', ''))}
            </table>
        </div>
    </body>
    </html>
    """
    
    return html_content

@app.post("/api/generate-pdf")
async def generate_pdf(
    data: dict, # { "data": {...} }
):
    try:
        report_data = data.get("data")
        if not report_data:
             raise HTTPException(status_code=400, detail="No data provided for report generation")
             
        # Generate HTML content
        html_content = generate_formatted_html(report_data)
        
        # Prepare filenames in /tmp (writable in HF Spaces)
        temp_dir = "/tmp"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir, exist_ok=True)
            
        timestamp = int(time.time())
        output_pdf = f"Report_{timestamp}.pdf"
        output_path = os.path.join(temp_dir, output_pdf)
        
        # Use html2image with CRITICAL flags for Docker/Linux
        # Set a very large height to capture full content (approx 4 pages worth)
        hti = Html2Image(
            output_path=temp_dir, 
            temp_path=temp_dir, 
            size=(1240, 7016), # 4 * 1754 (A4 Height at ~96dpi or similar scale)
            custom_flags=['--no-sandbox', '--disable-gpu', '--headless', '--disable-dev-shm-usage']
        )
        
        # 1. Screenshot to PNG (Capture full scroll)
        output_png = f"Report_{timestamp}.png"
        png_path = os.path.join(temp_dir, output_png)
        
        hti.screenshot(html_str=html_content, save_as=output_png)
        
        if not os.path.exists(png_path):
             raise HTTPException(status_code=500, detail="HTML render failed: PNG snapshot not created.")

        # 2. Process image into Multi-Page PDF
        image = Image.open(png_path)
        if image.mode == 'RGBA':
            image = image.convert('RGB')

        A4_WIDTH = 1240
        A4_HEIGHT = 1754
        
        img_width, img_height = image.size
        pages = []
        
        current_y = 0
        
        while current_y < img_height:
            # Determine maximum possible cut point (bottom of A4)
            # But don't just take A4, looking for a smart break within the last 30% of the page
            limit_y = min(current_y + A4_HEIGHT, img_height)
            
            # If we are near the end (less than half a page left), just take it all if it fits
            # Or if it fits exactly
            if limit_y == img_height:
                box = (0, current_y, A4_WIDTH, limit_y)
                page = image.crop(box)
                
                # Content Check: Is this page empty?
                # Convert to grayscale, invert, getbbox to find non-white pixels
                # Or just iterate a few pixels.
                # Fast check: getbbox() returns None if image is all black (after inverting white to black)
                # But easiest is:
                gray = page.convert("L")
                # Counting whitespace is slow, let's use getbbox on inverted
                # If page is white, inverted is black. getbbox on black returns valid box ONLY if there are non-black pixels.
                from PIL import ImageOps
                inverted = ImageOps.invert(gray)
                if inverted.getbbox():
                     # Pad to A4
                    pdf_page = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
                    pdf_page.paste(page, (0, 0))
                    pages.append(pdf_page)
                break

            # SMART SLICING: Scan upwards from limit_y to find a safe break
            # We prioritize table borders (grey lines) or whitespace
            
            found_cut = -1
            scan_start = limit_y
            scan_end = max(current_y + 100, limit_y - 600) # Scan up to 600px upwards
            
            # We seek a row that is "uniform". 
            # Uniform White = Best
            # Uniform Grey (Border) = Good (Cut before it)
            
            for test_y in range(scan_start, scan_end, -2): # Scan upwards
                
                # Check row uniformity
                # Sample 20 points across the row
                row_pixels = []
                is_uniform = True
                first_pixel = None
                
                # Fast sample (center 80%)
                for x in range(100, A4_WIDTH - 100, 50):
                    p = image.getpixel((x, test_y))
                    # Convert to simple brightness
                    b = sum(p) # 0-765
                    
                    if first_pixel is None:
                        first_pixel = b
                    
                    # Allow small noise (JPEG artifacts etc) -> +/- 15 brightness
                    if abs(b - first_pixel) > 30:
                        is_uniform = False
                        break
                
                if is_uniform:
                    # We found a uniform row!
                    # Is it white? (Brightness > 700)
                    if first_pixel > 700:
                        found_cut = test_y
                        break
                    
                    # Is it a table border? (Grey, Brightness around 500-700 usually, or darker)
                    # If it's a border, we might want to ensure we cut BEFORE it if we are scanning up, 
                    # or allow it to be the bottom of the previous page.
                    # Let's say any uniform row is a potential cut.
                    found_cut = test_y
            
            # Decide where to cut
            if found_cut != -1:
                cut_y = found_cut
            else:
                cut_y = limit_y # Fallback to hard cut
            
            # Perform Crop
            box = (0, current_y, A4_WIDTH, cut_y)
            page = image.crop(box)
            
            # Content Check before adding
            gray = page.convert("L")
            inverted = ImageOps.invert(gray)
            
            if inverted.getbbox():
                # Create PDF friendly page (White Background A4)
                pdf_page = Image.new("RGB", (A4_WIDTH, A4_HEIGHT), (255, 255, 255))
                pdf_page.paste(page, (0, 0)) # Paste at top
                pages.append(pdf_page)
            else:
                 # If this page was empty, likely the rest is empty too?
                 # Don't add, and maybe break?
                 # But sticking to logic: just don't add.
                 pass
            
            # Move current_y to the cut point
            current_y = cut_y

        if not pages:
            raise HTTPException(status_code=500, detail="PDF conversion failed: No pages generated.")

        # Save all pages to PDF
        # First page is the "base", others are appended
        pages[0].save(
            output_path, 
            "PDF", 
            resolution=100.0, 
            save_all=True, 
            append_images=pages[1:]
        )
        
        if not os.path.exists(output_path):
             raise HTTPException(status_code=500, detail="PDF conversion failed.")

        # Return the file
        return FileResponse(
            output_path, 
            media_type='application/pdf', 
            filename="Bid_Analysis_Report.pdf"
        )

    except Exception as e:
        print(f"PDF Gen Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# CATCH-ALL ROUTE for Frontend (must be last)
@app.get("/{rest_of_path:path}")
async def catch_all(rest_of_path: str):
    # If the path looks like an API call but wasn't caught, return 404
    if rest_of_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
        
    # Otherwise serve index.html
    if os.path.exists("dist/index.html"):
        return FileResponse("dist/index.html")
    return {"error": "Frontend not found"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print(f"Starting Backend Server on Port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
