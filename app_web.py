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

if 'menu_selezionato' not in st.session_state:
    st.session_state.menu_selezionato = "📅 Planning Principale"

# ==================== MENU LATERALE ULTRA COMPATTO ====================
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

st.sidebar.subheader("📌 Navigazione")
if st.sidebar.button("📅 Planning Principale", use_container_width=True):
    st.session_state.menu_selezionato = "📅 Planning Principale"
if st.sidebar.button("📁 Archivio Storico", use_container_width=True):
    st.session_state.menu_selezionato = "📁 Archivio Storico"
if st.sidebar.button("👥 Gestione Clienti", use_container_width=True):
    st.session_state.menu_selezionato = "👥 Gestione Clienti"
if st.sidebar.button("🛠️ Gestione Tecnici", use_container_width=True):
    st.session_state.menu_selezionato = "🛠️ Gestione Tecnici"

if st.session_state.gruppo_corrente == "admin":
    if st.sidebar.button("🏢 Gestione Gruppi e Utenti", use_container_width=True):
        st.session_state.menu_selezionato = "🏢 Gestione Gruppi e Utenti"

st.sidebar.markdown("---")

dim_testo = st.sidebar.slider("Dimensione testo Planning (px)", min_value=12, max_value=30, value=16)
dim_titoli = st.sidebar.slider("Dimensione Titoli (px)", min_value=20, max_value=50, value=32)

st.markdown(f"""
    <style>
    /* Rimozione spazi e margini aggressivi nel menu di sinistra di Streamlit */
    [data-testid="stSidebar"] div.block-container {{
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        gap: 0.2rem !important;
    }}
    [data-testid="stSidebar"] hr {{
        margin: 0.4rem 0 !important;
    }}
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
        padding: 2px 2px;
        font-size: 12px;
        margin-bottom: 1px;
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
                bg_color, border_color, col_colore = "rgba(129, 199, 132, 0.15)", "#81C784", "🟢"
            else:
                bg_color, border_color, col_colore = "rgba(207, 216, 220, 0.15)", "#CFD8DC", "⚪"

            col_card, col_buttons = st.columns([10, 1.5])
            with col_card:
                st.markdown(f"""
                    <div class="planning-card" style="background-color: {bg_color}; border-left: 6px solid {border_color};">
                        <div><b>{col_colore} Data:</b> {r[1]} alle {r[2]} &nbsp;|&nbsp; <b>Titolo:</b> {r[3]} &nbsp;|&nbsp; <b>Cliente:</b> {r[4]} &nbsp;|&nbsp; <b>Gruppo:</b> <i>{r[12]}</i></div>
                        <div style="margin-top: 4px; opacity: 0.9;"><b>Tecnico:</b> {r[5]} &nbsp;|&nbsp; <b>Urgenza:</b> {r[7]} &nbsp;|&nbsp; <b>Scadenza:</b> {r[8]}</div>
                        <div style="margin-top: 4px; opacity: 0.8; font-style: italic;">Note: {r[9]}</div>
                        <div style="margin-top: 4px; color: #1976D2;"><b>Interventi fatti:</b><br>{r[10].replace('\n', '<br>') if r[10] else 'Nessun dettaglio inserito'}</div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col_buttons:
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

            # Sezione per gestire i singoli interventi con Inizio e Fine
            if st.session_state.get(f"open_interventi_{r[0]}", False):
                with st.form(f"form_int_fatti_{r[0]}"):
                    st.subheader(f"Gestione Interventi Fatti - #{r[0]}")
                    st.markdown("Inserisci i dettagli del singolo intervento con data e ora di inizio e fine:")
                    
                    col_i1, col_i2, col_i3 = st.columns(3)
                    with col_i1:
                        data_inz = st.date_input("Data Inizio", value=datetime.date.today(), key=f"dinz_{r[0]}")
                        ora_inz = st.text_input("Ora Inizio (es. 08:30)", value="08:30", key=f"oinz_{r[0]}")
                    with col_i2:
                        data_fin = st.date_input("Data Fine", value=datetime.date.today(), key=f"dfin_{r[0]}")
                        ora_fin = st.text_input("Ora Fine (es. 12:30)", value="12:30", key=f"ofin_{r[0]}")
                    with col_i3:
                        modalita = st.selectbox("Azione", ["Aggiungi nuovo intervento", "Sovrascrivi tutto"], key=f"mod_int_{r[0]}")
                    
                    testo_lav = st.text_area("Descrizione della lavorazione eseguita", key=f"tlav_{r[0]}")
                    
                    if st.form_submit_button("Salva Intervento"):
                        nuova_riga = f"• [Inizio: {data_inz} {ora_inz} | Fine: {data_fin} {ora_fin}] {testo_lav}"
                        
                        if modalita == "Sovrascrivi tutto" or not r[10]:
                            stringa_aggiornata = nuova_riga
                        else:
                            stringa_aggiornata = r[10] + "\n" + nuova_riga
                            
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE appuntamenti SET dettaglio_interventi = ? WHERE id = ?", (stringa_aggiornata, r[0]))
                        conn.commit()
                        conn.close()
                        st.session_state[f"open_interventi_{r[0]}"] = False
                        st.success("Intervento registrato con successo!")
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
                    try:
                        c_idx = c_list.index(r[4]) if r[4] in c_list else 0
                    except:
                        c_idx = 0
                    new_cliente = st.selectbox("Cliente", c_list if c_list else [""], index=c_idx)
                    
                    t_list = get_tecnici()
                    try:
                        t_idx = t_list.index(r[5]) if r[5] in t_list else 0
                    except:
                        t_idx = 0
                    new_tecnico = st.selectbox("Tecnico", t_list if t_list else [""], index=t_idx)
                    
                    urg_list = ["Urgente", "Normale", "Meno urgente"]
                    new_urg = st.selectbox("Urgenza", urg_list, index=urg_list.index(r[7]) if r[7] in urg_list else 1)
                    new_note = st.text_input("Note", value=r[9])
                    
                    if st.form_submit_button("Salva Modifiche"):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE appuntamenti SET titolo=?, cliente=?, tecnico=?, urgenza=?, note=? WHERE id=?",
                                       (new_titolo, new_cliente, new_tecnico, new_urg, new_note, r[0]))
                        conn.commit()
                        conn.close()
                        st.session_state[f"edit_app_{r[0]}"] = False
                        st.success("Modifiche salvate!")
                        st.rerun()

            st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
    else:
        st.info("Nessuna attività attiva trovata.")

# ==================== SEZIONE 2: ARCHIVIO STORICO ====================
elif menu == "📁 Archivio Storico":
    st.title("📁 Archivio Storico Interventi")
    
    arc_h1, arc_h2 = st.columns([4, 1])
    with arc_h1:
        ricerca_arc = st.text_input("🔍 Cerca nell'archivio storico")
    with arc_h2:
        st.markdown("<br>", unsafe_allow_html=True)
        conn = sqlite3.connect(DB_PATH)
        if st.session_state.gruppo_corrente == "admin":
            df_archivio = pd.read_sql_query("SELECT titolo, cliente, tecnico, categoria, urgenza, data, ora, scadenza, note, dettaglio_interventi, nota_chiusura, stato FROM appuntamenti WHERE stato = 'Chiuso'", conn)
        else:
            df_archivio = pd.read_sql_query("SELECT titolo, cliente, tecnico, categoria, urgenza, data, ora, scadenza, note, dettaglio_interventi, nota_chiusura, stato FROM appuntamenti WHERE stato = 'Chiuso' AND gruppo = ?", conn, params=(st.session_state.gruppo_corrente,))
        conn.close()
        csv_archivio = df_archivio.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📊 Esporta Storico",
            data=csv_archivio,
            file_name="archivio_interventi_agenda.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if st.session_state.gruppo_corrente == "admin":
        q = "SELECT id, data, ora, titolo, cliente, tecnico, categoria, urgenza, scadenza, note, dettaglio_interventi, nota_chiusura FROM appuntamenti WHERE stato = 'Chiuso'"
        params = []
    else:
        q = "SELECT id, data, ora, titolo, cliente, tecnico, categoria, urgenza, scadenza, note, dettaglio_interventi, nota_chiusura FROM appuntamenti WHERE stato = 'Chiuso' AND gruppo = ?"
        params = [st.session_state.gruppo_corrente]

    if ricerca_arc:
        q += " AND (titolo LIKE ? OR cliente LIKE ?)"
        p = f"%{ricerca_arc}%"
        params.extend([p, p])
    q += " ORDER BY data DESC"
    cursor.execute(q, params)
    rows_arc = cursor.fetchall()
    conn.close()
    
    if rows_arc:
        for r in rows_arc:
            st.markdown(f"""
                <div style="background-color: rgba(120, 144, 156, 0.15); border-left: 6px solid #78909C; padding: 10px; border-radius: 6px; margin-bottom: 10px;">
                    <div><b>Cliente:</b> {r[4]} | <b>Titolo:</b> {r[3]} | <b>Data:</b> {r[1]} - {r[2]}</div>
                    <div style="margin-top: 4px; opacity: 0.9;"><b>Tecnico:</b> {r[5]} | <b>Nota Chiusura:</b> {r[11]}</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button("🔄 Riattiva Intervento", key=f"riattiva_{r[0]}"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE appuntamenti SET stato = 'Attivo' WHERE id = ?", (r[0],))
                conn.commit()
                conn.close()
                st.success("Intervento rimesso nel planning attivo!")
                st.rerun()
            st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
    else:
        st.info("L'archivio storico è vuoto.")

# ==================== SEZIONE 3: CLIENTI ====================
elif menu == "👥 Gestione Clienti":
    st.title("👥 Gestione e Anagrafica Clienti")
    
    col_ins, col_lista = st.columns([1, 1])
    
    with col_ins:
        st.subheader("➕ Registra Nuovo Cliente")
        with st.form("form_cliente", clear_on_submit=True):
            cli_nome = st.text_input("Nome Azienda *")
            cli_ref = st.text_input("Referente")
            cli_tel = st.text_input("Telefono")
            cli_email = st.text_input("Email")
            cli_ind = st.text_input("Indirizzo")
            cli_note = st.text_input("Note")
                
            if st.form_submit_button("Salva Cliente"):
                if not cli_nome:
                    st.warning("Il nome azienda è obbligatorio.")
                else:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO clienti (nome_azienda, referente, telefono, email, indirizzo, note) VALUES (?, ?, ?, ?, ?, ?)',
                                   (cli_nome, cli_ref, cli_tel, cli_email, cli_ind, cli_note))
                    conn.commit()
                    conn.close()
                    st.success("Cliente registrato con successo!")
                    st.rerun()

    with col_lista:
        c_h1, c_h2 = st.columns([2, 1])
        with c_h1:
            st.subheader("📋 Elenco Clienti Registrati")
        with c_h2:
            conn = sqlite3.connect(DB_PATH)
            df_clienti = pd.read_sql_query("SELECT nome_azienda, referente, telefono, email, indirizzo, note FROM clienti", conn)
            conn.close()
            csv_clienti = df_clienti.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 Esporta Clienti",
                data=csv_clienti,
                file_name="clienti_agenda.csv",
                mime="text/csv",
                use_container_width=True
            )

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome_azienda, referente, telefono, email, indirizzo, note FROM clienti ORDER BY nome_azienda ASC")
        clienti_data = cursor.fetchall()
        conn.close()
        
        if clienti_data:
            for c in clienti_data:
                with st.container():
                    st.markdown(f"""
                        <div style="background-color: rgba(150, 150, 150, 0.1); padding: 10px; border-radius: 6px; border: 1px solid rgba(150, 150, 150, 0.2); margin-bottom: 8px;">
                            🏢 <b>{c[1]}</b><br>
                            <span style="opacity: 0.9;"><i>Referente:</i> {c[2] or 'N/D'} | <i>Tel:</i> {c[3] or 'N/D'}</span><br>
                            <span style="opacity: 0.8;"><i>Email:</i> {c[4] or 'N/D'} | <i>Indirizzo:</i> {c[5] or 'N/D'}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    c_b1, c_b2 = st.columns(2)
                    with c_b1:
                        if st.button("⚙️ Gestisci / Storico", key=f"apri_cli_{c[0]}"):
                            st.session_state["cliente_attivo_id"] = c[0]
                    with c_b2:
                        if st.button("🗑️ Elimina", key=f"del_cli_{c[0]}"):
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM clienti WHERE id = ?", (c[0],))
                            conn.commit()
                            conn.close()
                            st.success("Cliente eliminato!")
                            st.rerun()

                if st.session_state.get("cliente_attivo_id") == c[0]:
                    with st.container():
                        st.markdown(f"""
                            <div style="background-color: rgba(76, 175, 80, 0.15); padding: 15px; border-radius: 6px; border: 1px solid #4CAF50; margin-bottom: 10px;">
                                <h4>Modifica Scheda: {c[1]}</h4>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        with st.form(f"form_mod_cli_{c[0]}"):
                            m_nome = st.text_input("Nome Azienda", value=c[1])
                            m_ref = st.text_input("Referente", value=c[2] or "")
                            m_tel = st.text_input("Telefono", value=c[3] or "")
                            m_email = st.text_input("Email", value=c[4] or "")
                            m_ind = st.text_input("Indirizzo", value=c[5] or "")
                            m_note = st.text_input("Note", value=c[6] or "")
                            
                            col_salva, col_chiudi = st.columns(2)
                            with col_salva:
                                if st.form_submit_button("💾 Salva Modifiche"):
                                    conn = sqlite3.connect(DB_PATH)
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE clienti SET nome_azienda=?, referente=?, telefono=?, email=?, indirizzo=?, note=? WHERE id=?",
                                                   (m_nome, m_ref, m_tel, m_email, m_ind, m_note, c[0]))
                                    conn.commit()
                                    conn.close()
                                    st.success("Aggiornato!")
                                    st.rerun()
                            with col_chiudi:
                                if st.form_submit_button("❌ Chiudi Scheda"):
                                    st.session_state["cliente_attivo_id"] = None
                                    st.rerun()

                        st.markdown("##### 📂 Interventi collegati a questo cliente:")
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("SELECT data, ora, titolo, tecnico, urgenza, stato FROM appuntamenti WHERE cliente = ? ORDER BY data DESC", (c[1],))
                        app_cliente = cursor.fetchall()
                        conn.close()
                        
                        if app_cliente:
                            for ac in app_cliente:
                                stato_colore = "🟢 Attivo" if ac[5] == "Attivo" else "📁 Chiuso"
                                st.markdown(f"- **{ac[0]} ({ac[1]})** | *Titolo:* **{ac[2]}** | *Tecnico:* {ac[3]} | *Urgenza:* {ac[4]} | *Stato:* {stato_colore}")
                        else:
                            st.info("Nessun intervento registrato per questo cliente.")
        else:
            st.info("Nessun cliente registrato.")

# ==================== SEZIONE 4: TECNICI ====================
elif menu == "🛠️ Gestione Tecnici":
    st.title("🛠️ Gestione e Anagrafica Tecnici")
    
    col_t_ins, col_t_lista = st.columns([1, 1])
    
    with col_t_ins:
        st.subheader("➕ Inserisci Nuovo Tecnico")
        with st.form("form_tecnico", clear_on_submit=True):
            tec_nome = st.text_input("Nome Tecnico *")
            tec_spec = st.text_input("Specializzazione")
            tec_tel = st.text_input("Telefono")
            
            if st.form_submit_button("Salva Tecnico"):
                if not tec_nome:
                    st.warning("Il nome del tecnico è obbligatorio.")
                else:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('INSERT INTO tecnici (nome, specializzazione, telefono) VALUES (?, ?, ?)', (tec_nome, tec_spec, tec_tel))
                    conn.commit()
                    conn.close()
                    st.success("Tecnico aggiunto con successo!")
                    st.rerun()

    with col_t_lista:
        t_h1, t_h2 = st.columns([2, 1])
        with t_h1:
            st.subheader("📋 Elenco Tecnici Aziendali")
        with t_h2:
            conn = sqlite3.connect(DB_PATH)
            df_tecnici = pd.read_sql_query("SELECT nome, specializzazione, telefono FROM tecnici", conn)
            conn.close()
            csv_tecnici = df_tecnici.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 Esporta Tecnici",
                data=csv_tecnici,
                file_name="tecnici_agenda.csv",
                mime="text/csv",
                use_container_width=True
            )

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, specializzazione, telefono FROM tecnici ORDER BY nome ASC")
        tecnici_data = cursor.fetchall()
        conn.close()
        
        if tecnici_data:
            for t in tecnici_data:
                with st.container():
                    st.markdown(f"""
                        <div style="background-color: rgba(150, 150, 150, 0.1); padding: 10px; border-radius: 6px; border: 1px solid rgba(150, 150, 150, 0.2); margin-bottom: 8px;">
                            🔧 <b>{t[1]}</b><br>
                            <span style="opacity: 0.9;"><i>Specializzazione:</i> {t[2] or 'N/D'} | <i>Tel:</i> {t[3] or 'N/D'}</span>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    t_b1, t_b2 = st.columns(2)
                    with t_b1:
                        if st.button("⚙️ Gestisci / Storico", key=f"apri_tec_{t[0]}"):
                            st.session_state["tecnico_attivo_id"] = t[0]
                    with t_b2:
                        if st.button("🗑️ Elimina", key=f"del_tec_{t[0]}"):
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM tecnici WHERE id = ?", (t[0],))
                            conn.commit()
                            conn.close()
                            st.success("Tecnico eliminato!")
                            st.rerun()

                if st.session_state.get("tecnico_attivo_id") == t[0]:
                    with st.container():
                        st.markdown(f"""
                            <div style="background-color: rgba(33, 150, 243, 0.15); padding: 15px; border-radius: 6px; border: 1px solid #2196F3; margin-bottom: 10px;">
                                <h4>Modifica Scheda: {t[1]}</h4>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        with st.form(f"form_mod_tec_{t[0]}"):
                            tm_nome = st.text_input("Nome Tecnico", value=t[1])
                            tm_spec = st.text_input("Specializzazione", value=t[2] or "")
                            tm_tel = st.text_input("Telefono", value=t[3] or "")
                            
                            col_tsalva, col_tchiudi = st.columns(2)
                            with col_tsalva:
                                if st.form_submit_button("💾 Salva Modifiche"):
                                    conn = sqlite3.connect(DB_PATH)
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE tecnici SET nome=?, specializzazione=?, telefono=? WHERE id=?",
                                                   (tm_nome, tm_spec, tm_tel, t[0]))
                                    conn.commit()
                                    conn.close()
                                    st.success("Aggiornato!")
                                    st.rerun()
                            with col_tchiudi:
                                if st.form_submit_button("❌ Chiudi Scheda"):
                                    st.session_state["tecnico_attivo_id"] = None
                                    st.rerun()

                        st.markdown("##### 📂 Interventi assegnati a questo tecnico:")
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("SELECT data, ora, titolo, cliente, urgenza, stato FROM appuntamenti WHERE tecnico = ? ORDER BY data DESC", (t[1],))
                        app_tecnico = cursor.fetchall()
                        conn.close()
                        
                        if app_tecnico:
                            for at in app_tecnico:
                                stato_colore = "🟢 Attivo" if at[5] == "Attivo" else "📁 Chiuso"
                                st.markdown(f"- **{at[0]} ({at[1]})** | *Titolo:* **{at[2]}** | *Cliente:* {at[3]} | *Urgenza:* {at[4]} | *Stato:* {stato_colore}")
                        else:
                            st.info("Nessun intervento assegnato a questo tecnico.")
        else:
            st.info("Nessun tecnico registrato.")

# ==================== SEZIONE 5: GESTIONE GRUPPI E UTENTI ====================
elif menu == "🏢 Gestione Gruppi e Utenti":
    st.title("🏢 Gestione Gruppi e Utenti di Accesso")
    
    tab_gruppi, tab_utenti = st.tabs(["📁 Gestione Gruppi", "👥 Gestione Utenti"])
    
    with tab_gruppi:
        col_g1, col_g2 = st.columns([1, 1])
        with col_g1:
            st.subheader("➕ Crea Nuovo Gruppo")
            with st.form("form_nuovo_gruppo", clear_on_submit=True):
                nome_nuovo_gruppo = st.text_input("Nome del Gruppo * (es. software, commerciale)")
                if st.form_submit_button("Salva Gruppo"):
                    if not nome_nuovo_gruppo:
                        st.warning("Il nome del gruppo è obbligatorio.")
                    else:
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO gruppi (nome_gruppo) VALUES (?)", (nome_nuovo_gruppo.strip(),))
                            conn.commit()
                            conn.close()
                            st.success(f"Gruppo '{nome_nuovo_gruppo}' creato con successo!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore (gruppo probabilmente già esistente): {e}")
        with col_g2:
            st.subheader("📋 Gruppi Esistenti")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome_gruppo FROM gruppi ORDER BY nome_gruppo ASC")
            gruppi_attivi = cursor.fetchall()
            conn.close()
            
            if gruppi_attivi:
                for g in gruppi_attivi:
                    with st.container():
                        st.markdown(f"""
                            <div style="background-color: rgba(150, 150, 150, 0.1); padding: 8px 12px; border-radius: 6px; border: 1px solid rgba(150, 150, 150, 0.2); margin-bottom: 6px;">
                                📁 <b>Gruppo:</b> <code>{g[1]}</code>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        cg_b1, cg_b2 = st.columns(2)
                        with cg_b1:
                            if st.button("✏️ Modifica", key=f"mod_grp_{g[0]}"):
                                st.session_state["edit_gruppo_id"] = g[0]
                        with cg_b2:
                            if g[1] not in ["admin", "generale"]:
                                if st.button("🗑️ Elimina", key=f"del_grp_{g[0]}"):
                                    conn = sqlite3.connect(DB_PATH)
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM gruppi WHERE id = ?", (g[0],))
                                    conn.commit()
                                    conn.close()
                                    st.success("Gruppo eliminato!")
                                    st.rerun()
                            else:
                                st.caption("Protetto")

                    if st.session_state.get("edit_gruppo_id") == g[0]:
                        with st.form(f"form_mod_grp_{g[0]}"):
                            st.markdown(f"#### Modifica Gruppo: {g[1]}")
                            m_nome_gruppo = st.text_input("Nome Gruppo", value=g[1])
                            
                            c_gsalva, c_gchiudi = st.columns(2)
                            with c_gsalva:
                                if st.form_submit_button("💾 Salva Modifiche"):
                                    if not m_nome_gruppo:
                                        st.warning("Il nome del gruppo non può essere vuoto.")
                                    else:
                                        try:
                                            conn = sqlite3.connect(DB_PATH)
                                            cursor = conn.cursor()
                                            cursor.execute("UPDATE gruppi SET nome_gruppo = ? WHERE id = ?", (m_nome_gruppo.strip(), g[0]))
                                            conn.commit()
                                            conn.close()
                                            st.session_state["edit_gruppo_id"] = None
                                            st.success("Gruppo aggiornato!")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Errore: {e}")
                            with c_gchiudi:
                                if st.form_submit_button("❌ Annulla"):
                                    st.session_state["edit_gruppo_id"] = None
                                    st.rerun()
            else:
                st.info("Nessun gruppo registrato.")

    with tab_utenti:
        col_u1, col_u2 = st.columns([1, 1])
        with col_u1:
            st.subheader("➕ Crea Nuovo Utente e Assegna Gruppo")
            with st.form("form_nuovo_utente", clear_on_submit=True):
                nuovo_user = st.text_input("Nome Utente / Username *")
                nuova_pass = st.text_input("Password *", type="password")
                
                lista_g = get_gruppi_list()
                gruppo_assegnato_utente = st.selectbox("Seleziona Gruppo di Appartenenza *", lista_g)
                
                if st.form_submit_button("Salva Utente"):
                    if not nuovo_user or not nuova_pass or not gruppo_assegnato_utente:
                        st.warning("Tutti i campi sono obbligatori.")
                    else:
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO utenti (username, password, gruppo) VALUES (?, ?, ?)", (nuovo_user.strip(), nuova_pass, gruppo_assegnato_utente))
                            conn.commit()
                            conn.close()
                            st.success(f"Utente '{nuovo_user}' creato e associato al gruppo '{gruppo_assegnato_utente}' con successo!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore (username probabilmente già esistente): {e}")
        with col_u2:
            st.subheader("📋 Elenco Utenti Registrati")
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, password, gruppo FROM utenti ORDER BY gruppo ASC")
            utenti_data = cursor.fetchall()
            conn.close()
            
            if utenti_data:
                for u in utenti_data:
                    with st.container():
                        st.markdown(f"""
                            <div style="background-color: rgba(150, 150, 150, 0.1); padding: 10px; border-radius: 6px; border: 1px solid rgba(150, 150, 150, 0.2); margin-bottom: 8px;">
                                👤 <b>Utente:</b> {u[1]} &nbsp;|&nbsp; 🏢 <b>Gruppo:</b> <code>{u[3]}</code>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        col_ub1, col_ub2 = st.columns(2)
                        with col_ub1:
                            if st.button("✏️ Modifica Utente", key=f"mod_user_{u[0]}"):
                                st.session_state["edit_user_id"] = u[0]
                        with col_ub2:
                            if u[1] != "admin":
                                if st.button("🗑️ Elimina Utente", key=f"del_user_{u[0]}"):
                                    conn = sqlite3.connect(DB_PATH)
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM utenti WHERE id = ?", (u[0],))
                                    conn.commit()
                                    conn.close()
                                    st.success("Utente eliminato!")
                                    st.rerun()
                            else:
                                st.caption("Protetto (Impossibile eliminare admin)")

                    if st.session_state.get("edit_user_id") == u[0]:
                        with st.form(f"form_mod_user_{u[0]}"):
                            st.markdown(f"#### Modifica Utente: {u[1]}")
                            if u[1] == "admin":
                                st.info("Per l'utente admin è consentita solo la modifica della password.")
                                m_user = u[1]
                                m_gruppo = u[3]
                                m_pass = st.text_input("Nuova Password Admin", value=u[2])
                            else:
                                m_user = st.text_input("Username", value=u[1])
                                m_pass = st.text_input("Password", value=u[2])
                                g_list = get_gruppi_list()
                                try:
                                    g_idx = g_list.index(u[3]) if u[3] in g_list else 0
                                except:
                                    g_idx = 0
                                m_gruppo = st.selectbox("Gruppo", g_list, index=g_idx)
                            
                            c_ms, c_mc = st.columns(2)
                            with c_ms:
                                if st.form_submit_button("💾 Salva Modifiche"):
                                    conn = sqlite3.connect(DB_PATH)
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE utenti SET username = ?, password = ?, gruppo = ? WHERE id = ?", (m_user, m_pass, m_gruppo, u[0]))
                                    conn.commit()
                                    conn.close()
                                    st.session_state["edit_user_id"] = None
                                    st.success("Utente aggiornato con successo!")
                                    st.rerun()
                            with c_mc:
                                if st.form_submit_button("❌ Annulla"):
                                    st.session_state["edit_user_id"] = None
                                    st.rerun()
            else:
                st.info("Nessun utente registrato.")
