import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
import uuid
import gsheets as gs

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
        "📊 Dashboard",
        "✅ Contas Fixas",
        "➕ Gastos Variáveis",
        "💳 Cartões",
        "💰 Entradas",
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
    return sum(float(r.iloc[0].get(c, 0) or 0) for c in CARTAO_COLS)

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
# 📊 DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
if page == "📊 Dashboard":
    st.header(f"📊 Dashboard — {mes_sel}")

    a, m, ex = entradas_mes(mes_sel)
    entrada   = a + m + ex
    cart      = cartao_total_mes(mes_sel)
    fp, pp    = fixos_mes(mes_sel)
    fixos     = fp + pp
    vm        = var_mes(mes_sel)
    variaveis = float(vm['Valor'].sum()) if not vm.empty else 0.0
    saida     = fixos + cart + variaveis
    saldo     = entrada - saida

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💵 Entradas",     fmt(entrada))
    c2.metric("✅ Fixos pagos",  fmt(fp), delta=f"pendente: {fmt(pp)}", delta_color="inverse")
    c3.metric("💳 Cartões",      fmt(cart))
    c4.metric("💹 Saldo",        fmt(saldo), delta=fmt(saldo))

    # Barra de comprometimento
    st.divider()
    if entrada > 0:
        pct = min(saida / entrada, 1.0)
        cor = "🟢" if pct < 0.7 else "🟡" if pct < 0.9 else "🔴"
        st.caption(f"{cor} Comprometido: **{pct*100:.1f}%** da renda — {fmt(saida)} gastos de {fmt(entrada)} de entradas")
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
                          legend=dict(orientation='h', y=1.12),
                          **plot_cfg())
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader(f"Distribuição — {mes_sel}")
        labels = ['Fixos pagos', 'Fixos pendentes', 'Cartões', 'Variáveis']
        values = [fp, pp, cart, variaveis]
        colors = ['#1D9E75', '#EF9F27', '#D4537E', '#378ADD']
        fig2 = go.Figure(go.Pie(labels=labels, values=values, hole=0.6,
                                marker_colors=colors, textinfo='label+percent'))
        fig2.update_layout(height=280, margin=dict(l=0,r=0,t=10,b=0),
                           showlegend=False, **plot_cfg())
        st.plotly_chart(fig2, use_container_width=True)

    # Contas pendentes
    if not df_fixos.empty and mes_sel in df_fixos.columns:
        pend = df_fixos[df_fixos[mes_sel] != True][['Nome','Categoria','Valor']].copy()
        if not pend.empty:
            st.subheader(f"⏳ Pendente em {mes_sel}")
            pend['Valor'] = pend['Valor'].apply(fmt)
            st.dataframe(pend, hide_index=True, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# ✅ CONTAS FIXAS
# ════════════════════════════════════════════════════════════════════════════
elif page == "✅ Contas Fixas":
    st.header(f"✅ Contas Fixas — {mes_sel}")

    fp, pp = fixos_mes(mes_sel)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total fixos",  fmt(fp + pp))
    c2.metric("✅ Pago",      fmt(fp))
    c3.metric("⏳ Pendente",  fmt(pp))

    st.divider()

    if df_fixos.empty:
        st.info("Nenhuma conta fixa cadastrada.")
    elif mes_sel not in df_fixos.columns:
        st.warning(f"Coluna '{mes_sel}' não encontrada. Execute o setup_planilha.py.")
    else:
        header = st.columns([3, 2, 1.5, 2, 1.5])
        for h, t in zip(header, ["Nome","Categoria","Valor","Status","Ação"]):
            h.markdown(f"**{t}**")
        st.divider()

        for i, row in df_fixos.iterrows():
            pago = row.get(mes_sel, False) == True
            c1,c2,c3,c4,c5 = st.columns([3, 2, 1.5, 2, 1.5])
            c1.write(row.get('Nome',''))
            c2.write(row.get('Categoria',''))
            c3.write(fmt(row.get('Valor', 0)))
            c4.markdown("✅ **Pago**" if pago else "⏳ Pendente")
            label = "Desmarcar" if pago else "✓ Marcar pago"
            if c5.button(label, key=f"fixo_{i}_{mes_sel}", use_container_width=True):
                with st.spinner("Salvando..."):
                    gs.mark_pago(i, mes_sel, not pago)
                refresh()

    st.divider()
    with st.expander("➕ Adicionar nova conta fixa"):
        with st.form("nova_fixa"):
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome da conta")
            cat  = c2.selectbox("Categoria", CATEGORIAS)
            c3, c4 = st.columns(2)
            val  = c3.number_input("Valor (R$)", min_value=0.0, step=10.0)
            pgto = c4.selectbox("Forma de pagamento", PAGAMENTOS)
            if st.form_submit_button("Adicionar", use_container_width=True):
                if nome and val > 0:
                    gs.add_gasto_fixo([nome, cat, pgto, val] + [False] * 12)
                    st.success(f"'{nome}' adicionado!")
                    refresh()
                else:
                    st.warning("Preencha nome e valor.")


# ════════════════════════════════════════════════════════════════════════════
# ➕ GASTOS VARIÁVEIS
# ════════════════════════════════════════════════════════════════════════════
elif page == "➕ Gastos Variáveis":
    st.header(f"➕ Gastos Variáveis — {mes_sel}")

    with st.form("novo_gasto", clear_on_submit=True):
        c1, c2 = st.columns(2)
        desc   = c1.text_input("Descrição *")
        val    = c2.number_input("Valor (R$) *", min_value=0.0, step=0.01)
        c3, c4, c5 = st.columns(3)
        cat    = c3.selectbox("Categoria", CATEGORIAS)
        pgto   = c4.selectbox("Pagamento", PAGAMENTOS)
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
        c_fil, _ = st.columns([2, 4])
        cat_fil   = c_fil.selectbox("Filtrar categoria", cats_disp)
        vm_fil    = vm if cat_fil == 'Todas' else vm[vm['Categoria'] == cat_fil]

        st.caption(f"{len(vm_fil)} lançamentos · Total: **{fmt(vm_fil['Valor'].sum())}**")

        # Tabela de gastos
        h1,h2,h3,h4,h5,h6 = st.columns([3,1.8,1.5,1.5,1.2,0.7])
        for h,t in zip([h1,h2,h3,h4,h5,h6],["Descrição","Categoria","Valor","Pessoa","Data",""]):
            h.markdown(f"**{t}**")

        for _, row in vm_fil.iterrows():
            c1,c2,c3,c4,c5,c6 = st.columns([3,1.8,1.5,1.5,1.2,0.7])
            c1.write(row.get('Descricao',''))
            c2.write(row.get('Categoria',''))
            c3.write(fmt(row.get('Valor',0)))
            c4.write(row.get('Pessoa',''))
            c5.write(str(row.get('Data',''))[:10])
            if c6.button("🗑️", key=f"del_{row.get('ID','')}"):
                full = df_var[df_var['ID'] == row['ID']]
                if not full.empty:
                    gs.delete_gasto(full.index[0])
                    refresh()

        # Gráfico por categoria
        st.divider()
        st.subheader("Por categoria")
        cat_sum = vm['Categoria'].map(lambda x: x or 'Outros')
        cat_sum = vm.groupby('Categoria')['Valor'].sum().sort_values(ascending=True)
        colors  = [CAT_COLORS.get(c, '#888') for c in cat_sum.index]

        fig = go.Figure(go.Bar(
            x=cat_sum.values, y=cat_sum.index,
            orientation='h', marker_color=colors
        ))
        fig.update_layout(height=max(220, len(cat_sum)*38+60),
                          margin=dict(l=0,r=0,t=0,b=0), **plot_cfg())
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# 💳 CARTÕES
# ════════════════════════════════════════════════════════════════════════════
elif page == "💳 Cartões":
    st.header(f"💳 Cartões de Crédito — {mes_sel}")

    row_c = df_cart[df_cart['Mes'] == mes_sel]
    cart_vals = {c: float(row_c.iloc[0].get(c, 0) or 0) for c in CARTAO_COLS} \
                if not row_c.empty else {c: 0.0 for c in CARTAO_COLS}
    total_c = sum(cart_vals.values())

    a, m, _ = entradas_mes(mes_sel)
    c1, c2, c3 = st.columns(3)
    c1.metric("Total cartões", fmt(total_c))
    c2.metric("Amanda (Inter+Nubank+BRB)", fmt(sum(cart_vals[c] for c in ['Inter_Amanda','Nubank_Amanda','BRB_Amanda'])))
    c3.metric("Matheus (Inter+Nubank)",    fmt(sum(cart_vals[c] for c in ['Inter_Matheus','Nubank_Matheus','Outros'])))
    if (a + m) > 0:
        st.caption(f"💳 Cartões representam **{total_c/(a+m)*100:.1f}%** da renda do casal")
        st.progress(min(total_c / (a + m), 1.0))

    st.divider()
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

    # Histórico anual
    st.divider()
    st.subheader("Histórico anual de cartões")
    historico = []
    for mes in MESES:
        r = df_cart[df_cart['Mes'] == mes]
        t = sum(float(r.iloc[0].get(c,0) or 0) for c in CARTAO_COLS) if not r.empty else 0
        historico.append(t)

    fig = go.Figure(go.Bar(x=MESES_ABR, y=historico, marker_color='#D4537E'))
    fig.update_layout(height=240, margin=dict(l=0,r=0,t=0,b=0), **plot_cfg())
    st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# 💰 ENTRADAS
# ════════════════════════════════════════════════════════════════════════════
elif page == "💰 Entradas":
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
    fig.update_layout(barmode='stack', height=260,
                      margin=dict(l=0,r=0,t=10,b=0),
                      legend=dict(orientation='h', y=1.12), **plot_cfg())
    st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# 📈 RELATÓRIO ANUAL
# ════════════════════════════════════════════════════════════════════════════
elif page == "📈 Relatório Anual":
    st.header("📈 Relatório Anual — 2026")

    rows = []
    for mes in MESES:
        a_, m_, e_  = entradas_mes(mes)
        entrada     = a_ + m_ + e_
        fp, pp      = fixos_mes(mes)
        fixos       = fp + pp
        cart        = cartao_total_mes(mes)
        vm          = var_mes(mes)
        variaveis   = float(vm['Valor'].sum()) if not vm.empty else 0.0
        saida       = fixos + cart + variaveis
        rows.append({'Mês': mes[:3], 'Entradas': entrada, 'Fixos': fixos,
                     'Cartões': cart, 'Variáveis': variaveis,
                     'Saídas': saida, 'Saldo': entrada - saida})

    df_a = pd.DataFrame(rows)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total entradas",  fmt(df_a['Entradas'].sum()))
    c2.metric("Total fixos",     fmt(df_a['Fixos'].sum()))
    c3.metric("Total cartões",   fmt(df_a['Cartões'].sum()))
    c4.metric("Saldo acumulado", fmt(df_a['Saldo'].sum()))

    st.divider()

    # Evolução anual
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

    # Tabela
    st.subheader("Tabela mensal")
    df_fmt = df_a.copy()
    for col in ['Entradas','Fixos','Cartões','Variáveis','Saídas','Saldo']:
        df_fmt[col] = df_fmt[col].apply(fmt)
    st.dataframe(df_fmt, hide_index=True, use_container_width=True)

    # Categorias (gastos variáveis)
    if not df_var.empty:
        st.subheader("Gastos variáveis por categoria — ano completo")
        cat_a = df_var.groupby('Categoria')['Valor'].sum().sort_values(ascending=False)
        colors = [CAT_COLORS.get(c, '#888') for c in cat_a.index]
        fig2 = go.Figure(go.Bar(x=cat_a.index, y=cat_a.values, marker_color=colors))
        fig2.update_layout(height=280, margin=dict(l=0,r=0,t=0,b=0), **plot_cfg())
        st.plotly_chart(fig2, use_container_width=True)
