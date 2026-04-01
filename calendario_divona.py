import requests
import json
import os

TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def escanear_notion():
    print("Iniciando escáner de base de datos...")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    
    try:
        res = requests.post(url, headers=headers)
        data = res.json()
        
        if "results" not in data or len(data["results"]) == 0:
            print("No se encontraron reservas en la base de datos.")
            return

        print("\n=== RADIOGRAFÍA DE TUS COLUMNAS EN NOTION ===")
        # Cogemos la primera reserva como ejemplo
        propiedades = data["results"][0]["properties"]
        
        for nombre_columna, contenido in propiedades.items():
            tipo = contenido.get("type", "desconocido")
            print(f"- Columna: '{nombre_columna}' | Tipo de dato: {tipo}")
            
            # Si es una fecha, miramos qué formato tiene por dentro
            if tipo == "date" and contenido.get("date"):
                fecha_start = contenido["date"].get("start")
                fecha_end = contenido["date"].get("end")
                print(f"    > Ejemplo de fecha: Inicio {fecha_start} / Fin {fecha_end}")
                
        print("\n=============================================")
        print("Escáner terminado con éxito. La web no se ha modificado.")
        
    except Exception as e:
        print(f"Error al conectar: {e}")

if __name__ == "__main__":
    escanear_notion()
