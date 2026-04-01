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
    if not prop: return "No asignado"
    try:
        t = prop.get("type")
        if t in ["title", "rich_text"]: return prop[t][0]["plain_text"] if prop[t] else "No asignado"
        if t in ["select", "status"]: return prop[t]["name"] if prop[t] else "No asignado"
        if t == "phone_number": return prop.get("phone_number") or ""
        if t == "people": return prop["people"][0]["name"] if prop["people"] else "No asignado"
        if t == "email": return prop.get("email") or ""
        return "No asignado"
    except: return "No asignado"

def get_safe_num(prop):
    if not prop: return 0
    try:
        t = prop.get("type")
        if t == "number": return prop.get("number", 0) or 0
        if t == "formula": return prop.get("formula", {}).get("number", 0) or 0
        return 0
    except: return 0

def get_safe_multi(prop):
    if not prop: return ""
    try:
        if prop.get("type") == "multi_select": return ", ".join([x["name"] for x in prop["multi_select"]])
        return ""
    except: return ""

def get_safe_bool(prop):
    if not prop: return "NO"
    try: return "SÍ" if prop.get("checkbox") else "NO"
    except: return "NO"

def get_safe_date(prop):
    if not prop or not prop.get("date"): return None
    try: return datetime.strptime(prop["date"]["start"][:10], "%Y-%m-%d").date()
    except: return None

def get_safe_time(iso_str):
    if not iso_str or 'T' not in iso_str: return "--:--"
    try: return iso_str.split('T')[1][:5]
    except: return "--:--"

def html_safe(text):
    if not text: return ""
    return str(text).replace('"', '&quot;').replace("'", "&#39;").replace('\n', ' ').replace('\r', '')

def generar_dashboard():
    try:
        res = requests.post(f"https://api.notion.com/v1/databases/{DATABASE_ID}/query", headers=headers)
        data = res.json()

        agenda = {}
        ingresos_mes = {m: 0 for m in range(1, 13)}
        # Paleta de colores mejorada para fondos oscuros (Neon/Pastel brillantes)
        COLORES = ["#3b82f6", "#8b5cf6", "#ec4899", "#10b981", "#f59e0b", "#0ea5e9", "#f43f5e", "#6366f1", "#14b8a6", "#f97316", "#d946ef", "#84cc16"]

        for r in data.get("results", []):
            p = r["properties"]
            f_data = p.get("Fecha", {}).get("date", {})
            if not f_data: continue
            
            start_iso = f_data.get("start")
            end_iso = f_data.get("end") or start_iso
            start = datetime.strptime(start_iso[:10], "%Y-%m-%d").date()
            end = datetime.strptime(end_iso[:10], "%Y-%m-%d").date()
            
            hora_in = get_safe_time(start_iso)
            hora_out = get_safe_time(end_iso)
            
            monto = get_safe_num(p.get("Total cliente"))
            if get_safe_text(p.get("Estado")) != "CANCELADA": ingresos_mes[start.month] += monto

            res_id = r["id"].replace("-", "")
            color_idx = sum(ord(c) for c in res_id) % len(COLORES)
            color_res = COLORES[color_idx]
            
            nombre_real = get_safe_text(p.get("Cliente"))
            if nombre_real == "No asignado": nombre_real = get_safe_text(p.get("Nombre"))
                
            limpiador = get_safe_text(p.get("Cleaning"))
            encargado_in = get_safe_text(p.get("Check In by:"))
            encargado_out = get_safe_text(p.get("Check out by"))
            correo = get_safe_text(p.get("Correo electrónico 1"))
            telefono = get_safe_text(p.get("Teléfono"))
            pax = get_safe_num(p.get("TRIPULACIÓN"))
            patron = get_safe_bool(p.get("PATRON"))
            extras = get_safe_multi(p.get("EXTRAS"))
            deposito = get_safe_num(p.get("Deposit"))
            notas = get_safe_text(p.get("COMENTARIOS"))

            info = {
                "id": res_id, "nombre": nombre_real, "color": color_res,
                "tel": telefono, "correo": correo, "pax": pax, "patron": patron,
                "extras": extras, "deposito": deposito, "monto": monto, "notas": notas
            }

            curr = start
            while curr <= end:
                if curr not in agenda: agenda[curr] = {"res": None, "acts": []}
                agenda[curr]["res"] = info
                curr += timedelta(days=1)
            
            if start not in agenda: agenda[start] = {"res": None, "acts": []}
            agenda[start]["acts"].append({"tipo": "IN", "id": res_id, "email": correo, "nombre": nombre_real, "staff": encargado_in, "hora": hora_in})
            
            if end not in agenda: agenda[end] = {"res": None, "acts": []}
            agenda[end]["acts"].append({"tipo": "OUT", "id": res_id, "email": correo, "nombre": nombre_real, "staff": encargado_out, "hora": hora_out})

            f_limp = get_safe_date(p.get("Cleaning Date"))
            if f_limp:
                if f_limp not in agenda: agenda[f_limp] = {"res": None, "acts": []}
                agenda[f_limp]["acts"].append({"tipo": "LIMP", "id": res_id, "staff": limpiador, "hora": "--"})

        # --- GENERACIÓN HTML ESTÉTICA ---
        html = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>DIVONA 2026</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
        body { background-color: #0b1120; font-family: sans-serif; color: #f1f5f9; } 
        .month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1.25rem; overflow: hidden; height: 100%; display: flex; flex-direction: column; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.6); } 
        .grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); grid-template-rows: repeat(6, 1fr); gap: 4px; flex-grow: 1; min-height: 260px; padding: 6px; } 
        .day { min-height: 58px; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: flex-start; padding: 4px 2px; font-size: 0.7rem; transition: all 0.25s ease; position: relative; } 
        .empty-day { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.02); }
        .occupied { cursor: pointer; border-top: 1px solid rgba(255,255,255,0.05); border-right: 1px solid rgba(255,255,255,0.05); border-bottom: 1px solid rgba(255,255,255,0.05); } 
        .occupied:hover { transform: translateY(-3px) scale(1.02); box-shadow: 0 8px 16px rgba(0,0,0,0.4); filter: brightness(1.2); z-index: 10; }
        .dimmed { opacity: 0.15; filter: grayscale(1); } 
        .highlight { border: 2px solid white !important; background: rgba(255,255,255,0.15) !important; transform: scale(1.05) translateY(-3px); z-index: 20; box-shadow: 0 0 20px rgba(255,255,255,0.1); } 
        </style></head><body>
        """
        total_anual = sum(ingresos_mes.values())
        html += f'<div class="p-8 max-w-7xl mx-auto"><div class="flex flex-col md:flex-row justify-between items-end mb-12 gap-6"><div><h1 class="text-4xl font-black tracking-tighter uppercase drop-shadow-lg">Divona Center</h1><p class="text-blue-400 font-bold text-xl mt-2">TOTAL 2026: {total_anual:,.0f} €</p></div>'
        html += '<div class="flex flex-wrap gap-2 shadow-lg rounded-lg"><button onclick="filterView(\'all\', this)" class="filter-btn bg-blue-600 px-5 py-2.5 rounded-lg text-[11px] font-bold uppercase transition-colors">General</button>'
        html += '<button onclick="filterView(\'LIMP\', this)" class="filter-btn bg-slate-700 hover:bg-slate-600 px-5 py-2.5 rounded-lg text-[11px] font-bold uppercase transition-colors">Limpiezas</button>'
        html += '<button onclick="filterView(\'IN\', this)" class="filter-btn bg-slate-700 hover:bg-slate-600 px-5 py-2.5 rounded-lg text-[11px] font-bold uppercase transition-colors">Check-in</button>'
        html += '<button onclick="filterView(\'OUT\', this)" class="filter-btn bg-slate-700 hover:bg-slate-600 px-5 py-2.5 rounded-lg text-[11px] font-bold uppercase transition-colors">Check-out</button></div></div>'
        html += '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">'

        for mes in range(3, 13):
            ultimo = calendar.monthrange(2026, mes)[1]
            primer_dia = calendar.monthrange(2026, mes)[0]
            _, t_color = get_day_season(datetime(2026, mes, 15))
            
            html += f'<div><div class="month-card"><div class="p-4 border-b border-slate-700/50 flex justify-between items-center bg-slate-800/80"><span class="font-black text-[11px] uppercase tracking-wider" style="color:{t_color}; text-shadow: 0 0 10px {t_color}40;">{MESES_NOMBRES[mes]}</span><span class="text-white font-bold text-[10px] bg-slate-900/50 border border-slate-700 px-2 py-1.5 rounded-md shadow-inner">{ingresos_mes[mes]:,.0f} €</span></div><div class="p-1.5 flex-grow flex flex-col bg-slate-900/20"><div class="grid-cal">'
            
            # Espacios vacíos al principio del mes
            for _ in range(primer_dia): html += '<div class="day border-none bg-transparent"></div>'
            
            for dia in range(1, ultimo + 1):
                f_act = datetime(2026, mes, dia).date()
                d_day = agenda.get(f_act, {"res": None, "acts": []})
                res, acts = d_day["res"], d_day["acts"]
                
                tags = " ".join([a["tipo"] for a in acts])
                acts_html = ""
                
                for a in acts:
                    tipo = a["tipo"]
                    icon_id = f"{tipo}-{a['id']}"
                    staff = html_safe(a.get("staff", "")) or "No asignado"
                    hora = html_safe(a.get("hora", ""))
                    
                    if tipo == "LIMP":
                        acts_html += f'<span id="{icon_id}" class="op-icon cursor-pointer hover:scale-150 transition-transform text-[16px] drop-shadow-md z-20" data-type="operativa" data-op-tipo="Limpieza 🧹" data-hora="--" data-staff="{staff}" onclick="event.stopPropagation(); openModal(this)">🧹</span>'
                    else:
                        ico = "⚓" if tipo == "IN" else "🏁"
                        op_tipo = "Check-in ⚓" if tipo == "IN" else "Check-out 🏁"
                        
                        if a.get("email"):
                            asu = "Bienvenido a Divona" if tipo == "IN" else "Gracias y hasta pronto"
                            if tipo == "IN":
                                txt = f"Hola {a['nombre']},%0D%0A%0D%0AQueremos darte una cálida bienvenida y agradecerte de corazón por confiar en nosotros.%0D%0AEn un futuro muy cercano te enviaremos por aquí un enlace de YouTube con los vídeos de tu aventura.%0D%0A%0D%0A¡Que lo disfrutes muchísimo!%0D%0A%0D%0AEl equipo de Divona Center"
                            else:
                                txt = f"Hola {a['nombre']},%0D%0A%0D%0AEsperamos que hayas disfrutado al máximo tu experiencia con nosotros y que vuelvas muy pronto.%0D%0AComo agradecimiento por ser un cliente recurrente, si contactas con nosotros a través de este correo para tu próxima reserva, ¡te haremos un regalo especial!%0D%0A%0D%0AEl equipo de Divona Center"
                            
                            acts_html += f'<span id="{icon_id}" class="op-icon cursor-pointer hover:scale-150 transition-transform text-[16px] drop-shadow-md z-20" data-type="operativa" data-op-tipo="{op_tipo}" data-hora="{hora}" data-staff="{staff}" data-mail-to="{a["email"]}" data-mail-sub="{asu.replace(" ", "%20")}" data-mail-body="{txt}" data-btn-id="{icon_id}" onclick="event.stopPropagation(); openModal(this)">{ico}</span>'
                        else:
                            acts_html += f'<span class="cursor-pointer hover:scale-150 transition-transform text-[16px] drop-shadow-md z-20" data-type="operativa" data-op-tipo="{op_tipo}" data-hora="{hora}" data-staff="{staff}" onclick="event.stopPropagation(); openModal(this)">{ico}</span>'
                
                # Diseño de Celda
                if res:
                    css = "day day-cell occupied"
                    # Background con gradiente + borde grueso a la izquierda
                    style = f"background: linear-gradient(135deg, {res['color']}25 0%, {res['color']}08 100%); border-left: 4px solid {res['color']};"
                    data_attr = f'data-type="reserva" data-cliente="{html_safe(res["nombre"])}" data-tel="{html_safe(res["tel"])}" data-email="{html_safe(res["correo"])}" data-pax="{res["pax"]}" data-patron="{res["patron"]}" data-extras="{html_safe(res["extras"])}" data-deposito="{res["deposito"]}" data-total="{res["monto"]}" data-notas="{html_safe(res["notas"])}"'
                    
                    # Nombre corto para el calendario (máximo 8 letras para que quede estético)
                    nombre_corto = res["nombre"].split()[0][:8]
                    nombre_html = f'<span class="text-[8px] font-black uppercase tracking-wider truncate w-full text-center mt-0.5 z-10 drop-shadow-md" style="color:{res["color"]}">{nombre_corto}</span>'
                else:
                    css = "day day-cell empty-day"
                    style = ""
                    nombre_html = ""
                    data_type = "limpieza_sola" if "LIMP" in tags else "libre"
                    data_attr = f'data-type="{data_type}"'
                
                html += f'<div class="{css}" data-tags="{tags}" style="{style}" {data_attr} onclick="openModal(this)">'
                html += f'<span class="font-bold text-slate-300 text-[11px] z-10">{dia}</span>'
                html += nombre_html
                html += f'<div class="flex gap-1.5 mt-auto z-10 mb-0.5">{acts_html}</div></div>'
                
            html += '</div></div></div></div>'
            
        html += f'</div><div class="text-center text-xs text-slate-500 mt-10 pb-6 opacity-70">Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</div></div>'
        
        # --- HTML DEL MODAL Y SCRIPTS (LÓGICA INTACTA) ---
        js_modal = """
        <div id="modal" class="fixed inset-0 bg-slate-950/80 hidden z-50 flex items-center justify-center p-4 backdrop-blur-md opacity-0 transition-opacity duration-300" onclick="closeModal()">
            <div id="modal-panel" class="bg-slate-800 border border-slate-600/50 rounded-2xl shadow-[0_0_50px_-12px_rgba(0,0,0,0.8)] w-full max-w-md transform scale-95 transition-transform duration-300" onclick="event.stopPropagation()">
                <div class="p-4 border-b border-slate-700/80 flex justify-between items-center bg-gradient-to-r from-slate-800 to-slate-800/50 rounded-t-2xl">
                    <h3 id="modal-title" class="text-lg font-black text-blue-400 uppercase tracking-widest drop-shadow-md"></h3>
                    <button onclick="closeModal()" class="text-slate-400 hover:text-white transition-colors text-2xl leading-none font-light px-2">&times;</button>
                </div>
                <div id="modal-content" class="p-6 text-sm text-slate-300"></div>
            </div>
        </div>

        <script>
        function filterView(type, btn) {
            document.querySelectorAll(".filter-btn").forEach(b => { b.classList.replace("bg-blue-600", "bg-slate-700"); });
            btn.classList.replace("bg-slate-700", "bg-blue-600");
            document.querySelectorAll(".day-cell").forEach(day => {
                day.classList.remove("dimmed", "highlight");
                if (type === "all") return;
                if ((day.getAttribute("data-tags") || "").includes(type)) day.classList.add("highlight");
                else day.classList.add("dimmed");
            });
        }
        
        function openModal(el) {
            const type = el.getAttribute('data-type');
            const titleEl = document.getElementById('modal-title');
            const contentEl = document.getElementById('modal-content');

            if (type === 'reserva') {
                titleEl.innerText = "Ficha de Reserva";
                contentEl.innerHTML = `
                    <div class='grid grid-cols-2 gap-y-5 gap-x-4 mb-5'>
                        <div class='col-span-2'><span class='text-slate-500 text-[10px] font-bold block mb-1 uppercase tracking-wider'>Cliente</span><span class='font-black text-white text-xl tracking-tight'>${el.getAttribute('data-cliente')}</span></div>
                        <div><span class='text-slate-500 text-[10px] font-bold block mb-1 uppercase tracking-wider'>Teléfono</span><span class='text-slate-200 font-medium'>${el.getAttribute('data-tel') || '-'}</span></div>
                        <div><span class='text-slate-500 text-[10px] font-bold block mb-1 uppercase tracking-wider'>Email</span><span class='text-blue-300 font-medium truncate block'>${el.getAttribute('data-email') || '-'}</span></div>
                        <div><span class='text-slate-500 text-[10px] font-bold block mb-1 uppercase tracking-wider'>Tripulación</span><span class='text-slate-200 font-medium'>${el.getAttribute('data-pax')} personas</span></div>
                        <div><span class='text-slate-500 text-[10px] font-bold block mb-1 uppercase tracking-wider'>Patrón</span><span class='text-slate-200 font-medium'>${el.getAttribute('data-patron')}</span></div>
                        <div class='col-span-2'><span class='text-slate-500 text-[10px] font-bold block mb-1 uppercase tracking-wider'>Extras</span><span class='text-amber-400 font-bold'>${el.getAttribute('data-extras') || 'Ninguno'}</span></div>
                    </div>
                    <div class='flex justify-between items-center bg-slate-900/60 p-5 rounded-xl mb-5 border border-slate-700/50 shadow-inner'>
                        <div><span class='text-slate-500 text-[10px] font-bold block mb-1 uppercase tracking-wider'>Depósito</span><span class='text-white font-bold text-lg'>${el.getAttribute('data-deposito')} €</span></div>
                        <div class='text-right'><span class='text-slate-500 text-[10px] font-bold block mb-1 uppercase tracking-wider'>Total a Pagar</span><span class='text-emerald-400 font-black text-3xl drop-shadow-md'>${el.getAttribute('data-total')} €</span></div>
                    </div>
                    <div class='border-t border-slate-700/80 pt-5 mt-2'>
                        <span class='text-slate-500 text-[10px] font-bold block mb-2 uppercase tracking-wider'>Notas y Comentarios</span>
                        <p class='text-slate-300 italic text-xs leading-relaxed bg-slate-800/50 p-3 rounded-lg border border-slate-700/30'>${el.getAttribute('data-notas') || 'Sin comentarios adicionales.'}</p>
                    </div>
                `;
            } else if (type === 'operativa') {
                const opTipo = el.getAttribute('data-op-tipo');
                titleEl.innerText = "Gestión Operativa";
                let html = `
                    <div class='text-center mb-8 mt-4'>
                        <div class='text-xs text-blue-400 font-bold mb-4 uppercase tracking-[0.2em]'>${opTipo}</div>
                        ${el.getAttribute('data-hora') !== '--' ? `<div class='text-6xl font-black text-white mb-4 tracking-tighter drop-shadow-lg'>${el.getAttribute('data-hora')}</div>` : ''}
                        <div class='text-slate-400 text-sm bg-slate-900/40 inline-block px-4 py-2 rounded-full border border-slate-700/50 mt-2'>Encargado: <span class='text-white font-bold text-base ml-1'>${el.getAttribute('data-staff')}</span></div>
                    </div>
                `;

                const mailTo = el.getAttribute('data-mail-to');
                if (mailTo) {
                    const mailSub = el.getAttribute('data-mail-sub');
                    const mailBody = el.getAttribute('data-mail-body');
                    const btnId = el.getAttribute('data-btn-id');
                    
                    const isSent = localStorage.getItem("divona_" + btnId);
                    const btnClass = isSent ? "bg-slate-700 text-slate-400 border border-slate-600 shadow-inner" : "bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white shadow-[0_0_20px_rgba(37,99,235,0.4)]";
                    const btnText = isSent ? "Reenviar correo (Ya enviado)" : "Enviar Correo Automático";

                    html += `
                        <div class='border-t border-slate-700/80 pt-6'>
                            <a href="mailto:${mailTo}?subject=${mailSub}&body=${mailBody}"
                               onclick="markEmail('${btnId}'); closeModal();"
                               class="block w-full text-center py-4 rounded-xl font-bold transition-all transform hover:scale-[1.03] active:scale-95 ${btnClass} tracking-wide text-sm">
                               ✉️ ${btnText}
                            </a>
                        </div>
                    `;
                }
                contentEl.innerHTML = html;
            } else if (type === 'limpieza_sola') {
                titleEl.innerText = "Día de Mantenimiento";
                contentEl.innerHTML = `<div class='text-center py-12'><span class='text-6xl block mb-6 drop-shadow-lg'>🧹</span><span class='text-lg text-slate-300 font-medium'>Día asignado exclusivamente para limpieza.</span></div>`;
            } else {
                titleEl.innerText = "Día Libre";
                contentEl.innerHTML = `<div class='text-center py-12 text-slate-500'><span class='text-4xl block mb-4 opacity-50'>🌊</span><span class='text-sm uppercase tracking-widest font-bold'>Calendario Despejado</span></div>`;
            }

            const modal = document.getElementById('modal');
            const panel = document.getElementById('modal-panel');
            modal.classList.remove('hidden');
            void modal.offsetWidth; 
            modal.classList.remove('opacity-0');
            panel.classList.remove('scale-95');
        }

        function closeModal() {
            const modal = document.getElementById('modal');
            const panel = document.getElementById('modal-panel');
            modal.classList.add('opacity-0');
            panel.classList.add('scale-95');
            setTimeout(() => { modal.classList.add('hidden'); }, 300);
        }

        function markEmail(btnId) {
            localStorage.setItem("divona_" + btnId, "true");
            const icon = document.getElementById(btnId);
            if (icon) icon.classList.add("opacity-20", "grayscale");
        }

        document.addEventListener("DOMContentLoaded", () => {
            document.querySelectorAll(".op-icon").forEach(icon => {
                if(localStorage.getItem("divona_" + icon.id)) icon.classList.add("opacity-20", "grayscale");
            });
        });
        </script></body></html>
        """
        
        with open("index.html", "w", encoding="utf-8") as f: f.write(html + js_modal)
        
    except Exception as e:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(f"<html><body><h1 style='color:red;'>Error:</h1><pre>{traceback.format_exc()}</pre></body></html>")

if __name__ == "__main__": generar_dashboard()
