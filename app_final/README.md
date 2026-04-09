# 💰 Controle Financeiro — Amanda & Matheus

Painel online conectado ao Google Sheets. Tudo que você editar no painel salva na planilha automaticamente.

---

## Funcionalidades

- 📊 **Dashboard** — visão geral do mês com barra de comprometimento da renda
- ✅ **Contas Fixas** — marcar contas como pagas, ver pendentes vs pago
- ➕ **Gastos Variáveis** — lançar e excluir gastos, filtrar por categoria
- 💳 **Cartões** — lançar faturas por cartão (Inter, Nubank, BRB)
- 💰 **Entradas** — atualizar salários e extras por mês
- 📈 **Relatório Anual** — visão completa do ano com gráficos e tabela

---

## Como publicar (passo a passo)

### PASSO 1 — Criar conta de serviço no Google Cloud

1. Acesse https://console.cloud.google.com
2. Crie um projeto novo (ou use um existente)
3. No menu lateral: **APIs e Serviços → Biblioteca**
4. Ative: **Google Sheets API** e **Google Drive API**
5. Vá em: **APIs e Serviços → Credenciais**
6. Clique em **Criar Credenciais → Conta de serviço**
7. Dê um nome (ex: `controle-financeiro`) e clique em **Criar**
8. Na conta criada, clique em **Chaves → Adicionar chave → JSON**
9. Salve o arquivo JSON baixado como `credenciais.json`

### PASSO 2 — Criar a planilha no Google Sheets

1. Acesse https://sheets.google.com e crie uma planilha nova
2. Copie o **ID** da URL: `docs.google.com/spreadsheets/d/**ESTE_TRECHO**/edit`
3. Clique em **Compartilhar** e adicione o e-mail da service account
   (está no campo `client_email` do arquivo `credenciais.json`)
   com permissão de **Editor**

### PASSO 3 — Executar o setup inicial

Com Python instalado, rode no terminal:

```bash
pip install gspread google-auth
python setup_planilha.py SEU_ID_DA_PLANILHA caminho/credenciais.json
```

Isso cria as 4 abas necessárias (Gastos_Fixos, Gastos_Variaveis, Cartoes, Entradas) já com os dados iniciais.

### PASSO 4 — Subir no GitHub

1. Crie uma conta em https://github.com
2. Crie um repositório novo chamado `controle-financeiro` (público)
3. Faça upload de todos os arquivos desta pasta **exceto** `credenciais.json`

### PASSO 5 — Publicar no Streamlit Cloud

1. Acesse https://share.streamlit.io com sua conta GitHub
2. Clique em **New app**
3. Selecione o repositório `controle-financeiro`
4. Main file: `app.py`
5. Clique em **Advanced settings → Secrets**
6. Cole o conteúdo do arquivo `secrets.toml.example` preenchido com seus dados
7. Clique em **Deploy!**

Em ~2 minutos o app estará online com uma URL pública que você pode salvar nos favoritos.

---

## Estrutura dos arquivos

```
controle-financeiro/
├── app.py                          ← aplicação principal
├── gsheets.py                      ← conexão e operações no Google Sheets
├── setup_planilha.py               ← script de setup inicial (rodar 1x)
├── requirements.txt                ← dependências Python
└── .streamlit/
    └── secrets.toml.example        ← modelo de credenciais
```

## Estrutura da planilha (criada automaticamente)

| Aba | Descrição |
|-----|-----------|
| `Gastos_Fixos` | Contas fixas com status pago/pendente por mês |
| `Gastos_Variaveis` | Gastos avulsos lançados pelo painel |
| `Cartoes` | Faturas mensais por cartão |
| `Entradas` | Salários e extras por mês |
