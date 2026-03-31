import requests
import json
import os
from datetime import datetime, timedelta
import calendar

# Configuración de GitHub
TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def get_day_season(date_obj):
    m, d = date_obj.month, date_obj.day
    if (m == 6 and d >= 16) or (m in [7, 8]) or (m == 9 and d <= 15): return "ALTA", "#ef4444"
    if m in [4, 5] or (m == 6 and d <= 15) or (m == 9 and d >= 16) or m == 10: return "MEDIA", "#f59e0b"
    return "BAJA", "#64748b"

def generar_dashboard():
    res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
    data = res.json().get("results", [])
    
    ocupacion = {}
    limpiezas = {}

    for r in data:
        p = r["properties"]
        f_data = p.get("Fecha", {}).get("date", {})
        if not f_data: continue
        
        start = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d").date()
        end = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d").date()
        
        # Leemos el texto de comentarios para buscar nuestras etiquetas "secretas"
        comentarios_raw = p.get("COMENTARIOS", {}).get("rich_text", [])
        texto_coment = comentarios_raw[0]["plain_text"] if comentarios_raw else ""
        
        info = {
            "id": r["id"],
            "nombre": p["Nombre"]["title"][0]["plain_text"] if p["Nombre"]["title"] else "Reserva",
            "inicio": start, "fin": end,
            "raw_coment": texto_coment,
            "limpieza": "#LIMP" in texto_coment,
            "checkin": "#IN" in texto_coment,
            "checkout": "#OUT" in texto_coment
        }
        
        curr = start
        while curr <= end:
            ocupacion[curr] = info
            curr += timedelta(days=1)
        limpiezas[start - timedelta(days=1)] = info

    html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>SAILBOAT CHARTER MALLORCA | Deck</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
        <style>
            body {{ background-color: #0f172a; font-family: 'Inter', sans-serif; color: #f1f5f9; }}
            .month-card {{ background: #1e293b; border: 1px solid #334155; border-radius: 1.5rem; }}
            .grid-cal {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }}
            .day {{ min-height: 75px; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 0.65rem; border-radius: 8px; position: relative; }}
            .occupied {{ background: #1d4ed8; color: white; border-radius: 0; }}
            .start-res {{ border-top-left-radius: 12px; border-bottom-left-radius: 12px; border-left: 4px solid #60a5fa; }}
            .end-res {{ border-top-right-radius: 12px; border-bottom-right-radius: 12px; border-right: 4px solid #1e3a8a; }}
            .free {{ background: rgba(255,255,255,0.02); color: #475569; }}
            .btn-action {{ font-size: 0.5rem; padding: 4px 2px; border-radius: 4px; margin-top: 4px; font-weight: 800; cursor: pointer; width: 95%; text-align: center; border: none; transition: 0.3s; }}
            .btn-off {{ background: #f59e0b; color: #451a03; }}
            .btn-on {{ background: #22c55e; color: white; }}
        </style>
    </head>
    <body class="p-4 md:p-8">
        <div class="max-w-7xl mx-auto">
            <header class="flex items-center gap-6 mb-12 border-b border-slate-800 pb-8">
                <img src="https://i.ibb.co/680LhN0/Sailboat-Charter-Mallorca.png" class="w-16 h-16 rounded-full">
                <h1 style="font-family: 'Cinzel', serif;" class="text-2xl font-black">SAILBOAT CHARTER MALLORCA</h1>
            </header>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
    """

    for mes in range(3, 12):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia_sem = calendar.monthrange(2026, mes)[0]
        _, col_temp = get_day_season(datetime(2026, mes, 15))

        html += f"""
        <div class="month-card shadow-2xl overflow-hidden">
            <div class="p-4 flex justify-between items-center" style="background: {col_temp}15; border-bottom: 2px solid {col_temp}">
                <span class="font-black text-xs uppercase" style="color: {col_temp}">{MESES_NOMBRES[mes]}</span>
            </div>
            <div class="p-4"><div class="grid-cal">
        """
        for _ in range(primer_dia_sem): html += '<div></div>'
        
        for dia in range(1, ultimo + 1):
            f_act = datetime(2026, mes, dia).date()
            res = ocupacion.get(f_act)
            limp = limpiezas.get(f_act)
            
            css = "day "
            content = f'<span class="font-black mb-1">{dia}</span>'
            
            if res:
                css += "occupied "
                if res['inicio'] == f_act:
                    css += "start-res "
                    s_cl = "btn-on" if res['checkin'] else "btn-off"
                    lbl = "CHECK-IN ✅" if res['checkin'] else "⚓ CHECK-IN"
                    content += f'<button class="btn-action {s_cl}" onclick="toggleTag(\'{res["id"]}\', \'#IN\', {str(res["checkin"]).lower()}, this, \'⚓ CHECK-IN\', \'CHECK-IN ✅\')">{lbl}</button>'
                elif res['fin'] == f_act:
                    css += "end-res "
                    s_cl = "btn-on" if res['checkout'] else "btn-off"
                    lbl = "OUT OK ✅" if res['checkout'] else "🏁 CHECK-OUT"
                    content += f'<button class="btn-action {s_cl}" onclick="toggleTag(\'{res["id"]}\', \'#OUT\', {str(res["checkout"]).lower()}, this, \'🏁 CHECK-OUT\', \'OUT OK ✅\')">{lbl}</button>'
            elif limp:
                css += "free "
                s_cl = "btn-on" if limp['limpieza'] else "btn-off"
                lbl = "LIMPIO ✅" if limp['limpieza'] else "🧹 LIMPIEZA"
                content += f'<button class="btn-action {s_cl}" onclick="toggleTag(\'{limp["id"]}\', \'#LIMP\', {str(limp["limpieza"]).lower()}, this, \'🧹 LIMPIEZA\', \'LIMPIO ✅\')">{lbl}</button>'
            else:
                css += "free "

            html += f'<div class="{css}">{content}</div>'
        html += "</div></div></div>"

    html += f"""
            </div>
        </div>

        <script>
            async function toggleTag(pageId, tag, isEnabled, btn, labelOff, labelOn) {{
                const newStatus = !isEnabled;
                btn.innerText = "⏳...";
                btn.disabled = true;

                try {{
                    // 1. Obtener comentarios actuales
                    const getRes = await fetch(`https://api.notion.com/v1/pages/${{pageId}}`, {{
                        headers: {{ 'Authorization': 'Bearer {TOKEN}', 'Notion-Version': '2022-06-28' }}
                    }});
                    const pageData = await getRes.json();
                    let currentText = "";
                    const richText = pageData.properties.COMENTARIOS.rich_text;
                    if (richText.length > 0) currentText = richText[0].plain_text;

                    // 2. Modificar el texto con la etiqueta
                    let newText = currentText.replace(tag, "").trim();
                    if (newStatus) newText += " " + tag;

                    // 3. Guardar en Notion
                    const patchRes = await fetch(`https://api.notion.com/v1/pages/${{pageId}}`, {{
                        method: 'PATCH',
                        headers: {{ 'Authorization': 'Bearer {TOKEN}', 'Notion-Version': '2022-06-28', 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ properties: {{ COMENTARIOS: {{ rich_text: [{{ text: {{ content: newText }} }}] }} }} }})
                    }});

                    if (patchRes.ok) {{
                        btn.innerText = newStatus ? labelOn : labelOff;
                        btn.className = newStatus ? "btn-action btn-on" : "btn-action btn-off";
                        btn.setAttribute("onclick", `toggleTag('${{pageId}}', '${{tag}}', ${{newStatus}}, this, '${{labelOff}}', '${{labelOn}}')`);
                    }}
                }} catch (e) {{ alert("Error de conexión"); }}
                btn.disabled = false;
            }}
        </script>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f: f.write(html)

if __name__ == "__main__": generar_dashboard()
