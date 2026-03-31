import requests
import json
import os
from datetime import datetime, timedelta
import calendar
import sys

# 1. CARGA DE CONFIGURACIÓN
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
        if t == "rich_text": return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else ""
        return ""
    except: return ""

def generar_dashboard():
    print("--- INICIANDO DIAGNÓSTICO DEL DIVONA ---")
    try:
        url = "https://api.notion.com/v1/databases/" + str(DATABASE_ID) + "/query"
        res = requests.post(url, headers=headers)
        if res.status_code != 200:
            print(f"ERROR NOTION {res.status_code}: {res.text}")
            return
    except Exception as e:
        print(f"ERROR CRÍTICO CONEXIÓN: {e}")
        return

    ocupacion = {}
    limpiezas_previas = {}
    
    results = res.json().get("results", [])
    print(f"Se han encontrado {len(results)} registros en Notion.")

    for r in results:
        try:
            p = r["properties"]
            f_data = p.get("Fecha", {}).get("date", {})
            if not f_data or not f_data.get("start"):
                continue
            
            start_dt = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d")
            end_dt = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d")
            
            # --- ZONA DE PRUEBA (Aquí es donde solía fallar) ---
            # Usamos .get() con calma para no romper el código
            def check_date_prop(name):
                prop = p.get(name, {})
                return prop.get("date") is not None if prop else False

            info = {
                "id": r["id"],
                "nombre": get_safe_text(p.get("Nombre")).replace('"', '').replace("'", ""),
                "estado": get_safe_text(p.get("Estado")),
                "in_ok": check_date_prop("Check-in"),
                "out_ok": check_date_prop("Check-out"),
                "limp_ok": check_date_prop("Limpieza"),
                "inicio": start_dt.date(),
                "fin": end_dt.date()
            }
            
            curr = start_dt
            while curr <= end_dt:
                ocupacion[curr.date()] = info
                curr += timedelta(days=1)
            
            limpiezas_previas[(start_dt - timedelta(days=1)).date()] = info
        except Exception as e:
            print(f"AVISO: No se pudo procesar una reserva (ID: {r.get('id')}). Error: {e}")

    # CONSTRUCCIÓN DEL HTML
    try:
        html_start = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>DIVONA CONTROL</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body { background-color: #0f172a; font-family: sans-serif; color: #f1f5f9; }
            .month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1rem; overflow: hidden; margin-bottom: 20px; }
            .grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
            .day { aspect-ratio: 1/1; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.65rem; border-radius: 4px; position: relative; }
            .occupied { background: #3b82f6; color: white; font-weight: bold; cursor: pointer; }
            .free { background: rgba(255,255,255,0.03); color: #475569; }
            .btn-act { font-size: 0.4rem; padding: 2px 0; border-radius: 3px; margin-top: 2px; width: 92%; font-weight: 900; border: none; text-transform: uppercase; cursor: pointer; }
            .btn-off { background: #f59e0b; color: #451a03; }
            .btn-on { background: #22c55e; color: white; cursor: default; }
        </style></head><body class="p-4"><div class="max-w-7xl mx-auto">
        <h1 class="text-2xl font-bold mb-8 border-b border-slate-800 pb-4">SAILBOAT CHARTER MALLORCA</h1>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">"""

        html_meses = ""
        for mes in range(3, 12):
            ultimo = calendar.monthrange(2026, mes)[1]
            primer_dia = calendar.monthrange(2026, mes)[0]
            _, t_color = get_day_season(datetime(2026, mes, 15))
            
            html_meses += '<div class="month-card shadow-lg">'
            html_meses += '<div class="p-3 border-b border-slate-700 bg-slate-800/50">'
            html_meses += '<span class="font-bold text-xs uppercase" style="color: ' + t_color + '">' + MESES_NOMBRES[mes] + '</span></div>'
            html_meses += '<div class="p-3"><div class="grid-cal">'
            for _ in range(primer_dia): html_meses += '<div></div>'
            for dia in range(1, ultimo + 1):
                f_act = datetime(2026, mes, dia).date()
                res = ocupacion.get(f_act)
                lim = limpiezas_previas.get(f_act)
                
                if res:
                    btn = ""
                    if res['inicio'] == f_act:
                        cl, txt = ("btn-on", "IN OK ✅") if res['in_ok'] else ("btn-off", "⚓ IN")
                        btn = '<button class="btn-act ' + cl + '" onclick="event.stopPropagation(); mark(\'' + res['id'] + '\',\'Check-in\',this)">' + txt + '</button>'
                    elif res['fin'] == f_act:
                        cl, txt = ("btn-on", "OUT OK ✅") if res['out_ok'] else ("btn-off", "🏁 OUT")
                        btn = '<button class="btn-act ' + cl + '" onclick="event.stopPropagation(); mark(\'' + res['id'] + '\',\'Check-out\',this)">' + txt + '</button>'
                    html_meses += '<div onclick=\'alert("' + res['nombre'] + '")\' class="day occupied"><span>' + str(dia) + '</span>' + btn + '</div>'
                elif lim:
                    cl, txt = ("btn-on", "LIMP OK ✅") if lim['limp_ok'] else ("btn-off", "🧹 LIMP")
                    btn_l = '<button class="btn-act ' + cl + '" onclick="mark(\'' + lim['id'] + '\',\'Limpieza\',this)">' + txt + '</button>'
                    html_meses += '<div class="day free"><span>' + str(dia) + '</span>' + btn_l + '</div>'
                else:
                    html_meses += '<div class="day free">' + str(dia) + '</div>'
            html_meses += "</div></div></div>"

        html_end = """</div></div><script>
        async function mark(id, prop, btn) {
            if (btn.classList.contains('btn-on')) return;
            const today = new Date().toISOString().split('T')[0];
            btn.innerText = "...";
            try {
                const r = await fetch('https://api.notion.com/v1/pages/' + id, {
                    method: 'PATCH',
                    headers: { 'Authorization': 'Bearer """ + str(TOKEN) + """', 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json' },
                    body: JSON.stringify({ properties: { [prop]: { date: { start: today } } } })
                });
                if (r.ok) {
                    btn.innerText = (prop === "Limpieza" ? "LIMP" : prop.toUpperCase()) + " OK ✅";
                    btn.className = "btn-act btn-on";
                } else { alert("Error Notion: " + r.status); }
            } catch(e) { alert("Error Red"); }
        }</script></body></html>"""

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_start + html_meses + html_end)
        print("✅ PROCESO FINALIZADO CON ÉXITO.")
    except Exception as e:
        print(f"ERROR DURANTE GENERACIÓN HTML: {e}")

if __name__ == "__main__":
    generar_dashboard()
