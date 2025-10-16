import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap

st.set_page_config(page_title="Carteirinha Digital de Treinamento", page_icon="🎓")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

logo_path = "image.png"
layout_path = "image.png"
excel_path = "Treinamentos Normativos.xlsx"

st.title("Carteirinha Digital de Treinamento")

st.markdown("""
Preencha **RE** e **Data de Admissão** para gerar sua carteirinha.  
Formato da data: **DD/MM/AAAA**
""")

@st.cache_data
def carregar_planilha():
    return pd.read_excel(excel_path, sheet_name="BASE", engine="openpyxl")

@st.cache_data
def gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos):
    background = Image.open(layout_path).convert("RGB")
    draw = ImageDraw.Draw(background)

    logo = Image.open(logo_path).resize((150, 150))
    background.paste(logo, (50, 50))

    try:
        font_colab = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
        font_trein = ImageFont.truetype("DejaVuSans.ttf", 15)
    except:
        font_colab = ImageFont.load_default()
        font_trein = ImageFont.load_default()

    text_x = 50
    text_y_start = 220
    line_height = 45

    draw.text((text_x, text_y_start), f"NOME: {nome}", font=font_colab, fill="black")
    draw.text((text_x, text_y_start+line_height), f"RE: {re_input}", font=font_colab, fill="black")
    draw.text((text_x, text_y_start+2*line_height), f"CARGO: {cargo}", font=font_colab, fill="black")
    draw.text((text_x, text_y_start+3*line_height), f"DEPARTAMENTO: {depto}", font=font_colab, fill="black")
    draw.text((text_x, text_y_start+4*line_height), f"UNIDADE: {unidade}", font=font_colab, fill="black")

    train_x = background.width // 2 + 30
    train_y_start = 60
    max_chars = 65
texto_titulo = "TREINAMENTOS:"
text_width = draw.textlength(texto_titulo, font=font_trein_bold)
center_x = (background.width - text_width) // 2
draw.text((center_x, train_y_start), texto_titulo, font=font_trein_bold, fill="black")
    draw.text((train_x, train_y_start), "TREINAMENTOS:", font_trein_bold = ImageFont.truetype("Montserrat-Bold.ttf", 20)
    current_y = train_y_start + 40
    for treinamento in treinamentos:
        linhas = textwrap.wrap(treinamento, width=max_chars)
        for linha in linhas:
            draw.text((train_x + 20, current_y), linha, font=font_trein, fill="black")
            current_y += 25

    output_path = "carteirinha_final.png"
    background.save(output_path)
    return output_path

df = carregar_planilha()

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

    nome = filtro.iloc[0][col_nome]
    cargo = filtro.iloc[0][col_cargo] if col_cargo in filtro.columns else ""
    depto = filtro.iloc[0][col_depto] if col_depto in filtro.columns else ""
    unidade = filtro.iloc[0][col_unidade] if col_unidade in filtro.columns else ""
    treinamentos = filtro[col_trein].dropna().astype(str).tolist()

    imagem_path = gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos)

    st.image(imagem_path, caption="Carteirinha Digital", use_container_width=True)
    with open(imagem_path, "rb") as file:
        st.download_button("📥 Baixar Carteirinha", data=file, file_name="carteirinha_final.png", mime="image/png")






















