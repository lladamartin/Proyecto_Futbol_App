import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client
from datetime import datetime, timedelta
from dotenv import load_dotenv

# --- CONFIGURACIÓN Y CONEXIÓN A SUPABASE ---
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Jueves del Cordero Susurrador", layout="wide", page_icon="⚽")

# --- FUNCIONES DE BASE DE DATOS (SUPABASE) ---
def run_query(table):
    try:
        response = supabase.table(table).select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error al consultar la tabla {table}: {e}")
        return pd.DataFrame()

def insert_data(table, data):
    return supabase.table(table).insert(data).execute()

# --- CARGAR HISTÓRICO DE GOOGLE SHEETS PARA ENCUESTAS ---
sheet_id = "1oLcqFdkBREN_14_Z7syuzFQj0kiuz2e5SoLGIV2VufE"
google_sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=600)
def cargar_datos():
    df_alineaciones = run_query("alineaciones")
    df_jugadores = run_query("jugadores")
    
    try:
        df_form = pd.read_csv(google_sheet_url)
    except Exception:
        df_form = pd.DataFrame()
        
    return df_alineaciones, df_jugadores, df_form

st.title("⚽ Juevezzz 💋")
st.markdown("### Registro futbolístico - Jueves del Cordero Susurrador")

try:
    df_goals_date, df_players_db, df_form = cargar_datos()
    
    if df_goals_date.empty:
        st.warning("⚠️ No hay partidos cargados en Supabase. Ve al **Panel de Administración**.")
        fechas_jugadas_all = []
        df_fecha_player = pd.DataFrame(columns=['fecha', 'player_nickname', 'equipo', 'goles'])
    else:
        # --- PRE-PROCESAMIENTO GOLES ---
        df_fecha_player = df_goals_date.copy()
        df_fecha_player.columns = [col.lower() for col in df_fecha_player.columns]
        
        col_j_key = next((c for c in ['player_nickname', 'nickname', 'jugador'] if c in df_fecha_player.columns), df_fecha_player.columns[1])
        if col_j_key != 'player_nickname':
            df_fecha_player['player_nickname'] = df_fecha_player[col_j_key]
            
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
        
        fechas_jugadas_all = sorted(df_fecha_player[df_fecha_player['fecha'].dt.year == year_key]['fecha'].unique(), reverse=True)
        fechas_jugadas_count = len(fechas_jugadas_all)

        # --- PROCESAMIENTO GOOGLE FORM ---
        df_form_procesado = pd.DataFrame()
        col_fecha_form = None

        if not df_form.empty:
            for c in df_form.columns:
                if 'fecha' in c.lower() or 'partido' in c.lower():
                    col_fecha_form = c
                    break
                    
            if col_fecha_form:
                df_form[col_fecha_form] = pd.to_datetime(df_form[col_fecha_form], errors='coerce')
                df_form_procesado = df_form.dropna(subset=[col_fecha_form]).copy()

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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "⚽ Resultados & Puntajes", 
        "📊 Resumen y Tabla", 
        "💬 Encuesta (Votar)",
        "📋 Comentarios por Fecha", 
        "🦜 Loros (Ausencias)",
        "⚙️ Admin"
    ])

    with tab1:
        st.subheader("Resultados por Fecha Seleccionada")
        if len(fechas_jugadas_all) > 0:
            fecha_sel = st.selectbox(
                "Elige la fecha del partido:", 
                fechas_jugadas_all, 
                format_func=lambda x: pd.to_datetime(x).strftime('%d de %B, %Y'),
                key="select_fecha_tab1"
            )
            
            df_sel_goals = df_fecha_player[df_fecha_player['fecha'] == fecha_sel].copy()
            df_ultima_res = df_sel_goals.groupby('equipo')['goles'].sum().reset_index()
            
            celeste_goles = df_ultima_res.loc[df_ultima_res['equipo'] == 'Celeste', 'goles'].values[0] if 'Celeste' in df_ultima_res['equipo'].values else 0
            naranja_goles = df_ultima_res.loc[df_ultima_res['equipo'] == 'Naranja', 'goles'].values[0] if 'Naranja' in df_ultima_res['equipo'].values else 0
            
            df_resultado_final = pd.DataFrame({'Celeste': [celeste_goles], 'Naranja': [naranja_goles]})
            st.dataframe(df_resultado_final, use_container_width=True, hide_index=True)
            st.markdown(f"**Fecha analizada:** {pd.to_datetime(fecha_sel).strftime('%d de %B, %Y')}")
            
            st.markdown("---")
            st.subheader("Alineación, Goles y Puntaje")
            
            df_form_puntaje_sel = pd.DataFrame(columns=['jugador', 'puntaje'])
            if not df_form_procesado.empty and col_fecha_form:
                f_target = pd.to_datetime(fecha_sel).date()
                df_form2 = df_form_procesado[
                    (df_form_procesado[col_fecha_form].dt.date >= f_target - timedelta(days=1)) & 
                    (df_form_procesado[col_fecha_form].dt.date <= f_target + timedelta(days=1))
                ].copy()
                
                if not df_form2.empty:
                    lista_p = []
                    jugadores_excel = df_sel_goals[df_sel_goals['player_nickname'] != "En contra"]['player_nickname'].values
                    for i in range(1, 30):
                        col_j_name = [c for c in df_form2.columns if c.startswith(f"{i} -") and 'jugador' in c.lower()]
                        col_p_name = [c for c in df_form2.columns if c.startswith(f"{i} -") and 'puntaje' in c.lower()]
                        if col_j_name:
                            cj, cp = col_j_name[0], col_p_name[0] if col_p_name else None
                            for _, row in df_form2.iterrows():
                                j_val = row[cj]
                                if pd.notna(j_val) and cp and pd.notna(row[cp]):
                                    try:
                                        lista_p.append({'jugador': str(j_val).strip(), 'puntaje': float(row[cp])})
                                    except:
                                        pass
                    if len(lista_p) > 0:
                        df_p_raw = pd.DataFrame(lista_p)
                        jugadores_form = df_p_raw[~df_p_raw['jugador'].str.contains('Jugador nuevo', case=False, na=False)]['jugador'].unique()
                        jugadores_faltantes = [j for j in jugadores_excel if j not in jugadores_form]
                        if len(jugadores_faltantes) > 0:
                            df_p_raw.loc[df_p_raw['jugador'].str.contains('Jugador nuevo', case=False, na=False), 'jugador'] = jugadores_faltantes[0]
                        df_form_puntaje_sel = df_p_raw.groupby('jugador', as_index=False)['puntaje'].mean()
                        df_form_puntaje_sel['puntaje'] = df_form_puntaje_sel['puntaje'].round(0)

            if not df_form_puntaje_sel.empty:
                df_form_puntaje_sel['jugador_clean'] = df_form_puntaje_sel['jugador'].astype(str).str.strip().str.lower()
                df_sel_goals['jugador_clean'] = df_sel_goals['player_nickname'].astype(str).str.strip().str.lower()
                df_sel_goals = pd.merge(df_sel_goals, df_form_puntaje_sel[['jugador_clean', 'puntaje']], on='jugador_clean', how='left')
            else:
                df_sel_goals['puntaje'] = ""
                
            df_naranja = df_sel_goals[df_sel_goals['equipo'] == 'Naranja'].reset_index(drop=True)
            df_celeste = df_sel_goals[df_sel_goals['equipo'] == 'Celeste'].reset_index(drop=True)
            
            max_len = max(len(df_naranja), len(df_celeste))
            alineacion_data = []
            for i in range(max_len):
                jugador_n = df_naranja.loc[i, 'player_nickname'] if i < len(df_naranja) else ""
                goles_n = df_naranja.loc[i, 'goles'] if (i < len(df_naranja) and 'goles' in df_naranja.columns) else 0
                puntaje_n = df_naranja.loc[i, 'puntaje'] if (i < len(df_naranja) and 'puntaje' in df_naranja.columns and pd.notna(df_naranja.loc[i, 'puntaje'])) else ""
                
                jugador_c = df_celeste.loc[i, 'player_nickname'] if i < len(df_celeste) else ""
                goles_c = df_celeste.loc[i, 'goles'] if (i < len(df_celeste) and 'goles' in df_celeste.columns) else 0
                puntaje_c = df_celeste.loc[i, 'puntaje'] if (i < len(df_celeste) and 'puntaje' in df_celeste.columns and pd.notna(df_celeste.loc[i, 'puntaje'])) else ""
                
                alineacion_data.append({
                    'Jugador (Naranja)': jugador_n, 'Goles (Naranja)': goles_n, 'Puntaje (Naranja)': puntaje_n,
                    'Jugador (Celeste)': jugador_c, 'Goles (Celeste)': goles_c, 'Puntaje (Celeste)': puntaje_c
                })
                
            st.dataframe(pd.DataFrame(alineacion_data), use_container_width=True, hide_index=True)
        else:
            st.info("No hay partidos cargados.")

    with tab2:
        st.subheader("Tabla General de Posiciones (2026)")
        if not df_tabla_general.empty:
            st.dataframe(
                df_tabla_general.rename(columns={
                    'player_nickname': 'Jugador', 'jugados': 'Jugados', 'ganados': 'Ganados',
                    'empatados': 'Empatados', 'perdidos': 'Perdidos', 'goles': 'Goles',
                    'puntos': 'Puntos', 'ultimos_partidos': 'Últimas Fechas'
                }),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No hay datos generales suficientes.")

    with tab3:
        st.subheader("💬 Realizar Encuesta Post-Partido")
        col_jugador_db_key = next((c for c in ['player_nickname', 'nickname', 'nombre'] if not df_players_db.empty and c in df_players_db.columns), None)
        lista_jugadores_db = sorted(df_players_db[col_jugador_db_key].dropna().unique().tolist()) if not df_players_db.empty and col_jugador_db_key else []
        
        if len(fechas_jugadas_all) > 0 and len(lista_jugadores_db) > 0:
            with st.form("form_votacion_usuario"):
                f_voto = st.selectbox(
                    "Selecciona la fecha del partido a evaluar:", 
                    fechas_jugadas_all,
                    format_func=lambda x: pd.to_datetime(x).strftime('%d de %B, %Y'),
                    key="select_fecha_voto"
                )
                evaluado_input = st.selectbox("¿A qué jugador querés calificar?", lista_jugadores_db, key="evaluado_usuario")
                puntaje_input = st.slider("Puntaje (1 al 10)", min_value=1, max_value=10, value=7, key="puntaje_usuario")
                comentario_input = st.text_area("Comentario / Justificación", key="comentario_usuario")
                
                enviar_voto = st.form_submit_button("Enviar Voto")
                if enviar_voto:
                    data_voto = {
                        "fecha": pd.to_datetime(f_voto).strftime('%Y-%m-%d'),
                        "votante": "Anónimo",
                        "evaluado": evaluado_input,
                        "puntaje": puntaje_input,
                        "comentario": comentario_input
                    }
                    try:
                        insert_data("encuestas", data_voto)
                        st.success("¡Tu voto ha sido registrado con éxito en Supabase!")
                        st.cache_data.clear()
                    except Exception as voto_err:
                        st.error(f"Error al registrar el voto: {voto_err}")
        else:
            st.warning("Faltan jugadores registrados en Supabase o fechas de partidos para habilitar la votación.")

    with tab4:
        st.subheader("Comentarios y Evaluaciones por Fecha")
        if len(fechas_jugadas_all) > 0:
            fecha_form_sel = st.selectbox(
                "Selecciona la fecha del partido:", 
                fechas_jugadas_all,
                format_func=lambda x: pd.to_datetime(x).strftime('%d de %B, %Y'),
                key="select_fecha_form_tab4"
            )
            
            df_encuestas_sql = run_query("encuestas")
            lista_comentarios_combinados = []
            
            if not df_encuestas_sql.empty and 'fecha' in df_encuestas_sql.columns:
                df_encuestas_sql['fecha'] = pd.to_datetime(df_encuestas_sql['fecha']).dt.date
                f_target = pd.to_datetime(fecha_form_sel).date()
                df_sql_match = df_encuestas_sql[
                    (df_encuestas_sql['fecha'] >= f_target - timedelta(days=1)) & 
                    (df_encuestas_sql['fecha'] <= f_target + timedelta(days=1))
                ]
                for _, row in df_sql_match.iterrows():
                    evaluado = row.get('evaluado', row.get('jugador', ''))
                    comentario = row.get('comentario', '')
                    puntaje = row.get('puntaje', '')
                    if pd.notna(comentario) and str(comentario).strip() != "":
                        lista_comentarios_combinados.append({
                            'Jugador': evaluado, 
                            'Puntaje': puntaje, 
                            'Comentario': comentario
                        })

            if not df_form_procesado.empty and col_fecha_form:
                f_target = pd.to_datetime(fecha_form_sel).date()
                df_form2 = df_form_procesado[
                    (df_form_procesado[col_fecha_form].dt.date >= f_target - timedelta(days=1)) & 
                    (df_form_procesado[col_fecha_form].dt.date <= f_target + timedelta(days=1))
                ].copy()
                
                if not df_form2.empty:
                    for i in range(1, 30):
                        col_j_name = [c for c in df_form2.columns if c.startswith(f"{i} -") and 'jugador' in c.lower()]
                        col_p_name = [c for c in df_form2.columns if c.startswith(f"{i} -") and 'puntaje' in c.lower()]
                        col_c_name = [c for c in df_form2.columns if c.startswith(f"{i} -") and 'comentario' in c.lower()]
                        if col_j_name and col_c_name:
                            cj, cp, cc = col_j_name[0], col_p_name[0] if col_p_name else None, col_c_name[0]
                            for _, row in df_form2.iterrows():
                                j_val, c_val = row[cj], row[cc]
                                p_val = row[cp] if cp else ""
                                if pd.notna(j_val) and pd.notna(c_val) and str(c_val).strip() != "":
                                    lista_comentarios_combinados.append({
                                        'Jugador': str(j_val).strip(), 
                                        'Puntaje': p_val if pd.notna(p_val) else "", 
                                        'Comentario': str(c_val).strip()
                                    })
            
            if len(lista_comentarios_combinados) > 0:
                df_comentarios_final = pd.DataFrame(lista_comentarios_combinados).drop_duplicates().reset_index(drop=True)
                st.dataframe(df_comentarios_final, use_container_width=True, hide_index=True)
            else:
                st.info("No hay comentarios registrados para esta fecha.")
        else:
            st.info("No hay fechas de partidos disponibles.")

    with tab5:
        st.subheader("Tabla de Loros 🦜 (Ausencias del año)")
        if not df_goals_date.empty and not df_players_db.empty:
            df_panel = []
            col_p_nick = next((c for c in ['player_nickname', 'nickname', 'nombre'] if c in df_players_db.columns), df_players_db.columns[0])
            for _, player in df_players_db.iterrows():
                for f in fechas_jugadas_all:
                    df_panel.append({'player_nickname': player[col_p_nick], 'fecha': f})
            df_panel = pd.DataFrame(df_panel)
            
            df_panel = pd.merge(df_panel, df_fecha_player[['player_nickname', 'equipo', 'fecha']], on=['player_nickname', 'fecha'], how='left')
            missing_counts = df_panel[df_panel['equipo'].isna()].groupby('player_nickname').size().reset_index(name='numero_ausencias')
            missing_counts = missing_counts.sort_values(by='numero_ausencias', ascending=False).rename(columns={'player_nickname': 'Jugador', 'numero_ausencias': 'Número de ausencias'})
            
            st.dataframe(missing_counts.head(10), use_container_width=True, hide_index=True)
        else:
            st.info("Faltan datos para calcular ausencias.")

    with tab6:
        st.subheader("⚙️ Panel de Administración")
        password = st.text_input("Contraseña de Administrador", type="password")
        
        if password == ADMIN_PASSWORD and password is not None:
            st.success("Acceso concedido.")
            
            col_jugador_db_key = next((c for c in ['player_nickname', 'nickname', 'nombre'] if not df_players_db.empty and c in df_players_db.columns), None)
            lista_jugadores_db = sorted(df_players_db[col_jugador_db_key].dropna().unique().tolist()) if not df_players_db.empty and col_jugador_db_key else []
            
            with st.form("carga_partido_admin"):
                st.markdown("### Registrar Alineación y Goles")
                f_admin = st.date_input("Fecha del Partido").strftime("%Y-%m-%d")
                
                if len(lista_jugadores_db) > 0:
                    jugador_input = st.selectbox("Apodo / Nickname del Jugador", lista_jugadores_db)
                else:
                    jugador_input = st.text_input("Apodo / Nickname del Jugador (No hay jugadores cargados)")
                    
                equipo_input = st.selectbox("Equipo", ["Celeste", "Naranja"])
                goles_input = st.number_input("Goles", min_value=0, step=1)
                
                if st.form_submit_button("Guardar en Supabase"):
                    if not jugador_input:
                        st.error("Debes seleccionar o ingresar un jugador.")
                    else:
                        nuevo_registro = {
                            "fecha": f_admin,
                            "player_nickname": jugador_input,
                            "equipo": equipo_input,
                            "goles": goles_input
                        }
                        try:
                            insert_data("alineaciones", nuevo_registro)
                            st.success("¡Partido guardado correctamente en Supabase!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as db_err:
                            st.error(f"Error al guardar: {db_err}")
            
            st.markdown("---")
            with st.form("nuevo_jugador_admin"):
                st.markdown("### Registrar Nuevo Jugador en la Base de Datos")
                nuevo_nick = st.text_input("Apodo / Nickname (ej: Charly)")
                nuevo_nombre = st.text_input("Nombre (opcional)")
                nuevo_apellido = st.text_input("Apellido (opcional)")
                
                if st.form_submit_button("Guardar Nuevo Jugador"):
                    if not nuevo_nick.strip():
                        st.error("El apodo / nickname no puede estar vacío.")
                    else:
                        data_jugador = {
                            "player_nickname": nuevo_nick.strip(),
                            "nombre": nuevo_nombre.strip(),
                            "apellido": nuevo_apellido.strip()
                        }
                        try:
                            insert_data("jugadores", data_jugador)
                            st.success(f"¡Jugador '{nuevo_nick}' agregado con éxito a Supabase!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as j_err:
                            st.error(f"Error al registrar jugador: {j_err}")
                            
        elif password:
            st.error("Contraseña incorrecta.")

except Exception as e:
    st.error(f"Error general en la aplicación: {e}")