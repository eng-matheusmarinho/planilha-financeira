import gspread
import streamlit as st
from google.oauth2.service_account import Credentials
import pandas as pd

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
         'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

CARTAO_COLS = ['Inter_Amanda','Nubank_Amanda','BRB_Amanda',
               'Inter_Matheus','Nubank_Matheus','Outros']

@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)

def get_sheet():
    return get_client().open_by_key(st.secrets["sheets"]["planilha_id"])

def get_ws(name):
    return get_sheet().worksheet(name)

# ── READ ──────────────────────────────────────────────────────────────────────
def get_gastos_fixos():
    records = get_ws("Gastos_Fixos").get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        for mes in MESES:
            if mes in df.columns:
                df[mes] = df[mes].apply(lambda x: x is True or x == 'TRUE' or x == 'true')
        if 'Valor' in df.columns:
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
    return df

def get_gastos_variaveis():
    records = get_ws("Gastos_Variaveis").get_all_records()
    df = pd.DataFrame(records)
    if not df.empty and 'Valor' in df.columns:
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0)
    return df

def get_cartoes():
    records = get_ws("Cartoes").get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        for col in CARTAO_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def get_entradas():
    records = get_ws("Entradas").get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        for col in ['Amanda', 'Matheus', 'Extra']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# ── WRITE ─────────────────────────────────────────────────────────────────────
def mark_pago(df_row_idx, mes, pago):
    ws = get_ws("Gastos_Fixos")
    headers = ws.row_values(1)
    col = headers.index(mes) + 1
    gsheet_row = int(df_row_idx) + 2
    ws.update_cell(gsheet_row, col, pago)

def add_gasto_fixo(row_data):
    get_ws("Gastos_Fixos").append_row(row_data)

def add_gasto(row_data):
    get_ws("Gastos_Variaveis").append_row(row_data)

def delete_gasto(df_row_idx):
    ws = get_ws("Gastos_Variaveis")
    ws.delete_rows(int(df_row_idx) + 2)

def update_cartao(mes, col_name, valor):
    ws = get_ws("Cartoes")
    headers = ws.row_values(1)
    if col_name not in headers:
        return
    col = headers.index(col_name) + 1
    meses_col = ws.col_values(1)
    if mes not in meses_col:
        return
    ws.update_cell(meses_col.index(mes) + 1, col, valor)

def update_entrada(mes, col_name, valor):
    ws = get_ws("Entradas")
    headers = ws.row_values(1)
    if col_name not in headers:
        return
    col = headers.index(col_name) + 1
    meses_col = ws.col_values(1)
    if mes not in meses_col:
        return
    ws.update_cell(meses_col.index(mes) + 1, col, valor)
