import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Jueves del Cordero Susurrador", layout="wide", page_icon="⚽")

# Título y Bienvenida
st.title("⚽ Juevezzz 💋")
st.markdown("### Registro futbolístico - Jueves del Cordero Susurrador")

# Ruta del archivo Excel local y Google Sheets
excel_path = "data/Base Futbol Jueves del Cordero Susurrador.xlsx"
sheet_id = "1oLcqFdkBREN_14_Z7syuzFQj0kiuz2e5SoLGIV2VufE"
google_sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=600)
def cargar_datos():
    df_players = pd.read_excel(excel_path, sheet_name="Jugadores")
    df_players['label'] = df_players['Player_nickname'].astype(str) + " - " + df_players['Player_name'].astype(str) + " " + df_players['Player_lastname'].astype(str)
    
    df_goals = pd.read_excel(excel_path, sheet_name="Goles")
    df_players_grupo = pd.read_excel(excel_path, sheet_name="Fijo")
    
    try:
        df_form = pd.read_csv(google_sheet_url)
    except Exception as e:
        df_form = pd.DataFrame()
        
    return df_players, df_goals, df_players_grupo, df_form

try:
    df_players, df_goals_date, df_players_grupo, df_form = cargar_datos()
    
    # --- PRE-PROCESAMIENTO GOLES ---
    df_fecha_player = df_goals_date.copy()
    df_fecha_player.columns = [col.lower() for col in df_fecha_player.columns]
    df_fecha_player['fecha'] = pd.to_datetime(df_fecha_player['fecha'])
    
    df_fecha_goles = df_fecha_player.groupby(['fecha', 'equipo'], as_index=False)['goles'].sum()
    df_pivot = df_fecha_goles.pivot(index='fecha', columns='equipo', values='goles').reset_index().fillna(0)
    
    resultados_clean = []
    for _, row in df_pivot.iterrows():
        fecha = row['fecha']
        naranja = row.get('Naranja', 0)
        celeste = row.get('Celeste', 0)
        if naranja > celeste:
            rn, rc, pn, pc = 'G', 'P', 3, 0
        elif naranja < celeste:
            rn, rc, pn, pc = 'P', 'G', 0, 3
        else:
            rn, rc, pn, pc = 'E', 'E', 1, 1
        resultados_clean.append({'fecha': fecha, 'equipo': 'Naranja', 'resultado_label': rn, 'puntos': pn})
        resultados_clean.append({'fecha': fecha, 'equipo': 'Celeste', 'resultado_label': rc, 'puntos': pc})
        
    df_res_labels = pd.DataFrame(resultados_clean).drop_duplicates(subset=['fecha', 'equipo'])
    df_fecha_player = df_fecha_player.drop(columns=['resultado_label', 'puntos'], errors='ignore')
    df_fecha_player = pd.merge(df_fecha_player, df_res_labels, on=['fecha', 'equipo'], how='left')
    
    year_key = 2026
    ultima_fecha = df_fecha_player['fecha'].max()
    fecha_last_six = ultima_fecha - timedelta(weeks=6)
    
    fechas_jugadas_all = sorted(df_fecha_player[df_fecha_player['fecha'].dt.year == year_key]['fecha'].unique())
    fechas_jugadas_count = len(fechas_jugadas_all)

    # --- PROCESAMIENTO GOOGLE FORM CON CONDICIONAL DE JUGADOR NUEVO ---
    df_form_puntaje3 = pd.DataFrame(columns=['jugador', 'puntaje'])
    df_comentarios_limpio = pd.DataFrame(columns=['jugador', 'comentario'])

    if not df_form.empty:
        col_fecha = None
        for c in df_form.columns:
            if 'fecha' in c.lower() or 'partido' in c.lower():
                col_fecha = c
                break
                
        if col_fecha:
            df_form[col_fecha] = pd.to_datetime(df_form[col_fecha], errors='coerce')
            fecha_siguiente = pd.to_datetime(ultima_fecha) + timedelta(days=1)
            df_form.loc[df_form[col_fecha].dt.date == fecha_siguiente.date(), col_fecha] = pd.to_datetime(ultima_fecha)
            
            df_form2 = df_form[df_form[col_fecha].dt.date == pd.to_datetime(ultima_fecha).date()].copy()
            
            if not df_form2.empty:
                lista_p = []
                lista_c = []
                
                # Obtener la lista de jugadores reales del Excel para la última fecha (excluyendo "En contra")
                jugadores_excel = df_fecha_player[(df_fecha_player['fecha'] == ultima_fecha) & (df_fecha_player['player_nickname'] != "En contra")]['player_nickname'].values
                
                for i in range(1, 30):
                    col_j_name = [c for c in df_form2.columns if c.startswith(f"{i} -") and 'jugador' in c.lower()]
                    col_p_name = [c for c in df_form2.columns if c.startswith(f"{i} -") and 'puntaje' in c.lower()]
                    col_c_name = [c for c in df_form2.columns if c.startswith(f"{i} -") and 'comentario' in c.lower()]
                    
                    if col_j_name:
                        cj = col_j_name[0]
                        cp = col_p_name[0] if col_p_name else None
                        cc = col_c_name[0] if col_c_name else None
                        
                        for _, row in df_form2.iterrows():
                            j_val = row[cj]
                            if pd.notna(j_val):
                                j_str = str(j_val).strip()
                                
                                # Condicional idéntico a R: Si dice "Jugador nuevo", lo reemplazamos por el que falta en el Excel
                                if "jugador nuevo" in j_str.lower():
                                    # Ver qué jugadores ya se nombraron en este form
                                    pass # Se resuelve mapeando abajo con los faltantes
                                
                                if cp and pd.notna(row[cp]):
                                    try:
                                        p_val = float(row[cp])
                                        lista_p.append({'jugador': j_str, 'puntaje': p_val})
                                    except:
                                        pass
                                        
                                if cc and pd.notna(row[cc]):
                                    c_str = str(row[cc]).strip()
                                    if c_str != "":
                                        lista_c.append({'jugador': j_str, 'comentario': c_str})

                if len(lista_p) > 0:
                    df_p_raw = pd.DataFrame(lista_p)
                    
                    # Aplicar la regla de imputación del Jugador Nuevo
                    jugadores_form = df_p_raw[~df_p_raw['jugador'].str.contains('Jugador nuevo', case=False, na=False)]['jugador'].unique()
                    jugadores_faltantes = [j for j in jugadores_excel if j not in jugadores_form]
                    
                    if len(jugadores_faltantes) > 0:
                        df_p_raw.loc[df_p_raw['jugador'].str.contains('Jugador nuevo', case=False, na=False), 'jugador'] = jugadores_faltantes[0]
                    
                    df_form_puntaje3 = df_p_raw.groupby('jugador', as_index=False)['puntaje'].mean()
                    df_form_puntaje3['puntaje'] = df_form_puntaje3['puntaje'].round(0)
                    
                if len(lista_c) > 0:
                    df_c_raw = pd.DataFrame(lista_c)
                    if len(jugadores_faltantes) > 0:
                        df_c_raw.loc[df_c_raw['jugador'].str.contains('Jugador nuevo', case=False, na=False), 'jugador'] = jugadores_faltantes[0]
                    df_comentarios_limpio = df_c_raw.drop_duplicates().reset_index(drop=True)

    # --- TABLA GENERAL ---
    df_filtered_year = df_fecha_player[df_fecha_player['fecha'].dt.year == year_key]
    df_tabla_general = df_filtered_year.groupby('player_nickname').agg(
        jugados=('fecha', 'nunique'),
        ganados=('resultado_label', lambda x: (x == 'G').sum()),
        empatados=('resultado_label', lambda x: (x == 'E').sum()),
        perdidos=('resultado_label', lambda x: (x == 'P').sum()),
        goles=('goles', 'sum'),
        puntos=('puntos', 'sum')
    ).reset_index()
    
    df_rdo_ultimos = df_fecha_player[df_fecha_player['fecha'] >= fecha_last_six].sort_values('fecha')
    df_rdo_ultimos = df_rdo_ultimos.groupby('player_nickname')['resultado_label'].apply(lambda x: " ".join(x)).reset_index()
    df_rdo_ultimos.rename(columns={'resultado_label': 'ultimos_partidos'}, inplace=True)
    
    df_tabla_general = pd.merge(df_tabla_general, df_rdo_ultimos, on='player_nickname', how='left')
    df_tabla_general = df_tabla_general.sort_values(by='puntos', ascending=False)

    # --- TABS VISUALES PRINCIPALES ---
    tab1, tab2, tab3, tab4 = st.tabs(["⚽ Última Fecha & Puntajes", "📊 Resumen y Tabla", "💬 Comentarios por Jugador", "🦜 Loros (Ausencias)"])

    with tab1:
        st.subheader("Resultado de la Última Fecha")
        
        df_ult_goals = df_fecha_player[df_fecha_player['fecha'] == ultima_fecha].copy()
        df_ultima_res = df_ult_goals.groupby('equipo')['goles'].sum().reset_index()
        
        celeste_goles = df_ultima_res.loc[df_ultima_res['equipo'] == 'Celeste', 'goles'].values[0] if 'Celeste' in df_ultima_res['equipo'].values else 0
        naranja_goles = df_ultima_res.loc[df_ultima_res['equipo'] == 'Naranja', 'goles'].values[0] if 'Naranja' in df_ultima_res['equipo'].values else 0
        
        df_resultado_final = pd.DataFrame({
            'Celeste': [celeste_goles],
            'Naranja': [naranja_goles]
        })
        
        st.dataframe(df_resultado_final, use_container_width=True, hide_index=True)
        st.markdown(f"**Última fecha:** {pd.to_datetime(ultima_fecha).strftime('%d de %B, %Y')}  \n**Fechas con registro:** {fechas_jugadas_count}")
        
        st.markdown("---")
        st.subheader("Alineación y Puntaje")
        
        if not df_form_puntaje3.empty:
            df_form_puntaje3['jugador_clean'] = df_form_puntaje3['jugador'].astype(str).str.strip().str.lower()
            df_ult_goals['jugador_clean'] = df_ult_goals['player_nickname'].astype(str).str.strip().str.lower()
            df_ult_goals = pd.merge(df_ult_goals, df_form_puntaje3[['jugador_clean', 'puntaje']], on='jugador_clean', how='left')
        else:
            df_ult_goals['puntaje'] = ""
            
        df_naranja = df_ult_goals[df_ult_goals['equipo'] == 'Naranja'].reset_index(drop=True)
        df_celeste = df_ult_goals[df_ult_goals['equipo'] == 'Celeste'].reset_index(drop=True)
        
        max_len = max(len(df_naranja), len(df_celeste))
        alineacion_data = []
        for i in range(max_len):
            jugador_n = df_naranja.loc[i, 'player_nickname'] if i < len(df_naranja) else ""
            puntaje_n = df_naranja.loc[i, 'puntaje'] if (i < len(df_naranja) and 'puntaje' in df_naranja.columns and pd.notna(df_naranja.loc[i, 'puntaje'])) else ""
            jugador_c = df_celeste.loc[i, 'player_nickname'] if i < len(df_celeste) else ""
            puntaje_c = df_celeste.loc[i, 'puntaje'] if (i < len(df_celeste) and 'puntaje' in df_celeste.columns and pd.notna(df_celeste.loc[i, 'puntaje'])) else ""
            
            alineacion_data.append({
                'Jugador (Naranja)': jugador_n,
                'Puntaje (Naranja)': puntaje_n,
                'Jugador (Celeste)': jugador_c,
                'Puntaje (Celeste)': puntaje_c
            })
            
        df_alineacion_final = pd.DataFrame(alineacion_data)
        st.dataframe(df_alineacion_final, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("Tabla General de Posiciones (2026)")
        st.markdown(f"**Última fecha registrada:** {pd.to_datetime(ultima_fecha).strftime('%d de %B, %Y')} | **Fechas jugadas:** {fechas_jugadas_count}")
        
        st.dataframe(
            df_tabla_general.rename(columns={
                'player_nickname': 'Jugador',
                'jugados': 'Jugados',
                'ganados': 'Ganados',
                'empatados': 'Empatados',
                'perdidos': 'Perdidos',
                'goles': 'Goles',
                'puntos': 'Puntos',
                'ultimos_partidos': 'Últimas Fechas'
            }),
            use_container_width=True,
            hide_index=True
        )

    with tab3:
        st.subheader("Comentarios por Jugador (Última Fecha)")
        if not df_comentarios_limpio.empty:
            st.dataframe(df_comentarios_limpio, use_container_width=True, hide_index=True)
        else:
            st.info("No hay comentarios registrados para esta fecha en el Google Form.")

    with tab4:
        st.subheader("Tabla de Loros 🦜 (Ausencias del año)")
        df_panel = []
        for _, player in df_players_grupo.iterrows():
            for f in fechas_jugadas_all:
                df_panel.append({'player_nickname': player['Player_nickname'], 'fecha': f})
        df_panel = pd.DataFrame(df_panel)
        
        df_panel = pd.merge(df_panel, df_fecha_player[['player_nickname', 'equipo', 'fecha']], on=['player_nickname', 'fecha'], how='left')
        missing_counts = df_panel[df_panel['equipo'].isna()].groupby('player_nickname').size().reset_index(name='numero_ausencias')
        missing_counts = missing_counts.sort_values(by='numero_ausencias', ascending=False).rename(columns={'player_nickname': 'Jugador', 'numero_ausencias': 'Número de ausencias'})
        
        st.dataframe(missing_counts.head(10), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Error al cargar o procesar los datos: {e}")