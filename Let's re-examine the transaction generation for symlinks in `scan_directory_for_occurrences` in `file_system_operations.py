        if replace_occurrences(original_name) != original_name: 
            is_dir = item_path.is_dir() and not item_path.is_symlink() 
            tx_type_val = TransactionType.FOLDER_NAME.value if is_dir else TransactionType.FILE_NAME.value
            # ... appends transaction
