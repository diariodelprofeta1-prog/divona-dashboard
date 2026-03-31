import requests
import json
import os
from datetime import datetime, timedelta
import calendar

TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": "Bearer " + str(TOKEN),
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
    if not prop: return ""
    try:
        t = prop.get("type")
        if t == "title": return prop["title"][0]["plain_text"] if prop["title"] else "Reserva"
        if t in ["select", "status"]: return prop[t]["name"] if prop[t] else ""
        return ""
    except: return ""

def generar_dashboard():
    res = requests.post("https://api.notion.com/v1/databases/" + str(DATABASE_ID) + "/query", headers=headers)
    ocupacion = {} 
    
    # Lista de colores para diferenciar clientes
    COLORES = ["#3b82f6", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b", "#06b6d4", "#f43f5e", "#6366f1", "#14b8a6", "#f97316"]

    for r in res.json().get("results", []):
        p = r["properties"]
        f_data = p.get("Fecha", {}).get("date", {})
        if not f_data: continue
        start = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d")
        end = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d")
        
        # Asignamos color único por ID de reserva
        res_id = r["id"]
        idx = sum(ord(c) for c in res_id) % len(COLORES)
        color_reserva = COLORES[idx]

        info = {"nombre": get_safe_text(p.get("Nombre")), "estado": get_safe_text(p.get("Estado")), "color": color_reserva}
        curr = start
        while curr <= end:
            ocupacion[curr.date()] = info
            curr += timedelta(days=1)

    html = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>DIVONA</title>'
    html += '<script src="https://cdn.tailwindcss.com"></script>'
    html += '<style>'
    html += 'body { background-color: #0f172a; font-family: sans-serif; color: #f1f5f9; } '
    html += '.month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1.5rem; overflow: hidden; } '
    html += '.grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; } '
    html += '.day { aspect-ratio: 1/1; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; border-radius: 6px; border: 1px solid rgba(0,0,0,0.1); } '
    html += '.occupied { color: white; font-weight: 900; cursor: pointer; } '
    html += '.free { background: rgba(255,255,255,0.03); color: #475569; } '
    html += '</style></head><body class="p-8"><div class="max-w-7xl mx-auto">'
    html += '<h1 class="text-3xl font-black mb-12 border-b border-slate-800 pb-8 uppercase">Sailboat Charter Mallorca</h1>'
    html += '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">'

    for mes in range(3, 12):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia = calendar.monthrange(2026, mes)[0]
        _, t_color = get_day_season(datetime(2026, mes, 15))
        
        html += '<div class="month-card shadow-2xl">'
        html += '<div class="p-4 flex justify-between items-center" style="background: ' + t_color + '15; border-bottom: 2px solid ' + t_color + '">'
        html += '<span class="font-black text-xs" style="color: ' + t_color + '">' + MESES_NOMBRES[mes].upper() + '</span></div>'
        html += '<div class="p-4"><div class="grid-cal">'
        for _ in range(primer_dia): html += '<div></div>'
        for dia in range(1, ultimo + 1):
            f_actual = datetime(2026, mes, dia).date()
            res = ocupacion.get(f_actual)
            if res:
                html += '<div onclick=\'alert("' + res["nombre"] + '")\' class="day occupied" style="background-color: ' + res["color"] + '">' + str(dia) + '</div>'
            else:
                html += '<div class="day free">' + str(dia) + '</div>'
        html += "</div></div></div>"

    html += "</div></div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__": generar_dashboard()
