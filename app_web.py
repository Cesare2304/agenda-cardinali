import sqlite3
import datetime
import os
import json
import streamlit as st
import pandas as pd
from io import BytesIO

# Importazione per editor di testo avanzato (se disponibile)
try:
    from streamlit_quill import st_quill
    HAS_QUILL = True
except ImportError:
    HAS_QUILL = False

# Importazioni per ReportLab (PDF Design Avanzato)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

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
    
    # Tabella Appuntamenti / Interventi
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

    # Tabella Clienti (Anagrafica)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_azienda TEXT NOT NULL,
            referente TEXT,
            telefono TEXT,
            email TEXT,
            indirizzo TEXT,
            piva TEXT,
            note TEXT
        )
    ''')
    
    for col, col_type in [("piva", "TEXT"), ("indirizzo", "TEXT"), ("referente", "TEXT"), ("telefono", "TEXT"), ("email", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE clienti ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    # Tabella Gruppi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gruppi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_gruppo TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Tabella Utenti
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS utenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            gruppo TEXT NOT NULL DEFAULT 'generale',
            telefono TEXT
        )
    ''')
    
    # Tabella Impostazioni Report (Template HTML Avanzato)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS impostazioni_report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titolo_report TEXT DEFAULT 'RAPPORTO DI INTERVENTO TECNICO',
            font_family TEXT DEFAULT 'Helvetica',
            font_size INTEGER DEFAULT 10,
            colore_primario TEXT DEFAULT '#1976D2',
            template_html_personalizzato TEXT DEFAULT '',
            testo_garanzia TEXT DEFAULT 'Si certifica che i lavori sono stati eseguiti a regola d arte.',
            testo_pie TEXT DEFAULT 'Documento emesso da Agenda Cardinali - Tutti i diritti riservati.'
        )
    ''')
    
    colonne_report = [
        ("titolo_report", "TEXT DEFAULT 'RAPPORTO DI INTERVENTO TECNICO'"),
        ("font_family", "TEXT DEFAULT 'Helvetica'"),
        ("font_size", "INTEGER DEFAULT 10"),
        ("colore_primario", "TEXT DEFAULT '#1976D2'"),
        ("template_html_personalizzato", "TEXT DEFAULT ''"),
        ("testo_garanzia", "TEXT DEFAULT 'Si certifica che i lavori sono stati eseguiti a regola d arte.'"),
        ("testo_pie", "TEXT DEFAULT 'Documento emesso da Agenda Cardinali - Tutti i diritti riservati.'")
    ]
    for col, col_type in colonne_report:
        try:
            cursor.execute(f"ALTER TABLE impostazioni_report ADD COLUMN {col} {col_type}")
        except Exception:
            pass
    
    cursor.execute("SELECT COUNT(*) FROM gruppi")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO gruppi (nome_gruppo) VALUES ('admin')")
        cursor.execute("INSERT INTO gruppi (nome_gruppo) VALUES ('software')")

    cursor.execute("SELECT COUNT(*) FROM utenti")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO utenti (username, password, gruppo, telefono) VALUES (?, ?, ?, ?)", ("admin", "admin123", "admin", ""))
        cursor.execute("INSERT INTO utenti (username, password, gruppo, telefono) VALUES (?, ?, ?, ?)", ("software", "soft123", "software", ""))

    cursor.execute("SELECT COUNT(*) FROM impostazioni_report")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO impostazioni_report (titolo_report) VALUES ('RAPPORTO DI INTERVENTO TECNICO')")
        
    conn.commit()
    conn.close()

inizializza_db()

if 'autenticato' not in st.session_state:
    st.session_state.autenticato = False
    st.session_state.utente_corrente = None
    st.session_state.gruppo_corrente = None

if 'modello_report_path' not in st.session_state:
    st.session_state.modello_report_path = None

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

def get_clienti_dati(nome_cliente):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT nome_azienda, referente, telefono, email, indirizzo, piva FROM clienti WHERE nome_azienda = ?', (nome_cliente,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return {"nome": res[0], "referente": res[1] or "", "telefono": res[2] or "", "email": res[3] or "", "indirizzo": res[4] or "", "piva": res[5] or ""}
    return {"nome": nome_cliente, "referente": "", "telefono": "", "email": "", "indirizzo": "", "piva": ""}

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
    cursor.execute('SELECT username FROM utenti ORDER BY username ASC')
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

def get_template_report():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT titolo_report, font_family, font_size, colore_primario, 
                   template_html_personalizzato, testo_garanzia, testo_pie 
            FROM impostazioni_report LIMIT 1
        """)
        res = cursor.fetchone()
        conn.close()
        if res:
            return res
    except Exception:
        pass
    return ("RAPPORTO DI INTERVENTO", "Helvetica", 10, "#1976D2", "", "Garanzia standard...", "Piè di pagina...")

# Generatore PDF basato su Template HTML Dinamico e Tag di Merge
def genera_pdf_report(cliente_info, titolo, tecnico, dettagli, nota_chiusura):
    tpl = get_template_report()
    titolo_rep, font_fam, font_sz, colore_p, html_pers, t_gar, t_pie = tpl
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    
    try:
        main_color = colors.HexColor(colore_p)
    except:
        main_color = colors.HexColor('#1976D2')

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=font_sz + 5, textColor=main_color, spaceAfter=4)
    company_style = ParagraphStyle('CompanyStyle', parent=styles['Normal'], fontSize=font_sz - 1, textColor=colors.HexColor('#555555'), spaceAfter=2)
    normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=font_sz, textColor=colors.HexColor('#333333'), spaceAfter=6)
    bold_style = ParagraphStyle('BoldStyle', parent=styles['Normal'], fontSize=font_sz, fontName='Helvetica-Bold', textColor=colors.HexColor('#111111'))
    
    if st.session_state.modello_report_path and os.path.exists(st.session_state.modello_report_path):
        try:
            from reportlab.platypus import Image as RLImage
            elements.append(RLImage(st.session_state.modello_report_path, width=540, height=130))
            elements.append(Spacer(1, 10))
        except Exception:
            pass

    data_header = [
        [
            Paragraph(f"<b>{NOME_DITTA}</b><br/><font size=8>P.IVA: 01234567890 | Via Roma 1, Firenze<br/>Tel: 055123456 | Email: info@agendacardinali.it</font>", company_style),
            Paragraph(f"<b>{titolo_rep}</b>", ParagraphStyle('SubH', parent=title_style, alignment=2))
        ]
    ]
    t_header = Table(data_header, colWidths=[270, 270])
    t_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 10)]))
    elements.append(t_header)
    elements.append(HRFlowable(width="100%", thickness=2, color=main_color, spaceAfter=12))
    
    # Sostituzione dei tag dinamici nel template HTML personalizzato scritto dall'utente
    if html_pers and html_pers.strip():
        html_compilato = html_pers \
            .replace("{cliente}", cliente_info['nome']) \
            .replace("{referente}", cliente_info['referente']) \
            .replace("{telefono}", cliente_info['telefono']) \
            .replace("{email}", cliente_info['email']) \
            .replace("{indirizzo}", cliente_info['indirizzo']) \
            .replace("{piva}", cliente_info['piva']) \
            .replace("{titolo_attivita}", titolo) \
            .replace("{tecnico}", tecnico) \
            .replace("{dettagli_interventi}", dettagli) \
            .replace("{nota_chiusura}", nota_chiusura) \
            .replace("{data_corrente}", str(datetime.date.today()))
            
        elements.append(Paragraph(html_compilato.replace('\n', '<br/>'), normal_style))
        elements.append(Spacer(1, 10))

    data_info = [
        [Paragraph(f"<b>Cliente:</b> {cliente_info['nome']}<br/><b>Indirizzo:</b> {cliente_info['indirizzo']}<br/><b>P.IVA / CF:</b> {cliente_info['piva']}", normal_style), 
         Paragraph(f"<b>Data Report:</b> {datetime.date.today()}<br/><b>Referente:</b> {cliente_info['referente']}<br/><b>Tel Cliente:</b> {cliente_info['telefono']}", normal_style)],
        [Paragraph(f"<b>Oggetto Attività:</b> {titolo}", normal_style), Paragraph(f"<b>Tecnico Incaricato:</b> {tecnico}", normal_style)]
    ]
    t_info = Table(data_info, colWidths=[270, 270])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 12))
    
    elements.append(Paragraph("<b>Dettaglio Interventi e Attività Eseguite:</b>", bold_style))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(dettagli.replace('\n', '<br/>'), normal_style))
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("<b>Esito e Note di Chiusura:</b>", bold_style))
    elements.append(Paragraph(f"<b>Nota Finale:</b> {nota_chiusura}", normal_style))
    
    if t_gar:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"<b>Condizioni / Note Legali:</b><br/><i>{t_gar}</i>", normal_style))
    
    elements.append(Spacer(1, 20))
    data_firme = [
        [Paragraph("<b>Firma del Tecnico</b>", normal_style), Paragraph("<b>Firma per Accettazione Cliente</b>", normal_style)],
        [Paragraph("<br/><br/>___________________________", normal_style), Paragraph("<br/><br/>___________________________", normal_style)]
    ]
    t_firme = Table(data_firme, colWidths=[270, 270])
    t_firme.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('PADDING', (0,0), (-1,-1), 4)]))
    elements.append(t_firme)
    
    if t_pie:
        elements.append(Spacer(1, 25))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#CCCCCC'), spaceAfter=4))
        elements.append(Paragraph(f"<font size=7 color='#777777'>{t_pie}</font>", normal_style))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

if 'menu_selezionato' not in st.session_state:
    st.session_state.menu_selezionato = "📅 Planning Principale"

# ==================== MENU LATERALE ====================
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
if st.sidebar.button("🛠️ Gestione Tecnici / Utenti", use_container_width=True):
    st.session_state.menu_selezionato = "🛠️ Gestione Tecnici / Utenti"
if st.sidebar.button("🏢 Gestione Gruppi", use_container_width=True):
    st.session_state.menu_selezionato = "🏢 Gestione Gruppi"

if st.session_state.gruppo_corrente == "admin":
    if st.sidebar.button("⚙️ Report Studio (Template)", use_container_width=True):
        st.session_state.menu_selezionato = "⚙️ Report"

st.sidebar.markdown("---")
dim_testo = st.sidebar.slider("Dimensione testo Planning (px)", min_value=12, max_value=30, value=16)
dim_titoli = st.sidebar.slider("Dimensione Titoli (px)", min_value=20, max_value=50, value=32)

# CSS globale per azzerare i margini superiori e compattare lo spazio vuoto in alto
st.markdown(f"""
    <style>
    .block-container {{ padding-top: 0.8rem !important; padding-bottom: 1rem !important; }}
    [data-testid="stSidebar"] div.block-container {{ padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{ gap: 0.2rem !important; }}
    [data-testid="stSidebar"] hr {{ margin: 0.3rem 0 !important; }}
    .planning-card {{ font-size: {dim_testo}px !important; padding: 8px 10px; border-radius: 6px; box-sizing: border-box; width: 100%; line-height: 1.3; }}
    .planning-card div {{ font-size: {dim_testo}px !important; }}
    h1 {{ font-size: {dim_titoli}px !important; margin-top: 0px !important; padding-top: 0px !important; }}
    .stButton button {{ width: 100%; border-radius: 4px; padding: 4px 6px; font-size: 11px; margin-bottom: 2px; }}
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

# ==================== 1. PLANNING PRINCIPALE ====================
if menu == "📅 Planning Principale":
    st.title("📅 Planning Attività e Urgenze")
    
    with st.expander("➕ Inserisci Nuovo Appuntamento / Attività", expanded=False):
        with st.form("form_nuovo_app", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                titolo = st.text_input("Titolo Attività *")
                clienti_list = get_clienti()
                cliente = st.selectbox("Cliente (Anagrafica)", clienti_list if clienti_list else ["Nessun cliente registrato"])
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
                gruppo_assegnato = st.selectbox("Mansione di Competenza", gruppi_disponibili, index=gruppi_disponibili.index(st.session_state.gruppo_corrente) if st.session_state.gruppo_corrente in gruppi_disponibili else 0)
                
            note = st.text_input("Note aggiuntive")
            
            c_sub1, c_sub2 = st.columns(2)
            with c_sub1:
                salva_btn = st.form_submit_button("Salva Appuntamento", use_container_width=True)
            with c_sub2:
                annulla_btn = st.form_submit_button("❌ Annulla", use_container_width=True)
            
            if salva_btn:
                if not titolo:
                    st.warning("Inserisci almeno il titolo.")
                else:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO appuntamenti (titolo, cliente, tecnico, telefono, categoria, urgenza, data, ora, scadenza, note, gruppo, stato)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Attivo')
                    ''', (titolo, cliente, tecnico, telefono, categoria, urgenza, data_app.strftime('%Y-%m-%d'), ora_app, scadenza_app.strftime('%Y-%m-%d'), note, gruppo_assegnato))
                    conn.commit()
                    conn.close()
                    st.success("Attività salvata!")
                    st.rerun()
            if annulla_btn:
                st.info("Operazione annullata.")
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

            col_card, col_buttons = st.columns([10, 2])
            with col_card:
                st.markdown(f"""
                    <div class="planning-card" style="background-color: {bg_color}; border-left: 6px solid {border_color};">
                        <div><b>{col_colore} Data:</b> {r[1]} alle {r[2]} &nbsp;|&nbsp; <b>Titolo:</b> {r[3]} &nbsp;|&nbsp; <b>Cliente:</b> {r[4]} &nbsp;|&nbsp; <b>Scadenza:</b> {r[8]} &nbsp;|&nbsp; <b>Gruppo:</b> <i>{r[12]}</i></div>
                        <div style="margin-top: 3px; opacity: 0.9;"><b>Tecnico:</b> {r[5]} &nbsp;|&nbsp; <i>Note: {r[9]}</i> &nbsp;|&nbsp; <span style="color: #1976D2;"><b>Interventi:</b> {r[10].replace('\n', ' | ') if r[10] else 'Nessuno'}</span></div>
                    </div>
                """, unsafe_allow_html=True)
            
            with col_buttons:
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("🛠️", key=f"int_{r[0]}", help="Interventi", use_container_width=True):
                        st.session_state[f"open_interventi_{r[0]}"] = not st.session_state.get(f"open_interventi_{r[0]}", False)
                    if st.button("✏️", key=f"mod_{r[0]}", help="Modifica", use_container_width=True):
                        st.session_state[f"edit_app_{r[0]}"] = True
                with b2:
                    if st.button("✔️", key=f"chiudi_{r[0]}", help="Chiudi", use_container_width=True):
                        st.session_state[f"open_chiusura_{r[0]}"] = True
                    if st.button("🗑️", key=f"del_{r[0]}", help="Elimina", use_container_width=True):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM appuntamenti WHERE id = ?", (r[0],))
                        conn.commit()
                        conn.close()
                        st.rerun()

            if st.session_state.get(f"open_interventi_{r[0]}", False):
                with st.form(f"form_int_fatti_{r[0]}"):
                    st.subheader(f"Gestione Interventi Fatti - #{r[0]}")
                    
                    col_i1, col_i2, col_i3 = st.columns(3)
                    with col_i1:
                        data_inz = st.date_input("Data Inizio", value=datetime.date.today(), key=f"dinz_{r[0]}")
                        ora_inz = st.text_input("Ora Inizio", value="08:30", key=f"oinz_{r[0]}")
                    with col_i2:
                        data_fin = st.date_input("Data Fine", value=datetime.date.today(), key=f"dfin_{r[0]}")
                        ora_fin = st.text_input("Ora Fine", value="12:30", key=f"ofin_{r[0]}")
                    with col_i3:
                        modalita = st.selectbox("Azione", ["Aggiungi nuovo intervento", "Sovrascrivi tutto"], key=f"mod_int_{r[0]}")
                    
                    testo_lav = st.text_area("Descrizione della lavorazione eseguita", key=f"tlav_{r[0]}")
                    
                    c_s1, c_s2 = st.columns(2)
                    with c_s1:
                        sub_int = st.form_submit_button("Salva Intervento", use_container_width=True)
                    with c_s2:
                        ann_int = st.form_submit_button("❌ Annulla", use_container_width=True)
                        
                    if sub_int:
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
                        st.success("Intervento salvato!")
                        st.rerun()
                    if ann_int:
                        st.session_state[f"open_interventi_{r[0]}"] = False
                        st.rerun()

            if st.session_state.get(f"open_chiusura_{r[0]}", False):
                cliente_dati = get_clienti_dati(r[4])

                st.markdown(f"""
                    <div style="background-color: rgba(33, 150, 243, 0.1); padding: 15px; border-radius: 8px; border: 1px solid #2196F3; margin-bottom: 10px;">
                        <h4>✔️ Chiusura Intervento & Generazione PDF - #{r[0]}</h4>
                        <p>I dati aziendali e del cliente (<b>{cliente_dati['nome']}</b> - P.IVA: {cliente_dati['piva'] or 'N/D'}) sono stati acquisiti automaticamente dall'anagrafica.</p>
                    </div>
                """, unsafe_allow_html=True)

                with st.form(f"form_chiusura_{r[0]}"):
                    rep_nota = st.text_area("Nota finale di chiusura obbligatoria *", value="")
                    
                    c_c1, c_c2 = st.columns(2)
                    with c_c1:
                        sub_chiudi = st.form_submit_button("✔️ Conferma, Archivia e Genera PDF", use_container_width=True)
                    with c_c2:
                        ann_chiudi = st.form_submit_button("❌ Annulla", use_container_width=True)

                    if sub_chiudi:
                        if not rep_nota:
                            st.warning("Inserisci una nota finale di chiusura obbligatoria.")
                        else:
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE appuntamenti SET stato = 'Chiuso', nota_chiusura = ? WHERE id = ?", (rep_nota, r[0]))
                            conn.commit()
                            conn.close()
                            
                            pdf_buffer = genera_pdf_report(cliente_dati, r[3], r[5], r[10] or "", rep_nota)
                            st.session_state[f"pdf_data_{r[0]}"] = pdf_buffer.getvalue()
                            
                            st.session_state[f"open_chiusura_{r[0]}"] = False
                            st.success("Intervento chiuso e archiviato con successo!")
                            st.rerun()
                    if ann_chiudi:
                        st.session_state[f"open_chiusura_{r[0]}"] = False
                        st.rerun()

                if f"pdf_data_{r[0]}" in st.session_state:
                    st.download_button(
                        label=f"📥 Scarica PDF Ufficiale Intervento #{r[0]}",
                        data=st.session_state[f"pdf_data_{r[0]}"],
                        file_name=f"Rapporto_Intervento_{r[0]}_{r[4]}.pdf",
                        mime="application/pdf",
                        key=f"dl_pdf_{r[0]}"
                    )

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
                    
                    c_m1, c_m2 = st.columns(2)
                    with c_m1:
                        sub_mod = st.form_submit_button("Salva Modifiche", use_container_width=True)
                    with c_m2:
                        ann_mod = st.form_submit_button("❌ Annulla", use_container_width=True)

                    if sub_mod:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE appuntamenti SET titolo = ?, cliente = ?, tecnico = ?, urgenza = ?, note = ? WHERE id = ?", (new_titolo, new_cliente, new_tecnico, new_urg, new_note, r[0]))
                        conn.commit()
                        conn.close()
                        st.session_state[f"edit_app_{r[0]}"] = False
                        st.success("Modifiche salvate!")
                        st.rerun()
                    if ann_mod:
                        st.session_state[f"edit_app_{r[0]}"] = False
                        st.rerun()

# ==================== 2. ARCHIVIO STORICO ====================
elif menu == "📁 Archivio Storico":
    st.title("📁 Archivio Interventi Chiusi")
    
    conn = sqlite3.connect(DB_PATH)
    if st.session_state.gruppo_corrente == "admin":
        df_archivio = pd.read_sql_query("SELECT id, data, ora, titolo, cliente, tecnico, categoria, urgenza, scadenza, note, dettaglio_interventi, nota_chiusura, gruppo FROM appuntamenti WHERE stato = 'Chiuso'", conn)
    else:
        df_archivio = pd.read_sql_query("SELECT id, data, ora, titolo, cliente, tecnico, categoria, urgenza, scadenza, note, dettaglio_interventi, nota_chiusura, gruppo FROM appuntamenti WHERE stato = 'Chiuso' AND gruppo = ?", conn, params=(st.session_state.gruppo_corrente,))
    conn.close()
    
    if not df_archivio.empty:
        st.dataframe(df_archivio, use_container_width=True)
    else:
        st.info("Nessun intervento chiuso presente in archivio.")

# ==================== 3. GESTIONE CLIENTI ====================
elif menu == "👥 Gestione Clienti":
    st.title("👥 Anagrafica Clienti")
    
    with st.expander("➕ Aggiungi Nuovo Cliente", expanded=False):
        with st.form("form_nuovo_cliente"):
            c1, c2 = st.columns(2)
            with c1:
                nome_az = st.text_input("Nome Azienda / Cliente *")
                referente = st.text_input("Referente")
                telefono_c = st.text_input("Telefono")
            with c2:
                email_c = st.text_input("Email")
                piva_c = st.text_input("Partita IVA / Codice Fiscale")
                indirizzo_c = st.text_input("Indirizzo Sede")
            
            note_c = st.text_area("Note sul Cliente")
            sub_c = st.form_submit_button("Salva Cliente", use_container_width=True)
            
            if sub_c:
                if not nome_az:
                    st.warning("Inserisci il nome dell'azienda o del cliente.")
                else:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO clienti (nome_azienda, referente, telefono, email, indirizzo, piva, note)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (nome_az, referente, telefono_c, email_c, indirizzo_c, piva_c, note_c))
                    conn.commit()
                    conn.close()
                    st.success("Cliente salvato correttamente!")
                    st.rerun()

    st.divider()
    conn = sqlite3.connect(DB_PATH)
    df_clienti = pd.read_sql_query("SELECT id, nome_azienda, referente, telefono, email, indirizzo, piva, note FROM clienti ORDER BY nome_azienda ASC", conn)
    conn.close()
    
    if not df_clienti.empty:
        st.dataframe(df_clienti, use_container_width=True)
    else:
        st.info("Nessun cliente registrato nell'anagrafica.")

# ==================== 4. GESTIONE TECNICI / UTENTI ====================
elif menu == "🛠️ Gestione Tecnici / Utenti":
    st.title("🛠️ Gestione Utenti e Tecnici")
    
    if st.session_state.gruppo_corrente != "admin":
        st.error("Accesso negato. Questa sezione è riservata agli amministratori.")
    else:
        with st.expander("➕ Crea Nuovo Utente / Tecnico", expanded=False):
            with st.form("form_nuovo_utente"):
                u_user = st.text_input("Nome Utente (Username) *")
                u_pass = st.text_input("Password *", type="password")
                
                gruppi_list = get_gruppi_list()
                u_gruppo = st.selectbox("Mansione / Gruppo", gruppi_list)
                u_tel = st.text_input("Telefono")
                
                sub_u = st.form_submit_button("Crea Utente", use_container_width=True)
                if sub_u:
                    if not u_user or not u_pass:
                        st.warning("Username e password sono obbligatori.")
                    else:
                        try:
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO utenti (username, password, gruppo, telefono) VALUES (?, ?, ?, ?)", (u_user, u_pass, u_gruppo, u_tel))
                            conn.commit()
                            conn.close()
                            st.success(f"Utente '{u_user}' creato con successo!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Errore nella creazione (forse l'utente esiste già): {e}")

        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_utenti = pd.read_sql_query("SELECT id, username, gruppo, telefono FROM utenti ORDER BY username ASC", conn)
        conn.close()
        st.dataframe(df_utenti, use_container_width=True)

# ==================== 5. GESTIONE GRUPPI ====================
elif menu == "🏢 Gestione Gruppi":
    st.title("🏢 Gestione Mansioni / Gruppi")
    
    if st.session_state.gruppo_corrente != "admin":
        st.error("Accesso negato. Sezione riservata agli amministratori.")
    else:
        with st.form("form_nuovo_gruppo"):
            nome_g = st.text_input("Nome Nuovo Gruppo / Mansione *")
            sub_g = st.form_submit_button("Aggiungi Gruppo", use_container_width=True)
            if sub_g:
                if not nome_g:
                    st.warning("Inserisci il nome del gruppo.")
                else:
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO gruppi (nome_gruppo) VALUES (?)", (nome_g,))
                        conn.commit()
                        conn.close()
                        st.success(f"Gruppo '{nome_g}' aggiunto!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore (forse il gruppo esiste già): {e}")

        st.divider()
        conn = sqlite3.connect(DB_PATH)
        df_gruppi = pd.read_sql_query("SELECT * FROM gruppi ORDER BY nome_gruppo ASC", conn)
        conn.close()
        st.dataframe(df_gruppi, use_container_width=True)

# ==================== 6. REPORT STUDIO (TEMPLATE) ====================
elif menu == "⚙️ Report":
    st.title("⚙️ Report Studio & Template PDF")
    
    if st.session_state.gruppo_corrente != "admin":
        st.error("Accesso negato. Sezione riservata agli amministratori.")
    else:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT titolo_report, font_family, font_size, colore_primario, template_html_personalizzato, testo_garanzia, testo_pie FROM impostazioni_report LIMIT 1")
        rep_conf = cursor.fetchone()
        conn.close()
        
        t_rep, f_fam, f_sz, c_prim, t_html, t_gar, t_pie = rep_conf if rep_conf else ("RAPPORTO", "Helvetica", 10, "#1976D2", "", "", "")
        
        with st.form("form_impostazioni_report"):
            new_t_rep = st.text_input("Titolo del Report nei PDF", value=t_rep)
            new_c_prim = st.color_picker("Colore Principale Intestazione PDF", value=c_prim)
            new_t_gar = st.text_area("Testo Garanzia / Note Legali", value=t_gar)
            new_t_pie = st.text_input("Testo Piè di Pagina", value=t_pie)
            
            st.markdown("### Template HTML Personalizzato (Tag disponibili: `{cliente}`, `{referente}`, `{telefono}`, `{email}`, `{indirizzo}`, `{piva}`, `{titolo_attivita}`, `{tecnico}`, `{dettagli_interventi}`, `{nota_chiusura}`, `{data_corrente}`)")
            if HAS_QUILL:
                new_t_html = st_quill(value=t_html or "", placeholder="Scrivi qui il template HTML...", key="quill_rep_edit")
            else:
                new_t_html = st.text_area("Codice HTML personalizzato", value=t_html or "", height=150)
            
            sub_rep = st.form_submit_button("Salva Impostazioni Report", use_container_width=True)
            if sub_rep:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE impostazioni_report SET titolo_report = ?, colore_primario = ?, testo_garanzia = ?, testo_pie = ?, template_html_personalizzato = ?", (new_t_rep, new_c_prim, new_t_gar, new_t_pie, new_t_html if not HAS_QUILL else (new_t_html or "")))
                conn.commit()
                conn.close()
                st.success("Impostazioni report aggiornate con successo!")
                st.rerun()
