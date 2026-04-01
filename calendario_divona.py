import requests
import json
import os
from datetime import datetime, timedelta
import calendar
import urllib.parse
import traceback

# Configuración
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

def js_safe(text):
    if not text: return ""
    return str(text).replace("'", "´").replace('"', '´').replace('\n', ' - ').replace('\r', '')

def generar_dashboard():
    try:
        res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
        data = res.json()

        agenda = {}
        ingresos_mes = {m: 0 for m in range(1, 13)}
        COLORES = ["#3b82f6", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b", "#06b6d4", "#f43f5e", "#6366f1", "#14b8a6", "#f97316"]

        # 1. Procesamos todas las reservas de Notion
        for r in data.get("results", []):
            p = r["properties"]
            f_data = p.get("Fecha", {}).get("date", {})
            if not f_data: continue
            
            start = datetime.strptime(f_data.get("start")[:10], "%Y-%m-%d").date()
            end = datetime.strptime((f_data.get("end") or f_data.get("start"))[:10], "%Y-%m-%d").date()
            
            monto = get_safe_num(p.get("Total cliente"))
            estado = get_safe_text(p.get("Estado"))
            if estado != "CANCELADA": ingresos_mes[start.month] += monto

            res_id = r["id"].replace("-", "") 
            color_idx = sum(ord(c) for c in res_id) % len(COLORES)
            
            nombre_real = get_safe_text(p.get("Cliente"))
            if nombre_real == "Reserva" or nombre_real == "Sin Nombre": 
                nombre_real = get_safe_text(p.get("Nombre"))
                
            correo = get_safe_email(p.get("Correo electrónico 1"))
            comentarios = get_safe_text(p.get("COMENTARIOS"))
            
            info = {
                "nombre": nombre_real, 
                "color": COLORES[color_idx],
                "detalle": f"Cliente: {js_safe(nombre_real)}\\nTotal: {monto}€\\nEstado: {js_safe(estado)}\\nComentarios: {js_safe(comentarios)}"
            }

            # Rellenamos los días en la agenda
            curr = start
            while curr <= end:
                if curr not in agenda: agenda[curr] = {"res": None, "acts": []}
                agenda[curr]["res"] = info
                if curr == start: agenda[curr]["acts"].append({"tipo": "IN", "id": res_id, "email": correo, "nombre": nombre_real})
                if curr == end: agenda[curr]["acts"].append({"tipo": "OUT", "id": res_id, "email": correo, "nombre": nombre_real})
                curr += timedelta(days=1)
            
            # Día anterior es limpieza
            limp = start - timedelta(days=1)
            if limp not in agenda: agenda[limp] = {"res": None, "acts": []}
            agenda[limp]["acts"].append({"tipo": "LIMP", "id": res_id})

        # 2. Generamos el HTML
        html = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>DIVONA 2026</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
        body { background-color: #0f172a; font-family: sans-serif; color: #f1f5f9; } 
        .month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1rem; overflow: hidden; height: 100%; display: flex; flex-direction: column; } 
        .grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); grid-template-rows: repeat(6, 1fr); gap: 0px; flex-grow: 1; min-height: 250px; } 
        .day { min-height: 45px; display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: 4px 0; font-size: 0.65rem; border: 1px solid rgba(255,255,255,0.03); transition: all 0.2s ease; } 
        .occupied { border-width: 2px !important; cursor: pointer; } 
        .dimmed { opacity: 0.15; filter: grayscale(1); } 
        .highlight { border: 2px solid white !important; background: rgba(255,255,255,0.1); transform: scale(1.05); z-index: 10; } 
        </style></head><body>
        """
        
        total_anual = sum(ingresos_mes.values())
        html += '<div class="p-8 max-w-7xl mx-auto">'
        html += '<div class="flex flex-col md:flex-row justify-between items-end mb-12 gap-6">'
        html += '<div><h1 class="text-4xl font-black tracking-tighter uppercase">Divona Center</h1>'
        html += f'<p class="text-blue-400 font-bold text-xl mt-2">TOTAL 2026: {total_anual:,.0f} €</p></div>'
        
        # Filtros simplificados
        html += '<div class="flex flex-wrap gap-2">'
        html += '<button onclick="filterView(\'all\', this)" class="filter-btn bg-blue-600 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">General</button>'
        html += '<button onclick="filterView(\'LIMP\', this)" class="filter-btn bg-slate-700 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">Limpiezas</button>'
        html += '<button onclick="filterView(\'IN\', this)" class="filter-btn bg-slate-700 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">Check-in</button>'
        html += '<button onclick="filterView(\'OUT\', this)" class="filter-btn bg-slate-700 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">Check-out</button>'
        html += '</div></div>'
        
        html += '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">'

        for mes in range(3, 13):
            ultimo = calendar.monthrange(2026, mes)[1]
            primer_dia = calendar.monthrange(2026, mes)[0]
            _, t_color = get_day_season(datetime(2026, mes, 15))
            
            html += f'<div><div class="month-card shadow-2xl">'
            html += f'<div class="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/30">'
            html += f'<span class="font-bold text-[10px] uppercase" style="color:{t_color}">{MESES_NOMBRES[mes]}</span>'
            html += f'<span class="text-white font-black text-[10px] bg-slate-700 px-2 py-1 rounded">{ingresos_mes[mes]:,.0f} €</span></div>'
            html += '<div class="p-2 flex-grow flex flex-col"><div class="grid-cal">'
            
            for _ in range(primer_dia): 
                html += '<div class="day border-none"></div>'
            
            for dia in range(1, ultimo + 1):
                f_act = datetime(2026, mes, dia).date()
                data_day = agenda.get(f_act, {"res": None, "acts": []})
                res = data_day["res"]
                acts = data_day["acts"]
                
                # Preparamos las etiquetas (tags) ocultas para que el filtro sepa qué hay aquí
                tags_list = []
                acts_html = ""
                
                for act in acts:
                    if act["tipo"] == "LIMP":
                        tags_list.append("LIMP")
                        acts_html += '<span>🧹</span>'
                    elif act["tipo"] in ["IN", "OUT"]:
                        tags_list.append(act["tipo"])
                        icon = "⚓" if act["tipo"] == "IN" else "🏁"
                        
                        if act.get("email"):
                            if act["tipo"] == "IN":
                                asunto = "Bienvenido a Divona Center"
                                cuerpo = f"Hola {act['nombre']},\n\nQueremos darte una cálida bienvenida y agradecerte de corazón por confiar en nosotros.\n\nEl equipo de Divona Center"
                            else:
                                asunto = "Gracias y hasta pronto - Divona Center"
                                cuerpo = f"Hola {act['nombre']},\n\nEsperamos que hayas disfrutado tu experiencia. Si nos contactas por este correo para tu próxima reserva, tendrás un regalo especial.\n\nEl equipo de Divona Center"
                            
                            # Enlace nativo (100% seguro)
                            href = f"mailto:{act['email']}?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
                            acts_html += f'<a href="{href}" id="{act["tipo"]}-{act["id"]}" class="email-btn cursor-pointer hover:scale-150 transition-transform text-lg inline-block" onclick="toggleCorreo(event, this)">{icon}</a>'
                        else:
                            acts_html += f'<span>{icon}</span>'
                
                css = "day day-cell"
                style = ""
                
                if res:
                    css += " occupied"
                    style = f"background-color:{res['color']}15; border-color:{res['color']};"
                
                # Convertimos las etiquetas en texto (ejemplo: "IN LIMP")
                etiquetas = " ".join(tags_list)
                texto_alerta = res["detalle"] if res else ("Limpieza" if "LIMP" in tags_list else "Día Libre")
                
                html += f'<div class="{css}" data-tags="{etiquetas}" style="{style}" onclick="alert(\'{texto_alerta}\')">'
                html += f'<span class="font-bold">{dia}</span>'
                html += f'<div class="flex gap-1 items-center">{acts_html}</div></div>'
                
            html += '</div></div></div></div>'

        html += '</div>'
        html += f'<div class="text-center text-xs text-slate-500 mt-8 pb-4">Última actualización: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</div>'
        html += '</div>'
        
        # 3. Lógica JavaScript súper limpia y estable
        js_code = """
        <script>
        function filterView(type, btn) { 
          // Pintar botones
          document.querySelectorAll(".filter-btn").forEach(b => { 
            b.classList.remove("bg-blue-600"); 
            b.classList.add("bg-slate-700"); 
          }); 
          btn.classList.remove("bg-slate-700"); 
          btn.classList.add("bg-blue-600"); 
          
          // Filtrar días
          document.querySelectorAll(".day-cell").forEach(day => { 
            day.classList.remove("dimmed", "highlight"); 
            
            if (type === "all") return; // Si es 'General', acabamos aquí (todo visible)
            
            // Si tiene la etiqueta del filtro, lo resaltamos. Si no, lo apagamos.
            const etiquetas = day.getAttribute("data-tags") || "";
            if (etiquetas.includes(type)) {
                day.classList.add("highlight");
            } else {
                day.classList.add("dimmed");
            }
          }); 
        } 
        
        function toggleCorreo(event, elemento) { 
          event.stopPropagation(); // Evita que salga el cartel
          const key = "divona_" + elemento.id; 
          
          if (elemento.classList.contains("grayscale")) {
            // Ya estaba gris: lo ponemos a color y CANCELAMOS el correo
            localStorage.removeItem(key); 
            elemento.classList.remove("opacity-20", "grayscale"); 
            event.preventDefault(); 
          } else {
            // Estaba a color: lo ponemos gris y DEJAMOS que el correo se abra
            localStorage.setItem(key, "true"); 
            elemento.classList.add("opacity-20", "grayscale"); 
          }
        } 
        
        // Al cargar la página, comprobar qué correos ya se enviaron
        document.addEventListener("DOMContentLoaded", function() { 
          document.querySelectorAll(".email-btn").forEach(btn => { 
            if(localStorage.getItem("divona_" + btn.id)) { 
              btn.classList.add("opacity-20", "grayscale"); 
            } 
          }); 
        }); 
        </script>
        """
        html += js_code + "</body></html>"

        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html)

    except Exception as e:
        error_html = f"<!DOCTYPE html><html lang='es'><body><h1 style='color:red;'>Error Crítico:</h1><pre>{traceback.format_exc()}</pre></body></html>"
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(error_html)

if __name__ == "__main__":
    generar_dashboard()
