import requests
import json
import os
from datetime import datetime, timedelta
import calendar

# Configuración de Secrets
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
    if (m == 6 and d >= 16) or (m in [7, 8]) or (m == 9 and d <= 15): return "ALTA", "#ef4444"
    if m in [4, 5] or (m == 6 and d <= 15) or (m == 9 and d >= 16) or m == 10: return "MEDIA", "#f59e0b"
    return "BAJA", "#64748b"

def find_prop(props, possible_names):
    """Busca una propiedad en Notion sin importar mayúsculas/minúsculas"""
    for name in possible_names:
        if name in props: return name, props[name]
        if name.lower() in props: return name.lower(), props[name.lower()]
        if name.upper() in props: return name.upper(), props[name.upper()]
    return None, None

def generar_dashboard():
    print("🚢 Iniciando sistema inteligente de detección...")
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    if res.status_code != 200: exit(1)

    data = res.json().get("results", [])
    ocupacion = {}
    limpiezas = {}

    for r in data:
        p = r["properties"]
        
        # Detección dinámica de columnas
        name_key, name_prop = find_prop(p, ["Nombre", "Name", "NOMBRE"])
        date_key, date_prop = find_prop(p, ["Fecha", "Date", "FECHA"])
        com_key, com_prop = find_prop(p, ["COMENTARIOS", "Comentarios", "Comments"])

        f_val = date_prop.get("date", {}) if date_prop else {}
        if not f_val: continue
        
        try:
            start = datetime.strptime(f_val.get("start")[:10], "%Y-%m-%d").date()
            end = datetime.strptime((f_val.get("end") or f_val.get("start"))[:10], "%Y-%m-%d").date()
            
            texto_coment = ""
            if com_prop and com_prop.get("rich_text"):
                texto_coment = com_prop["rich_text"][0].get("plain_text", "")
            
            info = {
                "id": r["id"],
                "com_col": com_key or "COMENTARIOS",
                "nombre": name_prop["title"][0]["plain_text"] if name_prop and name_prop["title"] else "Reserva",
                "inicio": start, "fin": end,
                "limpieza": "#LIMP" in texto_coment,
                "checkin": "#IN" in texto_coment,
                "checkout": "#OUT" in texto_coment
            }
            
            curr = start
            while curr <= end:
                ocupacion[curr] = info
                curr += timedelta(days=1)
            limpiezas[start - timedelta(days=1)] = info
        except: continue

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>DIVONA MALLORCA | Deck</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            body {{ background-color: #0f172a; font-family: 'Inter', sans-serif; color: #f1f5f9; }}
            .month-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 1.5rem; }}
            .grid-cal {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }}
            .day {{ min-height: 80px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.7rem; border-radius: 8px; position: relative; }}
            .occupied {{ background: #1d4ed8; color: white; border-radius: 0; }}
            .start-res {{ border-top-left-radius: 12px; border-bottom-left-radius: 12px; border-left: 4px solid #60a5fa; }}
            .end-res {{ border-top-right-radius: 12px; border-bottom-right-radius: 12px; border-right: 4px solid #1e3a8a; }}
            .free {{ background: rgba(255,255,255,0.02); color: #475569; }}
            .btn-act {{ font-size: 0.55rem; padding: 4px 2px; border-radius: 4px; margin-top: 4px; font-weight: 800; cursor: pointer; width: 95%; text-align: center; border: none; transition: 0.3s; }}
            .btn-off {{ background: #f59e0b; color: #451a03; }}
            .btn-on {{ background: #22c55e; color: white; }}
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div class="max-w-7xl mx-auto">
            <header class="flex items-center gap-6 mb-12 border-b border-slate-800 pb-8">
                <img src="https://i.ibb.co/680LhN0/Sailboat-Charter-Mallorca.png" class="w-16 h-16 rounded-full shadow-lg">
                <h1 style="font-family: serif;" class="text-2xl font-black uppercase tracking-tighter">Sailboat Charter Mallorca</h1>
            </header>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
    """

    for mes in range(3, 12):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia = calendar.monthrange(2026, mes)[0]
        _, col_temp = get_day_season(datetime(2026, mes, 15))
        html += f"""<div class="month-card shadow-2xl overflow-hidden">
            <div class="p-4 flex justify-between items-center" style="background: {col_temp}15; border-bottom: 2px solid {col_temp}">
                <span class="font-black text-xs uppercase" style="color: {col_temp}">{MESES_NOMBRES[mes]}</span>
            </div>
            <div class="p-4"><div class="grid-cal">"""
        for _ in range(primer_dia): html += '<div></div>'
        for dia in range(1, ultimo + 1):
            f_act = datetime(2026, mes, dia).date()
            res = ocupacion.get(f_act)
            limp = limpiezas.get(f_act)
            css, content = "day free ", f'<span class="font-bold">{dia}</span>'
            if res:
                css = "day occupied "
                if res['inicio'] == f_act:
                    css += "start-res "
                    s, l = ("btn-on", "IN ✅") if res['checkin'] else ("btn-off", "⚓ IN")
                    content += f'<button class="btn-act {s}" onclick="toggleTag(\'{res["id"]}\',\'#IN\',{str(res["checkin"]).lower()},this,\'⚓ IN\',\'IN ✅\',\'{res["com_col"]}\')">{l}</button>'
                elif res['fin'] == f_act:
                    css += "end-res "
                    s, l = ("btn-on", "OUT ✅") if res['checkout'] else ("btn-off", "🏁 OUT")
                    content += f'<button class="btn-act {s}" onclick="toggleTag(\'{res["id"]}\',\'#OUT\',{str(res["checkout"]).lower()},this,\'🏁 OUT\',\'OUT ✅\',\'{res["com_col"]}\')">{l}</button>'
            elif limp:
                s, l = ("btn-on", "LIMP ✅") if limp['limpieza'] else ("btn-off", "🧹 LIMP")
                content += f'<button class="btn-act {s}" onclick="toggleTag(\'{limp["id"]}\',\'#LIMP\',{str(limp["limpieza"]).lower()},this,\'🧹 LIMP\',\'LIMP ✅\',\'{limp["com_col"]}\')">{l}</button>'
            html += f'<div class="{css}">{content}</div>'
        html += "</div></div></div>"

    html += f"""
            </div>
        </div>
        <script>
            async function toggleTag(id, tag, state, btn, lOff, lOn, colName) {{
                const nState = !state;
                btn.innerText = "...";
                btn.disabled = true;
                try {{
                    const r = await fetch(`https://api.notion.com/v1/pages/${{id}}`, {{
                        headers: {{ 'Authorization': 'Bearer {TOKEN}', 'Notion-Version': '2022-06-28' }}
                    }});
                    const d = await r.json();
                    let txt = "";
                    try {{ txt = d.properties[colName].rich_text[0].plain_text; }} catch(e) {{ txt = ""; }}
                    let nTxt = txt.replace(tag, "").trim();
                    if (nState) nTxt += " " + tag;
                    await fetch(`https://api.notion.com/v1/pages/${{id}}`, {{
                        method: 'PATCH',
                        headers: {{ 'Authorization': 'Bearer {TOKEN}', 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ properties: {{ [colName]: {{ rich_text: [{{ text: {{ content: nTxt }} }}] }} }} }})
                    }});
                    btn.innerText = nState ? lOn : lOff;
                    btn.className = "btn-act " + (nState ? "btn-on" : "btn-off");
                    btn.setAttribute("onclick", `toggleTag('${{id}}','${{tag}}',${{nState}},this,'${{lOff}}','${{lOn}}','${{colName}}')`);
                } catch(e) {{ alert("Error"); btn.innerText = lOff; }}
                btn.disabled = false;
            }}
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__": generar_dashboard()
