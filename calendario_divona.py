import requests
import json
import os
from datetime import datetime, timedelta
import calendar

# GitHub leerá esto de la "Caja Fuerte" que configuramos
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
    limpiezas_previas = {} # Diccionario para detectar el día antes de una reserva

    for r in res.json().get("results", []):
        p = r["properties"]
        f_data = p.get("Fecha", {}).get("date", {})
        if not f_data: continue
        
        start_dt = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d")
        end_dt = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d")
        
        # Extraemos los datos de las nuevas columnas de FECHA
        info = {
            "id": r["id"],
            "nombre": get_safe_text(p.get("Nombre")), 
            "inicio": start_dt.date(), 
            "fin": end_dt.date(), 
            "estado": get_safe_text(p.get("Estado")),
            "limpieza_ok": p.get("Limpieza", {}).get("date") is not None,
            "checkin_ok": p.get("Check-in", {}).get("date") is not None,
            "checkout_ok": p.get("Check-out", {}).get("date") is not None
        }
        
        # Llenamos ocupación
        curr = start_dt
        while curr <= end_dt:
            ocupacion[curr.date()] = info
            curr += timedelta(days=1)
        
        # Marcamos el día antes del inicio para la limpieza
        dia_antes = (start_dt - timedelta(days=1)).date()
        limpiezas_previas[dia_antes] = info

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>SAILBOAT CHARTER MALLORCA</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=Cinzel:wght@700&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body {{ background-color: #0f172a; font-family: 'Inter', sans-serif; color: #f1f5f9; }}
            h1 {{ font-family: 'Cinzel', serif; letter-spacing: 2px; }}
            .month-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 1.5rem; overflow: hidden; }}
            .grid-cal {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }}
            .day {{ aspect-ratio: 1/1; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.7rem; border-radius: 6px; position: relative; }}
            .occupied {{ background: #3b82f6; color: white; font-weight: 900; cursor: pointer; }}
            .free {{ background: rgba(255,255,255,0.03); color: #475569; }}
            .btn-action {{ font-size: 0.4rem; padding: 2px 0; border-radius: 4px; margin-top: 2px; width: 90%; font-weight: 900; border: none; text-transform: uppercase; cursor: pointer; }}
            .btn-off {{ background: #f59e0b; color: #451a03; }}
            .btn-on {{ background: #22c55e; color: white; cursor: default; }}
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div class="max-w-7xl mx-auto">
            <div class="flex flex-col md:flex-row justify-between items-center mb-12 pb-8 border-b border-slate-800">
                <div class="flex items-center gap-6">
                    <img src="https://i.ibb.co/680LhN0/Sailboat-Charter-Mallorca.png" alt="Logo" class="w-20 h-20 rounded-full border-2 border-slate-700 shadow-xl">
                    <div>
                        <h1 class="text-3xl font-black text-white">SAILBOAT CHARTER <span class="text-blue-500">MALLORCA</span></h1>
                        <p class="text-xs uppercase tracking-widest text-slate-500 font-bold">Fleet Command Dashboard</p>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
    """

    for mes in range(3, 12):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia = calendar.monthrange(2026, mes)[0]
        f_mid = datetime(2026, mes, 15)
        t_nombre, t_color, _ = get_day_season(f_mid)
        ocupados = sum(1 for d in range(1, ultimo + 1) if datetime(2026, mes, d).date() in ocupacion)
        
        html += f"""
        <div class="month-card shadow-2xl">
            <div class="p-4 flex justify-between items-center" style="background: {t_color}15; border-bottom: 2px solid {t_color}">
                <span class="font-black text-xs" style="color: {t_color}">{MESES_NOMBRES[mes].upper()}</span>
                <span class="text-[10px] font-black" style="color: {t_color}">{ocupados}/{ultimo} DÍAS</span>
            </div>
            <div class="p-4">
                <div class="grid grid-cols-7 gap-1 text-[8px] text-slate-600 font-bold mb-3 text-center">
                    <span>L</span><span>M</span><span>X</span><span>J</span><span>V</span><span>S</span><span>D</span>
                </div>
                <div class="grid-cal">"""
        
        for _ in range(primer_dia): html += '<div></div>'
        
        for dia in range(1, ultimo + 1):
            f_actual = datetime(2026, mes, dia).date()
            res = ocupacion.get(f_actual)
            limp = limpiezas_previas.get(f_actual)
            
            if res:
                btn_html = ""
                # Lógica de botones dentro del día ocupado
                if res['inicio'] == f_actual:
                    s, l = ("btn-on", "IN OK ✅") if res['checkin_ok'] else ("btn-off", "⚓ CHECK-IN")
                    btn_html = f'<button class="btn-action {s}" onclick="event.stopPropagation(); markDate(\'{res["id"]}\', \'Check-in\', this)">{l}</button>'
                elif res['fin'] == f_actual:
                    s, l = ("btn-on", "OUT OK ✅") if res['checkout_ok'] else ("btn-off", "🏁 OUT")
                    btn_html = f'<button class="btn-action {s}" onclick="event.stopPropagation(); markDate(\'{res["id"]}\', \'Check-out\', this)">{l}</button>'
                
                html += f'<div onclick=\'alert("{res["nombre"]} - {res["estado"]}")\' class="day occupied"><span>{dia}</span>{btn_html}</div>'
            
            elif limp:
                # El día antes mostramos el botón de limpieza
                s, l = ("btn-on", "LIMP OK ✅") if limp['limpieza_ok'] else ("btn-off", "🧹 LIMP")
                btn_limp = f'<button class="btn-action {s}" onclick="markDate(\'{limp["id"]}\', \'Limpieza\', this)">{l}</button>'
                html += f'<div class="day free"><span>{dia}</span>{btn_limp}</div>'
            
            else:
                html += f'<div class="day free">{dia}</div>'
                
        html += "</div></div></div>"

    html += f"""
            </div>
        </div>
        <script>
            async function markDate(id, prop, btn) {{
                if (btn.classList.contains('btn-on')) return;
                
                const today = new Date().toISOString().split('T')[0];
                btn.innerText = "...";
                
                try {{
                    const r = await fetch(`https://api.notion.com/v1/pages/${{id}}`, {{
                        method: 'PATCH',
                        headers: {{ 
                            'Authorization': 'Bearer {TOKEN}', 
                            'Notion-Version': '2022-06-28', 
                            'Content-Type': 'application/json' 
                        }},
                        body: JSON.stringify({{ 
                            properties: {{ 
                                [prop]: {{ date: {{ start: today }} }} 
                            }} 
                        }})
                    }});
                    if (r.ok) {{
                        btn.innerText = prop.toUpperCase() + " OK ✅";
                        btn.className = "btn-action btn-on";
                        btn.onclick = null;
                    }}
                }} catch(e) {{ alert("Error de conexión con Notion"); }}
            }}
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__": generar_dashboard()
