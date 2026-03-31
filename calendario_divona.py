import requests
import json
import os
from datetime import datetime, timedelta
import calendar

# Configuración de variables
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

    ocupacion = {} 
    limpiezas = {} 
    
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

        info = {"nombre": get_safe_text(p.get("Nombre")), "color": color_reserva, "es_fin": False}
        
        # Llenar ocupación
        curr = start
        while curr <= end:
            dia_info = info.copy()
            if curr == end: dia_info["es_fin"] = True
            ocupacion[curr] = dia_info
            curr += timedelta(days=1)
        
        # El día de limpieza es el anterior al inicio de la reserva
        limpiezas[start - timedelta(days=1)] = True

    # Generar el HTML
    html = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>DIVONA CONTROL</title>'
    html += '<script src="https://cdn.tailwindcss.com"></script>'
    html += '<style>'
    html += 'body { background-color: #0f172a; font-family: sans-serif; color: #f1f5f9; } '
    html += '.month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1rem; overflow: hidden; } '
    html += '.grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: 0px; } '
    html += '.day { aspect-ratio: 1/1; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.75rem; border: 1px solid rgba(255,255,255,0.05); position: relative; } '
    html += '.occupied { color: white; font-weight: 700; border-width: 2px !important; } '
    html += '.cleaning-needed { border: 2px solid #eab308 !important; background: rgba(234, 179, 8, 0.1) !important; } '
    html += '.btn-clean { font-size: 0.5rem; margin-top: 4px; padding: 2px 5px; border-radius: 4px; background: #eab308; color: #451a03; font-weight: 800; cursor: pointer; text-transform: uppercase; } '
    html += '.btn-clean.done { background: #22c55e; color: white; } '
    html += '.badge-out { font-size: 0.5rem; background: rgba(0,0,0,0.5); padding: 1px 4px; border-radius: 3px; color: #fb7185; font-weight: 900; margin-bottom: 2px; } '
    html += '.free { color: #475569; } '
    html += '</style></head><body>'
    html += '<div class="p-8 max-w-7xl mx-auto"><h1 class="text-3xl font-black mb-8 border-b border-slate-800 pb-4">DIVONA DASHBOARD</h1>'
    html += '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">'

    for mes in range(3, 12):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia = calendar.monthrange(2026, mes)[0]
        _, t_color = get_day_season(datetime(2026, mes, 15))
        
        html += '<div class="month-card shadow-2xl">'
        html += '<div class="p-4 border-b border-slate-700 font-bold text-xs uppercase" style="color:'+t_color+'">'+MESES_NOMBRES[mes]+'</div>'
        html += '<div class="p-4"><div class="grid-cal">'
        for _ in range(primer_dia): html += '<div class="day border-none"></div>'
        
        for dia in range(1, ultimo + 1):
            f_act = datetime(2026, mes, dia).date()
            res = ocupacion.get(f_act)
            necesita_limpieza = limpiezas.get(f_act)
            
            css_classes = "day"
            style = ""
            content = "<span>"+str(dia)+"</span>"
            
            if res:
                css_classes += " occupied"
                style = "background-color:"+res['color']+"22; border-color:"+res['color']+";"
                if res['es_fin']: content = '<span class="badge-out">SALIDA</span>' + content
            
            if necesita_limpieza:
                css_classes += " cleaning-needed"
                content += '<button onclick="this.classList.toggle(\'done\'); this.innerText=this.classList.contains(\'done\')?\'LISTO ✅\':\'🧹 AVISAR\';" class="btn-clean">🧹 AVISAR</button>'
            
            if not res and not necesita_limpieza:
                css_classes += " free"
                
            html += '<div class="' + css_classes + '" style="' + style + '">' + content + '</div>'
            
        html += '</div></div></div>'

    html += '</div></div></body></html>'
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__": generar_dashboard()
