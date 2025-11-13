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

background_texture_css = """
<style>
[data-testid="stAppViewContainer"] {
    /* Opção: Linho Preto (Sutil e Elegante) */
    background-image: url("https://www.transparenttextures.com/patterns/handmade-paper.png");
    background-repeat: repeat;
}
</style>
"""
st.markdown(background_texture_css, unsafe_allow_html=True)

def format_currency(value):
    if value is None:
        return "R$ 0,00"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

@st.cache_resource(ttl=3600)
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

@st.cache_data(ttl=600)
def carregar_dados_planilha():
    try:
        sheet = get_worksheet()
        if sheet is None:
            st.error("Falha ao carregar dados: conexão com planilha indisponível.")
            return pd.DataFrame()

        data = sheet.get_all_records()
        if not data:
            st.warning("Nenhuma simulação encontrada na planilha.")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        cols_para_converter = [
            'Preco Total', 'Valor Entrada', 'Valor Mensal', 'Valor Semestral', 'Valor Entrega',
            '% Entrada', '% Mensal', '% Semestral', '% Entrega',
            'Nº Mensal', 'Nº Semestral'
        ]
        
        for col in cols_para_converter:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
        return pd.DataFrame()

def set_default_values():
    defaults = {
        "main_unidade": "101",
        "main_preco_total": 100000.0,
        "main_num_mensal": 12,
        "main_num_semestral": 0,
        "perc_entrada": 20.0,
        "perc_mensal": 60.0,
        "perc_semestral": 0.0,
        "perc_entrega": 20.0,
        "total_percent": 100.0
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def reset_to_default_values():
    defaults = {
        "main_unidade": "101",
        "main_preco_total": 100000.0,
        "main_num_mensal": 12,
        "main_num_semestral": 0,
        "perc_entrada": 20.0,
        "perc_mensal": 60.0,
        "perc_semestral": 0.0,
        "perc_entrega": 20.0,
        "total_percent": 100.0
    }
    
    for key, value in defaults.items():
        st.session_state[key] = value
    
    st.session_state.summary_text = ""
    st.session_state.data_to_save = None
    
def edit_dialog(row_data, row_index, sheet):
    dialog = st.dialog("Editar Simulação", dismissible=True)
    with dialog:
        st.markdown(f"### Editando Unidade: {row_data['Unidade']}")
        
        key_prefix = f"edit_{row_index}"
        
        if f"{key_prefix}_preco" not in st.session_state:
            st.session_state[f"{key_prefix}_preco"] = float(row_data.get('Preco Total', 0))
            st.session_state[f"{key_prefix}_ent_perc"] = float(row_data.get('% Entrada', 0))
            st.session_state[f"{key_prefix}_mens_perc"] = float(row_data.get('% Mensal', 0))
            st.session_state[f"{key_prefix}_sem_perc"] = float(row_data.get('% Semestral', 0))
            st.session_state[f"{key_prefix}_entg_perc"] = float(row_data.get('% Entrega', 0))
            st.session_state[f"{key_prefix}_num_mens"] = int(row_data.get('Nº Mensal', 0))
            st.session_state[f"{key_prefix}_num_sem"] = int(row_data.get('Nº Semestral', 0))

        preco_total_edit = st.number_input(
            "Preço Total da Unidade (R$)", 
            min_value=0.0, 
            key=f"{key_prefix}_preco",
            format="%.2f",
            step=1000.0
        )
        
        edit_c1, edit_c2 = st.columns(2)
        with edit_c1:
            num_mensal_edit = st.number_input("Nº de Parcelas Mensais", min_value=0, step=1, key=f"{key_prefix}_num_mens")
        with edit_c2:
            num_semestral_edit = st.number_input("Nº de Parcelas Semestrais", min_value=0, step=1, key=f"{key_prefix}_num_sem")

        perc_entrada_edit = st.slider("Entrada (%)", 0.0, 100.0, key=f"{key_prefix}_ent_perc")
        perc_mensal_edit = st.slider("Total Parcelas Mensais (%)", 0.0, 100.0, key=f"{key_prefix}_mens_perc")
        perc_semestral_edit = st.slider("Total Parcelas Semestrais (%)", 0.0, 100.0, key=f"{key_prefix}_sem_perc")
        perc_entrega_edit = st.slider("Entrega (%)", 0.0, 100.0, key=f"{key_prefix}_entg_perc")
        
        total_percent_edit = perc_entrada_edit + perc_mensal_edit + perc_semestral_edit + perc_entrega_edit
        st.slider("Total (%)", 0.0, 200.0, total_percent_edit, disabled=True, key=f"{key_prefix}_total")
        
        if total_percent_edit != 100.0:
            st.warning(f"Atenção: A soma dos percentuais é {total_percent_edit:.2f}%. Deve ser 100%.")

        if st.button("Salvar Alterações", key=f"{key_prefix}_save_btn", type="primary"):
            if total_percent_edit != 100.0:
                st.error("A soma dos percentuais deve ser 100% para salvar.")
            else:
                try:
                    valor_entrada = preco_total_edit * (perc_entrada_edit / 100)
                    total_mensal = preco_total_edit * (perc_mensal_edit / 100)
                    valor_mensal = total_mensal / num_mensal_edit if num_mensal_edit > 0 else 0
                    total_semestral = preco_total_edit * (perc_semestral_edit / 100)
                    valor_semestral = total_semestral / num_semestral_edit if num_semestral_edit > 0 else 0
                    valor_entrega = preco_total_edit * (perc_entrega_edit / 100)

                    updated_row_data = [
                        row_data['Obra'],
                        row_data['Unidade'],
                        preco_total_edit,
                        perc_entrada_edit,
                        valor_entrada,
                        perc_mensal_edit,
                        num_mensal_edit,
                        valor_mensal,
                        perc_semestral_edit,
                        num_semestral_edit,
                        valor_semestral,
                        perc_entrega_edit,
                        valor_entrega,
                        row_data['Data/Hora']
                    ]
                    
                    sheet.update(f'A{row_index}:N{row_index}', [updated_row_data], value_input_option='USER_ENTERED')
                    st.success("Simulação atualizada com sucesso!")
                    st.cache_data.clear()
                    
                    keys_to_clear = [k for k in st.session_state if k.startswith(key_prefix)]
                    for k in keys_to_clear:
                        del st.session_state[k]
                    
                    st.rerun()
                
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
def main():
    
    set_default_values()

    if "summary_text" not in st.session_state:
        st.session_state.summary_text = ""
    if "data_to_save" not in st.session_state:
        st.session_state.data_to_save = None

    try:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image("LavieC.png", width=400)
    except Exception:
        st.error("Erro ao carregar logo. Verifique se 'LavieC.png' está na pasta.")

    st.title("Simulador de Negociação")

    lista_obras = [
        "Burj Lavie",
        "Lavie Areia Dourada",
        "The Well By OM25 e Lavie",
        "Lavie Camboinha",
        "Arc Space"
    ]
    obra_selecionada = st.selectbox("Obra", lista_obras, key="obra", label_visibility="collapsed")

    tab1, tab2 = st.tabs(["Simular Negociação", "Simulações Salvas"])

    with tab1:
        st.markdown(f"### Nova Simulação: <span style='color:{st.theme.primaryColor};'>{obra_selecionada}</span>", unsafe_allow_html=True)
        
        col_form_1, col_form_2 = st.columns(2)
        
        with col_form_1:
            st.markdown("##### Dados da Simulação")
            unidade = st.text_input("Unidade / Sala", key="main_unidade")
            preco_total = st.number_input(
                "Preço Total da Unidade (R$)", 
                min_value=0.0, 
                key="main_preco_total",
                format="%.2f",
                step=10000.0
            )

            st.markdown("##### Nº de Parcelas")
            num_mensal = st.number_input("Nº de Parcelas Mensais", min_value=0, step=1, key="main_num_mensal")
            num_semestral = st.number_input("Nº de Parcelas Semestrais", min_value=0, step=1, key="main_num_semestral")

        with col_form_2:
            st.markdown("##### Definição do Fluxo de Pagamento (%)")
            
            perc_entrada = st.slider("Entrada (%)", 0.0, 100.0, key="perc_entrada", step=0.5)
            perc_mensal = st.slider("Total Parcelas Mensais (%)", 0.0, 100.0, key="perc_mensal", step=0.5)
            perc_semestral = st.slider("Total Parcelas Semestrais (%)", 0.0, 100.0, key="perc_semestral", step=0.5)
            perc_entrega = st.slider("Entrega (%)", 0.0, 100.0, key="perc_entrega", step=0.5)
            
            total_percent = perc_entrada + perc_mensal + perc_semestral + perc_entrega
            st.slider("Total (%)", 0.0, 200.0, total_percent, disabled=True, key="total_percent")

            if total_percent != 100.0:
                st.warning(f"Atenção: A soma dos percentuais é {total_percent:.2f}%. Deve ser 100%.")

        st.divider()

        if st.button("Gerar Resumo", type="primary", use_container_width=True):
            st.session_state.summary_text = ""
            st.session_state.data_to_save = None
            
            if not unidade:
                st.error("Por favor, preencha o nome da Unidade / Sala.")
            elif preco_total <= 0:
                st.error("Por favor, preencha um Preço Total válido.")
            elif total_percent != 100.0:
                st.error(f"A soma dos percentuais deve ser 100% (atualmente: {total_percent:.2f}%).")
            else:
                valor_entrada = preco_total * (perc_entrada / 100)
                total_mensal = preco_total * (perc_mensal / 100)
                valor_mensal = total_mensal / num_mensal if num_mensal > 0 else 0
                total_semestral = preco_total * (perc_semestral / 100)
                valor_semestral = total_semestral / num_semestral if num_semestral > 0 else 0
                valor_entrega = preco_total * (perc_entrega / 100)

                data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                st.session_state.data_to_save = [
                    obra_selecionada,
                    unidade,
                    preco_total,
                    perc_entrada,
                    valor_entrada,
                    perc_mensal,
                    num_mensal,
                    valor_mensal,
                    perc_semestral,
                    num_semestral,
                    valor_semestral,
                    perc_entrega,
                    valor_entrega,
                    data_hora
                ]
                
                resumo = f"""
                Resumo da Simulação
                ---------------------------
                Obra: {obra_selecionada}
                Unidade: {unidade}
                Preço Total: {format_currency(preco_total)}
                Data/Hora: {data_hora}
                
                Fluxo de Pagamento:
                - Entrada ({perc_entrada:.2f}%): {format_currency(valor_entrada)}
                - Mensais ({perc_mensal:.2f}%): {format_currency(total_mensal)}
                  ({num_mensal}x de {format_currency(valor_mensal)})
                - Semestrais ({perc_semestral:.2f}%): {format_currency(total_semestral)}
                  ({num_semestral}x de {format_currency(valor_semestral)})
                - Entrega ({perc_entrega:.2f}%): {format_currency(valor_entrega)}
                """
                st.session_state.summary_text = resumo

        if st.session_state.summary_text:
            st.text_area("Resumo Gerado", st.session_state.summary_text, height=300)
            
            if st.button("Salvar na Planilha", use_container_width=True):
                sheet = get_worksheet()
                if sheet and st.session_state.data_to_save:
                    nova_linha = st.session_state.data_to_save
                    
                    try:
                        sheet.append_row(nova_linha, value_input_option='USER_ENTERED')
                        st.success("Simulação salva com sucesso na planilha!")
                        st.balloons()
                        
                        reset_to_default_values()
                        
                        st.cache_data.clear() 
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Erro ao salvar na planilha: {e}")
                else:
                    st.error("Não foi possível conectar à planilha ou não há dados para salvar.")


    with tab2:
        st.markdown(f"### Simulações Salvas", unsafe_allow_html=True)

        df = carregar_dados_planilha()

        if df.empty:
            sheet_check = get_worksheet()
            if sheet_check is None:
                st.error("Falha ao carregar dados: conexão com planilha indisponível.")
            else:
                st.info("Nenhuma simulação salva ainda.")
        else:
            df = df.sort_index(ascending=False)
            df['row_index'] = [i + 2 for i in df.index] 

            for index, row in df.iterrows():
                try:
                    row_index = row['row_index']
                    
                    preco_total_val = float(row.get('Preco Total', 0))
                    entrada_val = float(row.get('Valor Entrada', 0))
                    
                    with st.container(border=True):
                        st.markdown(f"**{row.get('Obra', 'N/A')} - Unidade {row.get('Unidade', 'N/A')}**")
                        st.caption(f"Salvo em: {row.get('Data/Hora', 'N/A')}")
                        
                        card_c1, card_c2 = st.columns(2)
                        with card_c1:
                            st.metric("Preço Total", format_currency(preco_total_val))
                        with card_c2:
                            st.metric("Entrada", format_currency(entrada_val))

                        with st.expander("Ver Resumo, Gráfico ou Excluir"):
                            
                            tab_resumo, tab_editar = st.tabs(["Resumo e Gráfico", "Editar / Excluir"])

                            with tab_resumo:
                                try:
                                    val_mensal = float(row.get('Valor Mensal', 0))
                                    num_mensal = int(row.get('Nº Mensal', 0))
                                    total_mensal = val_mensal * num_mensal
                                    
                                    val_semestral = float(row.get('Valor Semestral', 0))
                                    num_semestral = int(row.get('Nº Semestral', 0))
                                    total_semestral = val_semestral * num_semestral
                                    
                                    val_entrega = float(row.get('Valor Entrega', 0))
                                    
                                    res_c1, res_c2 = st.columns(2)
                                    with res_c1:
                                        st.metric(
                                            label="Parcelas Mensais",
                                            value=format_currency(val_mensal),
                                            delta=f"{num_mensal}x"
                                        )
                                        st.metric(
                                            label="Parcelas Semestrais",
                                            value=format_currency(val_semestral),
                                            delta=f"{num_semestral}x"
                                        )
                                    with res_c2:
                                        st.metric("Total (Mensais)", format_currency(total_mensal))
                                        st.metric("Total (Semestrais)", format_currency(total_semestral))
                                    
                                    st.metric("Valor da Entrega", format_currency(val_entrega))
                                    
                                    chart_data = pd.DataFrame({
                                        'Tipo': ['Entrada', 'Mensais', 'Semestrais', 'Entrega'],
                                        'Valor': [entrada_val, total_mensal, total_semestral, val_entrega]
                                    })
                                    chart_data = chart_data[chart_data['Valor'] > 0]
                                    
                                    pie_chart = alt.Chart(chart_data).mark_arc(outerRadius=120).encode(
                                        theta=alt.Theta("Valor:Q", stack=True),
                                        color=alt.Color("Tipo:N", 
                                            scale=alt.Scale(
                                                domain=chart_data['Tipo'].tolist(),
                                                range=['#E37026', '#FFA500', '#FFC04D', '#FFDAB9']
                                            )
                                        ),
                                        tooltip=['Tipo', 'Valor']
                                    ).properties(
                                        title="Composição do Valor"
                                    )
                                    st.altair_chart(pie_chart, use_container_width=True)

                                except (ValueError, TypeError) as e:
                                    st.error(f"Erro ao processar valores para o resumo: {e}")

                            with tab_editar:
                                st.markdown("##### Ações")
                                
                                if st.button("Editar Simulação", key=f"edit_{row_index}"):
                                    edit_dialog(row.to_dict(), row_index, get_worksheet())
                                
                                if st.button("Excluir Simulação", type="primary", key=f"del_{row_index}"):
                                    sheet = get_worksheet()
                                    if sheet:
                                        sheet.delete_rows(row_index)
                                        st.success(f"Simulação da unidade {row.get('Unidade')} excluída.")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error("Não foi possível conectar à planilha para excluir.")

                except Exception as e:
                    st.error(f"Erro ao renderizar card da simulação: {e}")
                    st.write(row)

if __name__ == "__main__":
    main()
