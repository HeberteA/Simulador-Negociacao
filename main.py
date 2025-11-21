import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import pandas as pd
import altair as alt
import time

st.set_page_config(
    page_title="Simulador de Negociação",
    page_icon="Lavie1.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

APP_STYLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

[data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 10% 20%, #1e1e24 0%, #050505 90%);
    background-attachment: fixed;
    font-family: 'Inter', sans-serif;
}

/* Inputs e Selects Glassmorphism */
div[data-baseweb="input"] > div, div[data-baseweb="select"] > div {
    background-color: rgba(255, 255, 255, 0.03) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    color: white !important;
    border-radius: 8px !important;
}
div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input {
    color: white !important;
}

/* Estilização dos Cards Customizados (Markdown) */
.lavie-card {
    background: linear-gradient(160deg, rgba(30,30,36, 0.6) 0%, rgba(10,10,10, 0.8) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 0px; /* Margem zero pois o expander vem logo abaixo */
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}
.lavie-card:hover {
    border-color: rgba(227, 112, 38, 0.3);
    box-shadow: 0 12px 32px rgba(227, 112, 38, 0.05);
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 16px;
    margin-bottom: 20px;
}
.card-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: -0.5px;
}
.card-tag {
    background: rgba(227, 112, 38, 0.15);
    color: #E37026;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 600;
    border: 1px solid rgba(227, 112, 38, 0.2);
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 24px;
}
.stat-item {
    display: flex;
    flex-direction: column;
}
.stat-label {
    font-size: 0.75rem;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 6px;
}
.stat-value {
    font-size: 1.2rem;
    color: #fff;
    font-weight: 600;
}
.stat-value.highlight {
    color: #E37026;
}
.stat-sub {
    font-size: 0.8rem;
    color: #555;
    margin-top: 2px;
}

/* Ajuste fino para o expander nativo parecer parte do card */
div[data-testid="stExpander"] {
    background-color: rgba(30,30,36, 0.3);
    border: 1px solid rgba(255,255,255,0.05);
    border-top: none;
    border-radius: 0 0 16px 16px;
    margin-top: -5px; /* Cola no card de cima */
    margin-bottom: 24px;
}
div[data-testid="stExpander"] details {
    border: none;
}
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
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def to_sheet_string(value):
    """Converte um float (ex: 5555.56) para uma string PT-BR (ex: "5555,56")"""
    return f"{value:.2f}".replace('.', ',')

@st.cache_resource(ttl=60)
def get_worksheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        spreadsheet_key = st.secrets["spreadsheet_info"]["spreadsheet_key"]
        worksheet_name = st.secrets["spreadsheet_info"]["worksheet_name"]
        spreadsheet = client.open_by_key(spreadsheet_key)
        worksheet = spreadsheet.worksheet(worksheet_name)
        return worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Erro: Planilha não encontrada. Verifique a 'spreadsheet_key' nos seus Segredos.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Erro: Aba '{worksheet_name}' não encontrada. Verifique o 'worksheet_name' nos seus Segredos.")
        return None
    except KeyError as e:
        if "spreadsheet_info" in str(e):
             st.error("Erro de Segredo: A seção '[spreadsheet_info]' está faltando no seu secrets.toml. Verifique o modelo.")
        else:
             st.error(f"Erro de Segredo: Chave não encontrada: {e}. Verifique seu secrets.toml.")
        return None
    except Exception as e:
        st.error(f"Erro ao autenticar ou abrir a planilha: {e}")
        return None

@st.cache_data(ttl=5) 
def carregar_dados_planilha():
    try:
        sheet = get_worksheet()
        if sheet is None: return pd.DataFrame()

        data = sheet.get_all_values()
        if not data or len(data) < 2: return pd.DataFrame()

        df = pd.DataFrame(data[1:], columns=data[0])
        cols_para_converter = [
            'Preco Total', 'Valor Entrada', 'Valor Mensal', 'Valor Semestral', 'Valor Entrega',
            '% Entrada', '% Mensal', '% Semestral', '% Entrega',
            'Nº Mensal', 'Nº Semestral'
        ]
        for col in cols_para_converter:
            if col in df.columns:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                    errors='coerce'
                ).fillna(0)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame()


def set_default_values():
    defaults = {
        "main_unidade": "101",
        "main_preco_total": 500000.0,
        "main_num_mensal": 36,
        "main_num_semestral": 6,
        "perc_entrada": 20.0,
        "perc_mensal": 40.0,
        "perc_semestral": 20.0,
        "perc_entrega": 20.0,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if "total_percent" not in st.session_state:
        st.session_state.total_percent = (
            defaults["perc_entrada"] +
            defaults["perc_mensal"] +
            defaults["perc_semestral"] +
            defaults["perc_entrega"]
        )

def reset_to_default_values():
    keys_to_clear = [
        "main_unidade", "main_preco_total", "main_num_mensal", "main_num_semestral",
        "perc_entrada", "perc_mensal", "perc_semestral", "perc_entrega",
        "total_percent", "summary_text", "data_to_save"
    ]

    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


@st.dialog("Editar Simulação")
def edit_dialog(row_data, sheet, sheet_row_index):
    st.markdown(f"Editando **{row_data['Obra']}** | Unidade: **{row_data['Unidade']}**")

    if "edit_total_percent" not in st.session_state:
        st.session_state.edit_total_percent = float(row_data.get('% Entrada', 0) + row_data.get('% Mensal', 0) + row_data.get('% Semestral', 0) + row_data.get('% Entrega', 0))

    def atualizar_percentual_edit():
        st.session_state.edit_total_percent = (
            st.session_state.get('edit_perc_entrada', 0.0) +
            st.session_state.get('edit_perc_mensal', 0.0) +
            st.session_state.get('edit_perc_semestral', 0.0) +
            st.session_state.get('edit_perc_entrega', 0.0)
        )

    form_cols = st.columns(2)
    with form_cols[0]:
        st.markdown("##### Dados da Simulação")
        st.text_input("Unidade / Sala", value=row_data['Unidade'], disabled=True)
        preco_total = st.number_input(
            "Preço Total (R$)", 
            min_value=0.0, 
            step=1000.0, 
            value=float(row_data.get('Preco Total', 500000)), 
            key="edit_preco_total"
        )
        st.markdown("##### Nº de Parcelas")
        num_mensal = st.number_input(
            "Nº de Parcelas Mensais", 
            min_value=0, 
            step=1, 
            value=int(row_data.get('Nº Mensal', 36)), 
            key="edit_num_mensal"
        )
        num_semestral = st.number_input(
            "Nº de Parcelas Semestrais", 
            min_value=0, 
            step=1, 
            value=int(row_data.get('Nº Semestral', 6)), 
            key="edit_num_semestral"
        )

    with form_cols[1]:
        st.markdown("##### Definição do Fluxo de Pagamento (%)")

        perc_entrada = st.number_input(
            "Entrada (%)", min_value=0.0, max_value=100.0,
            value=float(row_data.get('% Entrada', 0)), 
            step=0.5, key="edit_perc_entrada", format="%.2f", on_change=atualizar_percentual_edit
        )
        perc_mensal = st.number_input(
            "Total Parcelas Mensais (%)", min_value=0.0, max_value=100.0, 
            value=float(row_data.get('% Mensal', 0)), 
            step=0.5, key="edit_perc_mensal", format="%.2f", on_change=atualizar_percentual_edit
        )
        perc_semestral = st.number_input(
            "Total Parcelas Semestrais (%)", min_value=0.0, max_value=100.0, 
            value=float(row_data.get('% Semestral', 0)), 
            step=0.5, key="edit_perc_semestral", format="%.2f", on_change=atualizar_percentual_edit
        )
        perc_entrega = st.number_input(
            "Entrega (%)", min_value=0.0, max_value=100.0,
            value=float(row_data.get('% Entrega', 0)), 
            step=0.5, key="edit_perc_entrega", format="%.2f", on_change=atualizar_percentual_edit
        )

        total_percent = st.session_state.edit_total_percent
        if total_percent > 100.0:
            st.error(f"Percentual excede 100%! ({total_percent:.1f}%)")
        elif total_percent < 100.0:
            st.warning(f"Percentual não fecha 100%. ({total_percent:.1f}%)")
        else:
            st.success(f"Percentual fechado em 100%!")

    st.markdown("---")

    if st.button("Salvar Alterações", type="primary", use_container_width=True):
        if round(total_percent, 1) != 100.0:
            st.error(f"O percentual total deve ser 100% para salvar (Atual: {total_percent:.1f}%).")
        else:
            val_entrada = (preco_total * perc_entrada) / 100
            val_total_mensal = (preco_total * perc_mensal) / 100
            val_total_semestral = (preco_total * perc_semestral) / 100
            val_entrega = (preco_total * perc_entrega) / 100

            val_por_mensal = (val_total_mensal / num_mensal) if num_mensal > 0 else 0
            val_por_semestral = (val_total_semestral / num_semestral) if num_semestral > 0 else 0

            linha_atualizada = [
                row_data['Obra'], 
                row_data['Unidade'], 
                to_sheet_string(preco_total),
                to_sheet_string(perc_entrada), 
                to_sheet_string(val_entrada),
                to_sheet_string(perc_mensal), 
                num_mensal,
                to_sheet_string(val_por_mensal),
                to_sheet_string(perc_semestral), 
                num_semestral, 
                to_sheet_string(val_por_semestral),
                to_sheet_string(perc_entrega), 
                to_sheet_string(val_entrega),
                row_data['Data/Hora']
            ]

            try:
                range_to_update = f'A{sheet_row_index}:N{sheet_row_index}'
                sheet.update(range_to_update, [linha_atualizada], value_input_option='USER_ENTERED')

                st.toast("Alterações salvas com sucesso!")

                st.cache_data.clear()
                st.cache_resource.clear()

                keys_to_delete = [k for k in st.session_state if k.startswith('edit_')]
                for k in keys_to_delete:
                    del st.session_state[k]

                return True
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
                return False

    if st.button("Cancelar", use_container_width=True):
        keys_to_delete = [k for k in st.session_state if k.startswith('edit_')]
        for k in keys_to_delete:
            del st.session_state[k]
        return True

set_default_values()

try:
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        st.image("LavieC.png", width=750)
except FileNotFoundError:
    st.warning("Arquivo 'LavieC.png' não encontrado. Coloque-o na mesma pasta do app.py.")
except Exception as e:
    st.error(f"Não foi possível carregar a imagem: {e}")


st.title("Simulador de Negociação")
st.markdown("---")

lista_obras = [
    "Burj Lavie",
    "Lavie Areia Dourada",
    "The Well By OM25 e Lavie",
    "Lavie Camboinha",
    "Arc Space"
]

obra_selecionada = st.selectbox(
    "Escolha a Obra para simular:", 
    lista_obras, 
    key="obra", 
    label_visibility="collapsed"
)

tab1, tab2 = st.tabs(["Simular Negociação", "Simulações Salvas"])

with tab1:
    if "summary_text" not in st.session_state:
        st.session_state.summary_text = ""
    if "data_to_save" not in st.session_state:
        st.session_state.data_to_save = None

    st.markdown(f"<h3 style='color: #E37026; margin: 0 0 5px 0;'>Nova Simulação</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #666; font-size: 0.9rem; margin-bottom: 25px;'>Obra Selecionada: <strong style='color:#fff'>{obra_selecionada}</strong></p>", unsafe_allow_html=True)

    col_dados, col_prazos = st.columns([1.2, 1])
        
    with col_dados:
        with st.container(border=True):
            render_header("apartment", "Dados da Unidade")
            unidade = st.text_input("Unidade / Sala", key="main_unidade")
            preco_total = st.number_input("Preço Total (R$)", min_value=0.0, step=1000.0, key="main_preco_total", format="%.2f")    
    with col_prazos:
        with st.container(border=True):
            render_header("calendar_month", "Configuração de Prazos")
            num_mensal = st.number_input("Qtd. Mensais", min_value=0, step=1, key="main_num_mensal")
            num_semestral = st.number_input("Qtd. Semestrais", min_value=0, step=1, key="main_num_semestral")

    st.markdown("<br>", unsafe_allow_html=True)

    with st.container(border=True):
        render_header("pie_chart", "Distribuição do Fluxo (%)")

        if "total_percent" not in st.session_state:
            st.session_state.total_percent = 0.0

        def atualizar_percentual():
            st.session_state.total_percent = (
                st.session_state.get('perc_entrada', 0.0) +
                st.session_state.get('perc_mensal', 0.0) +
                st.session_state.get('perc_semestral', 0.0) +
                st.session_state.get('perc_entrega', 0.0)
            )

        c_flow = st.columns(4)
        perc_entrada = c_flow[0].number_input("Entrada (%)", 0.0, 100.0, step=1.0, format="%.2f", key="perc_entrada", on_change=atualizar_percentual)
        perc_mensal = c_flow[1].number_input("Mensais (%)", 0.0, 100.0, step=1.0, format="%.2f", key="perc_mensal", on_change=atualizar_percentual)
        perc_semestral = c_flow[2].number_input("Semestrais (%)", 0.0, 100.0, step=1.0, format="%.2f", key="perc_semestral", on_change=atualizar_percentual)
        perc_entrega = c_flow[3].number_input("Entrega (%)", 0.0, 100.0, step=1.0, format="%.2f", key="perc_entrega", on_change=atualizar_percentual)

        total_percent = st.session_state.total_percent
        color_st = "#09ab3b" if total_percent == 100 else "#ff4b4b"
        icon_st = "check_circle" if total_percent == 100 else "warning"

        st.markdown(f"""
        <div style="margin-top: 20px; display: flex; justify-content: flex-end; align-items: center; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.05);">
            <span style="font-size: 0.85rem; color: #666; margin-right: 10px;">Status do Fechamento:</span>
            <div style="display:flex; align-items:center; color: {color_st}; background: rgba(255,255,255,0.05); padding: 5px 10px; border-radius: 20px;">
                <span class="material-symbols-rounded" style="font-size:18px; margin-right:6px;">{icon_st}</span>
                <span style="font-weight:600;">{total_percent:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    val_entrada = (preco_total * perc_entrada) / 100
    val_total_mensal = (preco_total * perc_mensal) / 100
    val_total_semestral = (preco_total * perc_semestral) / 100
    val_entrega = (preco_total * perc_entrega) / 100

    val_por_mensal = (val_total_mensal / num_mensal) if num_mensal > 0 else 0
    val_por_semestral = (val_total_semestral / num_semestral) if num_semestral > 0 else 0

    st.markdown("<br>", unsafe_allow_html=True)
    
    # CARD DE RESULTADO (Manual)
    render_header("analytics", "Resultado Financeiro")

    f_ent = format_currency(val_entrada)
    f_men = format_currency(val_por_mensal)
    f_t_men = format_currency(val_total_mensal)
    f_sem = format_currency(val_por_semestral)
    f_t_sem = format_currency(val_total_semestral)
    f_entg = format_currency(val_entrega)

    card_html = f"""
    <div class="lavie-card">
    <div class="stats-grid">
    <div class="stat-item">
        <span class="stat-label">Entrada ({perc_entrada:.0f}%)</span>
        <span class="stat-value highlight">{f_ent}</span>
        <span class="stat-sub">Pagamento Ato</span>
    </div>
    <div class="stat-item">
        <span class="stat-label">Mensais ({num_mensal}x)</span>
        <span class="stat-value">{f_men}</span>
        <span class="stat-sub">Total: {f_t_men}</span>
    </div>
    <div class="stat-item">
        <span class="stat-label">Semestrais ({num_semestral}x)</span>
        <span class="stat-value">{f_sem}</span>
        <span class="stat-sub">Total: {f_t_sem}</span>
    </div>
    <div class="stat-item">
        <span class="stat-label">Entrega ({perc_entrega:.0f}%)</span>
        <span class="stat-value">{f_entg}</span>
        <span class="stat-sub">Pagamento Final</span>
    </div>
    </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("Gerar Resumo para Cópia", type="primary", use_container_width=True, key="btn_gerar_resumo"):
        
        if not unidade:
            st.error("Preencha a Unidade.")
        elif preco_total <= 0:
            st.error("Preencha o Preço Total.")
        elif round(st.session_state.total_percent, 1) != 100.0:
            st.error(f"Ajuste o percentual para 100% (Atual: {st.session_state.total_percent:.1f}%).")
        else:
            data_hora_atual = datetime.now().strftime("%Y-%m-%d")
            summary = f"""
Resumo da Simulação - {obra_selecionada}
Unidade: {unidade}

Preço Total: {format_currency(preco_total)}

Entrada ({perc_entrada:.1f}%): {val_entrada}
Mensais ({num_mensal}x): {val_por_mensal} (Total: {val_total_mensal})
Semestrais ({num_semestral}x): {val_por_semestral} (Total: {val_total_semestral})
Entrega ({perc_entrega:.1f}%): {val_entrega}

Data: {data_hora_atual}
"""
            st.session_state.summary_text = summary
            st.session_state.data_to_save = [
                obra_selecionada, unidade, to_sheet_string(preco_total),
                to_sheet_string(perc_entrada), to_sheet_string(val_entrada),
                to_sheet_string(perc_mensal), num_mensal, to_sheet_string(val_por_mensal),
                to_sheet_string(perc_semestral), num_semestral, to_sheet_string(val_por_semestral),
                to_sheet_string(perc_entrega), to_sheet_string(val_entrega),
                data_hora_atual
            ]

    if st.session_state.get("summary_text"):
        st.markdown("##### Resumo Pronto")
        st.text_area("Copie aqui:", value=st.session_state.summary_text, height=300, key="summary_display")

        if st.button("Salvar na Planilha", use_container_width=True, key="btn_salvar_final"):
            with st.spinner("Conectando ao Google Sheets..."):
                try:
                    sheet = get_worksheet()
                    if sheet and st.session_state.data_to_save:
                        nova_linha = st.session_state.data_to_save
                        nova_linha[-1] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
                        sheet.append_row(nova_linha, value_input_option='USER_ENTERED')
            
                        st.toast("Simulação salva com sucesso!", icon="✅")
                        carregar_dados_planilha.clear()
                        reset_to_default_values() 
                        time.sleep(1)
                        st.rerun()
                        
                    else:
                        st.error("Erro ao conectar com a planilha.")
                except Exception as e:
                    st.error(f"Erro: {e}")


with tab2:
    st.markdown(f"### <span style='color: {st.get_option('theme.primaryColor')};'>Simulações Salvas</span>", unsafe_allow_html=True)

    df = carregar_dados_planilha()

    if df is not None and not df.empty:
        df = df.sort_values(by="Data/Hora", ascending=False)
        sheet = get_worksheet()

        for index, row in df.iterrows():
            try:
                preco_total_num = float(row.get('Preco Total', 0))
                val_entrada_num = float(row.get('Valor Entrada', 0))
                val_mensal_num = float(row.get('Valor Mensal', 0))
                num_mensal_num = int(row.get('Nº Mensal', 0))
                val_semestral_num = float(row.get('Valor Semestral', 0))
                num_semestral_num = int(row.get('Nº Semestral', 0))
                val_entrega_num = float(row.get('Valor Entrega', 0))

                total_mensal = val_mensal_num * num_mensal_num
                total_semestral = val_semestral_num * num_semestral_num

            except (ValueError, TypeError) as e:
                st.error(f"Erro na linha {index}: {e}")
                continue
            
            fmt_preco = format_currency(preco_total_num)
            fmt_entrada = format_currency(val_entrada_num)
            fmt_mensal = format_currency(val_mensal_num)
            fmt_semestral = format_currency(val_semestral_num)
            fmt_entrega = format_currency(val_entrega_num)
            
            card_html = f"""
<div class="lavie-card" style="margin-bottom: 0px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px; border-bottom:1px solid rgba(255,255,255,0.1); padding-bottom:10px;">
    <span style="font-size:1.1rem; font-weight:bold; color:#fff;">{row['Obra']}</span>
    <span style="background:rgba(227,112,38,0.2); color:#E37026; padding:4px 10px; border-radius:12px; font-size:0.8rem;">Unidade {row['Unidade']}</span>
</div>
<div class="stats-grid">
    <div class="stat-item">
        <span class="stat-label">Preço Total</span>
        <span class="stat-value highlight">{fmt_preco}</span>
    </div>
    <div class="stat-item">
        <span class="stat-label">Entrada</span>
        <span class="stat-value">{fmt_entrada}</span>
    </div>
    <div class="stat-item">
        <span class="stat-label">Mensais ({num_mensal_num}x)</span>
        <span class="stat-value">{fmt_mensal}</span>
        <span class="stat-sub">Total: {format_currency(total_mensal)}</span>
    </div>
    <div class="stat-item">
        <span class="stat-label">Semestrais ({num_semestral_num}x)</span>
        <span class="stat-value">{fmt_semestral}</span>
        <span class="stat-sub">Total: {format_currency(total_semestral)}</span>
    </div>
</div>
</div>
"""
            st.markdown(card_html, unsafe_allow_html=True)
            st.markdown("")
            
            with st.expander("Opções e Detalhes"):
                c_act1, c_act2, c_act3, c_act4 = st.columns([1, 2, 2, 1])
                with c_act1:
                     if st.button(f"Editar {row['Unidade']}", key=f"edit_{index}"):
                        if sheet:
                            cell = sheet.find(row['Data/Hora'])
                            if cell: edit_dialog(row.to_dict(), sheet, cell.row)

                with c_act4:
                     if st.button(f"Excluir {row['Unidade']}", key=f"del_{index}", type="primary"):
                        if sheet:
                            cell = sheet.find(row['Data/Hora'])
                            if cell:
                                sheet.delete_rows(cell.row)
                                st.toast("Simulação excluída!", icon="🗑️")
                                carregar_dados_planilha.clear() 
                                time.sleep(1)
                                st.rerun() 

            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    else:
        st.info("Nenhuma simulação salva.")
