import os

def extract_bubbles(pdf_path):
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"[ERROR] PDF file not found: {pdf_path}")
        
        # Ask user to provide PDF
        pdf_path = input("\nEnter path to blank PDF template: ").strip()
        if not pdf_path or not os.path.exists(pdf_path):
            print("[ERROR] Invalid PDF path")
            return None
    
    try:
        from core.bubble_extraction import process_pdf_answer_sheet
        
        print(f"\nProcessing PDF: {pdf_path}")
        
        # Get options
        dpi = 300
        
        show_viz = input("Show visualization? (y/n, default y): ").strip().lower()
        show_visualization = show_viz != 'n'
        
        print("\nExtracting bubble positions...")
        print("This will detect questions AND student ID bubbles...\n")
        
        # Extract bubbles and save to JSON
        json_path = process_pdf_answer_sheet(
            pdf_path=pdf_path,
            dpi=dpi,
            keep_png=False,
            show_visualization=show_visualization
        )
        
        if json_path:
            print(f"\n[SUCCESS] Template saved to: {json_path}")
            return json_path
        else:
            print("[ERROR] Failed to extract bubbles")
            return None
            
    except ImportError as e:
        print(f"[ERROR] Failed to import bubble_detector: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to extract bubbles: {e}")
        return None