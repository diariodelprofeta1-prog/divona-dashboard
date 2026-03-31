import requests
import json
import os
from datetime import datetime, timedelta
import calendar
import urllib.parse

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
    if not prop: return "Sin Nombre"
    try:
        t = prop.get("type")
        if t == "title": return prop["title"][0]["plain_text"] if prop["title"] else "Reserva"
        if t == "rich_text": return prop["rich_text"][0]["plain_text"] if prop["rich_text"] else "Reserva"
        if t in ["select", "status"]: return prop[t]["name"] if prop[t] else ""
        if t == "people": return prop["people"][0]["name"] if prop["people"] else "Sin Nombre"
        return "Reserva"
    except: return "Reserva"

def get_safe_num(prop):
    if not prop: return 0
    try:
        t = prop.get("type")
        if t == "number": return prop.get("number", 0) or 0
        if t == "formula": return prop.get("formula", {}).get("number", 0) or 0
        return 0
    except: return 0

def get_safe_email(prop):
    if not prop: return ""
    try:
        if prop.get("type") == "email": return prop.get("email") or ""
        return ""
    except: return ""

def generar_dashboard():
    try:
        res = requests.post("https://api.notion.com/v1/databases/" + str(DATABASE_ID) + "/query", headers=headers)
        data = res.json()
    except: return

    agenda = {}
    ingresos_mes = {m: 0 for m in range(1, 13)}
    COLORES = ["#3b82f6", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b", "#06b6d4", "#f43f5e", "#6366f1", "#14b8a6", "#f97316"]

    for r in data.get("results", []):
        p = r["properties"]
        f_data = p.get("Fecha", {}).get("date", {})
        if not f_data: continue
        
        start = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d").date()
        end = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d").date()
        
        monto = get_safe_num(p.get("Total cliente"))
        estado = get_safe_text(p.get("Estado"))
        if estado != "CANCELADA": ingresos_mes[start.month] += monto

        res_id = r["id"].replace("-", "") # ID limpio
        color_idx = sum(ord(c) for c in res_id) % len(COLORES)
        
        nombre_real = get_safe_text(p.get("Cliente"))
        if nombre_real == "Reserva" or nombre_real == "Sin Nombre": 
            nombre_real = get_safe_text(p.get("Nombre"))
            
        correo = get_safe_email(p.get("Correo electrónico 1"))
        comentarios = get_safe_text(p.get("COMENTARIOS"))
        
        info = {
            "nombre": nombre_real, 
            "color": COLORES[color_idx],
            "detalle": "Cliente: " + nombre_real + "\\nTotal: " + str(monto) + "€\\nEstado: " + estado + "\\nComentarios: " + comentarios
        }

        curr = start
        while curr <= end:
            if curr not in agenda: agenda[curr] = {"res": None, "acts": []}
            agenda[curr]["res"] = info
            if curr == start: agenda[curr]["acts"].append({"tipo": "IN", "id": res_id, "email": correo, "nombre": nombre_real})
            if curr == end: agenda[curr]["acts"].append({"tipo": "OUT", "id": res_id, "email": correo, "nombre": nombre_real})
            curr += timedelta(days=1)
        
        limp = start - timedelta(days=1)
        if limp not in agenda: agenda[limp] = {"res": None, "acts": []}
        agenda[limp]["acts"].append({"tipo": "LIMP"})

    # HTML
    html = '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>DIVONA 2026</title>'
    html += '<script src="https://cdn.tailwindcss.com"></script>'
    html += '<style>'
    html += 'body { background-color: #0f172a; font-family: sans-serif; color: #f1f5f9; } '
    html += '.month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1rem; overflow: hidden; height: 100%; display: flex; flex-direction: column; } '
    html += '.grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); grid-template-rows: repeat(6, 1fr); gap: 0px; flex-grow: 1; min-height: 250px; } '
    html += '.day { min-height: 45px; display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: 4px 0; font-size: 0.65rem; border: 1px solid rgba(255,255,255,0.03); } '
    html += '.occupied { border-width: 2px !important; cursor: pointer; } '
    html += '.dimmed { opacity: 0.1; filter: grayscale(1); } '
    html += '.highlight { border: 2px solid white !important; background: rgba(255,255,255,0.05); } '
    html += '</style></head><body>'
    
    total_anual = sum(ingresos_mes.values())
    html += '<div class="p-8 max-w-7xl mx-auto">'
    html += '<div class="flex flex-col md:flex-row justify-between items-end mb-12 gap-6">'
    html += '<div><h1 class="text-4xl font-black tracking-tighter uppercase">Divona Center</h1>'
    html += '<p class="text-blue-400 font-bold text-xl mt-2">TOTAL 2026: ' + str(f"{total_anual:,.0f}") + ' €</p></div>'
    html += '<div class="flex gap-2">'
    html += '<button onclick="filterView(\'all\', this)" class="bg-blue-600 px-4 py-2 rounded-lg text-xs font-bold uppercase">General</button>'
    html += '<button onclick="filterView(\'LIMP\', this)" class="bg-slate-700 px-4 py-2 rounded-lg text-xs font-bold uppercase">Limpiezas</button>'
    html += '<button onclick="filterView(\'OPS\', this)" class="bg-slate-700 px-4 py-2 rounded-lg text-xs font-bold uppercase">Entradas/Salidas</button>'
    html += '</div></div>'
    
    html += '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">'

    for mes in range(3, 13):
        ultimo = calendar.monthrange(2026, mes)[1]
        primer_dia = calendar.monthrange(2026, mes)[0]
        _, t_color = get_day_season(datetime(2026, mes, 15))
        
        html += '<div><div class="month-card shadow-2xl">'
        html += '<div class="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/30">'
        html += '<span class="font-bold text-[10px] uppercase" style="color:'+t_color+'">'+MESES_NOMBRES[mes]+'</span>'
        html += '<span class="text-white font-black text-[10px] bg-slate-700 px-2 py-1 rounded">'+ str(f"{ingresos_mes[mes]:,.0f}") +' €</span></div>'
        html += '<div class="p-2 flex-grow flex flex-col"><div class="grid-cal">'
        for _ in range(primer_dia): html += '<div class="day border-none"></div>'
        
        for dia in range(1, ultimo + 1):
            f_act = datetime(2026, mes, dia).date()
            data = agenda.get(f_act, {"res": None, "acts": []})
            res = data["res"]
            acts = data["acts"]
            
            tag = "NONE"
            acts_html = ""
            
            for act in acts:
                if act["tipo"] == "LIMP":
                    tag = "LIMP" if tag == "NONE" else tag
                    acts_html += '<span>🧹</span>'
                elif act["tipo"] in ["IN", "OUT"]:
                    tag = "OPS"
                    icon = "⚓" if act["tipo"] == "IN" else "🏁"
                    
                    if act.get("email"):
                        btn_id = f'{act["tipo"]}-{act["id"]}'
                        
                        # Preparamos el correo desde Python para que sea un enlace nativo
                        if act["tipo"] == "IN":
                            asunto = "Bienvenido a Divona Center"
                            cuerpo = f"Hola {act['nombre']},\n\nQueremos darte una cálida bienvenida y agradecerte de corazón por confiar en nosotros para tu experiencia.\n\nEn un futuro muy cercano te enviaremos por aquí un enlace de YouTube con los vídeos de tu aventura.\n\n¡Que lo disfrutes muchísimo!\n\nEl equipo de Divona Center"
                        else:
                            asunto = "Gracias y hasta pronto - Divona Center"
                            cuerpo = f"Hola {act['nombre']},\n\nEsperamos que hayas disfrutado al máximo tu experiencia con nosotros y que vuelvas muy pronto.\n\nComo agradecimiento por ser un cliente recurrente, si contactas con nosotros a través de este correo para tu próxima reserva, ¡te haremos un regalo especial!\n\nGracias nuevamente por elegirnos.\n\nEl equipo de Divona Center"
                        
                        # urllib.parse.quote convierte los espacios y saltos de línea para que el correo los entienda
                        href = f"mailto:{act['email']}?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
                        
                        # Ahora es una etiqueta <a> real, el navegador nunca la bloquea
                        acts_html += f'<a href="{href}" id="{btn_id}" class="email-btn cursor-pointer hover:scale-150 transition-transform text-lg inline-block" onclick="toggleCorreo(event, \'{act["tipo"]}\', \'{act["id"]}\')">{icon}</a>'
                    else:
                        acts_html += f'<span>{icon}</span>'
            
            css = "day day-cell"
            style = ""
            if res:
                css += " occupied"
                style = "background-color:" + res['color'] + "15; border-color:" + res['color'] + ";"
            
            click = 'onclick="alert(\''+ (res['detalle'] if res else 'Día Libre') +'\')"'
            
            html += '<div class="' + css + '" data-tag="' + tag + '" style="' + style + '" ' + click + '>'
            html += '<span class="font-bold">' + str(dia) + '</span>'
            html += '<div class="flex gap-1 items-center">' + acts_html + '</div></div>'
            
        html += '</div></div></div></div>'

    html += '</div></div>'
    
    # --- SCRIPTS ---
    html += '<script>'
    html += 'function filterView(type, btn) { '
    html += '  document.querySelectorAll("button").forEach(b => b.classList.replace("bg-blue-600", "bg-slate-700")); '
    html += '  btn.classList.replace("bg-slate-700", "bg-blue-600"); '
    html += '  document.querySelectorAll(".day-cell").forEach(day => { '
    html += '    const tag = day.getAttribute("data-tag"); day.classList.remove("dimmed", "highlight"); '
    html += '    if (type === "all") return; '
    html += '    if (type === "OPS" && tag === "OPS") day.classList.add("highlight"); '
    html += '    else if (tag === type) day.classList.add("highlight"); '
    html += '    else day.classList.add("dimmed"); '
    html += '  }); '
    html += '} '
    
    # Función toggleCorreo ajustada para enlaces nativos
    html += 'function toggleCorreo(event, tipo, id) { '
    html += '  event.stopPropagation(); ' # Evita que salte el alert del día
    html += '  const key = "divona_" + tipo + "_" + id; '
    html += '  const btn = document.getElementById(tipo + "-" + id); '
    
    html += '  if(localStorage.getItem(key)) { '
    html += '    localStorage.removeItem(key); ' # Desmarcamos
    html += '    btn.classList.remove("opacity-20", "grayscale"); '
    html += '    event.preventDefault(); ' # IMPORTANTÍSIMO: Detiene el envío del correo porque solo queríamos desmarcarlo
    html += '  } else { '
    html += '    localStorage.setItem(key, "true"); ' # Marcamos
    html += '    btn.classList.add("opacity-20", "grayscale"); '
    html += '    // Al no poner preventDefault, el navegador abre el mailto: automáticamente de forma nativa'
    html += '  } '
    html += '} '
    
    html += 'document.addEventListener("DOMContentLoaded", function() { '
    html += '  document.querySelectorAll(".email-btn").forEach(btn => { '
    html += '    const key = "divona_" + btn.id.replace("-", "_"); '
    html += '    if(localStorage.getItem(key)) { btn.classList.add("opacity-20", "grayscale"); } '
    html += '  }); '
    html += '}); '
    
    html += '</script></body></html>'

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    generar_dashboard()
