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
    # Evita que el texto de Notion rompa el código interno de la web
    return str(text).replace("'", "´").replace('"', '´').replace('\n', ' - ').replace('\r', '')

def generar_dashboard():
    try:
        res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
        data = res.json()

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

            res_id = r["id"].replace("-", "") 
            color_idx = sum(ord(c) for c in res_id) % len(COLORES)
            
            nombre_real = get_safe_text(p.get("Cliente"))
            if nombre_real == "Reserva" or nombre_real == "Sin Nombre": 
                nombre_real = get_safe_text(p.get("Nombre"))
                
            correo = get_safe_email(p.get("Correo electrónico 1"))
            comentarios = get_safe_text(p.get("COMENTARIOS"))
            
            info = {
                "id": res_id,
                "nombre": nombre_real, 
                "color": COLORES[color_idx],
                "detalle": f"Cliente: {js_safe(nombre_real)}\\nTotal: {monto}€\\nEstado: {js_safe(estado)}\\nComentarios: {js_safe(comentarios)}"
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
            agenda[limp]["acts"].append({"tipo": "LIMP", "id": res_id})

        # INICIO DEL HTML
        html = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>DIVONA 2026</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
        body { background-color: #0f172a; font-family: sans-serif; color: #f1f5f9; } 
        .month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1rem; overflow: hidden; height: 100%; display: flex; flex-direction: column; } 
        .grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); grid-template-rows: repeat(6, 1fr); gap: 0px; flex-grow: 1; min-height: 250px; } 
        .day { min-height: 45px; display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: 4px 0; font-size: 0.65rem; border: 1px solid rgba(255,255,255,0.03); transition: all 0.3s ease; } 
        .occupied { border-width: 2px !important; cursor: pointer; } 
        .dimmed { opacity: 0.15; filter: grayscale(1); } 
        .highlight { border: 2px solid white !important; background: rgba(255,255,255,0.1); transform: scale(1.02); z-index: 10; } 
        </style></head><body>
        """
        
        total_anual = sum(ingresos_mes.values())
        html += '<div class="p-8 max-w-7xl mx-auto">'
        html += '<div class="flex flex-col md:flex-row justify-between items-end mb-12 gap-6">'
        html += '<div><h1 class="text-4xl font-black tracking-tighter uppercase">Divona Center</h1>'
        html += f'<p class="text-blue-400 font-bold text-xl mt-2">TOTAL 2026: {total_anual:,.0f} €</p></div>'
        
        html += '<div class="flex flex-wrap gap-2">'
        html += '<button onclick="filterView(\'all\', this)" class="filter-btn bg-blue-600 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">General</button>'
        html += '<button onclick="filterView(\'LIMP\', this)" class="filter-btn bg-slate-700 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">Limpiezas 🧹</button>'
        html += '<button onclick="filterView(\'IN\', this)" class="filter-btn bg-slate-700 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">Check-in ⚓</button>'
        html += '<button onclick="filterView(\'OUT\', this)" class="filter-btn bg-slate-700 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">Check-out 🏁</button>'
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
            for _ in range(primer_dia): html += '<div class="day border-none"></div>'
            
            for dia in range(1, ultimo + 1):
                f_act = datetime(2026, mes, dia).date()
                data_day = agenda.get(f_act, {"res": None, "acts": []})
                res = data_day["res"]
                acts = data_day["acts"]
                
                tiene_in = any(a["tipo"] == "IN" for a in acts)
                tiene_out = any(a["tipo"] == "OUT" for a in acts)
                tiene_limp = any(a["tipo"] == "LIMP" for a in acts)
                
                acts_html = ""
                for act in acts:
                    if act["tipo"] == "LIMP":
                        acts_html += '<span>🧹</span>'
                    elif act["tipo"] in ["IN", "OUT"]:
                        icon = "⚓" if act["tipo"] == "IN" else "🏁"
                        if act.get("email"):
                            if act["tipo"] == "IN":
                                asunto = "Bienvenido a Divona Center"
                                cuerpo = f"Hola {act['nombre']},\r\n\r\nQueremos darte una cálida bienvenida y agradecerte de corazón por confiar en nosotros para tu experiencia.\r\n\r\nEn un futuro muy cercano te enviaremos por aquí un enlace de YouTube con los vídeos de tu aventura.\r\n\r\n¡Que lo disfrutes muchísimo!\r\n\r\nEl equipo de Divona Center"
                            else:
                                asunto = "Gracias y hasta pronto - Divona Center"
                                cuerpo = f"Hola {act['nombre']},\r\n\r\nEsperamos que hayas disfrutado al máximo tu experiencia con nosotros y que vuelvas muy pronto.\r\n\r\nComo agradecimiento por ser un cliente recurrente, si contactas con nosotros a través de este correo para tu próxima reserva, ¡te haremos un regalo especial!\r\n\r\nGracias nuevamente por elegirnos.\r\n\r\nEl equipo de Divona Center"
                            
                            # Enlace Mailto clásico y seguro
                            href = f"mailto:{act['email']}?subject={urllib.parse.quote(asunto)}&body={urllib.parse.quote(cuerpo)}"
                            acts_html += f'<a href="{href}" id="{act["tipo"]}-{act["id"]}" class="email-btn cursor-pointer hover:scale-150 transition-transform text-lg inline-block" onclick="toggleCorreo(event, this)">{icon}</a>'
                        else:
                            acts_html += f'<span>{icon}</span>'
                
                css = "day day-cell"
                style = ""
                res_id_val = ""
                if res:
                    css += " occupied"
                    style = f"background-color:{res['color']}15; border-color:{res['color']};"
                    res_id_val = res["id"]
                
                # Guardamos los datos ocultos para que el filtro trabaje bien
                filtro_data = f'data-res-id="{res_id_val}" data-in="{"true" if tiene_in else "false"}" data-out="{"true" if tiene_out else "false"}" data-limp="{"true" if tiene_limp else "false"}"'
                
                html += f'<div class="{css}" {filtro_data} onclick="alert(\'{res["detalle"] if res else "Día Libre"}\')">'
                html += f'<span class="font-bold">{dia}</span>'
                html += f'<div class="flex gap-1 items-center">{acts_html}</div></div>'
                
            html += '</div></div></div></div>'

        html += '</div>'
        html += f'<div class="text-center text-xs text-slate-500 mt-8 pb-4">Última actualización: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</div>'
        html += '</div>'
        
        # JAVASCRIPT PROTEGIDO
        js_code = """
        <script>
        function filterView(type, btn) { 
          // 1. Cambiar colores del menú superior
          document.querySelectorAll(".filter-btn").forEach(b => { 
            b.classList.remove("bg-blue-600"); 
            b.classList.add("bg-slate-700"); 
          }); 
          btn.classList.remove("bg-slate-700"); 
          btn.classList.add("bg-blue-600"); 
          
          const allDays = document.querySelectorAll(".day-cell");
          
          if (type === "all") {
             allDays.forEach(day => day.classList.remove("dimmed", "highlight"));
             return;
          }
          
          // 2. Buscar qué IDs de reserva coinciden con el filtro
          let matchedResIds = new Set();
          allDays.forEach(day => {
              if (type === "LIMP" && day.getAttribute("data-limp") === "true") {
                  matchedResIds.add(day.getAttribute("data-res-id"));
              }
              if (type === "IN" && day.getAttribute("data-in") === "true") {
                  matchedResIds.add(day.getAttribute("data-res-id"));
              }
              if (type === "OUT" && day.getAttribute("data-out") === "true") {
                  matchedResIds.add(day.getAttribute("data-res-id"));
              }
          });
          
          // 3. Iluminar TODA LA RESERVA, no solo un día suelto
          allDays.forEach(day => { 
            day.classList.remove("dimmed", "highlight"); 
            const resId = day.getAttribute("data-res-id");
            
            // Si el día pertenece a una reserva que cumple el filtro, se ilumina.
            if (resId && matchedResIds.has(resId)) {
                day.classList.add("highlight");
            } else {
                day.classList.add("dimmed");
            }
          }); 
        } 
        
        function toggleCorreo(event, elemento) { 
          event.stopPropagation();  // Evita que salga el cartel negro de Notion
          const key = "divona_" + elemento.id; 
          
          if(localStorage.getItem(key)) { 
            // Si está gris, despíntalo y CANCELA la acción de enviar correo
            localStorage.removeItem(key); 
            elemento.classList.remove("opacity-20", "grayscale"); 
            event.preventDefault();  
          } else { 
            // Si está a color, píntalo de gris y DEJA que se abra el programa de correos
            localStorage.setItem(key, "true"); 
            elemento.classList.add("opacity-20", "grayscale"); 
          } 
        } 
        
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
