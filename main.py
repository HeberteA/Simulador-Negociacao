import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
import json
import locale

st.set_page_config(
    page_title="Simulador de Negociação",
    page_icon="Lavie1.png",
    layout="centered" 
)

COR_PRIMARIA = "#E37026" 

def format_currency(value):
    try:
        locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
        return locale.currency(value, grouping=True, symbol='R$')
    except (ValueError, TypeError):
        return "R$ 0,00"
    except Exception:
        return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
def get_gspread_client():
    try:
        creds_json = dict(st.secrets.gcp_service_account)
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Erro ao conectar com o Google Sheets (Autenticação): {e}")
        return None

def get_worksheet(client):
    try:
        spreadsheet_key = st.secrets.spreadsheet_key
        worksheet_name = st.secrets.worksheet_name
        sheet = client.open_by_key(spreadsheet_key).worksheet(worksheet_name)
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Erro: Planilha (Spreadsheet) não encontrada. Verifique a 'spreadsheet_key'.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Erro: Aba (Worksheet) '{worksheet_name}' não encontrada. Verifique 'worksheet_name'.")
        return None
    except Exception as e:
        st.error(f"Erro ao abrir a planilha: {e}")
        return None


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
    
    if st.button("Atualizar Dados"):
        st.cache_data.clear() 
        st.rerun()

    client = get_gspread_client()
    if client:
        sheet = get_worksheet(client)
        if sheet:
            df = carregar_dados_planilha(sheet)
            
            if not df.empty:
                df = df.sort_values(by="Data/Hora", ascending=False)
                
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
                    
                    except (ValueError, TypeError):
                        st.error(f"Erro ao processar dados numéricos da linha {index}. Verifique a planilha.")
                        continue


                    with st.container(border=True):
                        cols_header = st.columns([1, 1.5, 1.5, 1.5])
                        cols_header[0].markdown(f"**{row['Obra']}** | Unidade: **{row['Unidade']}**")
                        cols_header[1].metric("Preço Total", format_currency(preco_total_num))
                        cols_header[2].metric("Entrada", format_currency(val_entrada_num))
                        cols_header[3].metric(f"Mensais ({num_mensal_num}x)", format_currency(val_mensal_num))
                        
                        with st.expander("Ver Detalhes, Gráfico ou Excluir"):
                            
                            tab_resumo, tab_editar = st.tabs(["Resumo e Gráfico", "Editar / Excluir"])
                            
                            with tab_resumo:
                                st.markdown("##### Resumo Detalhado")
                                detail_cols = st.columns(3)
                                detail_cols[0].metric("Total em Mensais", format_currency(total_mensal))
                                detail_cols[1].metric(f"Semestrais ({num_semestral_num}x)", format_currency(val_semestral_num))
                                detail_cols[2].metric("Total em Semestrais", format_currency(total_semestral))
                                detail_cols[0].metric("Entrega", format_currency(val_entrega_num))

                                st.markdown("##### Composição do Pagamento")
                                
                                try:
                                    chart_data = pd.DataFrame({
                                        'Tipo': ['Entrada', 'Mensais', 'Semestrais', 'Entrega'],
                                        'Valor': [val_entrada_num, total_mensal, total_semestral, val_entrega_num]
                                    })
                                    chart_data = chart_data[chart_data['Valor'] > 0]
                                    
                                    pie_chart = alt.Chart(chart_data).mark_arc(outerRadius=120, innerRadius=80).encode(
                                        theta=alt.Theta("Valor:Q", stack=True),
                                        color=alt.Color("Tipo:N", title="Tipo de Pagamento"),
                                        tooltip=['Tipo', 'Valor', alt.Tooltip("Valor:Q", format=".1%", title="% do Total")]
                                    ).properties(
                                        title="Composição do Valor Total"
                                    )
                                    st.altair_chart(pie_chart, use_container_width=True)
                                except Exception as e:
                                    st.error(f"Não foi possível gerar o gráfico. {e}")

                            with tab_editar:
                                st.markdown("##### Ações")
                                st.info("A função 'Editar' ainda não está disponível.")
                                
                                delete_key = f"delete_{index}_{row['Unidade']}"
                                if st.button("Excluir Simulação", key=delete_key, type="primary"):
                                    try:
                                        
                                        row_to_delete = index + 2
                                        sheet.delete_rows(row_to_delete)
                                        st.success(f"Simulação da Unidade '{row['Unidade']}' excluída.")
                                        st.cache_data.clear()
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Erro ao excluir linha: {e}")
            else:
                st.info("Nenhuma simulação salva para exibir.")
