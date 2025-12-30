
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
from deep_translator import GoogleTranslator
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# 1. Setup & Config
load_dotenv()

app = FastAPI()

# Allow CORS for React (Vite defaults to localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# DEBUG: List available models on startup
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("--- AVAILABLE GEMINI MODELS ---")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Model: {m.name}")
        print("-------------------------------")
    except Exception as e:
        print(f"Failed to list models on startup: {e}")

# 2. Text Extraction
def extract_text_from_file_path(file_path: str):
    text_content = ""
    try:
        if file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()

        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                return None
            
            # Limit to first 15 pages for speed/context limits
            for i, page in enumerate(pdf.pages[:15]): 
                text = page.extract_text()
                if text:
                    text_content += text + "\n"
        return text_content
    except Exception as e:
        print(f"Extraction Error: {e}")
        return None

# 3. Groq Analysis
# 3. Gemini Analysis
def analyze_with_gemini(file_path: str, api_key: str):
    genai.configure(api_key=api_key)
    
    # Upload to Gemini (supports PDF natively, including scanned)
    print("Uploading to Gemini...")
    sample_file = genai.upload_file(path=file_path, display_name="Tender_Doc")
    
    # Wait for processing
    while sample_file.state.name == "PROCESSING":
        time.sleep(1)
        sample_file = genai.get_file(sample_file.name)
        
    if sample_file.state.name == "FAILED":
        raise ValueError("Gemini failed to process the file.")

    prompt = """
    You are an expert Tender Analyst. Analyze this document and extract the following details into a strict JSON format.
    
    Fields to Extract:
    - Tender_Reference (String)
    - Issuing_Authority (String)
    - Project_Name (String)
    - Estimated_Value (String)
    - EMD_Amount (String)
    - Tender_Fee (String)
    - Bid_Submission_Deadline (Format: DD-MM-YYYY HH:mm)
    - Bid_Opening_Date (Format: DD-MM-YYYY HH:mm)
    - Min_Turnover (String)
    - Experience_Required (String)
    - Required_Documents (List of top 5 mandatory documents)
    - Executive_Summary (A concise 3-4 sentence summary of the project)

    Return ONLY the JSON object. Do not add markdown backticks.
    If a value is not found, use "Not Specified".
    """

    # Strictly using user-requested model
    model_name = 'gemini-2.5-flash'
    try:
        model = genai.GenerativeModel(model_name)
        print(f"Generating content with {model_name}...")
        response = model.generate_content([sample_file, prompt])
    except Exception as e:
        print(f"Error with {model_name}: {e}")
        print("Attempting to list available models for debugging...")
        try:
            for m in genai.list_models():
                print(f" - {m.name}")
        except:
            print("Could not list models.")
        raise e
    
    # Text clean up
    clean_json = response.text.strip()
    if clean_json.startswith("```json"):
        clean_json = clean_json[7:]
    if clean_json.endswith("```"):
        clean_json = clean_json[:-3]
        
    return json.loads(clean_json)

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

# Recursive translation helper
def recursive_translate(data, target_lang):
    translator = GoogleTranslator(source='auto', target=target_lang)
    
    if isinstance(data, dict):
        return {k: recursive_translate(v, target_lang) for k, v in data.items()}
    elif isinstance(data, list):
        return [recursive_translate(item, target_lang) for item in data]
    elif isinstance(data, str) and data.strip():
        try:
             # Skip translating keys or tech identifiers if possible, but here we translate values
             # Limit length
             return translator.translate(data[:4500])
        except:
             return data
    else:
        return data

@app.post("/translate")
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

@app.post("/generate-pdf")
async def generate_pdf(
    data: dict, # { "data": {...}, "filename": "report.pdf" }
):
    try:
        report_data = data.get("data")
        safe_name = f"Report_{int(time.time())}.pdf"
        output_path = generate_pdf_report(report_data, safe_name)
        return FileResponse(output_path, media_type='application/pdf', filename=safe_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("Starting Backend Server on Port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
