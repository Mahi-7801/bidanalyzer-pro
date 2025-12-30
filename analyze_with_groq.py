
import os
import json
import time
import pdfplumber
from dotenv import load_dotenv
from groq import Groq
from deep_translator import GoogleTranslator
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# 1. Configuration
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("WARNING: GROQ_API_KEY not found in environment variables.")
    # Attempt to ask user if in interactive mode
    try:
        input_key = input("Please enter your Groq API Key: ").strip()
        if input_key:
            GROQ_API_KEY = input_key
    except:
        pass

if not GROQ_API_KEY:
    print("Error: Cannot proceed without Groq API Key.")
    exit(1)

client = Groq(api_key=GROQ_API_KEY)

FILES_TO_PROCESS = [
    'CPP.pdf',
    'eprocurement.pdf',
    'GeM-Bidding-8551552.pdf',
    'IREPS.pdf'
]

OUTPUT_DIR = "Analysis_Reports"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 2. Text Extraction (Python Script via pdfplumber)
def extract_text_from_pdf(pdf_path):
    print(f"Extracting text from {os.path.basename(pdf_path)}...")
    text_content = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            if not pdf.pages:
                return None
            
            # Limit to first 10 pages to avoid token overflow generally, or extract all and truncate later
            # For these specific tenders, important info is usually in first 10-15 pages.
            for i, page in enumerate(pdf.pages[:15]): 
                text = page.extract_text()
                if text:
                    text_content += text + "\n"
                    
        return text_content
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None

# 3. Groq LLM Analysis
def analyze_with_groq(text):
    print("Analyzing text with Groq (Llama-3.3-70b)...")
    
    # Truncate text if it's too massive (approx char count for 32k context might be around 100k chars safe)
    # Llama 3.3 70b has 128k context, so we can be generous.
    safe_text = text[:100000] 
    
    system_prompt = """
    You are an expert Tender Analyst. Extract the following details from the tender document into a JSON format.
    
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

    Return ONLY the JSON object. Do not add markdown backticks or explanations.
    If a value is not found, use "Not Specified".
    """
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this tender text:\n\n{safe_text}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = completion.choices[0].message.content
        return json.loads(result)
    except Exception as e:
        print(f"Groq API Error: {e}")
        return None

# 4. Translation
def translate_data(data, target_lang='hi'):
    # Simple recursive translation for strings/lists
    print(f"Translating to {target_lang}...")
    translator = GoogleTranslator(source='auto', target=target_lang)
    translated = {}
    
    for k, v in data.items():
        try:
            if isinstance(v, str) and v and v != "Not Specified":
                translated[k] = translator.translate(v[:4500]) # Limit for translator
            elif isinstance(v, list):
                translated[k] = [translator.translate(item[:4500]) for item in v]
            else:
                translated[k] = v
        except:
            translated[k] = v
    return translated

# 5. PDF Generation
def create_pdf_report(filename, data, language_code='en'):
    doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()

    # Custom Styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        alignment=1, # Center
        spaceAfter=20
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=1,
        spaceAfter=30
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.white,
        backColor=colors.HexColor('#667eea'),
        borderPadding=6,
        spaceBefore=15,
        spaceAfter=10
    )
    
    normal_style = styles["Normal"]

    # --- Content Building ---
    story.append(Paragraph(f"Bid Analysis Report", title_style))
    story.append(Paragraph(f"Generated by Bid Analyser Pro via Groq • Language: {language_code.upper()}", subtitle_style))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"<b>EXECUTIVE SUMMARY</b>", section_header_style))
    summary_text = data.get('Executive_Summary', 'No summary available.')
    story.append(Paragraph(summary_text, normal_style))
    story.append(Spacer(1, 10))

    def create_section_table(data_dict):
        table_data = []
        for label, val in data_dict.items():
            if isinstance(val, list):
                val = ", ".join(val)
            table_data.append([Paragraph(f"<b>{label}</b>", normal_style), Paragraph(str(val), normal_style)])
        
        t = Table(table_data, colWidths=[2.5*inch, 4.5*inch])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('BOX', (0, 0), (-1, -1), 0.25, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    story.append(Paragraph("<b>BASIC INFORMATION</b>", section_header_style))
    basic_info = {
        "Tender Reference": data.get("Tender_Reference"),
        "Issuing Authority": data.get("Issuing_Authority"),
        "Project Name": data.get("Project_Name")
    }
    story.append(create_section_table(basic_info))
    
    story.append(Paragraph("<b>KEY FINANCIALS</b>", section_header_style))
    financials = {
        "Estimated Value": data.get("Estimated_Value"),
        "EMD Amount": data.get("EMD_Amount"),
        "Tender Fee": data.get("Tender_Fee")
    }
    story.append(create_section_table(financials))

    story.append(Paragraph("<b>CRITICAL DATES</b>", section_header_style))
    dates = {
        "Bid Submission Deadline": data.get("Bid_Submission_Deadline"),
        "Bid Opening Date": data.get("Bid_Opening_Date")
    }
    story.append(create_section_table(dates))

    story.append(Paragraph("<b>ELIGIBILITY & REQUIREMENTS</b>", section_header_style))
    eligibility = {
        "Minimum Turnover": data.get("Min_Turnover"),
        "Experience Required": data.get("Experience_Required"),
        "Documents Required": data.get("Required_Documents")
    }
    story.append(create_section_table(eligibility))

    try:
        doc.build(story)
        print(f"Report saved: {filename}")
    except Exception as e:
        print(f"Failed to build PDF: {e}")

# Main Loop
def main():
    print("Starting Groq-Powered Batch Analysis...")
    
    for filename in FILES_TO_PROCESS:
        file_path = os.path.join(os.getcwd(), filename)
        
        if not os.path.exists(file_path):
             print(f"Skipping missing file: {filename}")
             continue
             
        # 1. Extract Text
        text = extract_text_from_pdf(file_path)
        if not text or len(text.strip()) < 50:
             print(f"Warning: Could not extract sufficient text from {filename} (Might be scanned?). Skipping.")
             continue
             
        # 2. Analyze
        data = analyze_with_groq(text)
        if not data:
            continue
            
        # 3. Create English PDF
        out_name = os.path.join(OUTPUT_DIR, f"Analysis_Groq_{filename}.pdf")
        create_pdf_report(out_name, data, 'en')

    print(f"\nDone! Reports are in {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
