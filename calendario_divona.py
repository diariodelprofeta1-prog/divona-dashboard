import requests
import json
import os
from datetime import datetime, timedelta
import calendar

TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

MESES_NOMBRES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def get_day_season(date_obj):
    m, d = date_obj.month, date_obj.day
    if (m == 6 and d >= 16) or (m in [7, 8]) or (m == 9 and d <= 15): return "ALTA", "#ef4444", "#fee2e2"
    if m in [4, 5] or (m == 6 and d <= 15) or (m == 9 and d >= 16) or m == 10: return "MEDIA", "#f59e0b", "#fef3c7"
    return "BAJA", "#64748b", "#f1f5f9"

def get_safe_text(prop):
    if not prop: return ""
    t = prop.get("type")
    try:
        if t == "title": return prop["title"][0]["plain_text"] if prop["title"] else "Reserva"
        if t in ["select", "status"]: return prop[t]["name"] if prop[t] else ""
        if t == "rich_text": return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else ""
        if t == "phone_number": return prop["phone_number"] or ""
        return ""
    except: return ""

def generar_dashboard():
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    ocupacion = {} 
    for r in res.json().get("results", []):
        p = r["properties"]
        f_data = p.get("Fecha", {}).get("date", {})
        if not f_data: continue
        start = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d")
        end = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d")
        
        # --- PASO 1: SOLO LEER LAS NUEVAS FECHAS ---
        # Si la columna tiene fecha, pondremos 'OK', si no 'Pendiente'
        limp = "OK" if p.get("Limpieza", {}).get("date") else "Pendiente"
        c_in = "OK" if p.get("Check-in", {}).get("date") else "Pendiente"
        c_out = "OK" if p.get("Check-out", {}).get("date") else "Pendiente"

        info = {
            "nombre": get_safe_text(p.get("Nombre")), 
            "estado": get_safe_text(p.get("Estado")),
            "limp": limp, "in": c_in, "out": c_out
        }
        
        curr = start
        while curr <= end:
            ocupacion[curr.date()] = info
            curr += timedelta(days=1)

    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=Cinzel:wght@700&display=swap" rel="stylesheet">
        <style>
            body { background-color: #0f172a; font-family: 'Inter', sans-serif; color: #f1f5f9; }
            h1 { font-family: 'Cinzel', serif; letter-spacing: 2px; }
            .month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1.5rem; overflow: hidden; }
            .grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
            .day { aspect-ratio: 1/1; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; border-radius: 6px; }
            .occupied { background: #3b82f6; color: white; font-weight: 900; cursor: pointer; }
            .free { background: rgba(255,255,255,0.03); color: #475569; }
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div class="max-w-7xl mx-auto">
            <h1 class="text-3xl font-black text-white mb-12 border-b border-slate-800 pb-8">SAILBOAT CHARTER MALLORCA</h1>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
    """

    for mes in range(3, 12):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia = calendar.monthrange(2026, mes)[0]
        f_mid = datetime(2026, mes, 15)
        _, t_color, _ = get_day_season(f_mid)
        html += f"""
        <div class="month-card shadow-2xl">
            <div class="p-4 flex justify-between items-center" style="background: {t_color}15; border-bottom: 2px solid {t_color}">
                <span class="font-black text-xs" style="color: {t_color}">{MESES_NOMBRES[mes].upper()}</span>
            </div>
            <div class="p-4"><div class="grid-cal">"""
        for _ in range(primer_dia): html += '<div></div>'
        for dia in range(1, ultimo + 1):
            f_actual = datetime(2026, mes, dia).date()
            res = ocupacion.get(f_actual)
            if res:
                # Ahora el alert muestra si la limpieza/in/out están hechos
                msg = f"{res['nombre']}\\nEstado: {res['estado']}\\nLimpieza: {res['limp']}\\nCheck-in: {res['in']}\\nCheck-out: {res['out']}"
                html += f'<div onclick=\'alert("{msg}")\' class="day occupied">{dia}</div>'
            else:
                html += f'<div class="day free">{dia}</div>'
        html += "</div></div></div>"

    html += "</div></div></body></html>"
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__": generar_dashboard()
