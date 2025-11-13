def create_sheet():    
    try:
        from core.sheet_maker import AnswerSheetDesigner
        
        # Get user input
        print("\nAnswer Sheet Configuration:")
        num_questions = input("Number of questions: ").strip()
        if not num_questions:
            num_questions = "40"
        
        try:
            num_questions = int(num_questions)
        except ValueError:
            print("[ERROR] Invalid number. Using 40 questions.")
            num_questions = 40
        
        # Get output path
        output_path = input(f"Save as (default: answer_sheet.pdf): ").strip()
        if not output_path:
            output_path = f'answer_sheet.pdf'
        
        if not output_path.endswith('.pdf'):
            output_path += '.pdf'
        
        print(f"\nCreating {num_questions}-question answer sheet...")
        
        # Create designer and generate PDF
        designer = AnswerSheetDesigner()
        designer.set_config(include_student_id=True)
        
        # Use preset for optimal layout
        designer.create_answer_sheet(
            total_questions=num_questions,
            output_path=output_path,
            format='pdf',
            use_preset=True
        )
        
        print(f"\n[SUCCESS] Blank sheet created: {output_path}")
        return output_path
        
    except ImportError as e:
        print(f"[ERROR] Failed to import sheet_maker: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to create blank sheet: {e}")
        return None