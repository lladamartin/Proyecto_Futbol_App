import pandas as pd
from supabase import create_client, Client

SUPABASE_URL = "https://bmhftbmzaujquvmjycee.supabase.co"
SUPABASE_KEY = "sb_publishable_cU51AGZB06h6ri6hDGfumQ_8yl8NglE"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
excel_path = "./data/Base Futbol Jueves del Cordero Susurrador.xlsx"

print("Subiendo jugadores...")
try:
    df_players = pd.read_excel(excel_path, sheet_name="Jugadores")
    df_players = df_players.where(pd.notnull(df_players), None)
    
    jugadores_list = []
    for _, row in df_players.iterrows():
        nickname = row.get("Player_nickname")
        if nickname and str(nickname).strip() != "":
            jugadores_list.append({
                "nickname": str(nickname).strip(),
                "nombre": str(row.get("Player_name")) if row.get("Player_name") is not None else None,
                "apellido": str(row.get("Player_lastname")) if row.get("Player_lastname") is not None else None
            })
    
    if jugadores_list:
        supabase.table("jugadores").upsert(jugadores_list, on_conflict="nickname").execute()
    print(f"¡{len(jugadores_list)} jugadores subidos con éxito!")
except Exception as e:
    print(f"Error en jugadores: {e}")

print("Subiendo goles / alineaciones de forma masiva...")
try:
    df_goles = pd.read_excel(excel_path, sheet_name="Goles")
    df_goles = df_goles.where(pd.notnull(df_goles), None)
    
    goles_list = []
    for _, row in df_goles.iterrows():
        fecha_raw = row.get("Fecha")
        nickname = row.get("Player_nickname")
        
        # Filtrar solo filas que tengan datos reales y evitar filas vacías del Excel
        if nickname and fecha_raw is not None and str(nickname).strip() != "":
            raw_fecha = str(fecha_raw)[:10]
            if raw_fecha != "NaT" and len(raw_fecha) == 10:
                goles_val = row.get("Goles")
                goles_list.append({
                    "fecha": raw_fecha,
                    "nickname": str(nickname).strip(),
                    "equipo": str(row.get("Equipo")) if row.get("Equipo") is not None else "Desconocido",
                    "goles": int(goles_val) if goles_val is not None and str(goles_val).isdigit() else 0
                })
    
    if goles_list:
        # Subir en bloques de 100 para que vuele
        batch_size = 100
        for i in range(0, len(goles_list), batch_size):
            batch = goles_list[i:i + batch_size]
            supabase.table("alineaciones").upsert(batch, on_conflict="fecha,nickname").execute()
            
    print(f"¡{len(goles_list)} registros de alineaciones subidos en segundos!")
except Exception as e:
    print(f"Error en goles: {e}")

print("¡Migración rápida finalizada!")