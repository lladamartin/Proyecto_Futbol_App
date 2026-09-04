import os
from supabase import create_client, Client
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def chequear_fechas_alineaciones():
    try:
        response = supabase.table("alineaciones").select("Fecha").execute()
        df = pd.DataFrame(response.data)
        
        print("--- ESTADO DE FECHAS EN 'alineaciones' ---")
        if df.empty:
            print("⚠️ La tabla no devolvió registros.")
        else:
            print(f"Total de registros encontrados: {len(df)}")
            print("\nPrimeras fechas brutas:")
            print(df.head())
            
            # Limpiar y obtener fechas únicas ordenadas
            df['Fecha'] = pd.to_datetime(df['Fecha'], format='mixed', dayfirst=True, errors='coerce')
            fechas_unicas = sorted(df['Fecha'].dropna().unique(), reverse=True)
            
            print(f"\n✅ Fechas únicas detectadas ({len(fechas_unicas)} en total):")
            for f in fechas_unicas:
                print(pd.to_datetime(f).strftime('%d de %B, %Y'))
                
    except Exception as e:
        print(f"❌ Error al consultar las fechas: {e}")

if __name__ == "__main__":
    chequear_fechas_alineaciones()