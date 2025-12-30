
import os
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai
from deep_translator import GoogleTranslator
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# 1. Configuration & Setup
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    # Try looking in a parent directory or ask user
    print("WARNING: GEMINI_API_KEY not found in environment variables.")
    print("Please create a .env file in this directory with: GEMINI_API_KEY=your_api_key_here")
    # Interactive input as fallback
    try:
        input_key = input("Or paste your API Key here and press Enter: ").strip()
        if input_key:
            API_KEY = input_key
            genai.configure(api_key=API_KEY)
    except:
        pass

if API_KEY:
    genai.configure(api_key=API_KEY)

FILES_TO_PROCESS = [
    'CPP.pdf',
    'eprocurement.pdf',
    'GeM-Bidding-8551552.pdf',
    'IREPS.pdf'
]

OUTPUT_DIR = "Analysis_Reports"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# 2. AI Extraction Logic
def extract_data_from_pdf(pdf_path):
    """
    Uploads PDF to Gemini 1.5 Flash and extracts structured JSON data.
    """
    print(f"Processing {pdf_path}...")
    
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return None

    try:
        # Uploading file to Gemini File API
        print("  - Uploading to Gemini...")
        sample_file = genai.upload_file(path=pdf_path, display_name=os.path.basename(pdf_path))
        
        # Wait for processing state
        while sample_file.state.name == "PROCESSING":
            time.sleep(2)
            sample_file = genai.get_file(sample_file.name)
            
        if sample_file.state.name == "FAILED":
            print("  - Gemini failed to process the file.")
            return None

        print("  - Analyzing...")
        # Model w/ System Prompt
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = """
        You are a Tender Analyst. Analyze this document and extract the following details into a strict JSON format.
        
        Fields to Extract:
        - Tender_Reference (String)
        - Issuing_Authority (String)
        - Project_Name (String)
        - Estimated_Value (String - include currency)
        - EMD_Amount (String)
        - Tender_Fee (String)
        - Bid_Submission_Deadline (String - DD-MM-YYYY HH:mm format if possible)
        - Bid_Opening_Date (String - DD-MM-YYYY HH:mm format if possible)
        - Min_Turnover (String)
        - Experience_Required (String)
        - Required_Documents (List of Strings - top 5 mandatory docs)
        - Executive_Summary (String - Summary of the scope of work in 3-4 sentences)

        If a field is not found, set it to "Not Specified".
        Do not use code blocks. Just return the raw JSON object.
        """

        response = model.generate_content([sample_file, prompt])
        
        # Cleanup JSON usage
        clean_json = response.text.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
            
        try:
            data = json.loads(clean_json)
            return data
        except json.JSONDecodeError:
            print("  - Failed to parse JSON response.")
            return None

    except Exception as e:
        print(f"Error extracting data from {pdf_path}: {e}")
        return None

# 3. Translation Logic
def translate_data(data, target_lang='hi'):
    """
    Translates the values in the extracted data dictionary to the target language.
    Does not translate keys.
    """
    if target_lang == 'en':
        return data

    print(f"Translating data into {target_lang}...")
    translator = GoogleTranslator(source='auto', target=target_lang)
    
    translated_data = {}
    
    for key, value in data.items():
        try:
            if isinstance(value, str) and value.strip():
                # Split huge texts
                if len(value) > 4000:
                    value = value[:4000] + "..."
                translated_data[key] = translator.translate(value)
            elif isinstance(value, list):
                # Translate list items
                translated_list = []
                for item in value:
                    if len(item) > 1000:
                        item = item[:1000]
                    translated_list.append(translator.translate(item))
                translated_data[key] = translated_list
            else:
                translated_data[key] = value
        except Exception as e:
            print(f"Translation error for {key}: {e}")
            translated_data[key] = value # Fallback to original
            
    return translated_data

# 4. PDF Generation Logic
def create_pdf_report(filename, data, language_code='en'):
    """
    Generates a professional PDF report styled like 'Bid Analyser Pro' output.
    """
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
    
    # 1. Header
    story.append(Paragraph(f"Bid Analysis Report", title_style))
    story.append(Paragraph(f"Generated by Bid Analyser Pro - Language: {language_code.upper()}", subtitle_style))
    story.append(Spacer(1, 12))

    # 2. Executive Summary Box
    story.append(Paragraph(f"<b>EXECUTIVE SUMMARY</b>", section_header_style))
    summary_text = data.get('Executive_Summary', 'No summary available.')
    story.append(Paragraph(summary_text, normal_style))
    story.append(Spacer(1, 10))

    # 3. Tables Helper
    def create_section_table(data_dict):
        table_data = []
        for label, val in data_dict.items():
            if isinstance(val, list):
                val = ", ".join(val)
            # Handle unicode rendering in basic way (won't look great for non-latin without font, but won't crash)
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

    # 4. Basic Info
    story.append(Paragraph("<b>BASIC INFORMATION</b>", section_header_style))
    basic_info = {
        "Tender Reference": data.get("Tender_Reference"),
        "Issuing Authority": data.get("Issuing_Authority"),
        "Project Name": data.get("Project_Name")
    }
    story.append(create_section_table(basic_info))

    # 5. Key Financials
    story.append(Paragraph("<b>KEY FINANCIALS</b>", section_header_style))
    financials = {
        "Estimated Value": data.get("Estimated_Value"),
        "EMD Amount": data.get("EMD_Amount"),
        "Tender Fee": data.get("Tender_Fee")
    }
    story.append(create_section_table(financials))

    # 6. Critical Dates
    story.append(Paragraph("<b>CRITICAL DATES</b>", section_header_style))
    dates = {
        "Bid Submission Deadline": data.get("Bid_Submission_Deadline"),
        "Bid Opening Date": data.get("Bid_Opening_Date")
    }
    story.append(create_section_table(dates))

    # 7. Eligibility
    story.append(Paragraph("<b>ELIGIBILITY & REQUIREMENTS</b>", section_header_style))
    eligibility = {
        "Minimum Turnover": data.get("Min_Turnover"),
        "Experience Required": data.get("Experience_Required"),
        "Documents Required": data.get("Required_Documents")
    }
    story.append(create_section_table(eligibility))

    # Build contents
    try:
        doc.build(story)
        print(f"Report saved: {filename}")
    except Exception as e:
        print(f"Failed to build PDF: {e}")

# Main Execution Script
def main():
    if not API_KEY:
        print("Cannot proceed without API Key.")
        return

    print("Starting Batch Bid Analysis...")
    
    for filename in FILES_TO_PROCESS:
        file_path = os.path.join(os.getcwd(), filename)
        
        # 1. Extract
        data = extract_data_from_pdf(file_path)
        if not data:
            continue
            
        # 2. Save English Report
        out_name = os.path.join(OUTPUT_DIR, f"Analysis_{filename}.pdf")
        create_pdf_report(out_name, data, 'en')
        
    print(f"All tasks completed. Check the '{OUTPUT_DIR}' folder.")

if __name__ == "__main__":
    main()
