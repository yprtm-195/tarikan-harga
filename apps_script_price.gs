function doGet(e) {
  const SPREADSHEET_ID = SpreadsheetApp.getActiveSpreadsheet().getId();
  try {
    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const storeSheet = ss.getSheetByName("Daftar Toko");
    const tokenSheet = ss.getSheetByName("Daftar Token");
    const productSheet = ss.getSheetByName("Daftar Produk");

    const storeDataValues = storeSheet.getDataRange().getValues();
    const rawTokenData = tokenSheet.getDataRange().getValues();
    const rawProductData = productSheet.getDataRange().getValues();

    // --- Proses Data Toko ---
    let stores = [];
    if (storeDataValues.length > 1) {
      const storeHeaders = storeDataValues.shift();
      stores = storeDataValues.map(row => {
        let obj = {};
        storeHeaders.forEach((h, i) => { obj[h] = row[i]; });
        return obj;
      });
    }

    // --- Proses Data Token (Kolom B) ---
    let tokens = [];
    if (rawTokenData.length > 1) {
      rawTokenData.shift();
      tokens = rawTokenData.map(row => String(row[1])).filter(String);
    }

    // --- Proses Pemetaan Produk (Satu Nama Banyak ID) ---
    let productMap = {};
    if (rawProductData.length > 1) {
      rawProductData.shift();
      rawProductData.forEach(row => {
        const id = String(row[0]);
        const name = String(row[1]);
        if (name && id) {
          if (!productMap[name]) productMap[name] = [];
          productMap[name].push(id);
        }
      });
    }

    return ContentService.createTextOutput(JSON.stringify({
      stores: stores,
      tokens: tokens,
      productMap: productMap
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doPost(e) {
  const SHEET_NAME_PRICE = "Data Harga Terkini";
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    let sheet = ss.getSheetByName(SHEET_NAME_PRICE);
    if (!sheet) sheet = ss.insertSheet(SHEET_NAME_PRICE);

    const payload = JSON.parse(e.postData.contents);
    const data = payload.data; // Array of arrays

    if (!Array.isArray(data) || data.length === 0) throw new Error("Data kosong.");

    // Karena ini Monitoring Harga Terkini, kita CLEAR dan TULIS ULANG tiap hari
    sheet.clear();
    
    // Pastikan data dikirim dalam bentuk list of lists (baris & kolom)
    sheet.getRange(1, 1, data.length, data[0].length).setValues(data);

    return ContentService.createTextOutput(JSON.stringify({ status: "success", message: `${data.length - 1} baris harga berhasil diupdate.` }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ status: "error", message: err.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
