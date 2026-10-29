import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(
    page_title="Agenda Cardinali",
    page_icon="📅",
    layout="wide"
)

NOME_DITTA = 'Agenda Cardinali'

# Connessione al database PostgreSQL via Supabase
@st.cache_resource
def get_engine():
    db_url = st.secrets["SUPABASE_URL"]
    return create_engine(db_url)

engine = get_engine()

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

# Interfaccia Streamlit
st.title(f"📅 {NOME_DITTA}")

menu = ["Pianificazione", "Archivio Interventi", "Gestione Clienti e Tecnici"]
scelta = st.sidebar.selectbox("Navigazione", menu)

if scelta == "Pianificazione":
    st.header("Nuovo Intervento")
    
    with engine.connect() as conn:
        clienti_df = pd.read_sql(text("SELECT nome FROM clienti ORDER BY nome"), conn)
        tecnici_df = pd.read_sql(text("SELECT nome FROM tecnici ORDER BY nome"), conn)
    
    lista_clienti = clienti_df['nome'].tolist() if not clienti_df.empty else ["Nessun cliente registrato"]
    lista_tecnici = tecnici_df['nome'].tolist() if not tecnici_df.empty else ["Nessun tecnico registrato"]

    with st.form("form_intervento"):
        titolo = st.text_input("Oggetto / Titolo Intervento*")
        col1, col2 = st.columns(2)
        with col1:
            cliente = st.selectbox("Cliente", lista_clienti)
            data = st.date_input("Data")
        with col2:
            tecnico = st.selectbox("Tecnico Assegnato", lista_tecnici)
            ora = st.time_input("Ora")
        
        note = st.text_area("Note o Dettagli")
        submit = st.form_submit_button("Salva Appuntamento")

        if submit:
            if not titolo:
                st.error("Il titolo è obbligatorio.")
            else:
                data_ora_str = f"{data} {ora}"
                with engine.begin() as conn:
                    conn.execute(
                        text("INSERT INTO appuntamenti (titolo, cliente, tecnico, data_ora, note) VALUES (:t, :c, :tec, :d, :n)"),
                        {"t": titolo, "c": cliente, "tec": tecnico, "d": data_ora_str, "n": note}
                    )
                st.success("Appuntamento salvato con successo!")

elif scelta == "Archivio Interventi":
    st.header("Elenco Interventi")
    with engine.connect() as conn:
        df = pd.read_sql(text("SELECT id, titolo, cliente, tecnico, data_ora, note, stato FROM appuntamenti ORDER BY data_ora DESC"), conn)
    
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nessun intervento registrato.")

elif scelta == "Gestione Clienti e Tecnici":
    st.header("Anagrafiche")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Aggiungi Cliente")
        nuovo_cliente = st.text_input("Nome Cliente")
        if st.button("Salva Cliente"):
            if nuovo_cliente:
                try:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO clienti (nome) VALUES (:n)"), {"n": nuovo_cliente})
                    st.success(f"Cliente '{nuovo_cliente}' aggiunto!")
                    st.rerun()
                except Exception:
                    st.warning("Cliente già esistente o errore nel salvataggio.")
            else:
                st.error("Inserisci il nome del cliente.")
                
        with engine.connect() as conn:
            c_df = pd.read_sql(text("SELECT nome FROM clienti ORDER BY nome"), conn)
        st.write("### Clienti registrati", c_df)

    with col2:
        st.subheader("Aggiungi Tecnico")
        nuovo_tecnico = st.text_input("Nome Tecnico")
        if st.button("Salva Tecnico"):
            if nuovo_tecnico:
                try:
                    with engine.begin() as conn:
                        conn.execute(text("INSERT INTO tecnici (nome) VALUES (:n)"), {"n": nuovo_tecnico})
                    st.success(f"Tecnico '{nuovo_tecnico}' aggiunto!")
                    st.rerun()
                except Exception:
                    st.warning("Tecnico già esistente o errore nel salvataggio.")
            else:
                st.error("Inserisci il nome del tecnico.")
                
        with engine.connect() as conn:
            t_df = pd.read_sql(text("SELECT nome FROM tecnici ORDER BY nome"), conn)
        st.write("### Tecnici registrati", t_df)
