import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import locale

st.set_page_config(
    page_title="Simulador de Negociação",
    page_icon="Lavie1.png",
    layout="centered"
)

COR_PRIMARIA = "#E37026"

@st.cache_resource
def connect_to_gsheets():
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = [
            "https.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        spreadsheet_key = st.secrets["spreadsheet_key"]
        spreadsheet = client.open_by_key(spreadsheet_key)
        worksheet_name = st.secrets["worksheet_name"]
        worksheet = spreadsheet.worksheet(worksheet_name)
        return worksheet
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets: {e}")
        st.info("Verifique se as credenciais 'gcp_service_account', 'spreadsheet_key' e 'worksheet_name' estão configuradas corretamente nos Segredos (Secrets) do Streamlit.")
        return None

@st.cache_data(ttl=60)
def load_data_from_gsheets(_worksheet):
    if _worksheet:
        try:
            data = _worksheet.get_all_records()
            df = pd.DataFrame(data)
            return df
        except Exception as e:
            st.error(f"Erro ao carregar dados da planilha: {e}")
    return pd.DataFrame()

def format_currency(value):
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        return locale.currency(value, grouping=True, symbol=True)
    except:
        return f"R$ {value:,.2f}"

col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    try:
        st.image("Lavie.png", width=400)
    except Exception as e:
        st.error(f"Não foi possível carregar a imagem 'LavieC.png'. Verifique se o arquivo está no lugar certo. Erro: {e}")

st.title("Simulador de Negociação Imobiliária")

tab1, tab2 = st.tabs(["Simular Negociação", "Simulações Salvas"])

with tab1:
    st.markdown(f'<h3 style="color: {COR_PRIMARIA};">1. Selecione a Obra</h3>', unsafe_allow_html=True)
    
    lista_obras = [
        "Burj Lavie",
        "Lavie Areia Dourada",
        "The Well By OM25 e Lavie",
        "Lavie Camboinha",
        "Arc Space"
    ]
    st.selectbox("Obra", lista_obras, key="obra", label_visibility="collapsed")

    
    col_inputs1, col_inputs2 = st.columns(2)

    with col_inputs1:
        st.markdown(f'<h3 style="color: {COR_PRIMARIA};">2. Dados da Simulação</h3>', unsafe_allow_html=True)
        st.text_input("Número da Sala / Unidade", key="sala")
        preco_total = st.number_input("Preço da Sala (R$)", min_value=0.0, value=500000.0, step=1000.0, format="%.2f")

        st.divider()
        st.markdown(f'<h3 style="color: {COR_PRIMARIA};">4. Número de Parcelas (N/P)</h3>', unsafe_allow_html=True)
        num_mensal = st.number_input("Nº de Parcelas Mensais", min_value=1, value=36, step=1)
        num_semestral = st.number_input("Nº de Parcelas Semestrais", min_value=1, value=6, step=1)

    with col_inputs2:
        st.markdown(f'<h3 style="color: {COR_PRIMARIA};">3. Definição do Fluxo (%)</h3>', unsafe_allow_html=True) 
        perc_entrada = st.slider("Entrada (%)", 0, 100, 20)
        perc_mensal = st.slider("Parcelas Mensais (%)", 0, 100, 30)
        perc_semestral = st.slider("Parcelas Semestrais (%)", 0, 100, 20)
        perc_entrega = st.slider("Entrega (%)", 0, 100, 30)
        
        st.divider()
        total_perc = perc_entrada + perc_mensal + perc_semestral + perc_entrega
        if total_perc != 100:
            st.warning(f"Soma: {total_perc}%. (Ideal: 100%)") 
        else:
            st.success("Soma: 100%.") 

    st.divider() 

    if preco_total > 0:
        valor_total_entrada = preco_total * (perc_entrada / 100)
        valor_total_mensal = preco_total * (perc_mensal / 100)
        valor_total_semestral = preco_total * (perc_semestral / 100)
        valor_total_entrega = preco_total * (perc_entrega / 100)
        
        valor_parcela_mensal = valor_total_mensal / num_mensal if num_mensal > 0 else 0
        valor_parcela_semestral = valor_total_semestral / num_semestral if num_semestral > 0 else 0

        st.markdown(f'<h3 style="color: {COR_PRIMARIA};">5. Valores Calculados</h3>', unsafe_allow_html=True)
        
        col3, col4 = st.columns(2)
        with col3:
            st.metric("Valor da Entrada", f"R$ {valor_total_entrada:,.2f}")
            st.metric(f"Valor por Parcela Mensal ({num_mensal}x)", f"R$ {valor_parcela_mensal:,.2f}")
        with col4:
            st.metric("Valor na Entrega", f"R$ {valor_total_entrega:,.2f}")
            st.metric(f"Valor por Parcela Semestral ({num_semestral}x)", f"R$ {valor_parcela_semestral:,.2f}")

        st.divider()
        st.markdown(f'<h3 style="color: {COR_PRIMARIA};">6. Resumo para Envio</h3>', unsafe_allow_html=True)
        
        resumo = f"""
        *Resumo da Simulação - {st.session_state.obra}*
        *Unidade:* {st.session_state.sala or 'N/D'}
        *Preço Total:* R$ {preco_total:,.2f}

        *Fluxo de Pagamento:*
        - *Entrada ({perc_entrada}%):* R$ {valor_total_entrada:,.2f}
        - *Mensais ({perc_mensal}%):* {num_mensal}x de R$ {valor_parcela_mensal:,.2f}
        - *Semestrais ({perc_semestral}%):* {num_semestral}x de R$ {valor_parcela_semestral:,.2f}
        - *Entrega ({perc_entrega}%):* R$ {valor_total_entrega:,.2f}
        """
        st.text_area("Resumo", resumo, height=250)
        
        if st.button("Salvar Simulação na Planilha", type="primary", use_container_width=True):
            client = get_gspread_client()
            if client:
                sheet = get_worksheet(client)
                if sheet:
                    try:
                        data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        nova_linha = [
                            st.session_state.obra,
                            st.session_state.sala,
                            preco_total,
                            perc_entrada,
                            valor_total_entrada,
                            perc_mensal,
                            num_mensal,
                            valor_parcela_mensal,
                            perc_semestral,
                            num_semestral,
                            valor_parcela_semestral,
                            perc_entrega,
                            valor_total_entrega,
                            data_hora
                        ]
                        
                        sheet.append_row(nova_linha)
                        st.success("Simulação salva na planilha com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao salvar dados na planilha: {e}")

with tab2:
    st.markdown(f'<h3 style="color: {COR_PRIMARIA};">Simulações Salvas</h3>', unsafe_allow_html=True)
    
    client = get_gspread_client()
    if client:
        sheet = get_worksheet(client)
        if sheet:
            try:
                dados = sheet.get_all_records()
                if dados:
                    df = pd.DataFrame(dados)
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("Nenhuma simulação salva ainda.")
            except Exception as e:
                st.error(f"Erro ao carregar dados da planilha: {e}")
    
    if st.button("Atualizar Dados"):
        st.rerun()
