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
    if not prop: return ""
    try:
        t = prop.get("type")
        if t in ["title", "rich_text"]: return prop[t][0]["plain_text"] if prop[t] else ""
        if t in ["select", "status"]: return prop[t]["name"] if prop[t] else ""
        if t == "phone_number": return prop.get("phone_number") or ""
        if t == "people": return prop["people"][0]["name"] if prop["people"] else ""
        if t == "email": return prop.get("email") or ""
        return ""
    except: return ""

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

        for r in data.get("results", []):
            p = r["properties"]
            f_data = p.get("Fecha", {}).get("date", {})
            if not f_data: continue
            
            start = datetime.strptime(f_data["start"][:10], "%Y-%m-%d").date()
            end = datetime.strptime((f_data.get("end") or f_data["start"])[:10], "%Y-%m-%d").date()
            
            monto = get_safe_num(p.get("Total cliente"))
            if get_safe_text(p.get("Estado")) != "CANCELADA": ingresos_mes[start.month] += monto

            res_id = r["id"].replace("-", "")
            color_idx = sum(ord(c) for c in res_id) % len(COLORES)
            
            nombre_real = get_safe_text(p.get("Cliente")) or get_safe_text(p.get("Nombre"))
            info_det = (f"CLIENTE: {js_safe(nombre_real)}\\n"
                        f"BOOKING: {get_safe_text(p.get('BOOKING NUMBER'))} | IDIOMA: {get_safe_text(p.get('Idioma'))}\\n"
                        f"TEL: {get_safe_text(p.get('Teléfono'))} | PERSONAS: {int(get_safe_num(p.get('TRIPULACIÓN')))}\\n"
                        f"PATRÓN: {get_safe_bool(p.get('PATRON'))} | EXTRAS: {js_safe(get_safe_multi(p.get('EXTRAS')))}\\n"
                        f"DEPÓSITO: {int(get_safe_num(p.get('Deposit')))}€ | TOTAL: {int(monto)}€\\n"
                        f"CHECK-IN: {get_safe_text(p.get('Check In by:'))} | CHECK-OUT: {get_safe_text(p.get('Check out by'))}\\n"
                        f"NOTAS: {js_safe(get_safe_text(p.get('COMENTARIOS')))}")

            info = {"id": res_id, "nombre": nombre_real, "color": COLORES[color_idx], "detalle": info_det}

            # Rellenar calendario días ocupados
            curr = start
            while curr <= end:
                if curr not in agenda: agenda[curr] = {"res": None, "acts": []}
                agenda[curr]["res"] = info
                if curr == start: 
                    agenda[curr]["acts"].append({"tipo": "IN", "id": res_id, "email": get_safe_text(p.get("Correo electrónico 1")), "nombre": nombre_real})
                curr += timedelta(days=1)
            
            # Check-out dinámico
            f_out = get_safe_date(p.get("Check out")) or end
            if f_out not in agenda: agenda[f_out] = {"res": None, "acts": []}
            agenda[f_out]["acts"].append({"tipo": "OUT", "id": res_id, "email": get_safe_text(p.get("Correo electrónico 1")), "nombre": nombre_real})

            # LIMPIEZA DINÁMICA (SOLO si hay fecha en la columna)
            f_limp = get_safe_date(p.get("Cleaning Date"))
            if f_limp:
                if f_limp not in agenda: agenda[f_limp] = {"res": None, "acts": []}
                agenda[f_limp]["acts"].append({"tipo": "LIMP", "id": res_id})

        # --- HTML ---
        html = """<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><title>DIVONA 2026</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
        body { background-color: #0f172a; font-family: sans-serif; color: #f1f5f9; } 
        .month-card { background: #1e293b; border: 1px solid #334155; border-radius: 1rem; overflow: hidden; height: 100%; display: flex; flex-direction: column; } 
        .grid-cal { display: grid; grid-template-columns: repeat(7, 1fr); grid-template-rows: repeat(6, 1fr); gap: 0px; flex-grow: 1; min-height: 250px; } 
        .day { min-height: 45px; display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: 4px 0; font-size: 0.65rem; border: 1px solid rgba(255,255,255,0.03); transition: all 0.2s ease; } 
        .occupied { border-width: 2px !important; cursor: pointer; } 
        .dimmed { opacity: 0.15; filter: grayscale(1); } 
        .highlight { border: 2px solid white !important; background: rgba(255,255,255,0.1); transform: scale(1.03); z-index: 10; } 
        </style></head><body>
        """
        total_anual = sum(ingresos_mes.values())
        html += f'<div class="p-8 max-w-7xl mx-auto"><div class="flex flex-col md:flex-row justify-between items-end mb-12 gap-6"><div><h1 class="text-4xl font-black tracking-tighter uppercase">Divona Center</h1><p class="text-blue-400 font-bold text-xl mt-2">TOTAL 2026: {total_anual:,.0f} €</p></div>'
        html += '<div class="flex flex-wrap gap-2"><button onclick="filterView(\'all\', this)" class="filter-btn bg-blue-600 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">General</button>'
        html += '<button onclick="filterView(\'LIMP\', this)" class="filter-btn bg-slate-700 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">Limpiezas</button>'
        html += '<button onclick="filterView(\'IN\', this)" class="filter-btn bg-slate-700 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">Check-in</button>'
        html += '<button onclick="filterView(\'OUT\', this)" class="filter-btn bg-slate-700 px-4 py-2 rounded-lg text-[10px] font-bold uppercase">Check-out</button></div></div>'
        html += '<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">'

        for mes in range(3, 13):
            ultimo = calendar.monthrange(2026, mes)[1]
            primer_dia = calendar.monthrange(2026, mes)[0]
            _, t_color = get_day_season(datetime(2026, mes, 15))
            html += f'<div><div class="month-card shadow-2xl"><div class="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/30"><span class="font-bold text-[10px] uppercase" style="color:{t_color}">{MESES_NOMBRES[mes]}</span><span class="text-white font-black text-[10px] bg-slate-700 px-2 py-1 rounded">{ingresos_mes[mes]:,.0f} €</span></div><div class="p-2 flex-grow flex flex-col"><div class="grid-cal">'
            for _ in range(primer_dia): html += '<div class="day border-none"></div>'
            for dia in range(1, ultimo + 1):
                f_act = datetime(2026, mes, dia).date()
                d_day = agenda.get(f_act, {"res": None, "acts": []})
                res, acts = d_day["res"], d_day["acts"]
                tags = " ".join([a["tipo"] for a in acts])
                acts_html = ""
                for a in acts:
                    if a["tipo"] == "LIMP": acts_html += '<span>🧹</span>'
                    else:
                        ico = "⚓" if a["tipo"] == "IN" else "🏁"
                        if a.get("email"):
                            asu = "Bienvenido a Divona" if a["tipo"] == "IN" else "Gracias por venir"
                            txt = f"Hola {a['nombre']}..." 
                            href = f"mailto:{a['email']}?subject={urllib.parse.quote(asu)}&body={urllib.parse.quote(txt)}"
                            acts_html += f'<a href="{href}" id="{a["tipo"]}-{a["id"]}" class="email-btn cursor-pointer hover:scale-150 transition-transform text-lg" onclick="toggleCorreo(event, this)">{ico}</a>'
                        else: acts_html += f'<span>{ico}</span>'
                css = "day day-cell " + ("occupied" if res else "")
                style = f"background-color:{res['color']}15; border-color:{res['color']};" if res else ""
                html += f'<div class="{css}" data-tags="{tags}" style="{style}" onclick="alert(\'{res["detalle"] if res else ("Limpieza" if "LIMP" in tags else "Libre")}\')"><span class="font-bold">{dia}</span><div class="flex gap-1">{acts_html}</div></div>'
            html += '</div></div></div></div>'
        html += f'</div><div class="text-center text-xs text-slate-500 mt-8 pb-4">Actualizado: {datetime.now().strftime("%d/%m/%Y %H:%M")}</div></div>'
        js = """<script>
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
        function toggleCorreo(e, el) {
            e.stopPropagation();
            if(localStorage.getItem(el.id)) { localStorage.removeItem(el.id); el.classList.remove("opacity-20", "grayscale"); e.preventDefault(); }
            else { localStorage.setItem(el.id, "true"); el.classList.add("opacity-20", "grayscale"); }
        }
        document.addEventListener("DOMContentLoaded", () => {
            document.querySelectorAll(".email-btn").forEach(b => { if(localStorage.getItem(b.id)) b.classList.add("opacity-20", "grayscale"); });
        });
        </script></body></html>"""
        with open("index.html", "w", encoding="utf-8") as f: f.write(html + js)
    except Exception as e:
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(f"<html><body><h1>Error:</h1><pre>{traceback.format_exc()}</pre></body></html>")

if __name__ == "__main__": generar_dashboard()
