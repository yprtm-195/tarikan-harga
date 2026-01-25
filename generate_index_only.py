import requests
import json
import os

# --- KONSTANTA ---
APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_PRICE_URL", "https://script.google.com/macros/s/AKfycbw4YJNU0Z5fP5h50vXN-nZar7lh435kRTLjyKzZ6IPZaco87G242aRLL1atMgh4GQE/exec")
OUTPUT_DIR = "data"

def main():
    print("Memulai Generator Index Kilat...")
    
    # 1. Ambil Config dari Apps Script
    print(f"Mengambil daftar toko dari: {APPS_SCRIPT_URL}")
    try:
        config = requests.get(APPS_SCRIPT_URL, timeout=30).json()
    except Exception as e:
        print(f"Gagal ambil config: {e}")
        return

    stores = config.get("stores", [])
    
    if not stores:
        print("Daftar toko kosong. Keluar.")
        return

    print(f"Berhasil memuat {len(stores)} toko.")

    # 2. Build Index
    store_index_map = {}
    
    for store in stores:
        store_id = store['store_code']
        b_name = store.get('branch_name', 'N/A').strip().upper()
        
        # Logic nama file sama persis dengan main_price.py
        branch_filename = f"{b_name.replace(' ', '_')}.json"
        
        store_index_map[store_id] = branch_filename

    # 3. Save File
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    index_filepath = os.path.join(OUTPUT_DIR, "store_index.json")
    print(f"Menyimpan Index Toko ke '{index_filepath}'...")
    
    with open(index_filepath, 'w', encoding='utf-8') as f:
        json.dump(store_index_map, f, indent=2, ensure_ascii=False)
        
    print(f"SUKSES! File {index_filepath} berhasil dibuat.")

if __name__ == "__main__":
    main()
