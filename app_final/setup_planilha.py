"""
Execute UMA VEZ para criar a estrutura no Google Sheets.
Uso: python setup_planilha.py <planilha_id> <caminho/credenciais.json>
"""
import sys
import gspread
from google.oauth2.service_account import Credentials

MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
         'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']

CARTAO_COLS = ['Inter_Amanda','Nubank_Amanda','BRB_Amanda',
               'Inter_Matheus','Nubank_Matheus','Outros']

FIXOS_INICIAIS = [
    ['Aluguel',              'Contas',        'Boleto', 3500],
    ['Plano de Saúde',       'Saúde',         'Boleto',  800],
    ['Luz',                  'Contas',        'Pix',     120],
    ['Água',                 'Contas',        'Pix',     100],
    ['Internet',             'Contas',        'Pix',     110],
    ['Parcela Cerato x/36',  'Financiamento', 'Boleto', 1201],
    ['Parcela IPVA',         'Transporte',    'Pix',     200],
    ['Estacionamento Osório', 'Transporte',   'Pix',     250],
    ['Fies Matheus',         'Estudos',       'Pix',       0],
    ['Pós Graduação',        'Estudos',       'Boleto',    0],
    ['IPVA 2025',            'Transporte',    'Pix',    2500],
]

ENTRADAS_INICIAIS = {
    'Janeiro':   {'Amanda': 10000, 'Matheus': 7300, 'Extra': 2600},
    'Fevereiro': {'Amanda': 10000, 'Matheus': 7300, 'Extra': 0},
    'Março':     {'Amanda': 10000, 'Matheus': 7300, 'Extra': 2600},
    'Abril':     {'Amanda': 10000, 'Matheus': 7300, 'Extra': 0},
    'Maio':      {'Amanda': 10000, 'Matheus': 7300, 'Extra': 560},
    'Junho':     {'Amanda': 10000, 'Matheus': 6800, 'Extra': 0},
    'Julho':     {'Amanda': 10000, 'Matheus': 7300, 'Extra': 1197},
    'Agosto':    {'Amanda': 10000, 'Matheus': 7300, 'Extra': 400},
    'Setembro':  {'Amanda': 10000, 'Matheus': 7300, 'Extra': 649},
    'Outubro':   {'Amanda': 10000, 'Matheus': 6120, 'Extra': 0},
    'Novembro':  {'Amanda': 10000, 'Matheus': 6800, 'Extra': 0},
    'Dezembro':  {'Amanda': 10000, 'Matheus': 7300, 'Extra': 4987},
}

CARTOES_INICIAIS = {
    'Janeiro':   {'Inter_Amanda': 3111.01, 'Nubank_Amanda': 1801.00, 'Inter_Matheus': 9765.44, 'Nubank_Matheus': 250.00},
    'Fevereiro': {'Inter_Amanda': 2500.00, 'Nubank_Amanda': 1200.00, 'Nubank_Matheus': 891.81},
    'Março':     {'Nubank_Amanda': 130.96},
    'Abril':     {'Inter_Amanda': 1800.00, 'Nubank_Amanda': 1000.00, 'Inter_Matheus': 1836.66},
}


def setup(planilha_id: str, creds_path: str):
    print("Conectando ao Google Sheets...")
    creds = Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    sh = client.open_by_key(planilha_id)
    existing = [ws.title for ws in sh.worksheets()]

    def get_or_create(name, rows=200, cols=20):
        if name not in existing:
            ws = sh.add_worksheet(name, rows=rows, cols=cols)
            print(f"  Aba '{name}' criada.")
        else:
            ws = sh.worksheet(name)
            ws.clear()
            print(f"  Aba '{name}' limpa e recriada.")
        return ws

    # ── Gastos_Fixos ──────────────────────────────────────────────────────────
    ws = get_or_create("Gastos_Fixos", rows=100, cols=20)
    ws.append_row(['Nome', 'Categoria', 'Pgto', 'Valor'] + MESES)
    for fixo in FIXOS_INICIAIS:
        ws.append_row(fixo + [False] * 12)
    print("  ✅ Gastos_Fixos populado.")

    # ── Gastos_Variaveis ──────────────────────────────────────────────────────
    ws2 = get_or_create("Gastos_Variaveis", rows=1000, cols=10)
    ws2.append_row(['ID','Data','Mes','Descricao','Categoria','Pgto','Pessoa','Valor','Parcela'])
    print("  ✅ Gastos_Variaveis pronto (vazio).")

    # ── Cartoes ───────────────────────────────────────────────────────────────
    ws3 = get_or_create("Cartoes", rows=20, cols=8)
    ws3.append_row(['Mes'] + CARTAO_COLS)
    for mes in MESES:
        ci = CARTOES_INICIAIS.get(mes, {})
        ws3.append_row([mes] + [ci.get(c, 0) for c in CARTAO_COLS])
    print("  ✅ Cartoes populado.")

    # ── Entradas ──────────────────────────────────────────────────────────────
    ws4 = get_or_create("Entradas", rows=20, cols=6)
    ws4.append_row(['Mes','Amanda','Matheus','Extra','Observacao'])
    for mes in MESES:
        ei = ENTRADAS_INICIAIS.get(mes, {})
        ws4.append_row([mes, ei.get('Amanda',0), ei.get('Matheus',0), ei.get('Extra',0), ''])
    print("  ✅ Entradas populado.")

    print("\n🎉 Setup concluído com sucesso!")
    print("Próximo passo: compartilhe a planilha com o e-mail da sua service account.")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Uso: python setup_planilha.py <planilha_id> <caminho/credenciais.json>")
        print("Exemplo: python setup_planilha.py 1BxiMVs0XRA... credenciais.json")
        sys.exit(1)
    setup(sys.argv[1], sys.argv[2])
