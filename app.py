import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import pytz
import hashlib
import pyodbc

# Configuração da página
st.set_page_config(page_title="Carteirinha Digital de Treinamento", page_icon="🎓")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Funções de banco de dados
def conectar_sql():
    return pyodbc.connect(
        "DRIVER={SQL Server};SERVER=SEU_SERVIDOR;DATABASE=SEU_BANCO;UID=SEU_USUARIO;PWD=SUA_SENHA"
    )

def gerar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def verificar_login(re, senha):
    conn = conectar_sql()
    cursor = conn.cursor()
    cursor.execute("SELECT senha_hash FROM usuarios WHERE re = ?", re)
    row = cursor.fetchone()
    conn.close()
    if row:
        return gerar_hash(senha) == row[0]
    return False

def registrar_acesso(re, acao):
    conn = conectar_sql()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO log_acessos (re, data_hora, acao) VALUES (?, ?, ?)",
                   re, datetime.now(), acao)
    conn.commit()
    conn.close()

def atualizar_senha(re, nova_senha):
    conn = conectar_sql()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET senha_hash = ? WHERE re = ?",
                   gerar_hash(nova_senha), re)
    conn.commit()
    conn.close()

# Validação de senha forte
def senha_valida(senha):
    return (
        len(senha) >= 10 and
        any(c.isupper() for c in senha) and
        any(c.islower() for c in senha) and
        any(c.isdigit() for c in senha) and
        any(c in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/" for c in senha)
    )

# Tela de recuperação/criação de senha
def tela_recuperacao():
    st.subheader("🔑 Primeiro acesso / Recuperar senha")
    cpf = st.text_input("CPF")
    codigo = st.text_input("Código verificador")
    nascimento = st.date_input("Data de nascimento")
    nova_senha = st.text_input("Nova senha", type="password")
    confirmar_senha = st.text_input("Confirme a senha", type="password")

    if st.button("Criar/Atualizar senha"):
        if not cpf or not codigo or not nascimento or not nova_senha or not confirmar_senha:
            st.error("Preencha todos os campos.")
            return
        if nova_senha != confirmar_senha:
            st.error("As senhas não coincidem.")
            return
        if not senha_valida(nova_senha):
            st.error("A senha deve conter números, letras maiúsculas e minúsculas, caracteres especiais e no mínimo 10 caracteres.")
            return

        # Carregar planilha de colaboradores
        df_id = pd.read_excel("ID_Colaboradores.xlsx", engine="openpyxl")
        col_re, col_cpf, col_nasc = "COD_FUNCIONARIO", "CPF", "DATA_NASCIMENTO"

        colaborador = df_id[(df_id[col_cpf].astype(str) == str(cpf)) & (pd.to_datetime(df_id[col_nasc]).dt.date == nascimento)]
        if colaborador.empty:
            st.error("Dados não encontrados.")
            return

        re = str(colaborador.iloc[0][col_re])
        ano_nasc = nascimento.year
        codigo_correto = cpf[:3] + str(ano_nasc) + re

        if codigo != codigo_correto:
            st.error("Código verificador inválido.")
            return

        atualizar_senha(re, nova_senha)
        st.success("Senha criada/atualizada com sucesso!")
        registrar_acesso(re, "Senha criada/atualizada")

# Tela de login
def tela_login():
    st.subheader("🔐 Login")
    re = st.text_input("RE")
    senha = st.text_input("Senha", type="password")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Entrar"):
            if verificar_login(re, senha):
                st.session_state["usuario_logado"] = re
                registrar_acesso(re, "Login realizado")
                st.success("Login bem-sucedido!")
            else:
                st.error("RE ou senha inválidos.")
    with col2:
        if st.button("Primeiro acesso / Recuperar senha"):
            st.session_state["recuperar"] = True

if "usuario_logado" not in st.session_state:
    if st.session_state.get("recuperar"):
        tela_recuperacao()
    else:
        tela_login()
    st.stop()

# Após login, segue geração da carteirinha
logo_path = "logo.png"
layout_path = "image.png"
excel_path = "Treinamentos Normativos.xlsx"

st.title("Carteirinha Digital de Treinamento")
st.markdown("Preencha **RE** e **Data de Admissão** para gerar sua carteirinha. Formato: **DD/MM/AAAA**")

@st.cache_data
def carregar_planilha():
    return pd.read_excel(excel_path, sheet_name="BASE", engine="openpyxl")

def gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos_ordenados):
    background = Image.open(layout_path).convert("RGB")
    draw = ImageDraw.Draw(background)
    logo = Image.open(logo_path).resize((250, 150))
    background.paste(logo, (50, 50))

    font_colab = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    font_trein = ImageFont.truetype("DejaVuSans.ttf", 18)
    rodape_font = ImageFont.truetype("DejaVuSans.ttf", 15)

    info_pessoal = [f"NOME: {nome}", f"RE: {re_input}", f"CARGO: {cargo}", f"DEPARTAMENTO: {depto}", f"UNIDADE: {unidade}"]
    text_x, text_y_start, line_height = 50, 220, 45
    for info in info_pessoal:
        for linha in textwrap.wrap(info, width=30):
            draw.text((text_x, text_y_start), linha, font=font_colab, fill="#304F7E")
            text_y_start += line_height

    train_x, train_y_start = 500, 100
    for treinamento in treinamentos_ordenados:
        for linha in textwrap.wrap(treinamento, width=70):
            draw.text((train_x + 10, train_y_start), linha, font=font_trein, fill="black")
            train_y_start += 30
        train_y_start += 10
    hora_local = datetime.now(pytz.timezone("America/Campo_Grande")).strftime("%d/%m/%Y %H:%M")
    draw.text((10, background.height - 30), f"Consulta em: {hora_local}", font=rodape_font, fill="gray")

    output_image_path = "carteirinha_final.png"
    background.save(output_image_path)

    output_pdf_path = "carteirinha_final.pdf"
    c = canvas.Canvas(output_pdf_path, pagesize=(25.4*cm, 15*cm))
    c.drawImage(output_image_path, 0, 0, width=25.4*cm, height=15*cm)
    c.showPage()
    c.save()
    return output_image_path, output_pdf_path

df = carregar_planilha()
col_cod = next((c for c in ["COD_FUNCIONARIO","RE","Cod","cod_funcionario","cod"] if c in df.columns), None)
col_adm = next((c for c in ["DATA_ADMISSAO","Admissao","admissao","DataAdmissao","DATA_ADM"] if c in df.columns), None)
col_nome = next((c for c in ["NOME","Nome","nome"] if c in df.columns), None)
col_cargo = next((c for c in ["CARGO","Cargo","cargo"] if c in df.columns), None)
col_depto = next((c for c in ["DEPARTAMENTO","Departamento","departamento"] if c in df.columns), None)
col_unidade = next((c for c in ["FILIAL_NOME","Unidade","unidade","FILIAL"] if c in df.columns), None)
col_trein = next((c for c in ["TREINAMENTO_STATUS_GERAL"] if c in df.columns), None)
col_trilha = next((c for c in ["TRILHA DE TREINAMENTO ","Trilha","TRILHA","trilha"] if c in df.columns), None)

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
    filtro = df[(df[col_cod].astype(str) == str(re_input)) & (df[col_adm] == adm_date) & (df[col_trilha] == "TRILHA SEGURANÇA DO TRABALHO")]
    if filtro.empty:
        st.warning("Nenhum registro encontrado.")
        st.stop()
    nome = filtro.iloc[0][col_nome]
    cargo = filtro.iloc[0][col_cargo] if col_cargo else ""
    depto = filtro.iloc[0][col_depto] if col_depto else ""
    unidade = filtro.iloc[0][col_unidade] if col_unidade else ""
    treinamentos_ordenados = sorted(filtro[col_trein].dropna().astype(str).unique())
    img_path, pdf_path = gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos_ordenados)
    st.image(img_path, caption="Carteirinha Digital", use_container_width=True)
    with open(img_path, "rb") as img_file:
        st.download_button("📥 Baixar como PNG", img_file, "carteirinha_final.png", "image/png")
    with open(pdf_path, "rb") as pdf_file:
        st.download_button("📄 Baixar como PDF", pdf_file, "carteirinha_final.pdf", "application/pdf")
