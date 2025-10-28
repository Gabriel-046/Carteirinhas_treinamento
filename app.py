import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import pytz
import hashlib
import os

# Configuração da página
st.set_page_config(page_title="Carteirinha Digital de Treinamento", page_icon="🎓")

usuarios_file = "usuarios.xlsx"
treinamentos_file = "Treinamentos Normativos.xlsx"

# Funções auxiliares
def gerar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def senha_valida(senha):
    return (
        len(senha) >= 10 and
        any(c.isupper() for c in senha) and
        any(c.islower() for c in senha) and
        any(c.isdigit() for c in senha) and
        any(c in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/" for c in senha)
    )

def carregar_usuarios():
    return pd.read_excel(usuarios_file)

def salvar_usuarios(df):
    df.to_excel(usuarios_file, index=False)

def verificar_login(re, senha):
    df_users = carregar_usuarios()
    user = df_users[df_users["RE"].astype(str) == str(re)]
    if not user.empty:
        return gerar_hash(senha) == user.iloc[0]["senha_hash"], user.iloc[0]["perfil"]
    return False, None

def atualizar_senha(re, nova_senha):
    df_users = carregar_usuarios()
    if re in df_users["RE"].astype(str).values:
        df_users.loc[df_users["RE"].astype(str) == str(re), "senha_hash"] = gerar_hash(nova_senha)
    else:
        df_users = pd.concat([df_users, pd.DataFrame({"RE": [re], "senha_hash": [gerar_hash(nova_senha)], "perfil": ["USER"]})])
    salvar_usuarios(df_users)

def atualizar_perfil(re, perfil):
    df_users = carregar_usuarios()
    if re in df_users["RE"].astype(str).values:
        df_users.loc[df_users["RE"].astype(str) == str(re), "perfil"] = perfil
    else:
        df_users = pd.concat([df_users, pd.DataFrame({"RE": [re], "senha_hash": [""], "perfil": [perfil]})])
    salvar_usuarios(df_users)

# Inicialização do arquivo de usuários
if not os.path.exists(usuarios_file):
    df_init = pd.DataFrame([{
        "RE": "1",
        "senha_hash": gerar_hash("master123!"),
        "perfil": "MASTER"
    }])
    df_init.to_excel(usuarios_file, index=False)
else:
    df_users = pd.read_excel(usuarios_file)
    if "perfil" not in df_users.columns:
        df_users["perfil"] = "USER"
        df_users.loc[df_users["RE"].astype(str) == "1", "perfil"] = "MASTER"
        df_users.to_excel(usuarios_file, index=False)

# Interface principal
aba = st.radio("Selecione a opção:", ["Login", "Primeiro acesso / Recuperar senha"])

if aba == "Login":
    st.subheader("🔐 Login")
    re = st.text_input("RE")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        ok, perfil = verificar_login(re, senha)
        if ok:
            st.session_state["usuario_logado"] = re
            st.session_state["perfil"] = perfil
            st.success(f"Login bem-sucedido! Perfil: {perfil}")
        else:
            st.error("RE ou senha inválidos.")

elif aba == "Primeiro acesso / Recuperar senha":
    st.subheader("🔑 Criar ou recuperar senha")
    re_input = st.text_input("Digite seu RE")
    nova_senha = st.text_input("Nova senha", type="password")
    confirmar_senha = st.text_input("Confirme a senha", type="password")

    if st.button("Criar/Atualizar senha"):
        if not re_input or not nova_senha or not confirmar_senha:
            st.error("Preencha todos os campos.")
        elif nova_senha != confirmar_senha:
            st.error("As senhas não coincidem.")
        elif not senha_valida(nova_senha):
            st.error("A senha deve conter números, letras maiúsculas e minúsculas, caracteres especiais e no mínimo 10 caracteres.")
        else:
            atualizar_senha(re_input, nova_senha)
            st.success("Senha criada/atualizada com sucesso! Volte para a aba Login.")

# Após login
if "usuario_logado" in st.session_state and "perfil" in st.session_state:
    perfil = st.session_state["perfil"]
    st.title("Carteirinha Digital de Treinamento")

    # Definir abas conforme perfil
    if perfil == "MASTER":
        tabs = st.tabs(["Minha Carteirinha", "Gerar Carteirinha de Outro", "Gerenciar Perfis"])
    elif perfil == "ADM":
        tabs = st.tabs(["Minha Carteirinha", "Gerar Carteirinha de Outro"])
    else:
        tabs = st.tabs(["Minha Carteirinha"])

    # Função para buscar treinamentos
    @st.cache_data
    def carregar_planilha():
        return pd.read_excel(treinamentos_file, sheet_name="BASE", engine="openpyxl")

    def buscar_treinamentos(df, re_consulta):
        df[col_cod] = df[col_cod].astype(str).str.strip()
        df[col_trilha] = df[col_trilha].astype(str).str.strip().str.upper()
        df[col_trein] = df[col_trein].astype(str).str.strip()
        re_consulta = str(re_consulta).strip()

        filtro = df[
            (df[col_cod] == re_consulta) &
            (df[col_trilha].str.contains("SEGURANÇA DO TRABALHO"))
        ]

        if filtro.empty:
            return None, []

        nome = filtro.iloc[0][col_nome]
        cargo = filtro.iloc[0][col_cargo] if col_cargo else ""
        depto = filtro.iloc[0][col_depto] if col_depto else ""
        unidade = filtro.iloc[0][col_unidade] if col_unidade else ""
        treinamentos_ordenados = sorted(filtro[col_trein].dropna().unique())

        return (nome, cargo, depto, unidade), treinamentos_ordenados

    def gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos_ordenados):
        background = Image.open("image.png").convert("RGB")
        draw = ImageDraw.Draw(background)
        logo = Image.open("logo.png").resize((250, 150))
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
    col_nome = next((c for c in ["NOME","Nome","nome"] if c in df.columns), None)
    col_cargo = next((c for c in ["CARGO","Cargo","cargo"] if c in df.columns), None)
    col_depto = next((c for c in ["DEPARTAMENTO","Departamento","departamento"] if c in df.columns), None)
    col_unidade = next((c for c in ["FILIAL_NOME","Unidade","unidade","FILIAL"] if c in df.columns), None)
    col_trein = next((c for c in ["TREINAMENTO_STATUS_GERAL"] if c in df.columns), None)
    col_trilha = next((c for c in ["TRILHA DE TREINAMENTO ","Trilha","TRILHA","trilha"] if c in df.columns), None)

    # Aba Minha Carteirinha
    with tabs[0]:
        st.subheader("Minha Carteirinha")
        re_consulta = st.session_state["usuario_logado"]
        if st.button("Gerar Minha Carteirinha"):
            dados, treinamentos = buscar_treinamentos(df, re_consulta)
            if not dados:
                st.warning(f"Nenhum treinamento encontrado para RE {re_consulta}.")
            else:
                st.write("Treinamentos encontrados:", len(treinamentos))
                for t in treinamentos:
                    st.write("-", t)
                img_path, pdf_path = gerar_carteirinha(dados[0], re_consulta, dados[1], dados[2], dados[3], treinamentos)
                st.image(img_path, caption="Carteirinha Digital", use_container_width=True)
                with open(img_path, "rb") as img_file:
                    st.download_button("📥 Baixar como PNG", img_file, "carteirinha_final.png", "image/png")
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button("📄 Baixar como PDF", pdf_file, "carteirinha_final.pdf", "application/pdf")

    # Aba Gerar Carteirinha de Outro
    if perfil in ["MASTER", "ADM"]:
        with tabs[1]:
            st.subheader("Gerar Carteirinha de Outro Colaborador")
            re_outro = st.text_input("Digite o RE do colaborador")
            if st.button("Gerar Carteirinha de Outro"):
                dados, treinamentos = buscar_treinamentos(df, re_outro)
                if not dados:
                    st.warning(f"Nenhum treinamento encontrado para RE {re_outro}.")
                else:
                    st.write("Treinamentos encontrados:", len(treinamentos))
                    for t in treinamentos:
                        st.write("-", t)
                    img_path, pdf_path = gerar_carteirinha(dados[0], re_outro, dados[1], dados[2], dados[3], treinamentos)
                    st.image(img_path, caption="Carteirinha Digital", use_container_width=True)
                    with open(img_path, "rb") as img_file:
                        st.download_button("📥 Baixar como PNG", img_file, "carteirinha_final.png", "image/png")
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button("📄 Baixar como PDF", pdf_file, "carteirinha_final.pdf", "application/pdf")

    # Aba Gerenciar Perfis
    if perfil == "MASTER":
        with tabs[2]:
            st.subheader("Gerenciar Perfis")
            re_alvo = st.text_input("RE para alterar perfil")
            novo_perfil = st.selectbox("Novo perfil", ["USER", "ADM", "MASTER"])
            if st.button("Atualizar perfil"):
                atualizar_perfil(re_alvo, novo_perfil)
                st.success(f"Perfil de {re_alvo} atualizado para {novo_perfil}")
