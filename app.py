import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image

# Configuração da página
st.set_page_config(page_title="Carteirinha Digital de Treinamento", page_icon="🎓")

# Ocultar menu e rodapé do Streamlit
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# Exibir logo
logo = Image.open("logo.webp")  # Certifique-se de que o nome do arquivo está correto
st.image(logo, width=200)

st.title("Carteirinha Digital de Treinamento")

st.markdown("""
Preencha **RE** e **Data de Admissão** para ver a carteirinha.  
Formato da data: **DD/MM/AAAA** (ex: 15/03/2022)
""")

# Caminho do arquivo Excel
LOCAL_PATH = "Treinamentos Normativos.xlsx"

# Carregar a planilha
try:
    df = pd.read_excel(LOCAL_PATH, sheet_name="BASE", engine="openpyxl")
except FileNotFoundError:
    st.error("Arquivo padrão não encontrado. Certifique-se de que 'Treinamentos Normativos.xlsx' está no repositório.")
    st.stop()
except Exception as e:
    st.error(f"Erro ao carregar o arquivo Excel: {e}")
    st.stop()

# Mapeamento automático de colunas
def find_col(possible):
    for c in possible:
        if c in df.columns:
            return c
    return None

possible_cod = ["COD_FUNCIONARIO", "RE", "Cod", "cod_funcionario", "cod"]
possible_adm = ["DATA_ADMISSAO", "Admissao", "admissao", "DataAdmissao", "DATA_ADM"]
possible_nome = ["NOME", "Nome", "nome"]
possible_cargo = ["CARGO", "Cargo", "cargo"]
possible_trein = ["TREINAMENTO_STATUS_GERAL"]
possible_depto = ["DEPARTAMENTO", "Departamento", "departamento"]
possible_unidade = ["FILIAL_NOME", "Unidade", "unidade", "FILIAL"]
possible_trilha = ["TRILHA DE TREINAMENTO", "Trilha", "TRILHA"]

col_cod = find_col(possible_cod)
col_adm = find_col(possible_adm)
col_nome = find_col(possible_nome)
col_cargo = find_col(possible_cargo)
col_trein = find_col(possible_trein)
col_depto = find_col(possible_depto)
col_unidade = find_col(possible_unidade)
col_trilha = find_col(possible_trilha)

if not col_cod or not col_adm or not col_nome:
    st.error(
        "Não encontrei colunas essenciais automaticamente. "
        "Verifique os nomes das colunas na planilha. "
        "Colunas procuradas: RE/COD_FUNCIONARIO, DATA_ADMISSAO, NOME."
    )
    st.stop()

# Entrada do usuário
re_input = st.text_input("Digite seu RE (apenas números):")
admissao_input = st.text_input("Informe a data de admissão (DD/MM/AAAA):")

if st.button("Consultar"):
    if not re_input or not admissao_input:
        st.error("Preencha RE e data de admissão.")
    else:
        try:
            adm_date = datetime.strptime(admissao_input, "%d/%m/%Y").date()
        except:
            st.error("Formato de data inválido. Use DD/MM/AAAA.")
            st.stop()

        try:
            df[col_adm] = pd.to_datetime(df[col_adm]).dt.date
        except Exception as e:
            st.error(f"Erro ao converter a coluna de admissão: {e}")
            st.stop()

        filtro = df[(df[col_cod].astype(str) == str(re_input)) & (df[col_adm] == adm_date)]

        # Filtrar pelas trilhas desejadas
        trilhas_desejadas = [
            "TRILHA COMPLIANCE",
            "TRILHA DA MANUTENÇÃO",
            "TRILHA SEGURANÇA DO TRABALHO",
            "TRILHA SGI",
            "TRILHA TI"
        ]

        if col_trilha and col_trilha in filtro.columns:
            filtro = filtro[filtro[col_trilha].isin(trilhas_desejadas)]
        else:
            st.warning("Coluna 'TRILHA DE TREINAMENTO' não encontrada na planilha.")

        if filtro.empty:
            st.warning(f"Nenhum registro encontrado para RE {re_input} e admissão {admissao_input} nas trilhas selecionadas.")
        else:
            nome = filtro.iloc[0][col_nome]
            cargo = filtro.iloc[0][col_cargo] if col_cargo in filtro.columns else ""
            depto = filtro.iloc[0][col_depto] if col_depto in filtro.columns else ""
            unidade = filtro.iloc[0][col_unidade] if col_unidade in filtro.columns else ""
            st.success(f"{nome} — {cargo} — {depto} — {unidade}")
            st.write(f"RE: **{re_input}** | Admissão: **{adm_date.strftime('%d/%m/%Y')}**")

            st.subheader("Treinamentos:")
            st.dataframe(filtro)
