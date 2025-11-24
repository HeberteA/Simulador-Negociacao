import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import time

st.set_page_config(
    page_title="Simulador de Negociação",
    page_icon="Lavie1.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

APP_STYLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0');

/* Fundo Geral do App */
[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 10% 20%, #3b3b3b 10%, #000000 100%);
    font-family: 'Inter', sans-serif;
    color: #ffffff;
}

/* --- CORREÇÃO DO GRADIENTE NOS INPUTS (Containers) --- */
/* Alvo: st.container(border=True) */
.st-key-gradiente_container {
    background-color: transparent !important;
    background-image: linear-gradient(160deg, #1e1e24 0%, #0a0a0c 100%) !important;
    
    border: 1px solid rgba(255, 255, 255, 0.5) !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7) !important;
    padding: 24px !important;
    margin-bottom: 20px !important;
}
.st-key-gradiente_container1 {
    background-color: transparent !important;
    background-image: linear-gradient(160deg, #1e1e24 0%, #0a0a0c 100%) !important;
    
    border: 1px solid rgba(255, 255, 255, 0.5) !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7) !important;
    padding: 24px !important;
    margin-bottom: 20px !important;
}

.st-key-gradiente_container2 {
    background-color: transparent !important;
    background-image: linear-gradient(160deg, #1e1e24 0%, #0a0a0c 100%) !important;
    
    border: 1px solid rgba(255, 255, 255, 0.5) !important;
    border-radius: 16px !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7) !important;
    padding: 24px !important;
    margin-bottom: 20px !important;
}


/* Garante que o fundo interno seja transparente */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    background-color: transparent !important;
}

/* --- Estilização de Inputs --- */
div[data-baseweb="input"] > div, 
div[data-baseweb="select"] > div, 
div[data-baseweb="base-input"] {
    background-color: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: white !important;
    border-radius: 8px !important;
    height: auto !important;
}

/* Resumo (Textarea) */
div[data-baseweb="textarea"] > div {
    background-color: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 8px !important;
    color: white !important;
    height: 48px;
}

/* Texto interno dos inputs */
div[data-testid="stNumberInput"] input, 
div[data-testid="stTextInput"] input {
    color: white !important;
    font-family: 'Inter', sans-serif;
}

/* Labels (Títulos dos inputs) */
label[data-testid="stLabel"] {
    color: rgba(255, 255, 255, 0.6) !important;
    font-size: 0.85rem !important;
    margin-bottom: 8px;
}

/* Headers Personalizados */
.section-header { display: flex; align-items: center; margin-bottom: 20px; }
.section-icon {
    font-family: 'Material Symbols Rounded'; font-size: 22px; margin-right: 10px;
    color: #E37026; background: rgba(227, 112, 38, 0.15); padding: 6px;
    border-radius: 8px; display: inline-flex; align-items: center; justify-content: center;
}
.section-title { font-size: 1.05rem; font-weight: 600; color: #fff; }

/* CARD DE RESULTADO (HTML) */
.lavie-card {
    background-color: transparent !important;
    background-image: linear-gradient(160deg, #3b3b3b 0%, #0a0a0c 100%) !important;
    
    border: 1px solid rgba(255, 255, 255, 0.5) !important;
    padding: 30px;
    border-radius: 16px !important;
    box-shadow: 0 15px 40px rgba(0, 0, 0, 0.7) !important;
    margin-top: 10px;
}

.stats-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; width: 100%;
}
@media (max-width: 800px) { .stats-grid { grid-template-columns: 1fr 1fr; } }

.stat-item { display: flex; flex-direction: column; }
.stat-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; font-weight: 600; }
.stat-value { font-size: 1.4rem; color: #fff; font-weight: 700; letter-spacing: -0.5px; margin-bottom: 2px; }
.stat-value.highlight { color: #E37026; }
.stat-sub { font-size: 0.8rem; color: #555; }
</style>
"""
st.markdown(APP_STYLE_CSS, unsafe_allow_html=True)

def render_header(icon_name, title):
    st.markdown(f"""
        <div class="section-header">
            <span class="section-icon">{icon_name}</span>
            <span class="section-title">{title}</span>
        </div>
    """, unsafe_allow_html=True)

def format_currency(value):
    if value is None: return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def to_sheet_string(value):
    return f"{value:.2f}".replace('.', ',')

@st.cache_resource(ttl=60)
def get_worksheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet_key = st.secrets["spreadsheet_info"]["spreadsheet_key"]
        worksheet_name = st.secrets["spreadsheet_info"]["worksheet_name"]
        return client.open_by_key(spreadsheet_key).worksheet(worksheet_name)
    except Exception as e:
        st.error(f"Erro na planilha: {e}")
        return None

@st.cache_data(ttl=5) 
def carregar_dados_planilha():
    try:
        sheet = get_worksheet()
        if sheet is None: return pd.DataFrame()
        data = sheet.get_all_values()
        if not data or len(data) < 2: return pd.DataFrame()
        df = pd.DataFrame(data[1:], columns=data[0])
        cols = ['Preco Total', 'Valor Entrada', 'Valor Mensal', 'Valor Semestral', 'Valor Entrega', '% Entrada', '% Mensal', '% Semestral', '% Entrega', 'Nº Mensal', 'Nº Semestral', 'Nº Parc Entrada']
        for col in cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame()

def set_default_values():
    defaults = {
        "main_unidade": "101", "main_preco_total": 500000.0, "main_num_mensal": 36, 
        "main_num_intercalada": 6, "main_tipo_intercalada": "Semestral", "main_num_entrada": 1,
        "perc_entrada": 20.0, "perc_mensal": 40.0, "perc_intercalada": 20.0, "perc_entrega": 20.0
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v
    if "total_percent" not in st.session_state:
        st.session_state.total_percent = sum([defaults["perc_entrada"], defaults["perc_mensal"], defaults["perc_intercalada"], defaults["perc_entrega"]])

def reset_to_default_values():
    keys = ["main_unidade", "main_preco_total", "main_num_mensal", "main_num_intercalada", "main_num_entrada", "main_tipo_intercalada",
            "perc_entrada", "perc_mensal", "perc_intercalada", "perc_entrega", "total_percent", "summary_text", "data_to_save"]
    for k in keys:
        if k in st.session_state: del st.session_state[k]

@st.dialog("Editar Simulação")
def edit_dialog(row_data, sheet, sheet_row_index):
    st.markdown(f"Editando **{row_data.get('Obra','')}** | Unidade: **{row_data.get('Unidade','')}**")
    
    old_p_sem = float(row_data.get('% Semestral', 0)) if '% Semestral' in row_data else float(row_data.get('% Intercalada', 0))
    
    if "edit_total_percent" not in st.session_state:
        st.session_state.edit_total_percent = float(row_data.get('% Entrada', 0) + row_data.get('% Mensal', 0) + old_p_sem + row_data.get('% Entrega', 0))

    def update_edit_pct():
        st.session_state.edit_total_percent = st.session_state.edit_perc_entrada + st.session_state.edit_perc_mensal + st.session_state.edit_perc_semestral + st.session_state.edit_perc_entrega

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Dados")
        st.text_input("Unidade", value=row_data.get('Unidade',''), disabled=True)
        preco = st.number_input("Preço Total", min_value=0.0, step=1000.0, value=float(row_data.get('Preco Total', 0)), key="edit_preco_total")
        st.markdown("##### Prazos")
        nm = st.number_input("Nº Mensais", min_value=0, value=int(row_data.get('Nº Mensal', 0)), key="edit_num_mensal")
        
        old_ns = int(row_data.get('Nº Semestral', 0)) if 'Nº Semestral' in row_data else int(row_data.get('Nº Intercalada', 0))
        ns = st.number_input("Nº Intercaladas", min_value=0, value=old_ns, key="edit_num_semestral")
        
    with c2:
        st.markdown("##### Fluxo (%)")
        pe = st.number_input("Entrada %", 0.0, 100.0, value=float(row_data.get('% Entrada', 0)), step=0.5, key="edit_perc_entrada", on_change=update_edit_pct)
        pm = st.number_input("Mensais %", 0.0, 100.0, value=float(row_data.get('% Mensal', 0)), step=0.5, key="edit_perc_mensal", on_change=update_edit_pct)
        ps = st.number_input("Intercaladas %", 0.0, 100.0, value=old_p_sem, step=0.5, key="edit_perc_semestral", on_change=update_edit_pct)
        pent = st.number_input("Entrega %", 0.0, 100.0, value=float(row_data.get('% Entrega', 0)), step=0.5, key="edit_perc_entrega", on_change=update_edit_pct)
        
        tp = st.session_state.edit_total_percent
        if tp != 100.0: st.warning(f"Total: {tp:.1f}%")
        else: st.success("Total: 100%")

    st.markdown("---")
    if st.button("Salvar Alterações", type="primary", use_container_width=True):
        if round(tp, 1) != 100.0: st.error("Feche 100% para salvar.")
        else:
            ve = (preco * pe)/100; vm = (preco * pm)/100; vs = (preco * ps)/100; vent = (preco * pent)/100
            vpm = vm/nm if nm else 0; vps = vs/ns if ns else 0
            
            row_upd = [
                row_data.get('Obra',''), row_data.get('Unidade',''), to_sheet_string(preco),
                to_sheet_string(pe), to_sheet_string(ve), to_sheet_string(pm), nm,
                to_sheet_string(vpm), to_sheet_string(ps), ns, to_sheet_string(vps),
                to_sheet_string(pent), to_sheet_string(vent), row_data.get('Data/Hora','')
            ]
            try:
                sheet.update(f'A{sheet_row_index}:N{sheet_row_index}', [row_upd], value_input_option='USER_ENTERED')
                st.toast("Salvo!"); carregar_dados_planilha.clear()
                for k in list(st.session_state.keys()): 
                    if k.startswith('edit_'): del st.session_state[k]
                time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Erro: {e}")

set_default_values()

try:
    _, c, _ = st.columns([1, 4, 1])
    with c: st.image("LavieC.png", width=750)
except: pass

st.title("Simulador de Negociação")
st.markdown("---")

lista_obras = ["Burj Lavie", "Lavie Areia Dourada", "The Well By OM25 e Lavie", "Lavie Camboinha", "Arc Space"]
obra_selecionada = st.selectbox("Escolha a Obra:", lista_obras, label_visibility="collapsed")

tab1, tab2 = st.tabs(["Simular Negociação", "Simulações Salvas"])

with tab1:
    if "summary_text" not in st.session_state: st.session_state.summary_text = ""
    if "data_to_save" not in st.session_state: st.session_state.data_to_save = None

    st.markdown(f"<h3 style='color: #E37026; margin: 0 0 10px 0;'>Nova Simulação</h3>", unsafe_allow_html=True)
    
    with st.container(border=True,key="gradiente_container"):
        render_header("apartment", "Dados da Unidade")
        und, pre = st.columns([2, 4])
        unidade = und.text_input("Unidade / Sala", key="main_unidade")
        preco_total = pre.number_input("Preço Total (R$)", min_value=0.0, step=1000.0, key="main_preco_total", format="%.2f")
        
    with st.container(border=True, key="gradiente_container1"):
        render_header("calendar_month", "Configuração de Prazos")
        ent, tip, = st.columns(2)
        num_entrada = ent.number_input("Nº Parc. Entrada", min_value=1, step=1, key="main_num_entrada")
        num_mensal = ent.number_input("Nº Parc. Mensais", min_value=0, step=1, key="main_num_mensal")
      
        tipo_intercalada = tip.selectbox("Tipo", ["Semestrais", "Trimestrais", "Anuais", "Bimestrais", "Quadrimestrais"], key="main_tipo_intercalada")
        num_intercalada = tip.number_input("Nº Parc.", min_value=0, step=1, key="main_num_intercalada")


    with st.container(border=True, key="gradiente_container2"):
        render_header("pie_chart", "Distribuição do Fluxo (%)")
        if "total_percent" not in st.session_state: st.session_state.total_percent = 0.0
        
        def calc_pct():
            st.session_state.total_percent = st.session_state.perc_entrada + st.session_state.perc_mensal + st.session_state.perc_intercalada + st.session_state.perc_entrega
        
        c_flow = st.columns(4)
        perc_entrada = c_flow[0].number_input("Entrada (%)", 0.0, 100.0, step=1.0, format="%.2f", key="perc_entrada", on_change=calc_pct)
        perc_mensal = c_flow[1].number_input("Mensais (%)", 0.0, 100.0, step=1.0, format="%.2f", key="perc_mensal", on_change=calc_pct)
        
        label_inter = f"{tipo_intercalada} (%)" 
        perc_intercalada = c_flow[2].number_input(label_inter, 0.0, 100.0, step=1.0, format="%.2f", key="perc_intercalada", on_change=calc_pct)
        
        perc_entrega = c_flow[3].number_input("Entrega (%)", 0.0, 100.0, step=1.0, format="%.2f", key="perc_entrega", on_change=calc_pct)

        tot = st.session_state.total_percent
        color = "#09ab3b" if tot == 100 else "#ff4b4b"
        icon = "check_circle" if tot == 100 else "warning"
        st.markdown(f"""<div style="margin-top:15px; text-align:right; color:{color}; font-weight:bold;"><span class="material-symbols-rounded" style="vertical-align:middle;">{icon}</span> Fechamento: {tot:.1f}%</div>""", unsafe_allow_html=True)
        st.markdown("")

    val_entrada_total = (preco_total * perc_entrada) / 100
    val_entrada_parcela = val_entrada_total / num_entrada if num_entrada > 0 else 0
    
    val_total_mensal = (preco_total * perc_mensal) / 100
    val_por_mensal = (val_total_mensal / num_mensal) if num_mensal > 0 else 0
    
    val_total_intercalada = (preco_total * perc_intercalada) / 100
    val_por_intercalada = (val_total_intercalada / num_intercalada) if num_intercalada > 0 else 0
    
    val_entrega = (preco_total * perc_entrega) / 100

    f_preco = format_currency(preco_total)
    f_ent_total = format_currency(val_entrada_total)
    f_ent_parc = format_currency(val_entrada_parcela)
    f_men = format_currency(val_por_mensal)
    f_tot_men = format_currency(val_total_mensal)
    f_inter = format_currency(val_por_intercalada)
    f_tot_inter = format_currency(val_total_intercalada)
    f_entg = format_currency(val_entrega)

    st.markdown("<br>", unsafe_allow_html=True)
    render_header("analytics", "Resultado Financeiro")
    
    txt_entrada_main = f"{f_ent_total}" if num_entrada == 1 else f"{f_ent_parc}"
    sub_entrada_main = "Ato / Sinal" if num_entrada == 1 else f"Sinal em {num_entrada}x"
    
    card_html = f"""
    <div class="lavie-card">
        <div class="stats-grid">
            <div class="stat-item"><span class="stat-label">Entrada ({perc_entrada:.0f}%)</span><span class="stat-value highlight">{txt_entrada_main}</span><span class="stat-sub">{sub_entrada_main}</span></div>
            <div class="stat-item"><span class="stat-label">Mensais ({num_mensal}x)</span><span class="stat-value">{f_men}</span><span class="stat-sub">Total: {f_tot_men}</span></div>
            <div class="stat-item"><span class="stat-label">{tipo_intercalada} ({num_intercalada}x)</span><span class="stat-value">{f_inter}</span><span class="stat-sub">Total: {f_tot_inter}</span></div>
            <div class="stat-item"><span class="stat-label">Entrega ({perc_entrega:.0f}%)</span><span class="stat-value">{f_entg}</span><span class="stat-sub">Chaves</span></div>
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("Gerar Resumo para Cópia", type="primary", use_container_width=True):
        if not unidade: st.error("Preencha a Unidade.")
        elif preco_total <= 0: st.error("Preço inválido.")
        elif round(tot, 1) != 100.0: st.error("Feche 100% o fluxo.")
        else:
            dt = datetime.now().strftime("%d/%m/%Y")
            str_ent_res = f"{f_ent_total}" if num_entrada == 1 else f"{num_entrada}x de {f_ent_parc} (Total: {f_ent_total})"
            
            summary = f"""
*Simulação - {obra_selecionada}*
Unidade: {unidade} | Valor: {f_preco}

*Entrada ({perc_entrada:.1f}%):* {str_ent_res}
*Mensais ({num_mensal}x):* {f_men}
*{tipo_intercalada} ({num_intercalada}x):* {f_inter}
*Entrega ({perc_entrega:.1f}%):* {f_entg}

Data: {dt}
"""
            st.session_state.summary_text = summary
            st.session_state.data_to_save = [
                obra_selecionada, unidade, to_sheet_string(preco_total),
                to_sheet_string(perc_entrada), to_sheet_string(val_entrada_total),
                to_sheet_string(perc_mensal), num_mensal, to_sheet_string(val_por_mensal),
                to_sheet_string(perc_intercalada), num_intercalada, to_sheet_string(val_por_intercalada),
                to_sheet_string(perc_entrega), to_sheet_string(val_entrega), 
                datetime.now().strftime("%Y-%m-%d"),
                tipo_intercalada, num_entrada
            ]

    if st.session_state.get("summary_text"):
        st.markdown("##### Resumo Pronto")
        st.text_area("Copie aqui:", value=st.session_state.summary_text, height=300)
        if st.button("Salvar na Planilha", use_container_width=True):
            with st.spinner("Salvando..."):
                try:
                    sheet = get_worksheet()
                    if sheet:
                        nl = st.session_state.data_to_save
                        nl[13] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
                        sheet.append_row(nl, value_input_option='USER_ENTERED')
                        st.toast("Salvo!", icon="✅"); carregar_dados_planilha.clear()
                        reset_to_default_values(); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

with tab2:
    st.markdown(f"### <span style='color: {st.get_option('theme.primaryColor')};'>Simulações Salvas</span>", unsafe_allow_html=True)
    df = carregar_dados_planilha()
    
    if df is not None and not df.empty:
        df = df.sort_values(by="Data/Hora", ascending=False)
        sheet = get_worksheet()
        
        for idx, row in df.iterrows():
            try:
                pt = float(row.get('Preco Total', 0)); ve = float(row.get('Valor Entrada', 0))
                vm = float(row.get('Valor Mensal', 0)); 
                
                t_int = row.get('Tipo Intercalada', 'Semestrais') if 'Tipo Intercalada' in row else 'Semestrais'
                vi = float(row.get('Valor Intercalada', 0)) if 'Valor Intercalada' in row else float(row.get('Valor Semestral', 0))
                
                nm = int(row.get('Nº Mensal', 0))
                ni = int(row.get('Nº Intercalada', 0)) if 'Nº Intercalada' in row else int(row.get('Nº Semestral', 0))
                ne = int(row.get('Nº Parc Entrada', 1)) if 'Nº Parc Entrada' in row else 1
                
                tm = vm * nm; ti = vi * ni
                vent = float(row.get('Valor Entrega', 0))
                
                f_pt_s = format_currency(pt)
                f_ve_s = format_currency(ve)
                f_vm_s = format_currency(vm)
                f_tm_s = format_currency(tm)
                f_vi_s = format_currency(vi)
                f_ti_s = format_currency(ti)
                f_vent_s = format_currency(vent)
                
                data_salva = row.get('Data/Hora', '')

                txt_ent_salva = f"{f_ve_s}"
                if ne > 1:
                    v_parc_aprox = ve / ne
                    txt_ent_salva = f"{ne}x de {format_currency(v_parc_aprox)} (Total: {f_ve_s})"

                resumo_salvo = f"""
*Resumo da Simulação - {row.get('Obra','')}*
Unidade: {row.get('Unidade','')}

*Preço Total:* {f_pt_s}

*Entrada:* {txt_ent_salva}
*Mensais ({nm}x):* {f_vm_s} (Total: {f_tm_s})
*{t_int} ({ni}x):* {f_vi_s} (Total: {f_ti_s})
*Entrega:* {f_vent_s}

Data: {data_salva}
"""
            except: continue
            
            card_html = f"""
            <div class="lavie-card" style="margin-bottom:0;">
                <div style="display:flex; justify-content:space-between; margin-bottom:15px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:10px;">
                    <span style="font-size:1.1rem; font-weight:bold;">{row['Obra']}</span>
                    <span style="background:rgba(227,112,38,0.2); color:#E37026; padding:4px 10px; border-radius:12px; font-size:0.8rem;">Unidade {row['Unidade']}</span>
                </div>
                <div class="stats-grid">
                    <div class="stat-item"><span class="stat-label">Preço</span><span class="stat-value highlight">{f_pt_s}</span></div>
                    <div class="stat-item"><span class="stat-label">Entrada</span><span class="stat-value">{format_currency(ve)}</span></div>
                    <div class="stat-item"><span class="stat-label">Mensais ({nm}x)</span><span class="stat-value">{format_currency(vm)}</span><span class="stat-sub">Total: {f_tm_s}</span></div>
                    <div class="stat-item"><span class="stat-label">{t_int} ({ni}x)</span><span class="stat-value">{format_currency(vi)}</span><span class="stat-sub">Total: {f_ti_s}</span></div>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            st.markdown("")
            
            with st.expander("Opções e Copiar"):
                st.markdown("###### Copiar Resumo")
                st.code(resumo_salvo, language="markdown")
                
                c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
                if c1.button(f"Editar", key=f"ed_{idx}", use_container_width=True):
                    if sheet: 
                        c = sheet.find(row['Data/Hora'])
                        if c: edit_dialog(row.to_dict(), sheet, c.row)
                if c4.button(f"Excluir", key=f"dl_{idx}", type="primary", use_container_width=True):
                    if sheet:
                        c = sheet.find(row['Data/Hora'])
                        if c:
                            sheet.delete_rows(c.row); st.toast("Excluído!")
                            carregar_dados_planilha.clear(); time.sleep(1); st.rerun()
            st.markdown("<div style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
    else: st.info("Nenhuma simulação salva.")
