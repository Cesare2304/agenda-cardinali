import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# Configurazione della pagina
st.set_page_config(
    page_title="Agenda Cardinali",
    page_icon="📅",
    layout="wide"
)

# Stile CSS personalizzato
st.markdown("""
    <style>
    .main {
        padding: 1rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>select, .stTextArea>div>div>textarea {
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True)

NOME_DITTA = 'Agenda Cardinali'

# Connessione al database PostgreSQL via Supabase con diagnostica errori
@st.cache_resource
def get_engine():
    try:
        db_url = st.secrets["SUPABASE_URL"]
        eng = create_engine(db_url)
        # Test immediato della connessione per catturare eventuali errori
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return eng
    except Exception as e:
        st.error(f"❌ ERRORE DI CONNESSIONE AL DATABASE SUPABASE: {e}")
        st.info("💡 Verifica che la stringa nei Secrets sia corretta e che la password abbia i caratteri speciali codificati (es. %21 al posto di !).")
        st.stop()

engine = get_engine()

# Inizializzazione delle tabelle nel database cloud
def inizializza_db():
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS appuntamenti (
                id SERIAL PRIMARY KEY,
                titolo TEXT NOT NULL,
                cliente TEXT,
                tecnico TEXT,
                data_ora TIMESTAMP NOT NULL,
                note TEXT,
                stato TEXT DEFAULT 'In programma'
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS clienti (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL
            )
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS tecnici (
                id SERIAL PRIMARY KEY,
                nome TEXT UNIQUE NOT NULL
            )
        '''))

inizializza_db()

# Intestazione principale
st.title(f"📅 {NOME_DITTA}")

# Menu laterale di navigazione
menu = ["Pianificazione", "Archivio Interventi", "Gestione Clienti e Tecnici"]
scelta = st.sidebar.selectbox("Navigazione", menu)

# ==========================================
# 1. PIANIFICAZIONE INTERVENTI
# ==========================================
if scelta == "Pianificazione":
    st.header("📝 Nuovo Intervento")
    
    with engine.connect() as conn:
        clienti_df = pd.read_sql(text("SELECT nome FROM clienti ORDER BY nome"), conn)
        tecnici_df = pd.read_sql(text("SELECT nome FROM tecnici ORDER BY nome"), conn)
    
    lista_clienti = clienti_df['nome'].tolist() if not clienti_df.empty else []
    lista_tecnici = tecnici_df['nome'].tolist() if not tecnici_df.empty else []

    if not lista_clienti or not lista_tecnici:
        st.warning("⚠️ Prima di pianificare un intervento, assicurati di aver inserito almeno un Cliente e un Tecnico nella sezione 'Gestione Clienti e Tecnici'.")

    with st.form("form_intervento", clear_on_submit=True):
        titolo = st.text_input("Oggetto / Titolo Intervento*")
        
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.selectbox("Cliente", lista_clienti if lista_clienti else ["Nessun cliente"])
            data = st.date_input("Data Intervento", value=datetime.today())
        with col2:
            tecnico = st.selectbox("Tecnico Assegnato", lista_tecnici if lista_tecnici else ["Nessun tecnico"])
            ora = st.time_input("Ora Intervento")
        
        note = st.text_area("Note o Dettagli aggiuntivi")
        submit = st.form_submit_button("Salva Appuntamento nel Cloud")

        if submit:
            if not titolo:
                st.error("Il campo 'Oggetto / Titolo Intervento' è obbligatorio.")
            elif not lista_clienti or not lista_tecnici:
                st.error("Impossibile salvare: mancano clienti o tecnici nel database.")
            else:
                data_ora_str = f"{data} {ora}"
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO appuntamenti (titolo, cliente, tecnico, data_ora, note, stato) VALUES (:t, :c, :tec, :d, :n, :s)"),
                        {
                            "t": titolo, 
                            "c": cliente, 
                            "tec": tecnico, 
                            "d": data_ora_str, 
                            "n": note,
                            "s": "In programma"
                        }
                    )
                st.success("🎉 Appuntamento salvato con successo e sincronizzato nel cloud!")

# ==========================================
# 2. ARCHIVIO INTERVENTI
# ==========================================
elif scelta == "Archivio Interventi":
    st.header("📂 Archivio e Storico Interventi")
    
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT id, titolo, cliente, tecnico, data_ora, note, stato FROM appuntamenti ORDER BY data_ora DESC"), conn)
    
    if not df.empty:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            filtro_tecnico = st.selectbox("Filtra per Tecnico", ["Tutti"] + list(df['tecnico'].dropna().unique()))
        with col_f2:
            filtro_stato = st.selectbox("Filtra per Stato", ["Tutti", "In programma", "Completato", "Annullato"])
        
        df_filtrato = df.copy()
        if filtro_tecnico != "Tutti":
            df_filtrato = df_filtrato[df_filtrato['tecnico'] == filtro_tecnico]
        if filtro_stato != "Tutti":
            df_filtrato = df_filtrato[df_filtrato['stato'] == filtro_stato]

        st.dataframe(df_filtrato, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Gestione Intervento Selezionato")
        
        id_selezionato = st.selectbox("Seleziona ID Intervento da modificare/eliminare", df['id'].tolist())
        
        if id_selezionato:
            riga_sel = df[df['id'] == id_selezionato].iloc[0]
            c_stato, c_del = st.columns(2)
            
            with c_stato:
                nuovo_stato = st.selectbox("Aggiorna Stato", ["In programma", "Completato", "Annullato"], index=["In programma", "Completato", "Annullato"].index(riga_sel['stato']) if riga_sel['stato'] in ["In programma", "Completato", "Annullato"] else 0)
                if st.button("Aggiorna Stato"):
                    with engine.begin() as conn:
                        conn.execute(text("UPDATE appuntamenti SET stato = :s WHERE id = :id"), {"s": nuovo_stato, "id": id_selezionato})
                    st.success("Stato aggiornato correttamente!")
                    st.rerun()
            
            with c_del:
                st.write("###")
                if st.button("🗑️ Elimina Intervento", type="primary"):
                    with engine.begin() as conn:
                        conn.execute(text("DELETE FROM appuntamenti WHERE id = :id"), {"id": id_selezionato})
                    st.success("Intervento eliminato con successo!")
                    st.rerun()
    else:
        st.info("Nessun intervento registrato nell'archivio cloud.")

# ==========================================
# 3. GESTIONE CLIENTI E TECNICI
# ==========================================
elif scelta == "Gestione Clienti e Tecnici":
    st.header("👥 Gestione Anagrafiche")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Clienti")
        nuovo_cliente = st.text_input("Nome Nuovo Cliente")
        if st.button("Aggiungi Cliente"):
            if nuovo_cliente.strip():
                try:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO clienti (nome) VALUES (:n)"), {"n": nuovo_cliente.strip()})
                    st.success(f"Cliente '{nuovo_cliente}' aggiunto!")
                    st.rerun()
                except Exception:
                    st.warning("Questo cliente esiste già nel database.")
            else:
                st.error("Inserisci un nome valido.")
                
        with engine.connect() as conn:
            c_df = pd.read_sql(text("SELECT id, nome FROM clienti ORDER BY nome"), conn)
        
        if not c_df.empty:
            st.dataframe(c_df, use_container_width=True)
            id_del_c = st.selectbox("ID Cliente da rimuovere", [0] + c_df['id'].tolist(), key="del_c")
            if id_del_c != 0 and st.button("Elimina Cliente"):
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM clienti WHERE id = :id"), {"id": id_del_c})
                st.success("Cliente rimosso.")
                st.rerun()
        else:
            st.info("Nessun cliente registrato.")

    with col2:
        st.subheader("Tecnici")
        nuovo_tecnico = st.text_input("Nome Nuovo Tecnico")
        if st.button("Aggiungi Tecnico"):
            if nuovo_tecnico.strip():
                try:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO tecnici (nome) VALUES (:n)"), {"n": nuovo_tecnico.strip()})
                    st.success(f"Tecnico '{nuovo_tecnico}' aggiunto!")
                    st.rerun()
                except Exception:
                    st.warning("Questo tecnico esiste già nel database.")
            else:
                st.error("Inserisci un nome valido.")
                
        with engine.connect() as conn:
            t_df = pd.read_sql(text("SELECT id, nome FROM tecnici ORDER BY nome"), conn)
        
        if not t_df.empty:
            st.dataframe(t_df, use_container_width=True)
            id_del_t = st.selectbox("ID Tecnico da rimuovere", [0] + t_df['id'].tolist(), key="del_t")
            if id_del_t != 0 and st.button("Elimina Tecnico"):
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM tecnici WHERE id = :id"), {"id": id_del_t})
                st.success("Tecnico rimosso.")
                st.rerun()
        else:
            st.info("Nessun tecnico registrato.")
