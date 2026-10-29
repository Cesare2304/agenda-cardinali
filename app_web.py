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
            stato TEXT DEFAULT 'Attivo'
        )
    ''')
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
    conn.commit()
    conn.close()

inizializza_db()

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
st.sidebar.markdown("---")

# Tasto rapido di aggiornamento/sincronizzazione
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

# Sezione impostazioni visualizzazione per proiettore / schermo grande
st.sidebar.subheader("🖥️ Impostazioni Schermo")
dim_testo = st.sidebar.slider("Dimensione testo Planning (px)", min_value=12, max_value=30, value=16)
dim_titoli = st.sidebar.slider("Dimensione Titoli (px)", min_value=20, max_value=50, value=32)

# Applicazione dinamica delle dimensioni tramite CSS personalizzato
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
cursor.execute("SELECT COUNT(*) FROM appuntamenti WHERE urgenza = 'Urgente' AND (stato = 'Attivo' OR stato IS NULL)")
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
                        INSERT INTO appuntamenti (titolo, cliente, tecnico, telefono, categoria, urgenza, data, ora, scadenza, note, stato)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Attivo')
                    ''', (titolo, cliente, tecnico, telefono, categoria, urgenza, data_app.strftime('%Y-%m-%d'), ora_app, scadenza_app.strftime('%Y-%m-%d'), note))
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
        df_export = pd.read_sql_query("SELECT titolo, cliente, tecnico, telefono, categoria, urgenza, data, ora, scadenza, note, stato FROM appuntamenti WHERE stato = 'Attivo' OR stato IS NULL", conn)
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
    
    query = """
        SELECT id, data, ora, titolo, cliente, tecnico, telefono, categoria, urgenza, scadenza, note 
        FROM appuntamenti 
        WHERE (stato = 'Attivo' OR stato IS NULL)
    """
    params = []
    
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
            urg = r[8]
            if urg == "Urgente":
                bg_color, border_color, col_colore = "rgba(229, 115, 115, 0.15)", "#E57373", "🔴"
            elif urg == "Meno urgente":
                bg_color, border_color, col_colore = "rgba(129, 199, 132, 0.15)", "#81C784", "🟢"
            else:
                bg_color, border_color, col_colore = "rgba(207, 216, 220, 0.15)", "#CFD8DC", "⚪"

            st.markdown(f"""
                <div class="planning-card" style="background-color: {bg_color}; border-left: 6px solid {border_color}; padding: 14px; border-radius: 6px; margin-bottom: 10px;">
                    <div><b>{col_colore} Data:</b> {r[1]} alle {r[2]} &nbsp;|&nbsp; <b>Titolo:</b> {r[3]} &nbsp;|&nbsp; <b>Cliente:</b> {r[4]}</div>
                    <div style="margin-top: 4px; opacity: 0.9;"><b>Tecnico:</b> {r[5]} &nbsp;|&nbsp; <b>Tel:</b> {r[6]} &nbsp;|&nbsp; <b>Urgenza:</b> {r[8]} &nbsp;|&nbsp; <b>Scadenza:</b> {r[9]}</div>
                    <div style="margin-top: 4px; opacity: 0.8; font-style: italic;">Note: {r[10]}</div>
                </div>
            """, unsafe_allow_html=True)

            c_btn1, c_btn2, c_btn3, _ = st.columns([1, 1, 1, 5])
            with c_btn1:
                if st.button("✔️ Chiudi", key=f"chiudi_{r[0]}"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE appuntamenti SET stato = 'Chiuso' WHERE id = ?", (r[0],))
                    conn.commit()
                    conn.close()
                    st.success("Intervento archiviato!")
                    st.rerun()
            with c_btn2:
                if st.button("✏️ Modifica", key=f"mod_{r[0]}"):
                    st.session_state[f"edit_app_{r[0]}"] = True
            with c_btn3:
                if st.button("🗑️ Elimina", key=f"del_{r[0]}"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM appuntamenti WHERE id = ?", (r[0],))
                    conn.commit()
                    conn.close()
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
                    new_urg = st.selectbox("Urgenza", urg_list, index=urg_list.index(r[8]) if r[8] in urg_list else 1)
                    new_tel = st.text_input("Telefono", value=r[6])
                    new_note = st.text_input("Note", value=r[10])
                    
                    if st.form_submit_button("Salva Modifiche"):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE appuntamenti SET titolo=?, cliente=?, tecnico=?, urgenza=?, telefono=?, note=? WHERE id=?",
                                       (new_titolo, new_cliente, new_tecnico, new_urg, new_tel, new_note, r[0]))
                        conn.commit()
                        conn.close()
                        st.session_state[f"edit_app_{r[0]}"] = False
                        st.success("Modifiche salvate!")
                        st.rerun()

            st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)
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
        df_archivio = pd.read_sql_query("SELECT titolo, cliente, tecnico, telefono, categoria, urgenza, data, ora, scadenza, note, stato FROM appuntamenti WHERE stato = 'Chiuso'", conn)
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
    q = "SELECT id, data, ora, titolo, cliente, tecnico, telefono, categoria, urgenza, scadenza, note FROM appuntamenti WHERE stato = 'Chiuso'"
    params = []
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
                    <div><b>Data:</b> {r[1]} - {r[2]} | <b>Titolo:</b> {r[3]} | <b>Cliente:</b> {r[4]}</div>
                    <div style="margin-top: 4px; opacity: 0.9;"><b>Tecnico:</b> {r[5]} | <b>Scadenza:</b> {r[9]} | <b>Note:</b> {r[10]}</div>
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
