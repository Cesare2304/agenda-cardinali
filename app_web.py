import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

st.set_page_config(page_title="Agenda Cardinali", page_icon="📅", layout="wide")

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
