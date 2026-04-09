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

VALOR_COLS = [f'Valor_{m}' for m in MESES]
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

def get_gastos_fixos():
    records = get_ws("Gastos_Fixos").get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        for mes in MESES:
            if mes in df.columns:
                df[mes] = df[mes].apply(lambda x: x is True or x == 'TRUE' or x == 'true')
        for col in VALOR_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

def get_valor_mes(row, mes):
    """Retorna o valor do gasto fixo para o mês específico."""
    col = f'Valor_{mes}'
    v = row.get(col, 0)
    return float(v or 0)

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
        if 'Pago' not in df.columns:
            df['Pago'] = False
        else:
            df['Pago'] = df['Pago'].apply(lambda x: x is True or x == 'TRUE' or x == 'true')
    return df

def get_entradas():
    records = get_ws("Entradas").get_all_records()
    df = pd.DataFrame(records)
    if not df.empty:
        for col in ['Amanda','Matheus','Extra']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df

# ── GASTOS FIXOS ──────────────────────────────────────────────────────────────
def mark_pago(df_row_idx, mes, pago):
    ws = get_ws("Gastos_Fixos")
    headers = ws.row_values(1)
    col = headers.index(mes) + 1
    ws.update_cell(int(df_row_idx) + 2, col, pago)

def update_valor_mes(df_row_idx, mes, valor):
    """Atualiza o valor de um mês específico."""
    ws = get_ws("Gastos_Fixos")
    headers = ws.row_values(1)
    col_name = f'Valor_{mes}'
    if col_name not in headers:
        return
    col = headers.index(col_name) + 1
    ws.update_cell(int(df_row_idx) + 2, col, valor)

def update_gasto_fixo(df_row_idx, nome, cat, pgto):
    """Atualiza nome, categoria e pgto — sem alterar valores."""
    ws = get_ws("Gastos_Fixos")
    row = int(df_row_idx) + 2
    headers = ws.row_values(1)
    ws.update_cell(row, headers.index('Nome') + 1, nome)
    ws.update_cell(row, headers.index('Categoria') + 1, cat)
    ws.update_cell(row, headers.index('Pgto') + 1, pgto)

def add_gasto_fixo(row_data):
    get_ws("Gastos_Fixos").append_row(row_data)

def delete_gasto_fixo(df_row_idx):
    get_ws("Gastos_Fixos").delete_rows(int(df_row_idx) + 2)

# ── GASTOS VARIÁVEIS ──────────────────────────────────────────────────────────
def add_gasto(row_data):
    get_ws("Gastos_Variaveis").append_row(row_data)

def delete_gasto(df_row_idx):
    get_ws("Gastos_Variaveis").delete_rows(int(df_row_idx) + 2)

def update_gasto(df_row_idx, desc, cat, pgto, pessoa, val):
    ws = get_ws("Gastos_Variaveis")
    row = int(df_row_idx) + 2
    headers = ws.row_values(1)
    ws.update_cell(row, headers.index('Descricao') + 1, desc)
    ws.update_cell(row, headers.index('Categoria') + 1, cat)
    ws.update_cell(row, headers.index('Pgto') + 1, pgto)
    ws.update_cell(row, headers.index('Pessoa') + 1, pessoa)
    ws.update_cell(row, headers.index('Valor') + 1, val)

# ── CARTÕES ───────────────────────────────────────────────────────────────────
def update_cartao(mes, col_name, valor):
    ws = get_ws("Cartoes")
    headers = ws.row_values(1)
    if col_name not in headers:
        ws.update_cell(1, len(headers) + 1, col_name)
        headers.append(col_name)
    col = headers.index(col_name) + 1
    meses_col = ws.col_values(1)
    if mes in meses_col:
        ws.update_cell(meses_col.index(mes) + 1, col, valor)

# ── ENTRADAS ──────────────────────────────────────────────────────────────────
def update_entrada(mes, col_name, valor):
    ws = get_ws("Entradas")
    headers = ws.row_values(1)
    if col_name not in headers:
        return
    col = headers.index(col_name) + 1
    meses_col = ws.col_values(1)
    if mes in meses_col:
        ws.update_cell(meses_col.index(mes) + 1, col, valor)
