import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Configuração da página
st.set_page_config(page_title="Carteirinha Digital de Treinamento", page_icon="🎓")

# Ocultar menu e rodapé
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Logo
logo_path = "image.png"  # logo que será usada como "foto"
layout_path = "apresentacao-interna (3).jpg"  # layout da carteirinha

# Título
st.title("Carteirinha Digital de Treinamento")

st.markdown("""
Preencha **RE** e **Data de Admissão** para gerar sua carteirinha.  
Formato da data: **DD/MM/AAAA**
""")

# Caminho do arquivo Excel
LOCAL_PATH = "Treinamentos Normativos.xlsx"

# Carregar planilha
try:
    df = pd.read_excel(LOCAL_PATH, sheet_name="BASE", engine="openpyxl")
except Exception as e:
    st.error(f"Erro ao carregar o arquivo: {e}")
    st.stop()

# Mapeamento automático de colunas
def find_col(possible):
    for c in possible:
        if c in df.columns:
            return c
    return None

col_cod = find_col(["COD_FUNCIONARIO", "RE", "Cod", "cod_funcionario", "cod"])
col_adm = find_col(["DATA_ADMISSAO", "Admissao", "admissao", "DataAdmissao", "DATA_ADM"])
col_nome = find_col(["NOME", "Nome", "nome"])
col_cargo = find_col(["CARGO", "Cargo", "cargo"])
col_depto = find_col(["DEPARTAMENTO", "Departamento", "departamento"])
col_unidade = find_col(["FILIAL_NOME", "Unidade", "unidade", "FILIAL"])
col_trein = find_col(["TREINAMENTO_STATUS_GERAL"])
col_trilha = find_col(["TRILHA DE TREINAMENTO", "Trilha", "TRILHA"])

# Entrada do usuário
re_input = st.text_input("Digite seu RE:")
admissao_input = st.text_input("Data de admissão (DD/MM/AAAA):")

if st.button("Consultar"):
    if not re_input or not admissao_input:
        st.error("Preencha todos os campos.")
        st.stop()

    try:
        adm_date = datetime.strptime(admissao_input, "%d/%m/%Y").date()
        df[col_adm] = pd.to_datetime(df[col_adm]).dt.date
    except:
        st.error("Data inválida.")
        st.stop()

    filtro = df[(df[col_cod].astype(str) == str(re_input)) & (df[col_adm] == adm_date)]

    trilhas_desejadas = [
        "TRILHA COMPLIANCE",
        "TRILHA DA MANUTENÇÃO",
        "TRILHA SEGURANÇA DO TRABALHO",
        "TRILHA SGI",
        "TRILHA TI"
    ]

    if col_trilha in filtro.columns:
        filtro = filtro[filtro[col_trilha].isin(trilhas_desejadas)]

    if filtro.empty:
        st.warning("Nenhum registro encontrado.")
        st.stop()

    # Dados do colaborador
    nome = filtro.iloc[0][col_nome]
    cargo = filtro.iloc[0][col_cargo] if col_cargo in filtro.columns else ""
    depto = filtro.iloc[0][col_depto] if col_depto in filtro.columns else ""
    unidade = filtro.iloc[0][col_unidade] if col_unidade in filtro.columns else ""
    treinamentos = filtro[col_trein].dropna().astype(str).tolist()

    # Gerar carteirinha
    try:
        background = Image.open(layout_path).convert("RGB")
        draw = ImageDraw.Draw(background)

        # Inserir logo como foto
        logo = Image.open(logo_path).resize((150, 150))
        background.paste(logo, (50, 50))

        # Fontes
        try:
            font_text = ImageFont.truetype("arial.ttf", 24)
        except:
            font_text = ImageFont.load_default()

        # Dados abaixo da foto
        text_x = 50
        text_y_start = 220
        line_height = 35

        draw.text((text_x, text_y_start), f"NOME: {nome}", font=font_text, fill="black")
        draw.text((text_x, text_y_start+line_height), f"RE: {re_input}", font=font_text, fill="black")
        draw.text((text_x, text_y_start+2*line_height), f"CARGO: {cargo}", font=font_text, fill="black")
        draw.text((text_x, text_y_start+3*line_height), f"DEPARTAMENTO: {depto}", font=font_text, fill="black")
        draw.text((text_x, text_y_start+4*line_height), f"UNIDADE: {unidade}", font=font_text, fill="black")

        # Treinamentos na metade direita
        train_x = 450
        train_y_start = 100
        draw.text((train_x, train_y_start), "TREINAMENTOS:", font=font_text, fill="black")
        for i, treinamento in enumerate(treinamentos):
            draw.text((train_x + 20, train_y_start + 40 + i * 30), f"- {treinamento}", font=font_text, fill="black")

        # Salvar imagem
        output_path = "carteirinha_final.png"
        background.save(output_path)

        # Exibir e permitir download
        st.image(output_path, caption="Carteirinha Digital", use_column_width=True)
        with open(output_path, "rb") as file:
            st.download_button("📥 Baixar Carteirinha", data=file, file_name="carteirinha_final.png", mime="image/png")

    except Exception as e:
        st.error(f"Erro ao gerar carteirinha: {e}")
