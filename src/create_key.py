def create_key(template_json): 
    import os
    if not template_json or not os.path.exists(template_json):
        print(f"[ERROR] Template JSON not found: {template_json}")
        
        # Ask user to provide template
        template_json = input("\nEnter path to template JSON: ").strip()
        if not template_json or not os.path.exists(template_json):
            print("[ERROR] Invalid template path")
            return None
    
    try:
        from core.answer_key import load_template_info, create_answer_key_manual, create_answer_key_from_scan
        
        print(f"\nUsing template: {template_json}")
        
        # Load template info
        template_info = load_template_info(template_json)
        
        print("\nChoose answer key creation method:")
        print("1. Manual entry (type answers for each question)")
        print("2. Scan master answer sheet (automatic detection)")
        
        choice = input("\nEnter choice (1-2, default 1): ").strip()
        if not choice:
            choice = '1'
        
        if choice == '1':
            # Manual entry
            print("\n[MANUAL ENTRY MODE]")
            print("You will be prompted to enter the correct answer for each question.")
            print("Press Enter when ready...")
            input()
            
            answer_key, key_json = create_answer_key_manual(template_info)
            print(f"\n[SUCCESS] Answer key created: {key_json}")
            return key_json
            
        elif choice == '2':
            # Scan master sheet
            master_sheet = input("\nEnter path to master sheet image: ").strip()
            if not master_sheet:
                master_sheet = 'master_sheet.png'
            
            if not os.path.exists(master_sheet):
                print(f"[ERROR] Master sheet not found: {master_sheet}")
                return None
            
            threshold = input("Detection threshold (20-90, default 85): ").strip()
            threshold = int(threshold) if threshold else 85
            
            print("\nScanning master answer sheet...")
            
            answer_key, key_json = create_answer_key_from_scan(
                template_info,
                master_sheet,
                threshold_percent=threshold
            )
            
            if key_json:
                print(f"\n[SUCCESS] Answer key created: {key_json}")
                return key_json
            else:
                print("[ERROR] Failed to create answer key from scan")
                return None
        else:
            print("[ERROR] Invalid choice")
            return None
            
    except ImportError as e:
        print(f"[ERROR] Failed to import answer_key: {e}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to create answer key: {e}")
        return None