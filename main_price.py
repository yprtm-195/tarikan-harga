import requests
import base64
import json
import time
import random
import os
from datetime import datetime

# --- KONSTANTA ---
# Masukkan URL Apps Script Harga lu di GitHub Secrets nanti
APPS_SCRIPT_URL = os.environ.get("APPS_SCRIPT_PRICE_URL", "https://script.google.com/macros/s/AKfycbw4YJNU0Z5fP5h50vXN-nZar7lh435kRTLjyKzZ6IPZaco87G242aRLL1atMgh4GQE/exec")
KEYWORDS = ["cimory", "kanzler"]
API_URL = "https://webcommerce-gw.alfagift.id/v2/products/searches"
MAX_RETRIES = 3
RETRY_DELAY = 5

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
    headers = STATIC_HEADERS.copy()
    headers['storecode'] = encode_base64_json({
        "store_code": store_info['store_code'], "delivery": True, "depo_id": "", "sapa": True,
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
            print(f"Error {store_info['store_code']} {keyword} (Percobaan {attempt+1}): {e}")
            if attempt < MAX_RETRIES - 1: time.sleep(RETRY_DELAY)
    return None

def main():
    print("Memulai Scraper Harga...")
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

    final_data = []
    header_row = ["Tanggal", "Kode Toko", "Nama Toko", "Cabang", "ID Produk", "Nama Produk", "Harga Normal", "Harga Promo"]
    final_data.append(header_row)
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    token_idx = 0

    for i in range(0, len(stores), 5):
        batch = stores[i:i+5]
        print(f"\n--- Batch {i//5 + 1} ---")
        for store in batch:
            token = tokens[token_idx % len(tokens)]
            token_idx += 1
            store_results_count = 0
            
            for kw in KEYWORDS:
                api_res = make_api_request(store, token, kw)
                if api_res and 'products' in api_res:
                    for p in api_res['products']:
                        name = p.get('productName')
                        if name in filter_names:
                            base_price = p.get('basePrice', 0)
                            final_price = p.get('finalPrice', 0)
                            
                            # Logika Harga:
                            harga_normal = base_price
                            harga_promo = final_price if final_price < base_price else "" # Kosong jika tidak ada promo

                            ids = product_map[name]
                            for pid in ids:
                                final_data.append([
                                    current_date, store['store_code'], store['store_name'], store['fc_code'],
                                    pid, name, harga_normal, harga_promo
                                ])
                                store_results_count += 1
            
            print(f"Toko {store['store_code']}: {store_results_count} data harga ditarik.")
            time.sleep(random.uniform(1, 2))
        time.sleep(random.uniform(2, 3))

    # Kirim ke Apps Script
    print(f"\nMengirim {len(final_data)-1} baris ke Google Sheet...")
    try:
        res = requests.post(APPS_SCRIPT_URL, json={'data': final_data}, timeout=120)
        print(f"Respons: {res.text}")
    except Exception as e:
        print(f"Gagal kirim data: {e}")

if __name__ == "__main__":
    main()
