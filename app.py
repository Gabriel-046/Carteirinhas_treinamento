import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import pytz
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import hashlib
import os
import textwrap

st.set_page_config(page_title="Carteirinha Digital de Treinamento", page_icon="🎓")

usuarios_file = "usuarios.xlsx"
treinamentos_file = "Treinamentos Normativos.xlsx"
image_path = "image.png"
logo_path = "logo.png"

# Funções auxiliares
def gerar_hash(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def senha_valida(senha):
    return (
        len(senha) >= 10 and
        any(c.isupper() for c in senha) and
        any(c.islower() for c in senha) and
        any(c.isdigit() for c in senha) and
        any(c in "!@#$%^&*()-_=+[]{};:'\\\",.<>?/" for c in senha)
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

if not os.path.exists(usuarios_file):
    df_init = pd.DataFrame([{"RE": "1", "senha_hash": gerar_hash("master123!"), "perfil": "MASTER"}])
    df_init.to_excel(usuarios_file, index=False)

if "pagina" not in st.session_state:
    st.session_state["pagina"] = "login"

# Página de Login
if st.session_state["pagina"] == "login":
    st.title("🔐 Login")
    re = st.text_input("RE")
    senha = st.text_input("Senha", type="password")
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Entrar"):
            ok, perfil = verificar_login(re, senha)
            if ok:
                st.session_state["usuario_logado"] = re
                st.session_state["perfil"] = perfil
                st.session_state["pagina"] = "principal"
                st.success("Login realizado com sucesso!")
            else:
                st.error("RE ou senha inválidos.")
    with col2:
        if st.button("Redefinir senha"):
            st.session_state["pagina"] = "redefinir"

elif st.session_state["pagina"] == "redefinir":
    st.title("🔑 Redefinir Senha")
    re_input = st.text_input("Digite seu RE")
    nova_senha = st.text_input("Nova senha", type="password")
    confirmar_senha = st.text_input("Confirme a senha", type="password")
    if st.button("Atualizar senha"):
        if not re_input or not nova_senha or not confirmar_senha:
            st.error("Preencha todos os campos.")
        elif nova_senha != confirmar_senha:
            st.error("As senhas não coincidem.")
        elif not senha_valida(nova_senha):
            st.error("A senha deve conter números, letras maiúsculas e minúsculas, caracteres especiais e no mínimo 10 caracteres.")
        else:
            atualizar_senha(re_input, nova_senha)
            st.success("Senha atualizada com sucesso!")
            st.session_state["pagina"] = "login"

# Página principal
elif st.session_state["pagina"] == "principal":
    perfil = st.session_state["perfil"]
    st.title("Carteirinha Digital de Treinamento")

    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.session_state["pagina"] = "login"

    if perfil == "MASTER":
        tabs = st.tabs(["Minha Carteirinha", "Gerar Carteirinha de Outro", "Gerenciar Perfis"])
    elif perfil == "ADM":
        tabs = st.tabs(["Minha Carteirinha", "Gerar Carteirinha de Outro"])
    else:
        tabs = st.tabs(["Minha Carteirinha"])

    @st.cache_data
    def carregar_planilha():
        df = pd.read_excel(treinamentos_file, sheet_name="BASE", engine="openpyxl")
        df.columns = df.columns.str.strip().str.upper()
        return df

    def buscar_treinamentos(df, re_consulta):
        col_cod = "COD_FUNCIONARIO"
        col_nome = "NOME"
        col_cargo = "CARGO"
        col_depto = "DEPARTAMENTO"
        col_unidade = "FILIAL_NOME"
        col_trein = "TREINAMENTO_STATUS_GERAL"

        df[col_cod] = df[col_cod].astype(str).str.strip()
        re_consulta = str(re_consulta).strip()

        filtro = df[df[col_cod] == re_consulta]

        if filtro.empty:
            return None, []

        nome = filtro.iloc[0][col_nome]
        cargo = filtro.iloc[0][col_cargo]
        depto = filtro.iloc[0][col_depto]
        unidade = filtro.iloc[0][col_unidade]

        treinamentos = filtro[col_trein].dropna().tolist()

        return (nome, cargo, depto, unidade), treinamentos

    def gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos):
        background = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(background)

        if os.path.exists(logo_path):
            logo = Image.open(logo_path).resize((250, 150))
            background.paste(logo, (50, 30))

        try:
            font_info = ImageFont.truetype("DejaVuSans-Bold.ttf", 22)
            font_trein = ImageFont.truetype("DejaVuSans.ttf", 18)
        except:
            font_info = ImageFont.load_default()
            font_trein = ImageFont.load_default()

        info_x = 50
        info_y = 200
        line_height_info = 45
        max_width_info = 30
        info = [
            f"NOME: {nome}",
            f"RE: {re_input}",
            f"CARGO: {cargo}",
            f"DEPARTAMENTO: {depto}",
            f"UNIDADE: {unidade}"
        ]
        for linha in info:
            linhas_quebradas = textwrap.wrap(linha, width=max_width_info)
            for parte in linhas_quebradas:
                draw.text((info_x, info_y), parte, font=font_info, fill="#304F7E")
                info_y += line_height_info

        train_x = 500
        train_y = 100
        max_width = 50
        for t in treinamentos:
            linhas = textwrap.wrap(t, width=max_width)
            for linha in linhas:
                draw.text((train_x, train_y), linha, font=font_trein, fill="black")
                train_y += 28
            train_y += 10

        hora_local = datetime.now(pytz.timezone("America/Campo_Grande")).strftime("%d/%m/%Y %H:%M")
        draw.text((50, background.height - 40), f"Consulta em: {hora_local}", font=font_trein, fill="gray")

        img_path = "carteirinha_final.png"
        background.save(img_path)

        pdf_path = "carteirinha_final.pdf"
        c = canvas.Canvas(pdf_path, pagesize=(25.4 * cm, 15 * cm))
        c.drawImage(img_path, 0, 0, width=25.4 * cm, height=15 * cm)
        c.showPage()
        c.save()

        return img_path, pdf_path

    df = carregar_planilha()

    # Aba Minha Carteirinha
    with tabs[0]:
        st.subheader("Minha Carteirinha")
        re_consulta = st.session_state["usuario_logado"]
        dados, treinamentos = buscar_treinamentos(df, re_consulta)
        if not dados:
            st.warning(f"Nenhum treinamento encontrado para RE {re_consulta}.")
        else:
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
            if st.button("Gerar Carteirinha"):
                dados, treinamentos = buscar_treinamentos(df, re_outro)
                if not dados:
                    st.warning(f"Nenhum treinamento encontrado para RE {re_outro}.")
                else:
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
            re_alvo = st.text_input("Digite o RE para alterar perfil")
            novo_perfil = st.selectbox("Novo perfil", ["USER", "ADM", "MASTER"])
            if st.button("Atualizar Perfil"):
                atualizar_perfil(re_alvo, novo_perfil)
                st.success(f"Perfil de {re_alvo} atualizado para {novo_perfil}")
