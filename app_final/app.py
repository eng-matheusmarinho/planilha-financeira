import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import uuid
import gsheets as gs
from pdf_reader import render_leitor_fatura

st.set_page_config(
    page_title="Controle Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

# ── Sidebar ───────────────────────────────────────────────────────────────────
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
        "📄 Importar Fatura PDF",
        "📊 Dashboard",
        "📈 Relatório Anual",
    ])

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def load_all():
    return (
        gs.get_gastos_fixos(),
        gs.get_gastos_variaveis(),
        gs.get_cartoes(),
        gs.get_entradas(),
    )

def refresh():
    st.cache_data.clear()
    st.rerun()

try:
    df_fixos, df_var, df_cart, df_ent = load_all()
except Exception as e:
    st.error(f"❌ Erro ao conectar com Google Sheets: {e}")
    st.info("Verifique o arquivo `.streamlit/secrets.toml` com suas credenciais.")
    st.stop()

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
    pagos = float(df_fixos[df_fixos[mes] == True]['Valor'].sum())
    pend  = float(df_fixos[df_fixos[mes] != True]['Valor'].sum())
    return pagos, pend

def var_mes(mes):
    if df_var.empty:
        return pd.DataFrame()
    return df_var[df_var['Mes'] == mes].copy()


# ════════════════════════════════════════════════════════════════════════════
# 💰 ENTRADAS
# ════════════════════════════════════════════════════════════════════════════
if page == "💰 Entradas":
    st.header(f"💰 Entradas — {mes_sel}")

    row_e = df_ent[df_ent['Mes'] == mes_sel]
    ev = {'Amanda': 0.0, 'Matheus': 0.0, 'Extra': 0.0, 'Observacao': ''}
    if not row_e.empty:
        r = row_e.iloc[0]
        for k in ev:
            ev[k] = r.get(k, 0) or 0

    with st.form("entradas_form"):
        c1, c2, c3 = st.columns(3)
        am  = c1.number_input("Amanda (R$)",  value=float(ev['Amanda']),  min_value=0.0, step=100.0)
        ma  = c2.number_input("Matheus (R$)", value=float(ev['Matheus']), min_value=0.0, step=100.0)
        ex  = c3.number_input("Extra (R$)",   value=float(ev['Extra']),   min_value=0.0, step=100.0)
        obs = st.text_input("Observação (bônus, 13º, etc.)", value=str(ev['Observacao']))
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
    fig.update_layout(barmode='stack', height=300,
                      margin=dict(l=0,r=0,t=10,b=0),
                      legend=dict(orientation='h', y=1.12), **plot_cfg())
    st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# ✅ CONTAS FIXAS
# ════════════════════════════════════════════════════════════════════════════
elif page == "✅ Contas Fixas":
    st.header(f"✅ Contas Fixas — {mes_sel}")

    fp, pp = fixos_mes(mes_sel)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total fixos", fmt(fp + pp))
    c2.metric("✅ Pago",     fmt(fp))
    c3.metric("⏳ Pendente", fmt(pp))
    st.divider()

    if df_fixos.empty:
        st.info("Nenhuma conta fixa cadastrada.")
    elif mes_sel not in df_fixos.columns:
        st.warning(f"Coluna '{mes_sel}' não encontrada.")
    else:
        for i, row in df_fixos.iterrows():
            pago = row.get(mes_sel, False) == True
            with st.container():
                c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 2, 1.5, 1.8, 1.2, 1.2, 1.2])
                c1.write(row.get('Nome',''))
                c2.write(row.get('Categoria',''))
                c3.write(fmt(row.get('Valor', 0)))
                c4.markdown("✅ **Pago**" if pago else "⏳ Pendente")
                label = "Desmarcar" if pago else "✓ Pago"
                if c5.button(label, key=f"pago_{i}", use_container_width=True):
                    with st.spinner("Salvando..."):
                        gs.mark_pago(i, mes_sel, not pago)
                    refresh()
                if c6.button("✏️ Editar", key=f"edit_{i}", use_container_width=True):
                    st.session_state[f'editing_{i}'] = True
                if c7.button("🗑️ Excluir", key=f"del_fixo_{i}", use_container_width=True):
                    with st.spinner("Excluindo..."):
                        gs.delete_gasto_fixo(i)
                    refresh()

            if st.session_state.get(f'editing_{i}'):
                with st.form(f"edit_form_{i}"):
                    ec1, ec2, ec3, ec4 = st.columns(4)
                    novo_nome = ec1.text_input("Nome", value=row.get('Nome',''))
                    nova_cat  = ec2.selectbox("Categoria", CATEGORIAS,
                                             index=CATEGORIAS.index(row.get('Categoria','Outros'))
                                             if row.get('Categoria') in CATEGORIAS else 0)
                    novo_pgto = ec3.selectbox("Pgto", ['Pix','Boleto','Dinheiro','Débito'])
                    novo_val  = ec4.number_input("Valor", value=float(row.get('Valor',0)), min_value=0.0, step=10.0)
                    sc1, sc2 = st.columns(2)
                    if sc1.form_submit_button("💾 Salvar", use_container_width=True, type="primary"):
                        with st.spinner("Salvando..."):
                            gs.update_gasto_fixo(i, novo_nome, nova_cat, novo_pgto, novo_val)
                        st.session_state.pop(f'editing_{i}', None)
                        refresh()
                    if sc2.form_submit_button("Cancelar", use_container_width=True):
                        st.session_state.pop(f'editing_{i}', None)
                        st.rerun()
            st.divider()

    with st.expander("➕ Adicionar nova conta fixa"):
        with st.form("nova_fixa"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome da conta *")
            cat  = c2.selectbox("Categoria", CATEGORIAS)
            c3, c4 = st.columns(2)
            val  = c3.number_input("Valor (R$) *", min_value=0.0, step=10.0)
            pgto = c4.selectbox("Forma de pagamento", ['Pix','Boleto','Dinheiro','Débito'])
            if st.form_submit_button("Adicionar", use_container_width=True, type="primary"):
                if nome and val > 0:
                    gs.add_gasto_fixo([nome, cat, pgto, val] + [False] * 12)
                    st.success(f"'{nome}' adicionado!")
                    refresh()
                else:
                    st.warning("Preencha nome e valor.")


# ════════════════════════════════════════════════════════════════════════════
# 💳 CARTÕES
# ════════════════════════════════════════════════════════════════════════════
elif page == "💳 Cartões":
    st.header(f"💳 Cartões de Crédito — {mes_sel}")

    row_c = df_cart[df_cart['Mes'] == mes_sel]
    cart_vals = {c: float(row_c.iloc[0].get(c, 0) or 0) for c in CARTAO_COLS} \
                if not row_c.empty else {c: 0.0 for c in CARTAO_COLS}
    cart_pago = bool(row_c.iloc[0].get('Pago', False)) if not row_c.empty else False
    total_c   = sum(cart_vals.values())

    a, m, _ = entradas_mes(mes_sel)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total cartões", fmt(total_c))
    c2.metric("Amanda",  fmt(sum(cart_vals[c] for c in ['Inter_Amanda','Nubank_Amanda','BRB_Amanda'])))
    c3.metric("Matheus", fmt(sum(cart_vals[c] for c in ['Inter_Matheus','Nubank_Matheus','Outros'])))
    status_pago = "✅ Fatura paga" if cart_pago else "⏳ Fatura pendente"
    c4.metric("Status", status_pago)

    if (a + m) > 0:
        pct = total_c / (a + m)
        st.caption(f"💳 Cartões representam **{pct*100:.1f}%** da renda do casal")
        st.progress(min(pct, 1.0))

    st.divider()

    col_form, col_check = st.columns([3, 1])
    with col_form:
        st.subheader("Atualizar faturas")
        with st.form("cartoes_form"):
            st.markdown("**Amanda**")
            ca1, ca2, ca3 = st.columns(3)
            new_vals = {}
            new_vals['Inter_Amanda']   = ca1.number_input("Inter Amanda",   value=cart_vals['Inter_Amanda'],   min_value=0.0, step=0.01)
            new_vals['Nubank_Amanda']  = ca2.number_input("Nubank Amanda",  value=cart_vals['Nubank_Amanda'],  min_value=0.0, step=0.01)
            new_vals['BRB_Amanda']     = ca3.number_input("BRB Amanda",     value=cart_vals['BRB_Amanda'],     min_value=0.0, step=0.01)
            st.markdown("**Matheus**")
            cm1, cm2, cm3 = st.columns(3)
            new_vals['Inter_Matheus']  = cm1.number_input("Inter Matheus",  value=cart_vals['Inter_Matheus'],  min_value=0.0, step=0.01)
            new_vals['Nubank_Matheus'] = cm2.number_input("Nubank Matheus", value=cart_vals['Nubank_Matheus'], min_value=0.0, step=0.01)
            new_vals['Outros']         = cm3.number_input("Outros",         value=cart_vals['Outros'],         min_value=0.0, step=0.01)
            novo_total = sum(new_vals.values())
            st.metric("Novo total", fmt(novo_total))
            if st.form_submit_button("💾 Salvar faturas", use_container_width=True, type="primary"):
                with st.spinner("Salvando..."):
                    for col_name, valor in new_vals.items():
                        gs.update_cartao(mes_sel, col_name, valor)
                st.success("Faturas salvas!")
                refresh()

    with col_check:
        st.subheader("Status pagamento")
        st.write("")
        st.write("")
        novo_pago = st.checkbox("Fatura paga", value=cart_pago, key="cart_pago_check")
        if novo_pago != cart_pago:
            with st.spinner("Salvando..."):
                gs.mark_cartao_pago(mes_sel, novo_pago)
            refresh()
        if cart_pago:
            st.success(f"Fatura de {mes_sel} quitada!")
        else:
            st.warning(f"Fatura de {mes_sel} em aberto")
            st.metric("A pagar", fmt(total_c))

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
            c1,c2,c3,c4,c5,c6,c7 = st.columns([3,1.8,1.5,1.5,1.2,1,1])
            c1.write(row.get('Descricao',''))
            c2.write(row.get('Categoria',''))
            c3.write(fmt(row.get('Valor',0)))
            c4.write(row.get('Pessoa',''))
            c5.write(str(row.get('Data',''))[:10])

            if c6.button("✏️", key=f"gedit_{row['ID']}"):
                st.session_state[f'gedit_{row["ID"]}'] = True
            if c7.button("🗑️", key=f"gdel_{row['ID']}"):
                with st.spinner("Excluindo..."):
                    gs.delete_gasto(fidx)
                refresh()

            if st.session_state.get(f'gedit_{row["ID"]}'):
                with st.form(f"gform_{row['ID']}"):
                    gc1, gc2 = st.columns(2)
                    nd = gc1.text_input("Descrição", value=row.get('Descricao',''))
                    nv = gc2.number_input("Valor", value=float(row.get('Valor',0)), min_value=0.0, step=0.01)
                    gc3, gc4, gc5 = st.columns(3)
                    nc = gc3.selectbox("Categoria", CATEGORIAS,
                                      index=CATEGORIAS.index(row.get('Categoria','Outros'))
                                      if row.get('Categoria') in CATEGORIAS else 0)
                    np = gc4.selectbox("Pagamento", PAGAMENTOS)
                    npe = gc5.selectbox("Pessoa", ["Amanda","Matheus","Casa"])
                    gs1, gs2 = st.columns(2)
                    if gs1.form_submit_button("💾 Salvar", use_container_width=True, type="primary"):
                        with st.spinner("Salvando..."):
                            gs.update_gasto(fidx, nd, nc, np, npe, nv)
                        st.session_state.pop(f'gedit_{row["ID"]}', None)
                        refresh()
                    if gs2.form_submit_button("Cancelar", use_container_width=True):
                        st.session_state.pop(f'gedit_{row["ID"]}', None)
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
# 📄 IMPORTAR FATURA PDF
# ════════════════════════════════════════════════════════════════════════════
elif page == "📄 Importar Fatura PDF":
    render_leitor_fatura(
        mes_sel=mes_sel,
        meses=MESES,
        pagamentos=PAGAMENTOS,
        adicionar_gasto_fn=gs.add_gasto,
        refresh_fn=refresh
    )


# ════════════════════════════════════════════════════════════════════════════
# 📊 DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
elif page == "📊 Dashboard":
    st.header(f"📊 Dashboard — {mes_sel}")

    a, m, ex = entradas_mes(mes_sel)
    entrada   = a + m + ex
    cart      = cartao_total_mes(mes_sel)
    fp, pp    = fixos_mes(mes_sel)
    fixos     = fp + pp
    vm        = var_mes(mes_sel)
    saida     = fixos + cart
    saldo     = entrada - saida

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Entradas",    fmt(entrada))
    c2.metric("✅ Fixos pagos", fmt(fp), delta=f"-{fmt(pp)} pendente", delta_color="inverse")
    c3.metric("💳 Cartões",     fmt(cart))
    c4.metric("💹 Saldo",       fmt(saldo), delta=fmt(saldo))

    if entrada > 0:
        pct = min(saida / entrada, 1.0)
        cor = "🟢" if pct < 0.7 else "🟡" if pct < 0.9 else "🔴"
        st.caption(f"{cor} Comprometido: **{pct*100:.1f}%** — {fmt(saida)} de {fmt(entrada)}")
        st.progress(pct)

    st.divider()
    col_l, col_r = st.columns([3, 2])

    with col_l:
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
        fig.update_layout(barmode='group', height=280, margin=dict(l=0,r=0,t=10,b=0),
                          legend=dict(orientation='h', y=1.12), **plot_cfg())
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader(f"Distribuição — {mes_sel}")
        fig2 = go.Figure(go.Pie(
            labels=['Fixos pagos','Fixos pendentes','Cartões'],
            values=[fp, pp, cart],
            hole=0.6,
            marker_colors=['#1D9E75','#EF9F27','#D4537E'],
            textinfo='label+percent'
        ))
        fig2.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
                           showlegend=False, **plot_cfg())
        st.plotly_chart(fig2, use_container_width=True)

    # Gastos variáveis no dashboard
    if not vm.empty:
        st.divider()
        st.subheader(f"Detalhamento de gastos variáveis — {mes_sel}")
        cat_sum = vm.groupby('Categoria')['Valor'].sum().sort_values(ascending=False)
        total_gv = float(vm['Valor'].sum())
        st.caption(f"Total lançado: **{fmt(total_gv)}** em {len(vm)} itens")
        colors = [CAT_COLORS.get(c, '#888') for c in cat_sum.index]
        fig3 = go.Figure(go.Bar(
            x=cat_sum.index, y=cat_sum.values,
            marker_color=colors,
            text=[fmt(v) for v in cat_sum.values], textposition='outside'
        ))
        fig3.update_layout(height=260, margin=dict(l=0,r=0,t=10,b=0), **plot_cfg())
        st.plotly_chart(fig3, use_container_width=True)

    # Pendentes
    if not df_fixos.empty and mes_sel in df_fixos.columns:
        pend = df_fixos[df_fixos[mes_sel] != True][['Nome','Categoria','Valor']].copy()
        if not pend.empty:
            st.divider()
            st.subheader(f"⏳ Contas pendentes — {mes_sel}")
            pend['Valor'] = pend['Valor'].apply(fmt)
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
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total entradas",  fmt(df_a['Entradas'].sum()))
    c2.metric("Total fixos",     fmt(df_a['Fixos'].sum()))
    c3.metric("Total cartões",   fmt(df_a['Cartões'].sum()))
    c4.metric("Saldo acumulado", fmt(df_a['Saldo'].sum()))

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
