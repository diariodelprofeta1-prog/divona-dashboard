import requests
import json
import os
from datetime import datetime, timedelta
import calendar

# 1. CONFIGURACIÓN
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
    print("🚢 Conectando con Notion...")
    url = "https://api.notion.com/v1/databases/" + str(DATABASE_ID) + "/query"
    res = requests.post(url, headers=headers)
    
    if res.status_code != 200:
        print("❌ Error de Notion: " + res.text)
        exit(1)

    ocupacion = {}
    limpiezas_previas = {}

    results = res.json().get("results", [])
    for r in results:
        p = r["properties"]
        f_data = p.get("Fecha", {}).get("date", {})
        if not f_data or not f_data.get("start"): continue
        
        try:
            start_str = f_data.get("start")[:10]
            end_str = (f_data.get("end") or f_data.get("start"))[:10]
            start_dt = datetime.strptime(start_str, "%Y-%m-%d")
            end_dt = datetime.strptime(end_str, "%Y-%m-%d")
            
            info = {
                "id": r["id"],
                "nombre": get_safe_text(p.get("Nombre")).replace('"', ''),
                "estado": get_safe_text(p.get("Estado")),
                "in_ok": p.get("Check-in", {}).get("date") is not None,
                "out_ok": p.get("Check-out", {}).get("date") is not None,
                "limp_ok": p.get("Limpieza", {}).get("date") is not None,
                "inicio": start_dt.date(),
                "fin": end_dt.date()
            }
            
            curr = start_dt
            while curr <= end_dt:
                ocupacion[curr.date()] = info
                curr += timedelta(days=1)
            
            limpiezas_previas[(start_dt - timedelta(days=1)).date()] = info
        except Exception as e:
            print("⚠️ Error procesando reserva: " + str(e))

    # 2. CONSTRUCCIÓN DEL HTML (Sin f-strings para evitar errores de llaves {})
    html_start = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>SAILBOAT CHARTER MALLORCA</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=Cinzel:wght@700&display=swap" rel="stylesheet">
        <style>
            body { background-color: #0f172a; font-family: 'Inter', sans-serif; color: #f1f5f9; }
            h1 { font-family: 'Cinzel', serif; letter-spacing: 2px; }
            .month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1.5rem; overflow: hidden; }
            .grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
            .day { aspect-ratio: 1/1; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.7rem; border-radius: 6px; position: relative; }
            .occupied { background: #3b82f6; color: white; font-weight: 900; cursor: pointer; }
            .free { background: rgba(255,255,255,0.03); color: #475569; }
            .btn-act { font-size: 0.4rem; padding: 2px 0; border-radius: 3px; margin-top: 2px; width: 90%; font-weight: 900; border: none; text-transform: uppercase; cursor: pointer; }
            .btn-off { background: #f59e0b; color: #451a03; }
            .btn-on { background: #22c55e; color: white; cursor: default; }
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div class="max-w-7xl mx-auto">
            <h1 class="text-3xl font-black text-white mb-12 pb-8 border-b border-slate-800 uppercase">Sailboat Charter Mallorca</h1>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
    """

    html_meses = ""
    for mes in range(3, 12):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia = calendar.monthrange(2026, mes)[0]
        f_mid = datetime(2026, mes, 15)
        _, t_color = get_day_season(f_mid)
        
        html_meses += '<div class="month-card shadow-2xl">'
        html_meses += '<div class="p-4 border-b border-slate-700 bg-slate-800/50">'
        html_meses += '<span class="font-black text-xs uppercase" style="color: ' + t_color + '">' + MESES_NOMBRES[mes] + '</span></div>'
        html_meses += '<div class="p-4"><div class="grid-cal">'
        
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

    html_end = """
            </div>
        </div>
        <script>
            async function mark(id, prop, btn) {
                if (btn.classList.contains('btn-on')) return;
                const today = new Date().toISOString().split('T')[0];
                btn.innerText = "...";
                try {
                    const r = await fetch('https://api.notion.com/v1/pages/' + id, {
                        method: 'PATCH',
                        headers: { 
                            'Authorization': 'Bearer NOTION_TOKEN', 
                            'Notion-Version': '2022-06-28', 
                            'Content-Type': 'application/json' 
                        },
                        body: JSON.stringify({ properties: { [prop]: { date: { start: today } } } })
                    });
                    if (r.ok) {
                        btn.innerText = (prop === "Limpieza" ? "LIMP" : prop.toUpperCase()) + " OK ✅";
                        btn.className = "btn-act btn-on";
                    }
                } catch(e) { alert("Error de red"); }
            }
        </script>
    </body>
    </html>
    """

    # Inyectamos el TOKEN de forma segura al final
    final_html = html_start + html_meses + html_end.replace("NOTION_TOKEN", str(TOKEN))
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    print("✅ Web generada correctamente.")

if __name__ == "__main__":
    generar_dashboard()
