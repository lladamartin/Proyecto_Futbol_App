import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- CONFIGURACIÓN Y CONEXIÓN ---
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Jueves del Cordero Susurrador", layout="wide", page_icon="⚽")

# --- FUNCIONES DE BASE DE DATOS (SUPABASE) ---
def run_query(table):
    response = supabase.table(table).select("*").execute()
    return pd.DataFrame(response.data)

def insert_data(table, data):
    return supabase.table(table).insert(data).execute()

def upsert_data(table, data):
    return supabase.table(table).upsert(data).execute()

# --- CARGAR DATOS ---
def cargar_datos_supabase():
    df_alineaciones = run_query("alineaciones")
    df_encuestas = run_query("encuestas")
    df_jugadores = run_query("jugadores")
    
    # Conversión de fechas
    for df in [df_alineaciones, df_encuestas]:
        if not df.empty and 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'])
    return df_alineaciones, df_encuestas, df_jugadores

st.title("⚽ Juevezzz 💋")
st.markdown("### Registro futbolístico - Jueves del Cordero Susurrador")

df_goals_date, df_form_sql, df_players_db = cargar_datos_supabase()

try:
    if df_goals_date.empty:
        st.warning("⚠️ No hay partidos cargados. Ve al **Panel de Administración**.")
        fechas_jugadas_all = []
    else:
        # Lógica de procesamiento (idéntica a tu original)
        df_fecha_player = df_goals_date.copy()
        
        # --- (Tu lógica de cálculo de puntos y resultados aquí) ---
        # Nota: Asegúrate de que las columnas coincidan con las tablas de Supabase
        
        fechas_jugadas_all = sorted(df_fecha_player['fecha'].unique(), reverse=True)
    # --- TABS ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "⚽ Resultados por Fecha", "📊 Resumen y Tabla", "💬 Encuesta (Votar)", 
        "📋 Resultados de Encuestas", "🦜 Loros", "⚙️ Admin"
    ])

    with tab1:
        # ... (Tu lógica del tab1 usando run_query("alineaciones") y filtrando) ...
        pass

    with tab3:
        st.subheader("📝 Realizar Encuesta")
        # Para insertar en Supabase:
        # if st.form_submit_button("Enviar"):
        #     insert_data("encuestas", {"fecha": f_enc, "votante": votante, ...})
        pass

    with tab6:
        st.subheader("⚙️ Panel de Administración")
        password = st.text_input("Contraseña de Administrador", type="password")
        
        if password == ADMIN_PASSWORD and password is not None:
            st.success("Acceso concedido.")
            with st.form("carga_partido_admin"):
                f_admin = st.date_input("Fecha").strftime("%Y-%m-%d")
                # ... Lógica de carga ...
                if st.form_submit_button("Guardar"):
                    # Uso de insert_data / upsert_data
                    st.success("Guardado en Supabase.")
        elif password != "":
            st.error("Contraseña incorrecta.")

except Exception as e:
    st.error(f"Error: {e}")