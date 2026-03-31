import requests
import json
import os
from datetime import datetime, timedelta
import calendar

# Configuración de GitHub (Secrets)
TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

MESES_NOMBRES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def get_safe_text(prop):
    if not prop: return ""
    try:
        t = prop.get("type")
        if t == "title": return prop["title"][0]["plain_text"] if prop["title"] else "Reserva"
        if t == "rich_text": return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else ""
        return ""
    except: return ""

def generar_dashboard():
    # 1. Traer datos de Notion
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    if res.status_code != 200:
        print(f"Error de conexión: {res.status_code}"); return

    ocupacion = {}
    limpiezas_previas = {}

    for r in res.json().get("results", []):
        try:
            p = r["properties"]
            f_data = p.get("Fecha", {}).get("date", {})
            if not f_data or not f_data.get("start"): continue
            
            start = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d").date()
            end = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d").date()
            
            info = {
                "id": r["id"],
                "nombre": get_safe_text(p.get("Nombre")),
                "inicio": start,
                "fin": end,
                # Verificamos si las columnas de fecha tienen algo escrito
                "limpieza_ok": p.get("Limpieza", {}).get("date") is not None,
                "checkin_ok": p.get("Check-in", {}).get("date") is not None,
                "checkout_ok": p.get("Check-out", {}).get("date") is not None
            }
            
            curr = start
            while curr <= end:
                ocupacion[curr] = info
                curr += timedelta(days=1)
            limpiezas_previas[start - timedelta(days=1)] = info
        except Exception as e:
            print(f"Error procesando una reserva: {e}")
            continue

    # 2. Generar el HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DIVONA MALLORCA | Deck Control</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=Cinzel:wght@700&display=swap" rel="stylesheet">
        <style>
            body {{ background-color: #0f172a; font-family: 'Inter', sans-serif; color: #f1f5f9; }}
            h1 {{ font-family: 'Cinzel', serif; letter-spacing: 2px; }}
            .month-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 1.5rem; overflow: hidden; height: 100%; }}
            .grid-cal {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }}
            .day {{ min-height: 85px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.7rem; border-radius: 8px; }}
            .occupied {{ background: #1d4ed8; color: white; font-weight: 900; }}
            .free {{ background: rgba(255,255,255,0.03); color: #475569; }}
            .btn-nav {{ font-size: 0.5rem; padding: 4px 2px; border-radius: 4px; margin-top: 4px; width: 95%; font-weight: 800; cursor: pointer; border: none; text-transform: uppercase; transition: 0.3s; }}
            .btn-off {{ background: #f59e0b; color: #451a03; }}
            .btn-on {{ background: #22c55e; color: white; cursor: default; }}
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div class="max-w-7xl mx-auto">
            <header class="flex items-center gap-6 mb-12 pb-8 border-b border-slate-800">
                <img src="https://i.ibb.co/680LhN0/Sailboat-Charter-Mallorca.png" class="w-16 h-16 rounded-full shadow-2xl">
                <div>
                    <h1 class="text-2xl font-black">SAILBOAT CHARTER <span class="text-blue-500">MALLORCA</span></h1>
                    <p class="text-[10px] uppercase tracking-widest text-slate-500 font-bold">Fleet Command Center</p>
                </div>
            </header>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
    """

    for mes in range(3, 12):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia = calendar.monthrange(2026, mes)[0]
        html += f"""
        <div class="month-card shadow-2xl">
            <div class="p-4 border-b border-slate-700 bg-slate-800/50 flex justify-between">
                <span class="font-black text-xs text-blue-400">{MESES_NOMBRES[mes].upper()}</span>
            </div>
            <div class="p-4"><div class="grid-cal">"""
        
        for _ in range(primer_dia): html += '<div></div>'
        for dia in range(1, ultimo + 1):
            f_act = datetime(2026, mes, dia).date()
            res, lim = ocupacion.get(f_act), limpiezas_previas.get(f_act)
            cl, cont = "day free ", f"<b>{dia}</b>"
            
            if res:
                cl = "day occupied "
                if res['inicio'] == f_act:
                    s, l = ("btn-on", "IN OK ✅") if res['checkin_ok'] else ("btn-off", "⚓ CHECK-IN")
                    onclick = "" if res['checkin_ok'] else f'onclick="toggleDate(\'{res["id"]}\', \'Check-in\', this, \'IN OK ✅\')"'
                    cont += f'<button class="btn-nav {s}" {onclick}>{l}</button>'
                elif res['fin'] == f_act:
                    s, l = ("btn-on", "OUT OK ✅") if res['checkout_ok'] else ("btn-off", "🏁 CHECK-OUT")
                    onclick = "" if res['checkout_ok'] else f'onclick="toggleDate(\'{res["id"]}\', \'Check-out\', this, \'OUT OK ✅\')"'
                    cont += f'<button class="btn-nav {s}" {onclick}>{l}</button>'
            elif lim:
                s, l = ("btn-on", "LIMP OK ✅") if lim['limpieza_ok'] else ("btn-off", "🧹 LIMPIEZA")
                onclick = "" if lim['limpieza_ok'] else f'onclick="toggleDate(\'{lim["id"]}\', \'Limpieza\', this, \'LIMP OK ✅\')"'
                cont += f'<button class="btn-nav {s}" {onclick}>{l}</button>'

            html += f'<div class="{cl}">{cont}</div>'
        html += "</div></div></div>"

    html += f"""
            </div>
        </div>
        <script>
            async function toggleDate(id, prop, btn, labelOn) {{
                const today = new Date().toISOString().split('T')[0];
                const originalText = btn.innerText;
                btn.innerText = "...";
                btn.disabled = true;

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
                        btn.innerText = labelOn;
                        btn.className = "btn-nav btn-on";
                        btn.onclick = null;
                    }} else {{
                        alert("Error de Notion");
                        btn.innerText = originalText;
                    }}
                }} catch(e) {{ 
                    alert("Error de conexión"); 
                    btn.innerText = originalText;
                }}
                btn.disabled = false;
            }}
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)
    print("✅ Web generada con éxito.")

if __name__ == "__main__": generar_dashboard()
