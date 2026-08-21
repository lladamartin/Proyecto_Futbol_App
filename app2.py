import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# Configuración de la página
st.set_page_config(page_title="Jueves del Cordero Susurrador", layout="wide", page_icon="⚽")

# --- 1. INICIALIZACIÓN DE BASE DE DATOS LOCAL ---
def init_db():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS jugadores (id INTEGER PRIMARY KEY AUTOINCREMENT, nickname TEXT UNIQUE, nombre TEXT, apellido TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS partidos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS alineaciones (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, nickname TEXT, equipo TEXT, goles INTEGER DEFAULT 0, UNIQUE(fecha, nickname))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS encuestas (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, votante TEXT, evaluado TEXT, puntaje INTEGER, comentario TEXT)''')
    conn.commit()
    conn.close()

init_db()

def run_query(query, params=()):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def execute_query(query, params=()):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

st.title("⚽ Juevezzz 💋")
st.markdown("### Registro futbolístico - Jueves del Cordero Susurrador")

# --- CARGAR DATOS GENERALES DESDE SQLITE PARA LAS ESTADÍSTICAS ---
def cargar_datos_sql():
    df_alineaciones = run_query("SELECT fecha, nickname, equipo, goles FROM alineaciones")
    df_encuestas = run_query("SELECT fecha, votante, evaluado, puntaje, comentario FROM encuestas")
    df_jugadores = run_query("SELECT * FROM jugadores")
    if not df_alineaciones.empty:
        df_alineaciones['fecha'] = pd.to_datetime(df_alineaciones['fecha'])
    if not df_encuestas.empty:
        df_encuestas['fecha'] = pd.to_datetime(df_encuestas['fecha'])
    return df_alineaciones, df_encuestas, df_jugadores

df_goals_date, df_form_sql, df_players_db = cargar_datos_sql()

try:
    if df_goals_date.empty:
        st.warning("⚠️ No hay partidos cargados en la base de datos local. Ve al **Panel de Administración** para registrar fechas, alineaciones y goles.")
        fechas_jugadas_all = []
        fechas_jugadas_count = 0
        df_fecha_player = pd.DataFrame(columns=['fecha', 'nickname', 'equipo', 'goles'])
    else:
        df_fecha_player = df_goals_date.copy()
        df_fecha_player.columns = [col.lower() for col in df_fecha_player.columns]
        df_fecha_player['fecha'] = pd.to_datetime(df_fecha_player['fecha'])
        
        # --- PRE-PROCESAMIENTO GOLES Y PUNTOS ---
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

        # --- TABLA GENERAL (Estadísticas completas) ---
        df_filtered_year = df_fecha_player[df_fecha_player['fecha'].dt.year == year_key]
        df_tabla_general = df_filtered_year.groupby('nickname').agg(
            jugados=('fecha', 'nunique'),
            ganados=('resultado_label', lambda x: (x == 'G').sum()),
            empatados=('resultado_label', lambda x: (x == 'E').sum()),
            perdidos=('resultado_label', lambda x: (x == 'P').sum()),
            goles=('goles', 'sum'),
            puntos=('puntos', 'sum')
        ).reset_index()
        
        df_rdo_ultimos = df_fecha_player[df_fecha_player['fecha'] >= fecha_last_six].sort_values('fecha')
        df_rdo_ultimos = df_rdo_ultimos.groupby('nickname')['resultado_label'].apply(lambda x: " ".join(x)).reset_index()
        df_rdo_ultimos.rename(columns={'resultado_label': 'ultimos_partidos'}, inplace=True)
        
        df_tabla_general = pd.merge(df_tabla_general, df_rdo_ultimos, on='nickname', how='left')
        df_tabla_general = df_tabla_general.sort_values(by='puntos', ascending=False)

    # --- TABS VISUALES PRINCIPALES ---
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "⚽ Resultados por Fecha", 
        "📊 Resumen y Tabla", 
        "💬 Encuesta (Votar)", 
        "📋 Resultados de Encuestas", 
        "🦜 Loros", 
        "⚙️ Admin"
    ])

    with tab1:
        st.subheader("Resultado por Fecha Seleccionada")
        if len(fechas_jugadas_all) > 0:
            fecha_seleccionada = st.selectbox(
                "Elige la fecha del partido:", 
                fechas_jugadas_all, 
                format_func=lambda x: pd.to_datetime(x).strftime('%d de %B, %Y')
            )
            
            df_sel_goals = df_fecha_player[df_fecha_player['fecha'] == fecha_seleccionada].copy()
            df_sel_res = df_sel_goals.groupby('equipo')['goles'].sum().reset_index()
            
            celeste_goles = df_sel_res.loc[df_sel_res['equipo'] == 'Celeste', 'goles'].values[0] if 'Celeste' in df_sel_res['equipo'].values else 0
            naranja_goles = df_sel_res.loc[df_sel_res['equipo'] == 'Naranja', 'goles'].values[0] if 'Naranja' in df_sel_res['equipo'].values else 0
            
            df_resultado_final = pd.DataFrame({'Celeste': [celeste_goles], 'Naranja': [naranja_goles]})
            st.dataframe(df_resultado_final, use_container_width=True, hide_index=True)
            st.markdown(f"**Fecha analizada:** {pd.to_datetime(fecha_seleccionada).strftime('%d de %B, %Y')}")
            
            st.markdown("---")
            st.subheader("Alineación y Puntaje Promedio")
            
            df_puntajes_fecha = run_query("""
                SELECT evaluado as jugador, ROUND(AVG(puntaje), 1) as puntaje 
                FROM encuestas WHERE DATE(fecha) = DATE(?) GROUP BY evaluado
            """, (pd.to_datetime(fecha_seleccionada).strftime('%Y-%m-%d'),))
            
            if not df_puntajes_fecha.empty:
                df_puntajes_fecha['jugador_clean'] = df_puntajes_fecha['jugador'].astype(str).str.strip().str.lower()
                df_sel_goals['jugador_clean'] = df_sel_goals['nickname'].astype(str).str.strip().str.lower()
                df_sel_goals = pd.merge(df_sel_goals, df_puntajes_fecha[['jugador_clean', 'puntaje']], on='jugador_clean', how='left')
            else:
                df_sel_goals['puntaje'] = ""
                
            df_naranja = df_sel_goals[df_sel_goals['equipo'] == 'Naranja'].reset_index(drop=True)
            df_celeste = df_sel_goals[df_sel_goals['equipo'] == 'Celeste'].reset_index(drop=True)
            
            max_len = max(len(df_naranja), len(df_celeste))
            alineacion_data = []
            for i in range(max_len):
                jugador_n = df_naranja.loc[i, 'nickname'] if i < len(df_naranja) else ""
                puntaje_n = df_naranja.loc[i, 'puntaje'] if (i < len(df_naranja) and 'puntaje' in df_naranja.columns and pd.notna(df_naranja.loc[i, 'puntaje'])) else ""
                jugador_c = df_celeste.loc[i, 'nickname'] if i < len(df_celeste) else ""
                puntaje_c = df_celeste.loc[i, 'puntaje'] if (i < len(df_celeste) and 'puntaje' in df_celeste.columns and pd.notna(df_celeste.loc[i, 'puntaje'])) else ""
                
                alineacion_data.append({
                    'Jugador (Naranja)': jugador_n, 'Puntaje (Naranja)': puntaje_n,
                    'Jugador (Celeste)': jugador_c, 'Puntaje (Celeste)': puntaje_c
                })
                
            st.dataframe(pd.DataFrame(alineacion_data), use_container_width=True, hide_index=True)
        else:
            st.info("No hay fechas disponibles para mostrar.")

    with tab2:
        st.subheader("Tabla General de Posiciones (2026)")
        if not df_tabla_general.empty:
            st.dataframe(
                df_tabla_general.rename(columns={
                    'nickname': 'Jugador',
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
        else:
            st.info("No hay registros suficientes para armar la tabla general.")

    with tab3:
        st.subheader("📝 Realizar Encuesta Post-Partido")
        if len(fechas_jugadas_all) > 0:
            f_enc = st.selectbox("Selecciona la fecha del partido a evaluar:", fechas_jugadas_all, format_func=lambda x: pd.to_datetime(x).strftime('%d de %B, %Y'), key="select_voto")
            jugadores_fecha = run_query("SELECT nickname FROM alineaciones WHERE DATE(fecha)=DATE(?)", (pd.to_datetime(f_enc).strftime('%Y-%m-%d'),))['nickname'].tolist()
            
            if len(jugadores_fecha) > 0:
                with st.form("form_encuesta_app"):
                    votante = st.selectbox("¿Quién sos?", jugadores_fecha)
                    evaluado = st.selectbox("¿A qué jugador evaluás?", [j for j in jugadores_fecha if j != votante])
                    puntaje = st.slider("Puntaje (1 al 10)", 1, 10, 7)
                    comentario = st.text_area("Comentario (opcional)")
                    
                    enviar = st.form_submit_button("Enviar Evaluación")
                    if enviar:
                        execute_query("INSERT INTO encuestas (fecha, votante, evaluado, puntaje, comentario) VALUES (?, ?, ?, ?, ?)",
                                      (pd.to_datetime(f_enc).strftime('%Y-%m-%d'), votante, evaluado, puntaje, comentario))
                        st.success("¡Evaluación guardada con éxito en la base de datos!")
            else:
                st.warning("No hay jugadores cargados en la alineación de esta fecha para poder votar.")
        else:
            st.info("No hay fechas disponibles.")

    with tab4:
        st.subheader("📋 Resultados y Comentarios de Encuestas por Fecha")
        if len(fechas_jugadas_all) > 0:
            f_res = st.selectbox("Selecciona la fecha para ver los resultados de las encuestas:", fechas_jugadas_all, format_func=lambda x: pd.to_datetime(x).strftime('%d de %B, %Y'), key="select_resultados_encuesta")
            
            df_coments = run_query("""
                SELECT votante as Votante, evaluado as Evaluado, puntaje as Puntaje, comentario as Comentario 
                FROM encuestas WHERE DATE(fecha) = DATE(?) AND (comentario != '' OR puntaje IS NOT NULL)
            """, (pd.to_datetime(f_res).strftime('%Y-%m-%d'),))
            
            if not df_coments.empty:
                st.dataframe(df_coments, use_container_width=True, hide_index=True)
            else:
                st.info("No hay encuestas ni comentarios registrados para esta fecha en particular.")
        else:
            st.info("No hay fechas registradas.")

    with tab5:
        st.subheader("Tabla de Loros 🦜 (Ausencias del año)")
        if len(fechas_jugadas_all) > 0 and not df_players_db.empty:
            df_panel = []
            for _, player in df_players_db.iterrows():
                p_nick = player.get('nickname') or player.get('Player_nickname')
                for f in fechas_jugadas_all:
                    df_panel.append({'nickname': p_nick, 'fecha': f})
            df_panel = pd.DataFrame(df_panel)
            
            if not df_panel.empty:
                df_panel = pd.merge(df_panel, df_fecha_player[['nickname', 'equipo', 'fecha']], on=['nickname', 'fecha'], how='left')
                missing_counts = df_panel[df_panel['equipo'].isna()].groupby('nickname').size().reset_index(name='numero_ausencias')
                missing_counts = missing_counts.sort_values(by='numero_ausencias', ascending=False).rename(columns={'nickname': 'Jugador', 'numero_ausencias': 'Número de ausencias'})
                st.dataframe(missing_counts.head(15), use_container_width=True, hide_index=True)
            else:
                st.info("No hay suficientes datos procesados para calcular ausencias.")
        else:
            st.info("Faltan jugadores o fechas cargadas para calcular los loros.")

    with tab6:
        st.subheader("⚙️ Panel de Administración")
        password = st.text_input("Contraseña de Administrador", type="password")
        
        if password == "cordero2026":
            st.success("Acceso concedido.")
            with st.form("carga_partido_admin"):
                f_admin = st.date_input("Fecha del Partido").strftime("%Y-%m-%d")
                jugs_db = run_query("SELECT nickname FROM jugadores")['nickname'].tolist()
                
                if len(jugs_db) == 0:
                    st.warning("⚠️ Primero registra jugadores abajo.")
                
                naranjas = st.multiselect("Equipo Naranja", jugs_db)
                celestes = st.multiselect("Equipo Celeste", jugs_db)
                
                st.markdown("**Carga de Goles por Jugador:**")
                goles_n = {j: st.number_input(f"Goles {j} (Naranja)", 0, 10, 0, key=f"gn_{j}") for j in naranjas}
                goles_c = {j: st.number_input(f"Goles {j} (Celeste)", 0, 10, 0, key=f"gc_{j}") for j in celestes}
                
                if st.form_submit_button("Guardar Partido y Alineación"):
                    execute_query("INSERT OR IGNORE INTO partidos (fecha) VALUES (?)", (f_admin,))
                    for n, g in goles_n.items():
                        execute_query("INSERT OR REPLACE INTO alineaciones (fecha, nickname, equipo, goles) VALUES (?, ?, ?, ?)", (f_admin, n, 'Naranja', g))
                    for c, g in goles_c.items():
                        execute_query("INSERT OR REPLACE INTO alineaciones (fecha, nickname, equipo, goles) VALUES (?, ?, ?, ?)", (f_admin, c, 'Celeste', g))
                    st.success(f"¡Partido del {f_admin} guardado correctamente!")
            
            with st.form("nuevo_jugador_admin"):
                st.markdown("### Registrar Nuevo Jugador")
                nick = st.text_input("Apodo / Nickname (ej: Maxi Pintureria)")
                nombre = st.text_input("Nombre")
                apellido = st.text_input("Apellido")
                if st.form_submit_button("Guardar Jugador"):
                    if nick:
                        try:
                            execute_query("INSERT INTO jugadores (nickname, nombre, apellido) VALUES (?, ?, ?)", (nick, nombre, apellido))
                            st.success(f"Jugador {nick} registrado con éxito.")
                        except:
                            st.error("El apodo ya existe en la base de datos.")
        elif password != "":
            st.error("Contraseña incorrecta.")

except Exception as e:
    st.error(f"Error al procesar la aplicación: {e}")