import os
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd

# Cargar variables de entorno (asegúrate de tener tu archivo .env o las credenciales configuradas)
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Inicializar cliente de Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def verificar_tabla_jugadores():
    try:
        # Consulta explícita a la tabla 'jugadores'
        response = supabase.table("jugadores").select("*").execute()
        
        # Convertimos los datos a un DataFrame de pandas para inspeccionarlos fácil
        df_jugadores = pd.DataFrame(response.data)
        
        print("--- ESTADO DE LA TABLA 'jugadores' ---")
        if df_jugadores.empty:
            print("⚠️ La tabla 'jugadores' está vacía o no devolvió registros.")
        else:
            print(f"✅ ¡Conexión exitosa! Se encontraron {len(df_jugadores)} registros.")
            print("\nColumnas disponibles en la tabla:")
            print(df_jugadores.columns.tolist())
            
            print("\nMuestra de los primeros jugadores:")
            print(df_jugadores.head())
            
    except Exception as e:
        print(f"❌ Error al consultar la tabla 'jugadores': {e}")

if __name__ == "__main__":
    verificar_tabla_jugadores()