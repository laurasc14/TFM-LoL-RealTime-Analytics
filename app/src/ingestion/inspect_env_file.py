import os

dotenv_path = r"H:\00_TFM\PROYECTO\TFM-LoL-RealTime-Analytics\.env"

print("📄 Contenido crudo del archivo .env:")
print("-" * 40)

try:
    with open(dotenv_path, "rb") as f:
        raw = f.read()
        print(raw)
        print("\n🧾 Interpretado como texto:")
        print(raw.decode("utf-8-sig"))  # Soporta BOM si lo hubiera
except Exception as e:
    print("❌ Error leyendo el archivo:", e)
