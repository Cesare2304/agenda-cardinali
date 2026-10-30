import sqlite3
import datetime
import os
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Agenda Cardinali",
    page_icon="📅",
    layout="wide"
)

NOME_DITTA = 'Agenda Cardinali'

def get_db_path():
    appdata_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'AgendaCardinali')
    try:
        os.makedirs(appdata_dir, exist_ok=True)
        return os.path.join(appdata_dir, 'agenda.db')
    except Exception:
        return 'agenda.db'

DB_PATH = get_db_path()

def inizializza_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appuntamenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titolo TEXT NOT NULL,
            cliente TEXT,
            tecnico TEXT,
            telefono TEXT,
            categoria TEXT,
            urgenza TEXT DEFAULT 'Normale',
            data TEXT NOT NULL,
            ora TEXT NOT NULL,
            scadenza TEXT,
            note TEXT,
            gruppo TEXT DEFAULT 'generale',
            dettaglio_interventi TEXT,
            nota_chiusura TEXT,
            stato TEXT DEFAULT 'Attivo'
        )
    ''')
    
    for col, col_type in [("gruppo", "TEXT DEFAULT 'generale'"), ("dettaglio_interventi", "TEXT"), ("nota_chiusura", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE appuntamenti ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_azienda TEXT NOT NULL,
            referente TEXT,
            telefono TEXT,
            email TEXT,
            indirizzo TEXT,
            note TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tecnici (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            specializzazione TEXT,
            telefono TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gruppi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_gruppo TEXT NOT NULL UNIQUE
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            gruppo TEXT NOT NULL
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM gruppi")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO gruppi (nome_gruppo) VALUES ('admin')")
        cursor.execute("INSERT INTO gruppi (nome_gruppo) VALUES ('software')")

    cursor.execute("SELECT COUNT(*) FROM utenti")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO utenti (username, password, gruppo) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
        cursor.execute("INSERT INTO utenti (username, password, gruppo) VALUES (?, ?, ?)", ("software", "soft123", "software"))
    conn.commit()
    conn.close()

inizializza_db()

# Gestione Autenticazione Utenti / Gruppi
if 'autenticato' not in st.session_state:
    st.session_state.autenticato = False
    st.session_state.utente_corrente = None
    st.session_state.gruppo_corrente = None

if not st.session_state.autenticato:
    st.title(f"🔐 Accesso Riservato - {NOME_DITTA}")
    with st.form("form_login"):
        username_input = st.text_input("Nome Utente")
        password_input = st.text_input("Password", type="password")
        submit_login = st.form_submit_button("Accedi al Gestionale")
        
        if submit_login:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT gruppo FROM utenti WHERE username = ? AND password = ?", (username_input, password_input))
            res = cursor.fetchone()
            conn.close()
            
            if res:
                st.session_state.autenticato = True
                st.session_state.utente_corrente = username_input
                st.session_state.gruppo_corrente = res[0]
                st.success("Accesso effettuato con successo!")
                st.rerun()
            else:
                st.error("Credenziali non valide. Riprova.")
    st.stop()

def get_clienti():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT nome_azienda FROM clienti ORDER BY nome_azienda ASC')
    res = [r[0] for r in cursor.fetchall()]
    conn.close()
    return res

def get_tecnici():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT nome FROM tecnici ORDER BY nome ASC')
    res = [r[0] for r in cursor.fetchall()]
    conn.close()
    return res

def get_gruppi_list():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT nome_gruppo FROM gruppi ORDER BY nome_gruppo ASC')
    res = [r[0] for r in cursor.fetchall()]
    conn.close()
    return res if res else ["generale", "admin"]

# ==================== MENU LATERALE FISSO ====================
st.sidebar.title(f"📅 {NOME_DITTA}")
st.sidebar.markdown(f"👤 Utente: **{st.session_state.utente_corrente}** (*{st.session_state.gruppo_corrente}*)")
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.autenticato = False
    st.session_state.utente_corrente = None
    st.session_state.gruppo_corrente = None
    st.rerun()

st.sidebar.markdown("---")

if st.sidebar.button("🔄 Aggiorna / Sincronizza", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")

# Selezione Pagine con Radio Button nativo (affidabile e senza schermate bianche)
pagine_disponibili = ["📅 Planning Principale", "📁 Archivio Storico", "👥 Gestione Clienti", "🛠️ Gestione Tecnici"]
if st.session_state.gruppo_corrente == "admin":
    pagine_disponibili.append("🏢 Gestione Gruppi e Utenti")

menu = st.sidebar.radio("Navigazione", pagine_disponibili)

st.sidebar.markdown("---")

dim_testo = st.sidebar.slider("Dimensione testo Planning (px)", min_value=12, max_value=30, value=16)
dim_titoli = st.sidebar.slider("Dimensione Titoli (px)", min_value=20, max_value=50, value=32)

st.markdown(f"""
    <style>
    .planning-card {{
        font-size: {dim_testo}px !important;
        padding: 10px 12px;
        border-radius: 6px;
        box-sizing: border-box;
        height: 100%;
        width: 100%;
    }}
    .planning-card div {{
        font-size: {dim_testo}px !important;
    }}
    h1 {{
        font-size: {dim_titoli}px !important;
    }}
    .stButton button {{
        width: 100%;
        border-radius: 4px;
        padding: 4px 2px;
        font-size: 12px;
        margin-bottom: 2px;
    }}
    </style>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
if st.session_state.gruppo_corrente == "admin":
    cursor.execute("SELECT COUNT(*) FROM appuntamenti WHERE urgenza = 'Urgente' AND (stato = 'Attivo' OR stato IS NULL)")
else:
    cursor.execute("SELECT COUNT(*) FROM appuntamenti WHERE urgenza = 'Urgente' AND (stato = 'Attivo' OR stato IS NULL) AND gruppo = ?", (st.session_state.gruppo_corrente,))
count_urgenti = cursor.fetchone()[0]
conn.close()

if count_urgenti > 0:
    st.sidebar.error(f"⚠️ Interventi Urgenti: **{count_urgenti}**")

# ==================== SEZIONE 1: PLANNING ====================
if menu == "📅 Planning Principale":
    st.title("📅 Planning Attività e Urgenze")
    
    with st.expander("➕ Inserisci Nuovo Appuntamento / Attività", expanded=False):
        with st.form("form_nuovo_app", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                titolo = st.text_input("Titolo Attività *")
                clienti_list = get_clienti()
                cliente = st.selectbox("Cliente", clienti_list if clienti_list else ["Nessun cliente registrato"])
                telefono = st.text_input("Telefono / Riferimento")
            with col2:
                tecnici_list = get_tecnici()
                tecnico = st.selectbox("Tecnico Assegnato", tecnici_list if tecnici_list else ["Nessun tecnico registrato"])
                urgenza = st.selectbox("Urgenza", ["Urgente", "Normale", "Meno urgente"], index=1)
                categoria = st.selectbox("Categoria", ["Lavoro", "Cliente", "Fornitore", "Manutenzione", "Altro"])
            with col3:
                data_app = st.date_input("Data Intervento")
                ora_app = st.text_input("Ora (es. 09:00)", "09:00")
                scadenza_app = st.date_input("Data Scadenza")
                
                gruppi_disponibili = get_gruppi_list()
                gruppo_assegnato = st.selectbox("Gruppo di Competenza", gruppi_disponibili, index=gruppi_disponibili.index(st.session_state.gruppo_corrente) if st.session_state.gruppo_corrente in gruppi_disponibili else 0)
                
            note = st.text_input("Note aggiuntive")
            salva_btn = st.form_submit_button("Salva Appuntamento")
            
            if salva_btn:
                if not titolo:
                    st.warning("Inserisci almeno il titolo dell'attività.")
                else:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO appuntamenti (titolo, cliente, tecnico, telefono, categoria, urgenza, data, ora, scadenza, note, gruppo, stato)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Attivo')
                    ''', (titolo, cliente, tecnico, telefono, categoria, urgenza, data_app.strftime('%Y-%m-%d'), ora_app, scadenza_app.strftime('%Y-%m-%d'), note, gruppo_assegnato))
                    conn.commit()
                    conn.close()
                    st.success("Attività salvata con successo!")
                    st.rerun()

    st.divider()
    
    f_col1, f_col2, f_col3 = st.columns([2, 2, 1])
    with f_col1:
        ricerca_testo = st.text_input("🔍 Cerca per titolo, cliente o tecnico")
    with f_col2:
        filtro_urgenza = st.selectbox("Filtra per Urgenza", ["Tutti", "Urgente", "Normale", "Meno urgente"])
    with f_col3:
        st.markdown("<br>", unsafe_allow_html=True)
        conn = sqlite3.connect(DB_PATH)
        if st.session_state.gruppo_corrente == "admin":
            df_export = pd.read_sql_query("SELECT titolo, cliente, tecnico, categoria, urgenza, data, ora, scadenza, note, dettaglio_interventi, nota_chiusura, gruppo, stato FROM appuntamenti WHERE stato = 'Attivo' OR stato IS NULL", conn)
        else:
            df_export = pd.read_sql_query("SELECT titolo, cliente, tecnico, categoria, urgenza, data, ora, scadenza, note, dettaglio_interventi, nota_chiusura, gruppo, stato FROM appuntamenti WHERE (stato = 'Attivo' OR stato IS NULL) AND gruppo = ?", conn, params=(st.session_state.gruppo_corrente,))
        conn.close()
        csv_data = df_export.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Esporta Excel",
            data=csv_data,
            file_name="interventi_attivi_agenda.csv",
            mime="text/csv",
            use_container_width=True
        )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if st.session_state.gruppo_corrente == "admin":
        query = """
            SELECT id, data, ora, titolo, cliente, tecnico, categoria, urgenza, scadenza, note, dettaglio_interventi, nota_chiusura, gruppo
            FROM appuntamenti 
            WHERE (stato = 'Attivo' OR stato IS NULL)
        """
        params = []
    else:
        query = """
            SELECT id, data, ora, titolo, cliente, tecnico, categoria, urgenza, scadenza, note, dettaglio_interventi, nota_chiusura, gruppo
            FROM appuntamenti 
            WHERE (stato = 'Attivo' OR stato IS NULL) AND gruppo = ?
        """
        params = [st.session_state.gruppo_corrente]
    
    if ricerca_testo:
        query += " AND (titolo LIKE ? OR cliente LIKE ? OR tecnico LIKE ?)"
        p = f"%{ricerca_testo}%"
        params.extend([p, p, p])
        
    if filtro_urgenza != "Tutti":
        query += " AND urgenza = ?"
        params.append(filtro_urgenza)
        
    query += """
        ORDER BY 
        CASE urgenza 
            WHEN 'Urgente' THEN 1 
            WHEN 'Normale' THEN 2 
            WHEN 'Meno urgente' THEN 3 
            ELSE 4 
        END ASC, data ASC, ora ASC
    """
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    if rows:
        for r in rows:
            urg = r[7]
            if urg == "Urgente":
                bg_color, border_color, col_colore = "rgba(229, 115, 115, 0.15)", "#E57373", "🔴"
            elif urg == "Meno urgente":
                bg_color, border_color, col_colore = "rgba(129, 19
