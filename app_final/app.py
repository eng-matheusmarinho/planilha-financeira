import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import uuid
import gsheets as gs

st.set_page_config(
    page_title="Controle Financeiro",
    page_icon="💰",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── CSS Mobile-first ──────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Container mais largo em desktop, full em mobile */
.block-container { padding: 1rem 1rem 3rem; max-width: 860px; }

/* Tabelas responsivas */
.stDataFrame { overflow-x: auto; }

/* Botões mais fáceis de tocar */
.stButton > button { min-height: 2.4rem; font-size: 0.9rem; }

/* Inputs mais confortáveis */
.stTextInput input, .stNumberInput input, .stSelectbox select {
    font-size: 1rem !important;
}

/* Métricas compactas */
[data-testid="metric-container"] {
    background: var(--secondary-background-color);
    border-radius: 8px;
    padding: 0.6rem 0.8rem;
}

/* Remove padding excessivo em mobile */
@media (max-width: 640px) {
    .block-container { padding: 0.5rem 0.5rem 4rem; }
    h1 { font-size: 1.4rem !important; }
    h2 { font-size: 1.2rem !important; }
    h3 { font-size: 1rem !important; }
    [data-testid="metric-container"] { padding: 0.5rem; }
}
</style>
""", unsafe_allow_html=True)

MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
         'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
MESES_ABR = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

CATEGORIAS = ['Contas','Saúde','Lazer','Transporte','Vestuário','Ifood',
              'Mercado','Assinaturas','Beleza','Estudos','Financiamento',
              'Viagens','Home','Cartões','Antônio','Outros']

PAGAMENTOS = ['Pix','Boleto','Dinheiro','Débito',
              'Crédito Inter Amanda','Crédito Nubank Amanda','Crédito BRB Amanda',
              'Crédito Inter Matheus','Crédito Nubank Matheus']

CARTAO_COLS   = ['Inter_Amanda','Nubank_Amanda','BRB_Amanda','Inter_Matheus','Nubank_Matheus','Outros']
CARTAO_LABELS = ['Inter Amanda','Nubank Amanda','BRB Amanda','Inter Matheus','Nubank Matheus','Outros']

CAT_COLORS = {
    'Contas':'#378ADD','Saúde':'#1D9E75','Lazer':'#D4537E','Transporte':'#EF9F27',
    'Vestuário':'#9B72D0','Ifood':'#E24B4A','Mercado':'#0F6E56',
    'Assinaturas':'#63B3ED','Beleza':'#F4C0D1','Estudos':'#BA7517',
    'Financiamento':'#5F5E5A','Viagens':'#5DCAA5','Home':'#888780',
    'Cartões':'#534AB7','Antônio':'#F5C4B3','Outros':'#B4B2A9'
}

def fmt(v):
    try:
        return f"R$ {float(v):,.2f}".replace(',','X').replace('.',',').replace('X','.')
    except Exception:
        return "R$ 0,00"

def plot_cfg():
    return dict(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')

# ── Navigation ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("💰 Controle Financeiro")
    st.caption("Amanda & Matheus · 2026")
    st.divider()
    mes_idx = st.selectbox("Mês de referência", range(12),
                           format_func=lambda i: MESES[i],
                           index=date.today().month - 1)
    mes_sel = MESES[mes_idx]
    st.divider()
    page = st.radio("Página", [
        "💰 Entradas",
        "✅ Contas Fixas",
        "💳 Cartões",
        "➕ Gastos Variáveis",
        "📊 Dashboard",
        "📈 Relatório Anual",
    ])
    st.divider()
    if st.button("🔄 Atualizar dados", use_container_width=True):
        refresh()
    st.caption("Dados em cache por sessão")

# ── Cabeçalho mobile ──────────────────────────────────────────────────────────
c_title, c_mes, c_refresh = st.columns([3, 2, 1])
c_title.markdown(f"### 💰 {page.split(' ',1)[1] if ' ' in page else page}")
c_mes.markdown(f"<div style='text-align:right;padding-top:8px;font-size:0.9rem;color:gray'>{mes_sel}</div>", unsafe_allow_html=True)
if c_refresh.button("🔄", help="Atualizar dados"):
    refresh()
st.divider()

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=600)
def load_all():
    return (
        gs.get_gastos_fixos(),
        gs.get_gastos_variaveis(),
        gs.get_cartoes(),
        gs.get_entradas(),
    )

def refresh():
    st.cache_data.clear()
    for k in ['df_fixos','df_var','df_cart','df_ent']:
        st.session_state.pop(k, None)
    st.rerun()

# Carrega dados apenas uma vez por sessão
if 'df_fixos' not in st.session_state:
    import time
    tentativas = 3
    for t in range(tentativas):
        try:
            (st.session_state.df_fixos,
             st.session_state.df_var,
             st.session_state.df_cart,
             st.session_state.df_ent) = load_all()
            break
        except Exception as e:
            erro_str = str(e)
            if '429' in erro_str and t < tentativas - 1:
                with st.spinner(f"Aguardando limite do Google Sheets... tentativa {t+2}/{tentativas}"):
                    time.sleep(15)
            else:
                st.error("❌ Erro ao conectar com Google Sheets. Aguarde 1 minuto e recarregue a página.")
                st.caption(f"Detalhe: {erro_str[:200]}")
                if st.button("🔄 Tentar novamente"):
                    st.cache_data.clear()
                    st.rerun()
                st.stop()

df_fixos = st.session_state.df_fixos
df_var   = st.session_state.df_var
df_cart  = st.session_state.df_cart
df_ent   = st.session_state.df_ent

# ── Helpers ───────────────────────────────────────────────────────────────────
def entradas_mes(mes):
    r = df_ent[df_ent['Mes'] == mes]
    if r.empty:
        return 0.0, 0.0, 0.0
    row = r.iloc[0]
    return float(row.get('Amanda',0) or 0), float(row.get('Matheus',0) or 0), float(row.get('Extra',0) or 0)

def cartao_total_mes(mes):
    r = df_cart[df_cart['Mes'] == mes]
    if r.empty:
        return 0.0
    return sum(float(r.iloc[0].get(c, 0) or 0) for c in gs.CARTAO_COLS)

def fixos_mes(mes):
    if df_fixos.empty or mes not in df_fixos.columns:
        return 0.0, 0.0
    pagos = float(df_fixos[df_fixos[mes] == True].apply(lambda r: gs.get_valor_mes(r, mes), axis=1).sum())
    pend  = float(df_fixos[df_fixos[mes] != True].apply(lambda r: gs.get_valor_mes(r, mes), axis=1).sum())
    return pagos, pend

def var_mes(mes):
    if df_var.empty:
        return pd.DataFrame()
    return df_var[df_var['Mes'] == mes].copy()


# ════════════════════════════════════════════════════════════════════════════
# 💰 ENTRADAS
# ════════════════════════════════════════════════════════════════════════════
if page == "💰 Entradas":

    row_e = df_ent[df_ent['Mes'] == mes_sel]
    ev = {'Amanda': 0.0, 'Matheus': 0.0, 'Extra': 0.0, 'Observacao': ''}
    if not row_e.empty:
        r = row_e.iloc[0]
        for k in ev:
            ev[k] = r.get(k, 0) or 0

    with st.form("entradas_form"):
        c1, c2 = st.columns(2)
        am = c1.number_input("Amanda (R$)",  value=float(ev['Amanda']),  min_value=0.0, step=100.0)
        ma = c2.number_input("Matheus (R$)", value=float(ev['Matheus']), min_value=0.0, step=100.0)
        ex  = st.number_input("Extra / bônus (R$)", value=float(ev['Extra']), min_value=0.0, step=100.0)
        obs = st.text_input("Observação", value=str(ev['Observacao']))
        st.metric("Total do mês", fmt(am + ma + ex))
        if st.form_submit_button("💾 Salvar entradas", use_container_width=True, type="primary"):
            with st.spinner("Salvando..."):
                gs.update_entrada(mes_sel, 'Amanda', am)
                gs.update_entrada(mes_sel, 'Matheus', ma)
                gs.update_entrada(mes_sel, 'Extra', ex)
                gs.update_entrada(mes_sel, 'Observacao', obs)
            st.success("Entradas atualizadas!")
            refresh()

    st.divider()
    st.subheader("Entradas anuais")
    anos_a, anos_m, anos_e = [], [], []
    for mes in MESES:
        a_, m_, e_ = entradas_mes(mes)
        anos_a.append(a_); anos_m.append(m_); anos_e.append(e_)

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Amanda',  x=MESES_ABR, y=anos_a, marker_color='#1D9E75'))
    fig.add_trace(go.Bar(name='Matheus', x=MESES_ABR, y=anos_m, marker_color='#378ADD'))
    fig.add_trace(go.Bar(name='Extra',   x=MESES_ABR, y=anos_e, marker_color='#EF9F27'))
    fig.update_layout(barmode='stack', height=280,
                      margin=dict(l=0,r=0,t=10,b=0),
                      legend=dict(orientation='h', y=1.12), **plot_cfg())
    st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# ✅ CONTAS FIXAS
# ════════════════════════════════════════════════════════════════════════════
elif page == "✅ Contas Fixas":

    fp, pp = fixos_mes(mes_sel)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total", fmt(fp + pp))
    c2.metric("✅ Pago", fmt(fp))
    c3.metric("⏳ Pendente", fmt(pp))
    st.divider()

    if df_fixos.empty:
        st.info("Nenhuma conta fixa cadastrada.")
    elif mes_sel not in df_fixos.columns:
        st.warning(f"Coluna '{mes_sel}' não encontrada.")
    else:
        h1,h2,h3,h4,h5 = st.columns([3,2,1.8,1.5,2.5])
        for h,t in zip([h1,h2,h3,h4,h5],['Nome','Categoria','Valor no mês','Status','Ações']):
            h.markdown(f"<small style='color:gray'><b>{t}</b></small>", unsafe_allow_html=True)
        st.divider()

        for i, row in df_fixos.iterrows():
            pago    = row.get(mes_sel, False) == True
            val_mes = gs.get_valor_mes(row, mes_sel)
            c1,c2,c3,c4,c5 = st.columns([3, 2, 1.8, 1.5, 2.5])
            c1.write(row.get('Nome',''))
            c2.write(row.get('Categoria',''))
            c3.write(fmt(val_mes))
            c4.markdown("✅ Pago" if pago else "⏳ Pendente")
            with c5:
                b1, b2, b3 = st.columns(3)
                icon = "☑️" if pago else "⬜"
                if b1.button(icon, key=f"pago_{i}", use_container_width=True, help="Marcar/desmarcar pago"):
                    gs.mark_pago(i, mes_sel, not pago)
                    st.session_state.df_fixos.at[i, mes_sel] = not pago
                    st.rerun()
                if b2.button("✏️", key=f"edit_{i}", use_container_width=True, help="Editar"):
                    st.session_state[f'editing_{i}'] = True
                    st.rerun()
                if b3.button("🗑️", key=f"del_fixo_{i}", use_container_width=True, help="Excluir"):
                    gs.delete_gasto_fixo(i)
                    refresh()

            if st.session_state.get(f'editing_{i}'):
                with st.form(f"edit_form_{i}"):
                    st.caption(f"Editando: **{row.get('Nome','')}** — {mes_sel}")
                    ec1, ec2, ec3 = st.columns(3)
                    novo_nome = ec1.text_input("Nome", value=row.get('Nome',''))
                    nova_cat  = ec2.selectbox("Categoria", CATEGORIAS,
                                             index=CATEGORIAS.index(row.get('Categoria','Outros'))
                                             if row.get('Categoria') in CATEGORIAS else 0)
                    novo_pgto = ec3.selectbox("Pgto", ['Pix','Boleto','Dinheiro','Débito'])
                    novo_val  = st.number_input(
                        f"Valor em {mes_sel} (R$)",
                        value=gs.get_valor_mes(row, mes_sel),
                        min_value=0.0, step=10.0
                    )
                    sc1, sc2 = st.columns(2)
                    if sc1.form_submit_button("💾 Salvar", use_container_width=True, type="primary"):
                        gs.update_gasto_fixo(i, novo_nome, nova_cat, novo_pgto)
                        gs.update_valor_mes(i, mes_sel, novo_val)
                        st.session_state.pop(f'editing_{i}', None)
                        refresh()
                    if sc2.form_submit_button("Cancelar", use_container_width=True):
                        st.session_state.pop(f'editing_{i}', None)
                        st.rerun()
            st.divider()



    with st.expander("➕ Adicionar nova conta fixa"):
        with st.form("nova_fixa"):
            c1, c2, c3 = st.columns(3)
            nome = c1.text_input("Nome da conta *")
            cat  = c2.selectbox("Categoria", CATEGORIAS)
            pgto = c3.selectbox("Forma de pagamento", ['Pix','Boleto','Dinheiro','Débito'])
            val_padrao = st.number_input("Valor padrão (R$) — será aplicado a todos os meses *", min_value=0.0, step=10.0)
            if st.form_submit_button("Adicionar", use_container_width=True, type="primary"):
                if nome and val_padrao > 0:
                    # Nome, Categoria, Pgto + FALSE*12 meses pago + val_padrao*12 meses valor
                    row = [nome, cat, pgto] + [False]*12 + [val_padrao]*12
                    gs.add_gasto_fixo(row)
                    st.success(f"'{nome}' adicionado!")
                    refresh()
                else:
                    st.warning("Preencha nome e valor.")


# ════════════════════════════════════════════════════════════════════════════
# 💳 CARTÕES
# ════════════════════════════════════════════════════════════════════════════
elif page == "💳 Cartões":

    row_c = df_cart[df_cart['Mes'] == mes_sel]
    cart_vals = {c: float(row_c.iloc[0].get(c, 0) or 0) for c in CARTAO_COLS} \
                if not row_c.empty else {c: 0.0 for c in CARTAO_COLS}
    cart_pago = bool(row_c.iloc[0].get('Pago', False)) if not row_c.empty else False
    total_c   = sum(cart_vals.values())

    a, m, _ = entradas_mes(mes_sel)
    c1, c2 = st.columns(2)
    c1.metric("Total cartões", fmt(total_c))
    c2.metric("Status", "✅ Paga" if cart_pago else "⏳ Pendente")
    c3, c4 = st.columns(2)
    c3.metric("Amanda",  fmt(sum(cart_vals[c] for c in ['Inter_Amanda','Nubank_Amanda','BRB_Amanda'])))
    c4.metric("Matheus", fmt(sum(cart_vals[c] for c in ['Inter_Matheus','Nubank_Matheus','Outros'])))

    if (a + m) > 0:
        pct = total_c / (a + m)
        st.caption(f"💳 Cartões representam **{pct*100:.1f}%** da renda do casal")
        st.progress(min(pct, 1.0))

    st.subheader("Atualizar faturas")

    with st.form("cartoes_form"):
        st.markdown("**Amanda**")
        ca1, ca2, ca3 = st.columns(3)
        new_vals = {}
        new_vals['Inter_Amanda']   = ca1.number_input("Inter Amanda",  value=cart_vals['Inter_Amanda'],  min_value=0.0, step=0.01)
        new_vals['Nubank_Amanda']  = ca2.number_input("Nubank Amanda", value=cart_vals['Nubank_Amanda'], min_value=0.0, step=0.01)
        new_vals['BRB_Amanda']     = ca3.number_input("BRB Amanda",    value=cart_vals['BRB_Amanda'],    min_value=0.0, step=0.01)
        st.markdown("**Matheus**")
        cm1, cm2, cm3 = st.columns(3)
        new_vals['Inter_Matheus']  = cm1.number_input("Inter Matheus",  value=cart_vals['Inter_Matheus'],  min_value=0.0, step=0.01)
        new_vals['Nubank_Matheus'] = cm2.number_input("Nubank Matheus", value=cart_vals['Nubank_Matheus'], min_value=0.0, step=0.01)
        new_vals['Outros']         = cm3.number_input("Outros",         value=cart_vals['Outros'],         min_value=0.0, step=0.01)
        novo_total = sum(new_vals.values())
        st.metric("Total faturas", fmt(novo_total))
        if st.form_submit_button("💾 Salvar valores", use_container_width=True, type="primary"):
            with st.spinner("Salvando..."):
                for col_name, valor in new_vals.items():
                    gs.update_cartao(mes_sel, col_name, valor)
            st.success("Faturas salvas!")
            refresh()

    # Status de pagamento por cartão — fora do form
    st.markdown("**Status de pagamento por cartão**")
    CARTAO_PAGO_KEYS = ['Pago_Inter_Amanda','Pago_Nubank_Amanda','Pago_BRB_Amanda',
                        'Pago_Inter_Matheus','Pago_Nubank_Matheus','Pago_Outros']
    pago_por_cartao = {}
    if not row_c.empty:
        for k in CARTAO_PAGO_KEYS:
            v = row_c.iloc[0].get(k, False)
            pago_por_cartao[k] = v is True or v == 'TRUE' or v == 'true'
    else:
        pago_por_cartao = {k: False for k in CARTAO_PAGO_KEYS}

    pa1, pa2, pa3 = st.columns(3)
    pm1, pm2, pm3 = st.columns(3)
    checks = {
        'Pago_Inter_Amanda':  pa1.checkbox("Inter Amanda paga",   value=pago_por_cartao['Pago_Inter_Amanda'],  key="ck_ia"),
        'Pago_Nubank_Amanda': pa2.checkbox("Nubank Amanda paga",  value=pago_por_cartao['Pago_Nubank_Amanda'], key="ck_na"),
        'Pago_BRB_Amanda':    pa3.checkbox("BRB Amanda paga",     value=pago_por_cartao['Pago_BRB_Amanda'],    key="ck_ba"),
        'Pago_Inter_Matheus': pm1.checkbox("Inter Matheus pago",  value=pago_por_cartao['Pago_Inter_Matheus'], key="ck_im"),
        'Pago_Nubank_Matheus':pm2.checkbox("Nubank Matheus pago", value=pago_por_cartao['Pago_Nubank_Matheus'],key="ck_nm"),
        'Pago_Outros':        pm3.checkbox("Outros pagos",        value=pago_por_cartao['Pago_Outros'],        key="ck_ou"),
    }
    if st.button("💾 Salvar status de pagamento", use_container_width=False):
        with st.spinner("Salvando..."):
            for pago_key, pago_val in checks.items():
                gs.update_cartao(mes_sel, pago_key, pago_val)
        st.success("Status salvo!")
        refresh()

    pago_total = sum(cart_vals[c] for c, k in zip(CARTAO_COLS, CARTAO_PAGO_KEYS) if checks[k])
    pend_total = total_c - pago_total
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Total", fmt(total_c))
    mc2.metric("✅ Pago", fmt(pago_total))
    mc3.metric("⏳ Pendente", fmt(pend_total))

    st.divider()

    # Gráfico 1 — histórico total
    st.subheader("Histórico anual de cartões")
    historico = []
    for mes in MESES:
        r = df_cart[df_cart['Mes'] == mes]
        t = sum(float(r.iloc[0].get(c,0) or 0) for c in CARTAO_COLS) if not r.empty else 0
        historico.append(t)

    cores_hist = ['#1D9E75' if (df_cart[df_cart['Mes']==m].iloc[0].get('Pago', False) if not df_cart[df_cart['Mes']==m].empty else False) else '#D4537E' for m in MESES]
    fig1 = go.Figure(go.Bar(x=MESES_ABR, y=historico, marker_color=cores_hist, name='Total'))
    fig1.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0),
                       title_text="Verde = pago · Vermelho = pendente", **plot_cfg())
    st.plotly_chart(fig1, use_container_width=True)

    # Gráfico 2 — por cartão no mês selecionado
    st.subheader(f"Por cartão — {mes_sel}")
    vals_cart = [cart_vals[c] for c in CARTAO_COLS]
    cores_cart = ['#1D9E75','#378ADD','#534AB7','#D4537E','#EF9F27','#888780']
    fig2 = go.Figure(go.Bar(
        x=CARTAO_LABELS, y=vals_cart,
        marker_color=cores_cart, text=[fmt(v) for v in vals_cart],
        textposition='outside'
    ))
    fig2.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=40), **plot_cfg())
    st.plotly_chart(fig2, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# ➕ GASTOS VARIÁVEIS
# ════════════════════════════════════════════════════════════════════════════
elif page == "➕ Gastos Variáveis":
    st.header(f"➕ Gastos Variáveis — {mes_sel}")
    st.caption("Detalhamento dos gastos com cartão — não entra no balanço financeiro")

    with st.form("novo_gasto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        desc   = c1.text_input("Descrição *")
        val    = c2.number_input("Valor (R$) *", min_value=0.0, step=0.01)
        c3, c4, c5 = st.columns(3)
        cat    = c3.selectbox("Categoria", CATEGORIAS)
        pgto   = c4.selectbox("Cartão / Pagamento", PAGAMENTOS)
        pessoa = c5.selectbox("Pessoa", ["Amanda","Matheus","Casa"])
        c6, c7 = st.columns(2)
        data_g  = c6.date_input("Data", value=date.today())
        parcela = c7.text_input("Parcela (ex: 2/12)", placeholder="Opcional")
        if st.form_submit_button("✓ Adicionar gasto", use_container_width=True, type="primary"):
            if desc and val > 0:
                gs.add_gasto([str(uuid.uuid4())[:8], str(data_g), mes_sel,
                              desc, cat, pgto, pessoa, val, parcela or ''])
                st.success(f"Lançado: {desc} — {fmt(val)}")
                refresh()
            else:
                st.warning("Preencha descrição e valor.")

    st.divider()

    vm = var_mes(mes_sel)
    if vm.empty:
        st.info(f"Nenhum gasto lançado em {mes_sel}.")
    else:
        total_var = float(vm['Valor'].sum())
        cats_disp = ['Todas'] + sorted(vm['Categoria'].dropna().unique().tolist())
        c_fil, c_pes, _ = st.columns([2, 2, 4])
        cat_fil = c_fil.selectbox("Filtrar categoria", cats_disp)
        pes_fil = c_pes.selectbox("Filtrar pessoa", ['Todas','Amanda','Matheus','Casa'])
        vm_fil  = vm.copy()
        if cat_fil != 'Todas': vm_fil = vm_fil[vm_fil['Categoria'] == cat_fil]
        if pes_fil != 'Todas': vm_fil = vm_fil[vm_fil['Pessoa'] == pes_fil]

        st.caption(f"{len(vm_fil)} lançamentos · Total filtrado: **{fmt(vm_fil['Valor'].sum())}** · Total mês: **{fmt(total_var)}**")
        st.divider()

        for _, row in vm_fil.iterrows():
            full_row = df_var[df_var['ID'] == row['ID']]
            if full_row.empty:
                continue
            fidx = full_row.index[0]
            row_id = str(row['ID'])
            c1,c2,c3,c4,c5,c6,c7 = st.columns([3,1.8,1.5,1.5,1.2,1,1])
            c1.write(row.get('Descricao',''))
            c2.write(row.get('Categoria',''))
            c3.write(fmt(row.get('Valor',0)))
            c4.write(row.get('Pessoa',''))
            c5.write(str(row.get('Data',''))[:10])

            if c6.button("✏️", key=f"gedit_btn_{row_id}"):
                st.session_state['gedit_' + row_id] = True
            if c7.button("🗑️", key=f"gdel_{row_id}"):
                with st.spinner("Excluindo..."):
                    gs.delete_gasto(fidx)
                refresh()

            if st.session_state.get('gedit_' + row_id):
                with st.form(f"gform_{row_id}"):
                    gc1, gc2 = st.columns(2)
                    nd = gc1.text_input("Descrição", value=row.get('Descricao',''))
                    nv = gc2.number_input("Valor", value=float(row.get('Valor',0)), min_value=0.0, step=0.01)
                    gc3, gc4, gc5 = st.columns(3)
                    nc = gc3.selectbox("Categoria", CATEGORIAS,
                                      index=CATEGORIAS.index(row.get('Categoria','Outros'))
                                      if row.get('Categoria') in CATEGORIAS else 0)
                    np_ = gc4.selectbox("Pagamento", PAGAMENTOS)
                    npe = gc5.selectbox("Pessoa", ["Amanda","Matheus","Casa"])
                    gs1, gs2 = st.columns(2)
                    if gs1.form_submit_button("💾 Salvar", use_container_width=True, type="primary"):
                        with st.spinner("Salvando..."):
                            gs.update_gasto(fidx, nd, nc, np_, npe, nv)
                        st.session_state.pop('gedit_' + row_id, None)
                        refresh()
                    if gs2.form_submit_button("Cancelar", use_container_width=True):
                        st.session_state.pop('gedit_' + row_id, None)
                        st.rerun()
            st.divider()

        # Gráfico por categoria
        st.subheader("Resumo por categoria")
        cat_sum = vm.groupby('Categoria')['Valor'].sum().sort_values(ascending=True)
        colors  = [CAT_COLORS.get(c, '#888') for c in cat_sum.index]
        fig = go.Figure(go.Bar(
            x=cat_sum.values, y=cat_sum.index,
            orientation='h', marker_color=colors,
            text=[fmt(v) for v in cat_sum.values], textposition='outside'
        ))
        fig.update_layout(height=max(220, len(cat_sum)*38+60),
                          margin=dict(l=0,r=80,t=0,b=0), **plot_cfg())
        st.plotly_chart(fig, use_container_width=True)

        # Resumo por pessoa
        st.subheader("Por pessoa")
        pes_sum = vm.groupby('Pessoa')['Valor'].sum()
        fig2 = go.Figure(go.Pie(
            labels=pes_sum.index, values=pes_sum.values,
            hole=0.5, marker_colors=['#1D9E75','#378ADD','#EF9F27']
        ))
        fig2.update_layout(height=260, margin=dict(l=0,r=0,t=0,b=0),
                           showlegend=True, **plot_cfg())
        st.plotly_chart(fig2, use_container_width=True)




# ════════════════════════════════════════════════════════════════════════════
# 📊 DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":

    a, m, ex = entradas_mes(mes_sel)
    entrada   = a + m + ex
    cart      = cartao_total_mes(mes_sel)
    fp, pp    = fixos_mes(mes_sel)
    fixos     = fp + pp
    vm        = var_mes(mes_sel)
    saida     = fixos + cart
    saldo     = entrada - saida

    c1, c2 = st.columns(2)
    c1.metric("💵 Entradas",    fmt(entrada))
    c2.metric("💹 Saldo",       fmt(saldo), delta=fmt(saldo))
    c3, c4 = st.columns(2)
    c3.metric("✅ Fixos pagos", fmt(fp), delta=f"-{fmt(pp)} pendente", delta_color="inverse")
    c4.metric("💳 Cartões",     fmt(cart))

    if entrada > 0:
        pct = min(saida / entrada, 1.0)
        cor = "🟢" if pct < 0.7 else "🟡" if pct < 0.9 else "🔴"
        st.caption(f"{cor} Comprometido: **{pct*100:.1f}%** — {fmt(saida)} de {fmt(entrada)}")
        st.progress(pct)

    st.divider()
    st.subheader("Visão anual")
    anos_e, anos_f, anos_c = [], [], []
    for mes in MESES:
        a_, m_, e_ = entradas_mes(mes)
        anos_e.append(a_ + m_ + e_)
        f_, p_ = fixos_mes(mes)
        anos_f.append(f_ + p_)
        anos_c.append(cartao_total_mes(mes))

    fig = go.Figure()
    fig.add_trace(go.Bar(name='Entradas', x=MESES_ABR, y=anos_e, marker_color='#1D9E75'))
    fig.add_trace(go.Bar(name='Fixos',    x=MESES_ABR, y=anos_f, marker_color='#378ADD'))
    fig.add_trace(go.Bar(name='Cartões',  x=MESES_ABR, y=anos_c, marker_color='#D4537E'))
    fig.update_layout(barmode='group', height=260, margin=dict(l=0,r=0,t=10,b=0),
                      legend=dict(orientation='h', y=1.12), **plot_cfg())
    st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Distribuição — {mes_sel}")
    fig2 = go.Figure(go.Pie(
        labels=['Fixos pagos','Fixos pendentes','Cartões'],
        values=[fp, pp, cart],
        hole=0.6,
        marker_colors=['#1D9E75','#EF9F27','#D4537E'],
        textinfo='label+percent'
    ))
    fig2.update_layout(height=240, margin=dict(l=0,r=0,t=10,b=0),
                       showlegend=False, **plot_cfg())
    st.plotly_chart(fig2, use_container_width=True)

    # Gastos variáveis no dashboard
    if not vm.empty:
        st.divider()
        st.subheader(f"Gastos variáveis — {mes_sel}")
        cat_sum  = vm.groupby('Categoria')['Valor'].sum().sort_values(ascending=False)
        total_gv = float(vm['Valor'].sum())
        st.caption(f"Total: **{fmt(total_gv)}** em {len(vm)} itens")
        colors = [CAT_COLORS.get(c, '#888') for c in cat_sum.index]
        fig3 = go.Figure(go.Bar(
            x=cat_sum.index, y=cat_sum.values,
            marker_color=colors,
            text=[fmt(v) for v in cat_sum.values], textposition='outside'
        ))
        fig3.update_layout(height=240, margin=dict(l=0,r=0,t=10,b=40), **plot_cfg())
        st.plotly_chart(fig3, use_container_width=True)

    # Pendentes
    if not df_fixos.empty and mes_sel in df_fixos.columns:
        pend = df_fixos[df_fixos[mes_sel] != True][['Nome','Categoria']].copy()
        if not pend.empty:
            pend['Valor'] = df_fixos[df_fixos[mes_sel] != True].apply(
                lambda r: fmt(gs.get_valor_mes(r, mes_sel)), axis=1
            ).values
            st.divider()
            st.subheader(f"⏳ Pendentes — {mes_sel}")
            st.dataframe(pend, hide_index=True, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# 📈 RELATÓRIO ANUAL
# ════════════════════════════════════════════════════════════════════════════
elif page == "📈 Relatório Anual":
    st.header("📈 Relatório Anual — 2026")

    rows = []
    for mes in MESES:
        a_, m_, e_ = entradas_mes(mes)
        entrada    = a_ + m_ + e_
        fp, pp     = fixos_mes(mes)
        fixos      = fp + pp
        cart       = cartao_total_mes(mes)
        saida      = fixos + cart
        rows.append({'Mês': mes[:3], 'Entradas': entrada, 'Fixos': fixos,
                     'Cartões': cart, 'Saídas': saida, 'Saldo': entrada - saida})

    df_a = pd.DataFrame(rows)
    c1, c2 = st.columns(2)
    c1.metric("Total entradas",  fmt(df_a['Entradas'].sum()))
    c2.metric("Saldo acumulado", fmt(df_a['Saldo'].sum()))
    c3, c4 = st.columns(2)
    c3.metric("Total fixos",     fmt(df_a['Fixos'].sum()))
    c4.metric("Total cartões",   fmt(df_a['Cartões'].sum()))

    st.divider()
    fig = go.Figure()
    fig.add_trace(go.Scatter(name='Entradas', x=df_a['Mês'], y=df_a['Entradas'],
                             mode='lines+markers', line=dict(color='#1D9E75', width=2)))
    fig.add_trace(go.Scatter(name='Saídas',   x=df_a['Mês'], y=df_a['Saídas'],
                             mode='lines+markers', line=dict(color='#E24B4A', width=2)))
    fig.add_trace(go.Scatter(name='Saldo',    x=df_a['Mês'], y=df_a['Saldo'],
                             mode='lines+markers', line=dict(color='#378ADD', width=2, dash='dot')))
    fig.update_layout(height=300, margin=dict(l=0,r=0,t=10,b=0),
                      legend=dict(orientation='h', y=1.12), **plot_cfg())
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tabela mensal")
    df_fmt = df_a.copy()
    for col in ['Entradas','Fixos','Cartões','Saídas','Saldo']:
        df_fmt[col] = df_fmt[col].apply(fmt)
    st.dataframe(df_fmt, hide_index=True, use_container_width=True)

    if not df_var.empty:
        st.subheader("Gastos variáveis por categoria — ano")
        cat_a = df_var.groupby('Categoria')['Valor'].sum().sort_values(ascending=False)
        colors = [CAT_COLORS.get(c, '#888') for c in cat_a.index]
        fig2 = go.Figure(go.Bar(x=cat_a.index, y=cat_a.values, marker_color=colors))
        fig2.update_layout(height=280, margin=dict(l=0,r=0,t=0,b=0), **plot_cfg())
        st.plotly_chart(fig2, use_container_width=True)
