import requests
import json
import os
from datetime import datetime, timedelta
import calendar
import sys

# Secretos de GitHub
TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

if not TOKEN or not DATABASE_ID:
    print("❌ ERROR: Faltan los Secretos (Tokens) en GitHub.")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

MESES_NOMBRES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def get_day_season(date_obj):
    m, d = date_obj.month, date_obj.day
    if (m == 6 and d >= 16) or (m in [7, 8]) or (m == 9 and d <= 15): return "ALTA", "#ef4444"
    if m in [4, 5] or (m == 6 and d <= 15) or (m == 9 and d >= 16) or m == 10: return "MEDIA", "#f59e0b"
    return "BAJA", "#64748b"

def get_safe_text(prop):
    if not prop: return "Sin Nombre"
    try:
        t = prop.get("type")
        if t == "title": return prop["title"][0]["plain_text"] if prop["title"] else "Reserva"
        if t == "rich_text": return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else "Reserva"
        return "Reserva"
    except: return "Reserva"

def get_safe_num(prop):
    if not prop: return 0
    try:
        return prop.get("number", 0) or 0
    except: return 0

def generar_dashboard():
    print("🚀 Conectando con Notion...")
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    if res.status_code != 200:
        print(f"❌ Error API: {res.text}")
        sys.exit(1)
        
    data = res.json()
    agenda = {}
    ingresos_mes = {m: 0 for m in range(1, 13)}
    COLORES = ["#3b82f6", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b", "#06b6d4", "#f43f5e", "#6366f1", "#14b8a6", "#f97316"]

    for r in data.get("results", []):
        p = r["properties"]
        f_prop = p.get("Fecha", {}).get("date")
        if not f_prop: continue
        
        start = datetime.strptime(f_prop["start"][:10], "%Y-%m-%d").date()
        end_str = f_prop.get("end") or f_prop["start"]
        end = datetime.strptime(end_str[:10], "%Y-%m-%d").date()
        
        monto = get_safe_num(p.get("Precio"))
        ingresos_mes[start.month] += monto

        res_id = r["id"]
        color_idx = sum(ord(c) for c in res_id) % len(COLORES)
        
        info = {
            "nombre": get_safe_text(p.get("Nombre")), 
            "color": COLORES[color_idx],
            "monto": monto,
            "detalle": f"Precio: {monto}€\\nEstado: {get_safe_text(p.get('Estado'))}"
        }

        curr = start
        while curr <= end:
            if curr not in agenda: agenda[curr] = {"res": None, "acts": []}
            agenda[curr]["res"] = info
            if curr == start: agenda[curr]["acts"].append("IN")
            if curr == end: agenda[curr]["acts"].append("OUT")
            curr += timedelta(days=1)
        
        limp = start - timedelta(days=1)
        if limp not in agenda: agenda[limp] = {"res": None, "acts": []}
        agenda[limp]["acts"].append("LIMP")

    # --- HTML ---
    html = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><script src="https://cdn.tailwindcss.com"></script>'
    html += '<style>body{background:#0f172a;color:#f1f5f9}.month-card{background:#1e293b;border-radius:1rem;overflow:hidden}'
    html += '.grid-cal{display:grid;grid-template-columns:repeat(7,1fr);grid-template-rows:repeat(6,1fr);min-height:280px}'
    html += '.day{aspect-ratio:1/1;display:flex;flex-direction:column;align-items:center;padding:4px;font-size:0.65rem;border:1px solid rgba(255,255,255,0.03)}'
    html += '.occupied{border-width:2px!important;cursor:pointer}.dimmed{opacity:0.1}.highlight{border:2px solid white!important}</style></head><body>'
    
    total_anual = sum(ingresos_mes.values())
    html += f'<div class="p-8 max-w-7xl mx-auto"><div><h1 class="text-4xl font-black uppercase">Divona Center</h1>'
    html += f'<p class="text-blue-400 font-bold text-xl mb-8">INGRESOS 2026: {total_anual:,.2f} €</p></div>'
    html += '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">'

    for mes in range(3, 13):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia = calendar.monthrange(2026, mes)[0]
        _, t_color = get_day_season(datetime(2026, mes, 15))
        
        html += f'<div><div class="month-card shadow-2xl"><div class="p-4 border-b border-slate-700 flex justify-between bg-slate-800/30">'
        html += f'<span class="font-bold text-[10px] uppercase" style="color:{t_color}">{MESES_NOMBRES[mes]}</span>'
        html += f'<span class="bg-slate-700 px-2 py-1 rounded text-[10px]">{ingresos_mes[mes]:,.0f} €</span></div><div class="p-2"><div class="grid-cal">'
        
        for _ in range(primer_dia): html += '<div class="day border-none"></div>'
        for dia in range(1, ultimo + 1):
            f_act = datetime(2026, mes, dia).date()
            d_info = agenda.get(f_act, {"res": None, "acts": []})
            res = d_info["res"]
            acts = d_info["acts"]
            tag = "LIMP" if "LIMP" in acts else ("OPS" if ("IN" in acts or "OUT" in acts) else "NONE")
            style = f"background:{res['color']}15;border-color:{res['color']};" if res else ""
            html += f'<div class="day day-cell {"occupied" if res else ""}" data-tag="{tag}" style="{style}" onclick="alert(\'{res["nombre"] if res else "Libre"}\')">'
            html += f'<span>{dia}</span><div class="flex">{"🧹" if "LIMP" in acts else ""}{"⚓" if "IN" in acts else ""}{"🏁" if "OUT" in acts else ""}</div></div>'
        html += '</div></div></div></div>'
    html += '</div></div></body></html>'

    with open("index.html", "w", encoding="utf-8") as f: f.write(html)
    print("✅ Dashboard generado.")

if __name__ == "__main__": generar_dashboard()
