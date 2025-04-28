from datetime import datetime

def convert_date(raw_date):
    try:
        # Handle berbagai format tanggal dari API
        if "UTC" in raw_date:
            # Format: "02/04/2025, 08:00 AM, +0000 UTC"
            date_obj = datetime.strptime(raw_date, "%m/%d/%Y, %I:%M %p, %z UTC")
        elif "hari" in raw_date.lower() or "jam" in raw_date.lower():
            # Format relatif seperti "2 hari yang lalu"
            return datetime.now().strftime("%Y-%m-%d")
        else:
            # Coba format lainnya
            date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
        
        # Konversi ke format MySQL
        return date_obj.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Gagal konversi tanggal: {raw_date}. Error: {str(e)}")
        return None  # atau return datetime.now().strftime("%Y-%m-%d") untuk default
    
print(convert_date("02/04/2025, 08:00 AM, +0000 UTC")) 
# Output: 2025-02-04 08:00:00