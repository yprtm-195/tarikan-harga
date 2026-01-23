import requests
import base64
import json
import time
import random
import os
from datetime import datetime

# --- KONSTANTA ---
APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_PRICE_URL", "https://script.google.com/macros/s/AKfycbwu0GTeV9Qtdip_TtI-gYh-vR0bcquQSG3Mo0tVhyt8EWWkd3rEisv9xO9BNOfGeTAO/exec")
KEYWORDS = ["cimory", "kanzler"]
API_URL = "https://webcommerce-gw.alfagift.id/v2/products/searches"
MAX_RETRIES = 3
RETRY_DELAY = 5
OUTPUT_DIR = "data" # Folder untuk menyimpan file JSON per branch

STATIC_HEADERS = {
    'accept': 'application/json', 'accept-language': 'id', 'devicemodel': 'chrome',
    'devicetype': 'Web', 'fingerprint': 'XZ83Mtc0WRlnPTpgVdH6wfTzBg8ifrSx6CmR0RKLDtkAw9IuhDVATi7qPjylV6IG',
    'latitude': '0', 'longitude': '0', 'origin': 'https://alfagift.id', 'priority': 'u=1, i',
    'referer': 'https://alfagift.id/', 'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
    'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"macOS"', 'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors', 'sec-fetch-site': 'same-site', 'trxid': '4557999812',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
}

def encode_base64_json(data_dict):
    return base64.b64encode(json.dumps(data_dict, separators=(',', ':')).encode('utf-8')).decode('utf-8')

def make_api_request(store_info, token, keyword):
    store_code = store_info['store_code']
    headers = STATIC_HEADERS.copy()
    headers['storecode'] = encode_base64_json({
        "store_code": store_code, "delivery": True, "depo_id": "", "sapa": True,
        "store_method": 1, "distance": 0, "maxDistance": None, "flagRoute": store_info['flagroute']
    })
    headers['fccode'] = encode_base64_json({"seller_id": "1", "fc_code": store_info['fc_code']})
    headers['token'] = token
    
    for attempt in range(MAX_RETRIES):
        try:
            res = requests.get(API_URL, headers=headers, params={'keyword': keyword, 'start': 0, 'limit': 60}, timeout=15)
            res.raise_for_status()
            return res.json()
        except Exception as e:
            print(f"Error {store_code} {keyword} (Percobaan {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY)
    return None

def main():
    print("Memulai Scraper Harga (Versi JSON Branch)...")
    try:
        config = requests.get(APPS_SCRIPT_URL, timeout=30).json()
    except Exception as e:
        print(f"Gagal ambil config: {e}")
        return

    stores = config.get("stores", [])
    tokens = config.get("tokens", [])
    product_map = config.get("productMap", {})
    filter_names = set(product_map.keys())

    if not all([stores, tokens, filter_names]):
        print("Config tidak lengkap. Keluar.")
        return

    # Untuk Google Sheet
    sheet_data = []
    header_row = ["Tanggal", "Kode Toko", "Nama Toko", "Cabang", "ID Produk", "Nama Produk", "Harga Normal", "Harga Promo", "Branch Name", "MDS Name"]
    sheet_data.append(header_row)
    
    # Untuk JSON per Branch
    branch_data_map = {} # { 'MANADO': [ {product_info}, ... ], ... }

    current_date = datetime.now().strftime('%Y-%m-%d')
    token_idx = 0

    for i in range(0, len(stores), 5):
        batch = stores[i:i+5]
        print(f"\n--- Batch {i//5 + 1} ---")
        for store in batch:
            token = tokens[token_idx % len(tokens)]
            token_idx += 1
            store_results_count = 0
            
            b_name = store.get('branch_name', 'N/A').strip().upper()
            m_name = store.get('mds_name', 'N/A')
            
            if b_name not in branch_data_map:
                branch_data_map[b_name] = {} # Menggunakan dict {store_code: {products}} untuk memudahkan grouping

            store_id = store['store_code']
            if store_id not in branch_data_map[b_name]:
                branch_data_map[b_name][store_id] = {
                    "store_code": store_id,
                    "store_name": store['store_name'],
                    "fc_code": store['fc_code'],
                    "branch_name": b_name,
                    "mds_name": m_name,
                    "last_updated": current_date,
                    "products": []
                }

            for kw in KEYWORDS:
                api_res = make_api_request(store, token, kw)
                if api_res and 'products' in api_res:
                    for p in api_res['products']:
                        name = p.get('productName')
                        if name in filter_names:
                            base_price = p.get('basePrice', 0)
                            final_price = p.get('finalPrice', 0)
                            harga_normal = base_price
                            harga_promo = final_price if final_price < base_price else ""

                            ids = product_map[name]
                            for pid in ids:
                                # Data untuk Sheet
                                sheet_data.append([
                                    current_date, store_id, store['store_name'], store['fc_code'],
                                    pid, name, harga_normal, harga_promo, b_name, m_name
                                ])
                                
                                # Data untuk JSON
                                branch_data_map[b_name][store_id]["products"].append({
                                    "id": pid,
                                    "name": name,
                                    "normal": harga_normal,
                                    "promo": harga_promo
                                })
                                store_results_count += 1
            
            print(f"Toko {store_id}: {store_results_count} data harga ditarik.")
            time.sleep(random.uniform(1, 2))
        time.sleep(random.uniform(2, 3))

    # --- SAVE TO JSON ---
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    print(f"\nMenyimpan data JSON ke folder '{OUTPUT_DIR}'...")
    for branch, store_dict in branch_data_map.items():
        filename = f"{branch.replace(' ', '_')}.json" # Ganti spasi dengan underscore
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        # Konversi dict toko ke list untuk JSON akhir
        final_branch_list = list(store_dict.values())
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(final_branch_list, f, indent=2, ensure_ascii=False)
        print(f"- {filepath} berhasil dibuat.")

    # --- SEND TO GOOGLE SHEET ---
    print(f"\nMengirim {len(sheet_data)-1} baris ke Google Sheet...")
    try:
        res = requests.post(APPS_SCRIPT_URL, json={'data': sheet_data}, timeout=120)
        print(f"Respons: {res.text}")
    except Exception as e:
        print(f"Gagal kirim data ke Sheet: {e}")

if __name__ == "__main__":
    main()
