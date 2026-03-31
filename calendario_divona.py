import requests
import json
import os
from datetime import datetime, timedelta
import calendar
import sys

# DEBUG: Verificar secretos
TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

print("--- INICIANDO DIAGNÓSTICO ---")
if not TOKEN: print("❌ Error: NOTION_TOKEN está vacío.")
if not DATABASE_ID: print("❌ Error: DATABASE_ID está vacío.")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def get_safe_text(prop):
    if not prop: return "Reserva"
    try:
        t = prop.get("type")
        if t == "title": return prop["title"][0]["plain_text"] if prop["title"] else "Reserva"
        if t == "rich_text": return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else "Reserva"
        return "Reserva"
    except: return "Reserva"

def generar_dashboard():
    print("1️⃣ Intentando conectar con Notion...")
    try:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        res = requests.post(url, headers=headers)
        print(f"   Status Code: {res.status_code}")
        if res.status_code != 200:
            print(f"❌ Error de API: {res.text}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Fallo crítico en la petición: {e}")
        sys.exit(1)

    print("2️⃣ Procesando datos recibidos...")
    data = res.json()
    agenda = {}
    COLORES = ["#3b82f6", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b", "#06b6d4", "#f43f5e", "#6366f1", "#14b8a6", "#f97316"]

    results = data.get("results", [])
    print(f"   Se han encontrado {len(results)} filas en Notion.")

    for i, r in enumerate(results):
        try:
            p = r["properties"]
            f_data = p.get("Fecha", {}).get("date", {})
            if not f_data: continue
            
            start = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d").date()
            end = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d").date()
            
            res_id = r["id"]
            color_idx = sum(ord(c) for c in res_id) % len(COLORES)
            info = {"nombre": get_safe_text(p.get("Nombre")), "color": COLORES[color_idx]}

            curr = start
            while curr <= end:
                if curr not in agenda: agenda[curr] = {"res": None, "acts": []}
                agenda[curr]["res"] = info
                if curr == start: agenda[curr]["acts"].append("⚓")
                if curr == end: agenda[curr]["acts"].append("🏁")
                curr += timedelta(days=1)
            
            limp = start - timedelta(days=1)
            if limp not in agenda: agenda[limp] = {"res": None, "acts": []}
            agenda[limp]["acts"].append("🧹")
        except Exception as e:
            print(f"   ⚠️ Error en la fila {i}: {e}")

    print("3️⃣ Generando HTML...")
    # (Aquí va tu bloque de HTML que ya conoces)
    html = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><script src="https://cdn.tailwindcss.com"></script>'
    html += '<style>body{background:#0f172a;color:#f1f5f9}.month-card{background:#1e293b;border:1px solid #334155;border-radius:1rem;overflow:hidden}.grid-cal{display:grid;grid-template-columns:repeat(7,1fr);grid-template-rows:repeat(6,1fr);min-height:240px}.day{aspect-ratio:1/1;display:flex;flex-direction:column;align-items:center;justify-content:space-between;padding:4px 0;font-size:0.65rem;border:1px solid rgba(255,255,255,0.03)}.occupied{border-width:2px!important}</style></head><body>'
    html += '<div class="p-8 max-w-7xl mx-auto"><h1 class="text-4xl font-black mb-12 uppercase">Divona Center 2026</h1><div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">'
    
    meses_n = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    for m in range(3, 13):
        u = calendar.monthrange(2026, m)[1]
        p_d = calendar.monthrange(2026, m)[0]
        html += f'<div><div class="month-card shadow-2xl"><div class="p-4 bg-slate-800/30 text-blue-400 font-bold uppercase text-xs">{meses_n[m]}</div><div class="p-2"><div class="grid-cal">'
        for _ in range(p_d): html += '<div class="day border-none"></div>'
        for d in range(1, u + 1):
            f = datetime(2026, m, d).date()
            data_d = agenda.get(f, {"res": None, "acts": []})
            res, acts = data_d["res"], data_d["acts"]
            st = f"background:{res['color']}15;border-color:{res['color']};" if res else ""
            html += f'<div class="day {"occupied" if res else ""}" style="{st}" onclick="alert(\'{res["nombre"] if res else "Libre"}\')">'
            html += f'<span>{d}</span><div>{"".join(acts)}</div></div>'
        html += '</div></div></div></div>'
    html += '</div></div></body></html>'

    print("4️⃣ Intentando guardar index.html...")
    try:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("✅ Archivo index.html creado correctamente.")
    except Exception as e:
        print(f"❌ Error al escribir el archivo: {e}")
        sys.exit(1)

if __name__ == "__main__":
    generar_dashboard()
