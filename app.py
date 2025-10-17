import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import pytz

st.set_page_config(page_title="Carteirinha Digital de Treinamento", page_icon="🎓")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

logo_path = "logo.webp"
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

def gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos_ordenados):
    background = Image.open(layout_path).convert("RGB")
    draw = ImageDraw.Draw(background)

    logo = Image.open(logo_path).resize((250, 150))
    background.paste(logo, (50, 50))

    try:
        font_colab = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
        font_trein = ImageFont.truetype("DejaVuSans.ttf", 15)
        rodape_font = ImageFont.truetype("DejaVuSans.ttf", 12)
    except:
        font_colab = ImageFont.load_default()
        font_trein = ImageFont.load_default()
        rodape_font = ImageFont.load_default()

    text_x = 50
    text_y_start = 220
    line_height = 45
    max_chars_info = 30

    info_pessoal = [
        f"NOME: {nome}",
        f"RE: {re_input}",
        f"CARGO: {cargo}",
        f"DEPARTAMENTO: {depto}",
        f"UNIDADE: {unidade}"
    ]

    current_y = text_y_start
    for info in info_pessoal:
        linhas = textwrap.wrap(info, width=max_chars_info)
        for linha in linhas:
            draw.text((text_x, current_y), linha, font=font_colab, fill="black")
            current_y += line_height

    train_x = 500
    train_y_start = 60
    max_chars = 80
    current_y = train_y_start

    for treinamento in treinamentos_ordenados:
        linhas = textwrap.wrap(treinamento, width=max_chars)
        for linha in linhas:
            draw.text((train_x + 15, current_y), linha, font=font_trein, fill="black")
            current_y += 20
        current_y += 15

    # Horário local de Dourados/MS
    tz = pytz.timezone("America/Campo_Grande")
    hora_local = datetime.now(tz).strftime("%d/%m/%Y %H:%M")

    rodape_texto = f"Consulta em: {hora_local}"
    rodape_x = background.width - 300
    rodape_y = background.height - 30
    draw.text((rodape_x, rodape_y), rodape_texto, font=rodape_font, fill="gray")

    output_image_path = "carteirinha_final.png"
    background.save(output_image_path)

    # Redimensionar imagem para 5,4 cm x 8,5 cm com alta resolução
    width_pt = 5.4 * cm
    height_pt = 8.5 * cm
    resized_image = background.resize((int(width_pt), int(height_pt)), resample=Image.LANCZOS)
    resized_image_path = "resized_image_highres.png"
    resized_image.save(resized_image_path, dpi=(300, 300))

    # Gerar PDF com imagem em alta resolução
    output_pdf_path = "carteirinha_final.pdf"
    c = canvas.Canvas(output_pdf_path, pagesize=(width_pt, height_pt))
    c.drawImage(resized_image_path, 0, 0, width=width_pt, height=height_pt)
    c.setFont("Helvetica", 6)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(width_pt - 100, 10, f"Consulta em: {hora_local}")
    c.showPage()
    c.save()

    return output_image_path, output_pdf_path

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
col_trilha = find_col(["TRILHA DE TREINAMENTO ", "Trilha", "TRILHA", "trilha"])

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

    if not col_trilha:
        st.error("Coluna de trilha não encontrada na planilha.")
        st.stop()

    trilhas_desejadas = [
        "TRILHA COMPLIANCE ",
        "TRILHA SEGURANÇA DO TRABALHO",
        "TRILHA SGI",
        "TRILHA TI"
    ]

    filtro = df[
        (df[col_cod].astype(str) == str(re_input)) &
        (df[col_adm] == adm_date) &
        (df[col_trilha].isin(trilhas_desejadas))
    ].copy()

    if filtro.empty:
        st.warning("Nenhum registro encontrado.")
        st.stop()

    nome = filtro.iloc[0][col_nome]
    cargo = filtro.iloc[0][col_cargo] if col_cargo in filtro.columns else ""
    depto = filtro.iloc[0][col_depto] if col_depto in filtro.columns else ""
    unidade = filtro.iloc[0][col_unidade] if col_unidade in filtro.columns else ""

    treinamentos_ordenados = sorted(filtro[col_trein].dropna().astype(str).unique())

    imagem_path, pdf_path = gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos_ordenados)

    st.image(imagem_path, caption="Carteirinha Digital", use_container_width=True)

    with open(imagem_path, "rb") as img_file:
        st.download_button("📥 Baixar como PNG", data=img_file, file_name="carteirinha_final.png", mime="image/png")

    with open(pdf_path, "rb") as pdf_file:
        st.download_button("📄 Baixar como PDF (Alta Resolução)", data=pdf_file, file_name="carteirinha_final.pdf", mime="application/pdf")
