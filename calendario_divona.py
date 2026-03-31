import requests
import json
import os
from datetime import datetime, timedelta
import calendar

# Configuración
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
    if res.status_code != 200: return

    # Diccionario maestro: fecha -> { reserva: {}, acciones: [] }
    agenda = {}
    COLORES = ["#3b82f6", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b", "#06b6d4", "#f43f5e", "#6366f1", "#14b8a6", "#f97316"]

    for r in res.json().get("results", []):
        p = r["properties"]
        f_data = p.get("Fecha", {}).get("date", {})
        if not f_data: continue
        
        start = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d").date()
        end = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d").date()
        
        res_id = r["id"]
        color_idx = sum(ord(c) for c in res_id) % len(COLORES)
        color_reserva = COLORES[color_idx]
        info = {"nombre": get_safe_text(p.get("Nombre")), "color": color_reserva}

        # Llenar días de reserva
        curr = start
        while curr <= end:
            if curr not in agenda: agenda[curr] = {"res": None, "acts": []}
            agenda[curr]["res"] = info
            
            # Añadir Check-in o Check-out de forma sutil
            if curr == start: agenda[curr]["acts"].append("IN")
            if curr == end: agenda[curr]["acts"].append("OUT")
            curr += timedelta(days=1)
        
        # Añadir Limpieza (día antes del start)
        dia_limp = start - timedelta(days=1)
        if dia_limp not in agenda: agenda[dia_limp] = {"res": None, "acts": []}
        agenda[dia_limp]["acts"].append("LIMP")

    # HTML y CSS
    html = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>DIVONA COMMAND</title>'
    html += '<script src="https://cdn.tailwindcss.com"></script>'
    html += '<style>'
    html += 'body { background-color: #0f172a; font-family: sans-serif; color: #f1f5f9; } '
    html += '.month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1rem; overflow: hidden; } '
    html += '.grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: 0px; } '
    html += '.day { aspect-ratio: 1/1; display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: 4px 0; font-size: 0.7rem; border: 1px solid rgba(255,255,255,0.03); position: relative; } '
    html += '.occupied { border-width: 2px !important; cursor: pointer; } '
    html += '.btn-mini { font-size: 0.5rem; padding: 1px 3px; border-radius: 3px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); transition: all 0.2s; } '
    html += '.btn-mini:active { transform: scale(0.9); } '
    html += '.btn-limp.active { background: #eab308; color: #451a03; border-color: #eab308; } '
    html += '.btn-in.active { background: #3b82f6; color: white; border-color: #3b82f6; } '
    html += '.btn-out.active { background: #fb7185; color: white; border-color: #fb7185; } '
    html += '.free { color: #475569; } '
    html += '</style></head><body>'
    html += '<div class="p-8 max-w-7xl mx-auto"><h1 class="text-2xl font-black mb-8 border-b border-slate-800 pb-4">SAILBOAT CHARTER MALLORCA</h1>'
    html += '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">'

    for mes in range(3, 12):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia = calendar.monthrange(2026, mes)[0]
        _, t_color = get_day_season(datetime(2026, mes, 15))
        
        html += '<div class="month-card shadow-xl">'
        html += '<div class="p-3 border-b border-slate-700 font-bold text-[10px] uppercase tracking-tighter" style="color:'+t_color+'">'+MESES_NOMBRES[mes]+'</div>'
        html += '<div class="p-3"><div class="grid-cal">'
        for _ in range(primer_dia): html += '<div class="day border-none"></div>'
        
        for dia in range(1, ultimo + 1):
            f_act = datetime(2026, mes, dia).date()
            data = agenda.get(f_act, {"res": None, "acts": []})
            res = data["res"]
            acts = data["acts"]
            
            css = "day"
            style = ""
            if res:
                css += " occupied"
                style = "background-color:" + res['color'] + "15; border-color:" + res['color'] + ";"
            else:
                css += " free"
                
            html += '<div class="' + css + '" style="' + style + '" onclick="if('+str(res is not None).lower()+') alert(\''+(res['nombre'] if res else '')+'\')">'
            html += '<span class="font-bold">' + str(dia) + '</span>'
            
            # Contenedor de acciones (iconos pequeños abajo)
            html += '<div class="flex gap-0.5 justify-center">'
            if "LIMP" in acts:
                html += '<button onclick="event.stopPropagation(); this.classList.toggle(\'active\')" class="btn-mini btn-limp" title="Limpieza">🧹</button>'
            if "IN" in acts:
                html += '<button onclick="event.stopPropagation(); this.classList.toggle(\'active\')" class="btn-mini btn-in" title="Check-in">⚓</button>'
            if "OUT" in acts:
                html += '<button onclick="event.stopPropagation(); this.classList.toggle(\'active\')" class="btn-mini btn-out" title="Check-out">🏁</button>'
            html += '</div></div>'
            
        html += '</div></div></div>'

    html += '</div></div></body></html>'
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__":
    generar_dashboard()
