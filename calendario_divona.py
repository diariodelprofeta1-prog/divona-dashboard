import requests
import json
import os
from datetime import datetime, timedelta
import calendar

# Configuración (Secrets)
TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

MESES_NOMBRES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def generar_dashboard():
    # 1. Traer datos de Notion
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    if res.status_code != 200:
        print("Error de conexión"); return

    results = res.json().get("results", [])
    ocupacion = {}

    for r in results:
        p = r["properties"]
        f_data = p.get("Fecha", {}).get("date", {})
        if not f_data: continue
        
        start = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d").date()
        end = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d").date()
        
        # Leemos el nombre
        nombre = "Reserva"
        if p.get("Nombre", {}).get("title"):
            nombre = p["Nombre"]["title"][0]["plain_text"]

        info = {"nombre": nombre, "inicio": start, "fin": end}
        
        # Llenamos el calendario
        curr = start
        while curr <= end:
            ocupacion[curr] = info
            curr += timedelta(days=1)

    # 2. Crear el HTML (El diseño que te gustaba)
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background: #0f172a; color: white; font-family: sans-serif; }
            .grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
            .day { min-height: 60px; display: flex; align-items: center; justify-content: center; border-radius: 8px; background: rgba(255,255,255,0.05); }
            .occupied { background: #1d4ed8; font-weight: bold; }
        </style>
    </head>
    <body class="p-8">
        <h1 class="text-2xl font-bold mb-8">DIVONA MALLORCA - CALENDARIO BASE</h1>
        <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
    """

    for mes in range(3, 12):
        html += f'<div class="bg-slate-800 p-4 rounded-xl"> <h2 class="mb-4 text-blue-400 font-bold">{MESES_NOMBRES[mes]}</h2> <div class="grid-cal">'
        
        ultimo = calendar.monthrange(2026, mes)[1]
        vacio = calendar.monthrange(2026, mes)[0]
        
        for _ in range(vacio): html += '<div></div>'
        for dia in range(1, ultimo + 1):
            f_act = datetime(2026, mes, dia).date()
            clase = "day "
            if f_act in ocupacion: clase += "occupied"
            html += f'<div class="{clase}">{dia}</div>'
            
        html += '</div></div>'

    html += "</div></body></html>"
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    generar_dashboard()
