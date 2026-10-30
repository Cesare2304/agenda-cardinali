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
    
    # Aggiunge in sicurezza le colonne se il database esiste già senza di esse
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
        CREATE TABLE IF NOT EXISTS utenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            gruppo TEXT NOT NULL
        )
    ''')
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
        username_input = st.text_input("Nome Utente / Gruppo")
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

if 'menu_selezionato' not in st.session_state:
    st.session_state.menu_selezionato = "📅 Planning Principale"

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

if st.sidebar.button("📅 Planning Principale", use_container_width=True):
    st.session_state.menu_selezionato = "📅 Planning Principale"
if st.sidebar.button("📁 Archivio Storico", use_container_width=True):
    st.session_state.menu_selezionato = "📁 Archivio Storico"
if st.sidebar.button("👥 Gestione Clienti", use_container_width=True):
    st.session_state.menu_selezionato = "👥 Gestione Clienti"
if st.sidebar.button("🛠️ Gestione Tecnici", use_container_width=True):
    st.session_state.menu_selezionato = "🛠️ Gestione Tecnici"

st.sidebar.markdown("---")

dim_testo = st.sidebar.slider("Dimensione testo Planning (px)", min_value=12, max_value=30, value=16)
dim_titoli = st.sidebar.slider("Dimensione Titoli (px)", min_value=20, max_value=50, value=32)

st.markdown(f"""
    <style>
    .planning-card {{
        font-size: {dim_testo}px !important;
    }}
    .planning-card div {{
        font-size: {dim_testo}px !important;
    }}
    h1 {{
        font-size: {dim_titoli}px !important;
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

menu = st.session_state.menu_selezionato

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
                    ''', (titolo, cliente, tecnico, telefono, categoria, urgenza, data_app.strftime('%Y-%m-%d'), ora_app, scadenza_app.strftime('%Y-%m-%d'), note, st.session_state.gruppo_corrente))
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
            df_export = pd.read_sql_query("SELECT titolo, cliente, tecnico, categoria, urgenza, data, ora, scadenza, note, dettaglio_interventi, nota_chiusura, stato FROM appuntamenti WHERE stato = 'Attivo' OR stato IS NULL", conn)
        else:
            df_export = pd.read_sql_query("SELECT titolo, cliente, tecnico, categoria, urgenza, data, ora, scadenza, note, dettaglio_interventi, nota_chiusura, stato FROM appuntamenti WHERE (stato = 'Attivo' OR stato IS NULL) AND gruppo = ?", conn, params=(st.session_state.gruppo_corrente,))
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
            SELECT id, data, ora, titolo, cliente, tecnico, categoria, urgenza, scadenza, note, dettaglio_interventi, nota_chiusura
            FROM appuntamenti 
            WHERE (stato = 'Attivo' OR stato IS NULL)
        """
        params = []
    else:
        query = """
            SELECT id, data, ora, titolo, cliente, tecnico, categoria, urgenza, scadenza, note, dettaglio_interventi, nota_chiusura
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
                bg_color, border_color, col_colore = "rgba(129, 199, 132, 0.15)", "#81C784", "🟢"
            else:
                bg_color, border_color, col_colore = "rgba(207, 216, 220, 0.15)", "#CFD8DC", "⚪"

            col_card, col_btns = st.columns([4, 1])
            with col_card:
                st.markdown(f"""
                    <div class="planning-card" style="background-color: {bg_color}; border-left: 6px solid {border_color}; padding: 14px; border-radius: 6px; margin-bottom: 10px;">
                        <div><b>{col_colore} Cliente:</b> {r[4]} &nbsp;|&nbsp; <b>Titolo:</b> {r[3]} &nbsp;|&nbsp; <b>Data:</b> {r[1]} alle {r[2]}</div>
                        <div style="margin-top: 4px; opacity: 0.9;"><b>Tecnico:</b> {r[5]} &nbsp;|&nbsp; <b>Urgenza:</b> {r[7]} &nbsp;|&nbsp; <b>Scadenza:</b> {r[8]}</div>
                        <div style="margin-top: 4px; opacity: 0.8; font-style: italic;">Note: {r[9]}</div>
                        <div style="margin-top: 4px; color: #1976D2;"><b>Interventi fatti:</b> {r[10] or 'Nessun dettaglio inserito'}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col_btns:
                if st.button("🛠️ Interventi", key=f"int_{r[0]}", use_container_width=True):
                    st.session_state[f"open_interventi_{r[0]}"] = not st.session_state.get(f"open_interventi_{r[0]}", False)
                if st.button("✔️ Chiudi", key=f"chiudi_{r[0]}", use_container_width=True):
                    st.session_state[f"open_chiusura_{r[0]}"] = True
                if st.button("✏️ Modifica", key=f"mod_{r[0]}", use_container_width=True):
                    st.session_state[f"edit_app_{r[0]}"] = True
                if st.button("🗑️ Elimina", key=f"del_{r[0]}", use_container_width=True):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM appuntamenti WHERE id = ?", (r[0],))
                    conn.commit()
                    conn.close()
                    st.rerun()

            if st.session_state.get(f"open_interventi_{r[0]}", False):
                with st.form(f"form_int_fatti_{r[0]}"):
                    st.subheader(f"Gestione Interventi Fatti - #{r[0]}")
                    nuovo_intervento_testo = st.text_area("Aggiungi intervento fatto / lavorazione", value=r[10] or "")
                    c_d1, c_d2 = st.columns(2)
                    with c_d1:
                        data_intervento_fatto = st.date_input("Data Intervento Fatto", value=datetime.date.today())
                    with c_d2:
                        ora_intervento_fatto = st.text_input("Ora Intervento Fatto", value="09:00")
                    
                    if st.form_submit_button("Salva Dettaglio Interventi"):
                        stringa_aggiornata = f"[{data_intervento_fatto} {ora_intervento_fatto}] {nuovo_intervento_testo}"
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE appuntamenti SET dettaglio_interventi = ? WHERE id = ?", (stringa_aggiornata, r[0]))
                        conn.commit()
                        conn.close()
                        st.session_state[f"open_interventi_{r[0]}"] = False
                        st.success("Interventi salvati!")
                        st.rerun()

            if st.session_state.get(f"open_chiusura_{r[0]}", False):
                with st.form(f"form_chiusura_{r[0]}"):
                    st.subheader(f"Chiusura Intervento #{r[0]}")
                    nota_fin = st.text_area("Nota finale di chiusura *")
                    if st.form_submit_button("Conferma e Archivia"):
                        if not nota_fin:
                            st.warning("Inserisci una nota finale di chiusura.")
                        else:
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE appuntamenti SET stato = 'Chiuso', nota_chiusura = ? WHERE id = ?", (nota_fin, r[0]))
                            conn.commit()
                            conn.close()
                            st.session_state[f"open_chiusura_{r[0]}"] = False
                            st.success("Intervento chiuso e archiviato con successo!")
                            st.rerun()

            if st.session_state.get(f"edit_app_{r[0]}", False):
                with st.form(f"form_mod_app_{r[0]}"):
                    st.subheader(f"Modifica Intervento #{r[0]}")
                    new_titolo = st.text_input("Titolo", value=r[3])
                    
                    c_list = get_clienti()
