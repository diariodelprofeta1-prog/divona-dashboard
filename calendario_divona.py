import requests
import os
from datetime import datetime, timedelta
import calendar
import sys

# Configuración de Secretos
TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def get_safe_text(prop):
    if not prop: return "Reserva"
    try:
        t = prop.get("type")
        if t == "title": return prop["title"][0]["plain_text"]
        if t == "rich_text": return prop["rich_text"][0]["plain_text"]
        return "Reserva"
    except: return "Reserva"

def generar_dashboard():
    print("Conectando con Notion...")
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    
    if res.status_code != 200:
        print(f"Error: {res.text}")
        sys.exit(1)
        
    data = res.json()
    agenda = {}
    
    for r in data.get("results", []):
        p = r["properties"]
        f_prop = p.get("Fecha", {}).get("date")
        if not f_prop: continue
        
        start = datetime.strptime(f_prop["start"][:10], "%Y-%m-%d").date()
        end_str = f_prop.get("end") or f_prop["start"]
        end = datetime.strptime(end_str[:10], "%Y-%m-%d").date()
        
        # Sacamos el nombre (probando con 'Nombre' o 'Cliente')
        nombre = get_safe_text(p.get("Nombre")) or get_safe_text(p.get("Cliente"))

        curr = start
        while curr <= end:
            if curr not in agenda: agenda[curr] = {"nombre": nombre, "acts": []}
            if curr == start: agenda[curr]["acts"].append("⚓")
            if curr == end: agenda[curr]["acts"].append("🏁")
            curr += timedelta(days=1)
            
        limp = start - timedelta(days=1)
        if limp not in agenda: agenda[limp] = {"nombre": None, "acts": []}
        agenda[limp]["acts"].append("🧹")

    # HTML Simple
    html = '<!DOCTYPE html><html><head><meta charset="UTF-8"><script src="https://cdn.tailwindcss.com"></script>'
    html += '<style>body{background:#0f172a;color:white}.grid-cal{display:grid;grid-template-columns:repeat(7,1fr);grid-template-rows:repeat(6,1fr);min-height:250px}.day{border:1px solid #334155;aspect-ratio:1/1;padding:2px;font-size:0.7rem}</style></head><body class="p-4">'
    html += '<h1 class="text-2xl font-bold mb-4">Divona Dashboard</h1><div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">'

    meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    for m in range(3, 13): # De Marzo a Diciembre
        html += f'<div class="bg-slate-800 p-2 rounded-lg"><h2 class="text-center font-bold border-b border-slate-600 mb-2">{meses[m]}</h2><div class="grid-cal">'
        primer_dia = calendar.monthrange(2026, m)[0]
        dias_mes = calendar.monthrange(2026, m)[1]
        
        for _ in range(primer_dia): html += '<div></div>'
        for d in range(1, dias_mes + 1):
            f_actual = datetime(2026, m, d).date()
            info = agenda.get(f_actual, {"nombre": None, "acts": []})
            bg = "bg-blue-900/40" if info["nombre"] else ""
            acts = "".join(info["acts"])
            click = f"onclick=\"alert('{info['nombre'] or 'Libre'}')\""
            html += f'<div class="day {bg} cursor-pointer" {click}><span>{d}</span><div class="text-center">{acts}</div></div>'
        html += '</div></div>'
    
    html += '</div></body></html>'
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__": generar_dashboard()
