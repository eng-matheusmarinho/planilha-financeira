import pdfplumber
import re
import io
import streamlit as st
from datetime import date
import uuid

CATEGORIAS = ['Contas','Saúde','Lazer','Transporte','Vestuário','Ifood',
              'Mercado','Assinaturas','Beleza','Estudos','Financiamento',
              'Viagens','Home','Cartões','Antônio','Outros']

# ── Categorização por palavras-chave ─────────────────────────────────────────
KEYWORDS = {
    'Ifood':         ['ifood','ifd*','rappi','uber eat','james'],
    'Mercado':       ['mercado','supermercado','carrefour','extra','pao de acucar','atacadao',
                      'assai','dia ','hortifruti','feira','sacolao'],
    'Transporte':    ['uber','99pop','cabify','posto','shell','ipiranga','petrobras','combustivel',
                      'estacion','metr','onibus','passagem','pedagio','autopass'],
    'Saúde':         ['farmacia','drogaria','droga','ultrafarma','panvel','nissei','laboratorio',
                      'clinica','medico','dentista','hospital','plano de saude','unimed'],
    'Lazer':         ['cinema','ingresso','netflix','spotify','steam','playstation','xbox',
                      'bar ','balada','show','teatro','parque','clube'],
    'Assinaturas':   ['netflix','spotify','amazon prime','hbo','disney','globoplay','youtube',
                      'apple','microsoft','google one','dropbox','canva'],
    'Vestuário':     ['zara','renner','riachuelo','c&a','hm','shein','centauro','netshoes',
                      'nike','adidas','arezzo','lojas americanas','marisa'],
    'Viagens':       ['airbnb','hotel','pousada','booking','decolar','latam','gol','azul',
                      'aeroporto','bagagem'],
    'Beleza':        ['salao','barbearia','cabeleireir','manicure','estetica','perfum',
                      'sephora','o boticario','natura'],
    'Estudos':       ['escola','faculdade','curso','udemy','alura','coursera','duolingo',
                      'livro','amazon livro','livraria'],
    'Home':          ['leroy','tok stok','madeira madeira','etna','havan','ikea','telha norte',
                      'casa','construcao','eletrica'],
    'Financiamento': ['financiamento','parcela','cdc','emprestimo','credito pessoal'],
    'Contas':        ['energia','light','enel','cemig','copasa','sabesp','agua ','internet',
                      'vivo','claro','tim','oi ','net ','aluguel','condominio'],
}

def sugerir_categoria(descricao: str) -> str:
    desc_lower = descricao.lower()
    for cat, kws in KEYWORDS.items():
        for kw in kws:
            if kw in desc_lower:
                return cat
    return 'Outros'


# ── Extração de texto do PDF ──────────────────────────────────────────────────
def extrair_texto(arquivo_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(arquivo_bytes)) as pdf:
        return '\n'.join(p.extract_text() or '' for p in pdf.pages)


def detectar_banco(texto: str) -> str:
    t = texto.lower()
    if 'nubank' in t or 'nu pagamentos' in t:
        return 'Nubank'
    if 'banco inter' in t or 'inter s.a' in t or 'bco inter' in t:
        return 'Inter'
    if 'brb' in t or 'banco de brasilia' in t:
        return 'BRB'
    return 'Desconhecido'


# ── Parser Nubank ─────────────────────────────────────────────────────────────
# Linha típica: "15 JAN Descrição do lançamento 150,00"
# ou com parcela: "15 JAN Descrição 2/12 150,00"
RE_NUBANK = re.compile(
    r'(\d{1,2}\s+[A-Z]{3})\s+(.+?)\s+((?:\d+/\d+\s+)?)([\d\.]+,\d{2})\s*$',
    re.MULTILINE
)
RE_NUBANK_TOTAL = re.compile(r'total\s+[\w\s]*?R?\$?\s*([\d\.]+,\d{2})', re.IGNORECASE)

def parsear_nubank(texto: str) -> list:
    lancamentos = []
    for m in RE_NUBANK.finditer(texto):
        data_str  = m.group(1).strip()
        desc      = m.group(2).strip()
        parcela   = m.group(3).strip()
        valor_str = m.group(4).replace('.', '').replace(',', '.')

        # Ignora linhas de total/pagamento
        desc_low = desc.lower()
        if any(x in desc_low for x in ['pagamento', 'total', 'saldo', 'limite', 'vencimento', 'fatura']):
            continue

        try:
            valor = float(valor_str)
        except ValueError:
            continue

        if valor <= 0:
            continue

        lancamentos.append({
            'data':                data_str,
            'descricao':           desc,
            'valor':               valor,
            'parcela':             parcela,
            'categoria_sugerida':  sugerir_categoria(desc),
        })
    return lancamentos


# ── Parser Inter ──────────────────────────────────────────────────────────────
# Linha típica: "15/01/2026 Descrição do lançamento 150,00"
# ou:           "15/01 Descrição 150,00"
RE_INTER = re.compile(
    r'(\d{1,2}/\d{2}(?:/\d{2,4})?)\s+(.+?)\s+([\d\.]+,\d{2})\s*$',
    re.MULTILINE
)
RE_INTER_PARC = re.compile(r'\b(\d+/\d+)\b')

def parsear_inter(texto: str) -> list:
    lancamentos = []
    for m in RE_INTER.finditer(texto):
        data_str  = m.group(1).strip()
        desc      = m.group(2).strip()
        valor_str = m.group(3).replace('.', '').replace(',', '.')

        desc_low = desc.lower()
        if any(x in desc_low for x in ['pagamento', 'total', 'saldo', 'limite', 'estorno', 'credito']):
            continue

        try:
            valor = float(valor_str)
        except ValueError:
            continue

        if valor <= 0:
            continue

        # Extrai parcela da descrição se existir
        parc_m  = RE_INTER_PARC.search(desc)
        parcela = parc_m.group(1) if parc_m else ''
        if parcela:
            desc = desc.replace(parcela, '').strip()

        lancamentos.append({
            'data':                data_str,
            'descricao':           desc,
            'valor':               valor,
            'parcela':             parcela,
            'categoria_sugerida':  sugerir_categoria(desc),
        })
    return lancamentos


# ── Parser BRB ────────────────────────────────────────────────────────────────
RE_BRB = re.compile(
    r'(\d{2}/\d{2})\s+(\d{2}/\d{2})\s+(.+?)\s+([\d\.]+,\d{2})',
    re.MULTILINE
)

def parsear_brb(texto: str) -> list:
    lancamentos = []
    for m in RE_BRB.finditer(texto):
        data_str  = m.group(1).strip()
        desc      = m.group(3).strip()
        valor_str = m.group(4).replace('.', '').replace(',', '.')

        desc_low = desc.lower()
        if any(x in desc_low for x in ['pagamento','total','saldo','credito','estorno']):
            continue

        try:
            valor = float(valor_str)
        except ValueError:
            continue

        if valor <= 0:
            continue

        lancamentos.append({
            'data':                data_str,
            'descricao':           desc,
            'valor':               valor,
            'parcela':             '',
            'categoria_sugerida':  sugerir_categoria(desc),
        })
    return lancamentos


# ── Parser genérico (fallback) ────────────────────────────────────────────────
RE_GENERICO = re.compile(
    r'(\d{1,2}[/\s]\w{2,3}(?:[/\s]\d{2,4})?)\s+(.+?)\s+([\d\.]+,\d{2})\s*$',
    re.MULTILINE
)

def parsear_generico(texto: str) -> list:
    lancamentos = []
    for m in RE_GENERICO.finditer(texto):
        desc      = m.group(2).strip()
        valor_str = m.group(3).replace('.', '').replace(',', '.')
        desc_low  = desc.lower()
        if any(x in desc_low for x in ['pagamento','total','saldo','limite','credito','estorno']):
            continue
        try:
            valor = float(valor_str)
        except ValueError:
            continue
        if valor <= 0 or valor > 50000:
            continue
        lancamentos.append({
            'data':                m.group(1).strip(),
            'descricao':           desc,
            'valor':               valor,
            'parcela':             '',
            'categoria_sugerida':  sugerir_categoria(desc),
        })
    return lancamentos


# ── Dispatcher ────────────────────────────────────────────────────────────────
def processar_fatura(arquivo_bytes: bytes) -> dict:
    texto = extrair_texto(arquivo_bytes)
    banco = detectar_banco(texto)

    if banco == 'Nubank':
        lancamentos = parsear_nubank(texto)
    elif banco == 'Inter':
        lancamentos = parsear_inter(texto)
    elif banco == 'BRB':
        lancamentos = parsear_brb(texto)
    else:
        lancamentos = parsear_generico(texto)

    # Total da fatura
    total_m = re.search(r'total\D{0,10}([\d\.]+,\d{2})', texto, re.IGNORECASE)
    total   = float(total_m.group(1).replace('.','').replace(',','.')) if total_m else sum(l['valor'] for l in lancamentos)

    return {
        'banco':      banco,
        'total':      total,
        'lancamentos': lancamentos,
        'texto_bruto': texto,
    }


# ── Interface Streamlit ───────────────────────────────────────────────────────
def render_leitor_fatura(mes_sel, meses, pagamentos, adicionar_gasto_fn, refresh_fn):
    st.header("📄 Importar Fatura PDF")
    st.caption("Faça upload da fatura em PDF — os lançamentos são extraídos automaticamente, sem custo")

    arquivo = st.file_uploader(
        "Selecione o PDF da fatura",
        type=['pdf'],
        help="Nubank e Inter são totalmente suportados. BRB e outros bancos têm suporte parcial."
    )

    if not arquivo:
        st.info("👆 Faça upload de um PDF de fatura para começar")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Bancos com suporte completo**")
            st.markdown("- Nubank\n- Banco Inter")
        with col2:
            st.markdown("**Suporte parcial**")
            st.markdown("- BRB\n- Outros (modo genérico)")
        return

    with st.spinner("Lendo e analisando o PDF..."):
        try:
            resultado = processar_fatura(arquivo.read())
        except Exception as e:
            st.error(f"Erro ao processar o PDF: {e}")
            return

    lancamentos = resultado['lancamentos']
    banco       = resultado['banco']
    total       = resultado['total']

    if not lancamentos:
        st.warning("Nenhum lançamento encontrado. O PDF pode estar em formato não suportado ou ser uma imagem escaneada.")
        with st.expander("Ver texto extraído do PDF"):
            st.text(resultado['texto_bruto'][:3000])
        return

    st.success(f"✅ {len(lancamentos)} lançamentos encontrados!")
    c1, c2, c3 = st.columns(3)
    c1.metric("Banco detectado", banco)
    c2.metric("Lançamentos",     len(lancamentos))
    c3.metric("Total fatura",    f"R$ {total:,.2f}".replace(',','X').replace('.',',').replace('X','.'))

    if banco == 'Desconhecido':
        st.warning("Banco não identificado — usando modo genérico. Revise os lançamentos com atenção.")

    st.divider()

    # Controles de importação
    st.subheader("Configurar importação")
    ci1, ci2, ci3 = st.columns(3)
    mes_import    = ci1.selectbox("Mês:", meses, index=meses.index(mes_sel) if mes_sel in meses else 0)
    pgto_import   = ci2.selectbox("Cartão:", pagamentos)
    pessoa_import = ci3.selectbox("Pessoa:", ["Amanda","Matheus","Casa"])

    st.divider()
    st.subheader("Revisar lançamentos")
    st.caption("Desmarque o que não quer importar e ajuste as categorias se necessário")

    # Inicializa estado
    chave = f"lanc_{arquivo.name}"
    if chave not in st.session_state:
        st.session_state[chave]        = [dict(l) for l in lancamentos]
        st.session_state[f"sel_{chave}"] = [True] * len(lancamentos)

    lancs = st.session_state[chave]
    sels  = st.session_state[f"sel_{chave}"]

    # Cabeçalho
    hc = st.columns([0.5, 1.2, 3.5, 2.5, 1.8, 1.5])
    for h, t in zip(hc, ['', 'Data', 'Descrição', 'Categoria', 'Valor (R$)', 'Parcela']):
        h.markdown(f"**{t}**")

    total_sel = 0.0
    for idx, lanc in enumerate(lancs):
        cols = st.columns([0.5, 1.2, 3.5, 2.5, 1.8, 1.5])

        sels[idx] = cols[0].checkbox("", value=sels[idx], key=f"s_{chave}_{idx}", label_visibility='collapsed')
        cols[1].caption(lanc.get('data', ''))

        nova_desc = cols[2].text_input("", value=lanc['descricao'],
                                        key=f"d_{chave}_{idx}", label_visibility='collapsed')
        cat_idx   = CATEGORIAS.index(lanc['categoria_sugerida']) if lanc['categoria_sugerida'] in CATEGORIAS else 0
        nova_cat  = cols[3].selectbox("", CATEGORIAS, index=cat_idx,
                                       key=f"c_{chave}_{idx}", label_visibility='collapsed')
        novo_val  = cols[4].number_input("", value=float(lanc['valor']), min_value=0.0, step=0.01,
                                          key=f"v_{chave}_{idx}", label_visibility='collapsed')
        nova_parc = cols[5].text_input("", value=lanc.get('parcela',''),
                                        key=f"p_{chave}_{idx}", label_visibility='collapsed',
                                        placeholder="ex: 2/12")

        lancs[idx].update({'descricao': nova_desc, 'categoria_sugerida': nova_cat,
                           'valor': novo_val, 'parcela': nova_parc})
        if sels[idx]:
            total_sel += novo_val

    st.divider()
    n_sel = sum(sels)
    total_fmt = f"R$ {total_sel:,.2f}".replace(',','X').replace('.',',').replace('X','.')
    ca, cb = st.columns([3, 1])
    ca.metric(f"Total a importar — {n_sel} de {len(lancs)} lançamentos", total_fmt)

    if cb.button("✅ Importar", type="primary", use_container_width=True):
        if n_sel == 0:
            st.warning("Selecione ao menos um lançamento.")
            return
        with st.spinner(f"Importando {n_sel} lançamentos para {mes_import}..."):
            erros = 0
            for idx, lanc in enumerate(lancs):
                if not sels[idx]:
                    continue
                try:
                    adicionar_gasto_fn([
                        str(uuid.uuid4())[:8],
                        str(date.today()),
                        mes_import,
                        lanc['descricao'],
                        lanc['categoria_sugerida'],
                        pgto_import,
                        pessoa_import,
                        float(lanc['valor']),
                        lanc.get('parcela', '')
                    ])
                except Exception:
                    erros += 1

        if erros == 0:
            st.success(f"🎉 {n_sel} lançamentos importados para {mes_import}!")
            st.session_state.pop(chave, None)
            st.session_state.pop(f"sel_{chave}", None)
            refresh_fn()
        else:
            st.warning(f"Importado com {erros} erro(s). Verifique a conexão com o Sheets.")
