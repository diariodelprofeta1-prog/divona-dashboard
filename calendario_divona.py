import requests
import json
import os
from datetime import datetime, timedelta
import calendar

# Configuración básica
TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def generar_dashboard():
    print("🛰️ Iniciando escaneo de la base de datos...")
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}", headers=headers)
    
    if res.status_code == 200:
        columnas = res.json().get("properties", {}).keys()
        print(f"✅ CONEXIÓN EXITOSA. Columnas encontradas: {list(columnas)}")
    else:
        print(f"❌ ERROR DE CONEXIÓN: {res.status_code}")
        print(res.text)
        return

    # Generamos un HTML básico para que la web no esté vacía
    html = "<html><body style='background:#0f172a; color:white; font-family:sans-serif;'><h1>Escaneo en curso...</h1></body></html>"
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("🏁 Fin del escaneo.")

if __name__ == "__main__":
    generar_dashboard()
