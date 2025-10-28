import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import pytz
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import os
import textwrap

# Configuração da página
st.set_page_config(page_title="Carteirinha Digital de Treinamento", page_icon="🎓")

# Arquivos necessários
image_file = "image.png"
logo_file = "logo.png"
planilha_file = "Treinamentos Normativos.xlsx"

# Verificação de arquivos
if not os.path.exists(image_file):
    st.error(f"Arquivo de fundo '{image_file}' não encontrado.")
    st.stop()

# Função para carregar planilha
@st.cache_data
def carregar_planilha():
    try:
        df = pd.read_excel(planilha_file, sheet_name="BASE", engine="openpyxl")
        df.columns = df.columns.str.strip()  # Remove espaços extras
        return df
    except Exception as e:
        st.error(f"Erro ao carregar a planilha: {e}")
        return None

# Função para buscar treinamentos
def buscar_treinamentos(df, re_consulta):
    col_cod = "COD_FUNCIONARIO"
    col_nome = "NOME"
    col_cargo = "CARGO"
    col_depto = "DEPARTAMENTO"
    col_unidade = "FILIAL_NOME"
    col_trilha = "TRILHA DE TREINAMENTO"
    col_trein = "TREINAMENTO_STATUS_GERAL"

    # Normalização
    df[col_cod] = df[col_cod].astype(str).str.strip()
    df[col_trilha] = df[col_trilha].astype(str).str.upper().str.strip()
    df[col_trein] = df[col_trein].astype(str).str.strip()

    re_consulta = str(re_consulta).strip()
    filtro = df[(df[col_cod] == re_consulta) &
                (df[col_trilha].str.contains("TRILHA SEGURANCA DO TRABALHO"))]

    if filtro.empty:
        return None, []

    nome = filtro.iloc[0][col_nome]
    cargo = filtro.iloc[0][col_cargo]
    depto = filtro.iloc[0][col_depto]
    unidade = filtro.iloc[0][col_unidade]
    treinamentos = sorted(filtro[col_trein].dropna().unique())

    return (nome, cargo, depto, unidade), treinamentos
# Função para gerar carteirinha
def gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos):
    img = Image.open(image_file).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Fonte com fallback
    try:
        font = ImageFont.truetype("Montserrat.ttf", 20)
    except:
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()

    # Dados pessoais
    info = [f"NOME: {nome}", f"RE: {re_input}", f"CARGO: {cargo}",
            f"DEPARTAMENTO: {depto}", f"UNIDADE: {unidade}"]
    x, y = 50, 50
    for linha in info:
        draw.text((x, y), linha, font=font, fill="black")
        y += 30

    # Treinamentos
    y += 20
    for t in treinamentos:
        for linha in textwrap.wrap(t, width=40):
            draw.text((x, y), f"- {linha}", font=font, fill="black")
            y += 25

    # Timestamp
    hora_local = datetime.now(pytz.timezone("America/Campo_Grande")).strftime("%d/%m/%Y %H:%M")
    draw.text((x, y + 20), f"Gerado em: {hora_local}", font=font, fill="gray")

    # Salvar imagem e PDF
    img_path = "carteirinha_final.png"
    img.save(img_path)

    pdf_path = "carteirinha_final.pdf"
    c = canvas.Canvas(pdf_path, pagesize=(25.4 * cm, 15 * cm))
    c.drawImage(img_path, 0, 0, width=25.4 * cm, height=15 * cm)
    c.showPage()
    c.save()

    return img_path, pdf_path

# Interface Streamlit
st.title("Carteirinha Digital de Treinamento")
df = carregar_planilha()
if df is not None:
    re_input = st.text_input("Digite seu RE")
    if st.button("Gerar Carteirinha"):
        dados, treinamentos = buscar_treinamentos(df, re_input)
        if not dados:
            st.warning(f"Nenhum treinamento encontrado para RE {re_input}.")
        else:
            st.write("Treinamentos encontrados:", len(treinamentos))
            for t in treinamentos:
                st.write("-", t)
            img_path, pdf_path = gerar_carteirinha(dados[0], re_input, dados[1], dados[2], dados[3], treinamentos)
            st.image(img_path, caption="Carteirinha Digital", use_container_width=True)
            with open(img_path, "rb") as img_file:
                st.download_button("📥 Baixar como PNG", img_file, "carteirinha_final.png", "image/png")
            with open(pdf_path, "rb") as pdf_file:
                st.download_button("📄 Baixar como PDF", pdf_file, "carteirinha_final.pdf", "application/pdf")
