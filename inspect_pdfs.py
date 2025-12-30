
import pdfplumber
import os

files = ['bid_summary (4).pdf', 'CPP.pdf', 'eprocurement.pdf', 'GeM-Bidding-8551552.pdf', 'IREPS.pdf']
base_path = r'c:\Users\ameer\Downloads\Bidanalyzer Pro'

for fname in files:
    fpath = os.path.join(base_path, fname)
    print(f"--- ANALYZING {fname} ---")
    try:
        with pdfplumber.open(fpath) as pdf:
            if len(pdf.pages) > 0:
                text = pdf.pages[0].extract_text()
                try:
                    print(text[:500] if text else "[No Text Found]")
                except UnicodeEncodeError:
                    print(text[:500].encode('utf-8', errors='replace').decode('utf-8') if text else "[No Text Found]")
            else:
                print("[Empty PDF]")
    except Exception as e:
        # Handle encoding errors when printing exception messages on Windows
        try:
            print(f"Error reading {fname}: {e}")
        except UnicodeEncodeError:
            print(f"Error reading {fname}: [Encoding Error in Exception Message]")
    print("\n")
