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
    /* Opção: Papel Artesanal (Sutil e Elegante) */
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

def to_sheet_string(value):
    """Converte um float (ex: 5555.56) para uma string PT-BR (ex: "5555,56")"""
    return f"{value:.2f}".replace('.', ',')
    
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
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
                    errors='coerce'
                ).fillna(0)


        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados da planilha: {e}")
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

    st.markdown(f"### <span style='color: {st.get_option('theme.primaryColor')};'>Nova Simulação: {obra_selecionada}</span>", unsafe_allow_html=True)

    form_cols = st.columns(2)

    with form_cols[0]:
        st.markdown("##### Dados da Simulação")
        unidade = st.text_input("Unidade / Sala", key="main_unidade")
        preco_total = st.number_input("Preço Total da Unidade (R$)", min_value=0.0, step=1000.0, key="main_preco_total", format="%.2f")

        st.markdown("##### Nº de Parcelas")
        num_mensal = st.number_input("Nº de Parcelas Mensais", min_value=0, step=1, key="main_num_mensal")
        num_semestral = st.number_input("Nº de Parcelas Semestrais", min_value=0, step=1, key="main_num_semestral")

    with form_cols[1]:
        st.markdown("##### Definição do Fluxo de Pagamento (%)")

        if "total_percent" not in st.session_state:
            st.session_state.total_percent = 0.0

        def atualizar_percentual():
            st.session_state.total_percent = (
                st.session_state.get('perc_entrada', 0.0) +
                st.session_state.get('perc_mensal', 0.0) +
                st.session_state.get('perc_semestral', 0.0) +
                st.session_state.get('perc_entrega', 0.0)
            )

        perc_entrada = st.number_input("Entrada (%)", min_value=0.0, max_value=100.0, step=1.0, format="%.2f", key="perc_entrada", on_change=atualizar_percentual)
        perc_entrega = st.number_input("Entrega (%)", min_value=0.0, max_value=100.0, step=1.0, format="%.2f", key="perc_entrega", on_change=atualizar_percentual)
        st.markdown("##### % de Parcelas")
        perc_mensal = st.number_input("Total Parcelas Mensais (%)", min_value=0.0, max_value=100.0, step=1.0, format="%.2f", key="perc_mensal", on_change=atualizar_percentual)
        perc_semestral = st.number_input("Total Parcelas Semestrais (%)", min_value=0.0, max_value=100.0, step=1.0, format="%.2f", key="perc_semestral", on_change=atualizar_percentual)


        total_percent = st.session_state.total_percent

        if total_percent > 100.0:
            st.error(f"Percentual total excede 100%! (Total: {total_percent:.1f}%)")
        elif total_percent < 100.0:
            st.warning(f"Percentual não fecha 100%. (Total: {total_percent:.1f}%)")
        else:
            st.success(f"Percentual fechado em 100%!")

    st.markdown("---")

    val_entrada = (preco_total * perc_entrada) / 100
    val_total_mensal = (preco_total * perc_mensal) / 100
    val_total_semestral = (preco_total * perc_semestral) / 100
    val_entrega = (preco_total * perc_entrega) / 100

    val_por_mensal = (val_total_mensal / num_mensal) if num_mensal > 0 else 0
    val_por_semestral = (val_total_semestral / num_semestral) if num_semestral > 0 else 0

    st.markdown(f"### <span style='color: {st.get_option('theme.primaryColor')};'>Valores Calculados</span>", unsafe_allow_html=True)

    calc_cols_1 = st.columns(2)
    calc_cols_1[0].metric("Valor Entrada", format_currency(val_entrada))
    calc_cols_1[1].metric("Valor Entrega", format_currency(val_entrega))

    calc_cols_2 = st.columns(2)
    calc_cols_2[0].metric(f"Valor Mensal ", format_currency(val_por_mensal), delta=f"{num_mensal}x")
    calc_cols_2[1].metric(f"Valor Semestral", format_currency(val_por_semestral), delta=f"{num_semestral}x")


    st.markdown("---")

    if st.button("Gerar Resumo", type="primary", use_container_width=True, key="btn_gerar_resumo"):
        if not unidade:
            st.error("Por favor, preencha o nome da Unidade.")
            st.session_state.summary_text = ""
            st.session_state.data_to_save = None
        elif preco_total <= 0:
            st.error("Por favor, preencha o Preço Total.")
            st.session_state.summary_text = ""
            st.session_state.data_to_save = None
        elif round(total_percent, 1) != 100.0:
            st.error(f"O percentual total deve ser 100% para salvar (Atual: {total_percent:.1f}%).")
            st.session_state.summary_text = ""
            st.session_state.data_to_save = None
        else:
            data_hora_atual = datetime.now().strftime("%Y-%m-%d")
            summary = f"""
Resumo da Simulação
----------------------------------
Obra:     {obra_selecionada}
Unidade:  {unidade}
Data:     {data_hora_atual}
----------------------------------
Preço Total:   {format_currency(preco_total)}

Entrada:       {perc_entrada:.1f}%  | {format_currency(val_entrada)}
Mensais:       {perc_mensal:.1f}%  | {num_mensal}x de {format_currency(val_por_mensal)} (Total: {format_currency(val_total_mensal)})
Semestrais:    {perc_semestral:.1f}%  | {num_semestral}x de {format_currency(val_por_semestral)} (Total: {format_currency(val_total_semestral)})
Entrega:       {perc_entrega:.1f}%  | {format_currency(val_entrega)}
----------------------------------
Total:         {total_percent:.1f}% | {format_currency(preco_total)}
"""
            st.session_state.summary_text = summary

            st.session_state.data_to_save = [
                obra_selecionada, unidade, preco_total,
                perc_entrada, val_entrada,
                perc_mensal, num_mensal, val_por_mensal,
                perc_semestral, num_semestral, val_por_semestral,
                perc_entrega, val_entrega,
                data_hora_atual
            ]

    if st.session_state.summary_text:
        st.markdown("##### Resumo Gerado")
        st.text_area("Resumo para Copiar:", value=st.session_state.summary_text, height=300, key="summary_display", disabled=True)

        if st.button("Salvar na Planilha", use_container_width=True, key="btn_salvar_final"):
            with st.spinner("Conectando ao Google Sheets e salvando..."):
                try:
                    sheet = get_worksheet()
                    if sheet and st.session_state.data_to_save:
                        nova_linha = st.session_state.data_to_save
                        nova_linha[-1] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 

                        sheet.append_row(nova_linha, value_input_option='USER_ENTERED')
                        st.success("Simulação salva com sucesso na planilha!")

                        reset_to_default_values() 

                        st.cache_data.clear() 
                        st.cache_resource.clear()
                        time.sleep(1)
                        st.rerun() 
                    elif not st.session_state.data_to_save:
                         st.error("Erro: Dados do resumo perdidos. Tente gerar novamente.")
                    else:
                        st.error("Falha ao salvar: Não foi possível conectar à planilha.")
                except Exception as e:
                    st.error(f"Falha ao salvar na planilha: {e}")


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
                st.error(f"Erro ao processar dados da linha {index} (Unidade: {row.get('Unidade', 'N/A')}). Verifique a planilha. Erro: {e}")
                continue

            with st.container(border=True):
                st.markdown(f"**{row['Obra']}** | Unidade: **{row['Unidade']}**")
                cols_header = st.columns(2)
                cols_header[0].metric("Preço Total", format_currency(preco_total_num))
                cols_header[1].metric("Entrada", format_currency(val_entrada_num))

                with st.expander("Ver Detalhes, Gráfico ou Ações"):

                    tab_resumo, tab_acoes = st.tabs(["Resumo e Gráfico", "Editar / Excluir"])

                    with tab_resumo:
                        detail_cols = st.columns(2)
                        detail_cols[0].metric(
                            label="Valor Mensal", 
                            value=format_currency(val_mensal_num), 
                            delta=f"{num_mensal_num}x"
                        )
                        detail_cols[1].metric("Total em Mensais", format_currency(total_mensal))

                        detail_cols2 = st.columns(2)
                        detail_cols2[0].metric(
                            label="Valor Semestral", 
                            value=format_currency(val_semestral_num), 
                            delta=f"{num_semestral_num}x"
                        )
                        detail_cols2[1].metric("Total em Semestrais", format_currency(total_semestral))

                        st.metric("Entrega", format_currency(val_entrega_num))

                        try:
                            chart_data = pd.DataFrame({
                                'Tipo': ['Entrada', 'Mensais', 'Semestrais', 'Entrega'],
                                'Valor': [val_entrada_num, total_mensal, total_semestral, val_entrega_num]
                            })
                            chart_data = chart_data[chart_data['Valor'] > 0]

                            color_scheme = [st.get_option('theme.primaryColor'), '#FFA500', '#FFC04D', '#808080']

                            if not chart_data.empty:
                                pie_chart = alt.Chart(chart_data).mark_arc(outerRadius=120, innerRadius=80).encode(
                                    theta=alt.Theta("Valor:Q", stack=True),
                                    color=alt.Color("Tipo:N", 
                                                    title="Tipo de Pagamento", 
                                                    scale=alt.Scale(domain=['Entrada', 'Mensais', 'Semestrais', 'Entrega'], 
                                                                    range=color_scheme)),
                                    tooltip=['Tipo', 'Valor', alt.Tooltip("Valor:Q", format=".1%", title="% do Total")]
                                ).properties(
                                    title="Composição do Valor Total"
                                )
                                st.altair_chart(pie_chart, use_container_width=True)
                            else:
                                st.info("Não há dados de valor para exibir o gráfico.")
                        except Exception as e:
                            st.error(f"Não foi possível gerar o gráfico. {e}")

                    with tab_acoes:
                        st.markdown("##### Ações")

                        edit_key = f"edit_{index}_{row['Unidade']}"
                        if st.button("Editar Simulação", key=edit_key):
                            if sheet:
                                try:
                                    cell = sheet.find(row['Data/Hora'])
                                    if cell:
                                        edit_dialog(row.to_dict(), sheet, cell.row)
                                    else:
                                        st.error("Não foi possível encontrar a linha para editar. Tente recarregar.")
                                except Exception as e:
                                    st.error(f"Erro ao tentar editar: {e}")
                            else:
                                st.error("Não foi possível editar: conexão com planilha perdida.")

                        st.markdown("---") 

                        delete_key = f"delete_{index}_{row['Unidade']}"
                        if st.button("Excluir Simulação", key=delete_key, type="primary"):
                            if sheet:
                                try:
                                    cell = sheet.find(row['Data/Hora'])
                                    if cell:
                                        sheet.delete_rows(cell.row)
                                        st.success(f"Simulação da Unidade '{row['Unidade']}' excluída.")
                                        st.cache_data.clear()
                                        st.cache_resource.clear()
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Não foi possível encontrar a linha para excluir. Tente recarregar.")
                                except Exception as e:
                                    st.error(f"Erro ao excluir linha: {e}")
                            else:
                                st.error("Não foi possível excluir: conexão com planilha perdida.")

    else:
        st.info("Nenhuma simulação salva para exibir.")
