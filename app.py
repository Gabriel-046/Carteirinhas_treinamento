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
import unicodedata

# Configuração da página
st.set_page_config(page_title="Carteirinha Digital de Treinamento", page_icon="🎓")

usuarios_file = "usuarios.xlsx"
treinamentos_file = "Treinamentos Normativos.xlsx"
id_colaborador_file = "ID_Colaborador.xlsx"
log_file = "atividades.csv"  # ✅ Arquivo para registrar atividades

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

@st.cache_data
def carregar_id_colaborador():
    df_id = pd.read_excel(id_colaborador_file)
    df_id.columns = df_id.columns.str.strip()
    return df_id

# ✅ Função para registrar atividades detalhadas
def registrar_atividade(executado_por_re, executado_por_nome, alvo_re, alvo_nome, acao, detalhes=""):
    hora = datetime.now(pytz.timezone("America/Campo_Grande")).strftime("%d/%m/%Y %H:%M:%S")
    novo_registro = pd.DataFrame([[hora, executado_por_re, executado_por_nome, alvo_re, alvo_nome, acao, detalhes]],
                                  columns=["DataHora", "ExecutadoPor_RE", "ExecutadoPor_Nome", "Alvo_RE", "Alvo_Nome", "Acao", "Detalhes"])
    if os.path.exists(log_file):
        df_log = pd.read_csv(log_file)
        df_log = pd.concat([df_log, novo_registro], ignore_index=True)
    else:
        df_log = novo_registro
    df_log.to_csv(log_file, index=False)

# Inicialização do arquivo de usuários
if not os.path.exists(usuarios_file):
    df_init = pd.DataFrame([{"RE": "1", "senha_hash": gerar_hash("master123!"), "perfil": "MASTER"}])
    df_init.to_excel(usuarios_file, index=False)

# Controle de navegação
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
                df_id = carregar_id_colaborador()
                nome_usuario = df_id[df_id["COD_FUNCIONARIO"].astype(str) == str(re)]["NOME"].iloc[0] if not df_id.empty else ""
                registrar_atividade(re, nome_usuario, re, nome_usuario, "Login")
                st.session_state["usuario_logado"] = re
                st.session_state["nome_usuario"] = nome_usuario
                st.session_state["perfil"] = perfil
                st.session_state["pagina"] = "principal"
                st.rerun()
            else:
                st.error("RE ou senha inválidos.")
    with col2:
        if st.button("Redefinir senha"):
            st.session_state["pagina"] = "redefinir"

# Página de redefinição de senha
elif st.session_state["pagina"] == "redefinir":
    st.title("🔑 Redefinir Senha")
    re_input = st.text_input("Digite seu RE")
    cpf_inicio = st.text_input("Informe os 3 primeiros dígitos do CPF")
    ano_nasc = st.text_input("Informe seu ano de nascimento (AAAA)")
    nova_senha = st.text_input("Nova senha", type="password")
    confirmar_senha = st.text_input("Confirme a senha", type="password")

    df_id = carregar_id_colaborador()

    if st.button("Atualizar senha"):
        if not re_input or not cpf_inicio or not ano_nasc or not nova_senha or not confirmar_senha:
            st.error("Preencha todos os campos.")
        elif len(ano_nasc) != 4 or not ano_nasc.isdigit():
            st.error("Ano de nascimento inválido. Use formato AAAA.")
        else:
            filtro = df_id[df_id["COD_FUNCIONARIO"].astype(str) == str(re_input)]
            if filtro.empty:
                st.error("RE não encontrado.")
            else:
                cpf_real = str(filtro.iloc[0]["CPF"]).replace(".", "").replace("-", "").strip()
                cpf_tres = cpf_real[:3]
                data_nasc = filtro.iloc[0]["DATA_NASCIMENTO"]
                ano_real = str(data_nasc.year) if isinstance(data_nasc, datetime) else str(data_nasc).split("/")[-1]
                nome_alvo = filtro.iloc[0]["NOME"]

                if cpf_tres != cpf_inicio or ano_real != ano_nasc:
                    st.error("Validação falhou. Dados não conferem.")
                elif nova_senha != confirmar_senha:
                    st.error("As senhas não coincidem.")
                elif not senha_valida(nova_senha):
                    st.error("A senha deve conter números, letras maiúsculas e minúsculas, caracteres especiais e no mínimo 10 caracteres.")
                else:
                    atualizar_senha(re_input, nova_senha)
                    registrar_atividade(st.session_state.get("usuario_logado", re_input),
                                         st.session_state.get("nome_usuario", nome_alvo),
                                         re_input, nome_alvo, "Redefinição de senha")
                    st.success("Senha atualizada com sucesso!")
                    st.session_state["pagina"] = "login"
                    st.rerun()

# Página principal após login
elif st.session_state["pagina"] == "principal":
    perfil = st.session_state["perfil"]
    nome_usuario_logado = st.session_state["nome_usuario"]
    st.title("Carteirinha Digital de Treinamento")

    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.session_state["pagina"] = "login"
        st.rerun()

    if perfil == "MASTER":
        tabs = st.tabs(["Minha Carteirinha", "Gerar Carteirinha de Outro", "Gerenciar Perfis"])
    elif perfil == "ADM":
        tabs = st.tabs(["Minha Carteirinha", "Gerar Carteirinha de Outro"])
    else:
        tabs = st.tabs(["Minha Carteirinha"])

    @st.cache_data
    def carregar_planilha():
        df = pd.read_excel(treinamentos_file, sheet_name="BASE", engine="openpyxl")
        df.columns = df.columns.str.strip()
        return df

    def remover_acentos(texto):
        return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')

    def buscar_treinamentos(df, re_consulta):
        col_cod = "COD_FUNCIONARIO"
        col_nome = "NOME"
        col_cargo = "CARGO"
        col_depto = "DEPARTAMENTO"
        col_unidade = "FILIAL_NOME"
        col_trilha = "TRILHA DE TREINAMENTO"
        col_trein = "TREINAMENTO_STATUS_GERAL"
        df[col_cod] = df[col_cod].astype(str).str.strip()
        df[col_trilha] = df[col_trilha].apply(lambda x: remover_acentos(str(x)).upper().strip())
        df[col_trein] = df[col_trein].astype(str).str.strip()
        re_consulta = str(re_consulta).strip()
        filtro = df[df[col_cod] == re_consulta]
        if filtro.empty:
            return None, []
        nome = filtro.iloc[0][col_nome]
        cargo = filtro.iloc[0][col_cargo]
        depto = filtro.iloc[0][col_depto]
        unidade = filtro.iloc[0][col_unidade]
        treinamentos = sorted(filtro[col_trein].dropna().unique())
        return (nome, cargo, depto, unidade), treinamentos

    def gerar_carteirinha(nome, re_input, cargo, depto, unidade, treinamentos):
        azul = "#304F7E"
        cinza = "#BDBFC1"
        img = Image.open("image.png").convert("RGB")
        draw = ImageDraw.Draw(img)
        try:
            font_info = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
            font_treinamentos = ImageFont.truetype("DejaVuSans.ttf", 15)
        except:
            font_info = ImageFont.load_default()
            font_treinamentos = ImageFont.load_default()
        try:
            logo = Image.open("logo.png").convert("RGBA")
            logo = logo.resize((150, 150))
            img.paste(logo, (50, 20), logo)
        except:
            pass
        info = [f"NOME: {nome}", f"RE: {re_input}", f"CARGO: {cargo}",
                f"DEPARTAMENTO: {depto}", f"UNIDADE: {unidade}"]
        x_left, y_left = 12, 190
        for linha in info:
            for parte in textwrap.wrap(linha, width=30):
                draw.text((x_left, y_left), parte, font=font_info, fill=azul)
                y_left += 35
        x_right, y_right = 500, 120
        for t in treinamentos:
            for linha in textwrap.wrap(t, width=80):
                draw.text((x_right, y_right), linha, font=font_treinamentos, fill=azul)
                y_right += 22
        hora_local = datetime.now(pytz.timezone("America/Campo_Grande")).strftime("%d/%m/%Y %H:%M")
        draw.text((x_right, y_right + 20), f"Gerado em: {hora_local}", font=font_treinamentos, fill=cinza)
        img_path = "carteirinha_final.png"
        img.save(img_path)
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
            registrar_atividade(st.session_state["usuario_logado"], nome_usuario_logado, re_consulta, dados[0], "Gerar Carteirinha")
            st.image(img_path, caption="Carteirinha Digital", use_container_width=True)
            with open(img_path, "rb") as img_file:
                st.download_button("📥 Baixar como PNG", img_file, "carteirinha_final.png", "image/png", key="download_png_minha")
            with open(pdf_path, "rb") as pdf_file:
                st.download_button("📄 Baixar como PDF", pdf_file, "carteirinha_final.pdf", "application/pdf", key="download_pdf_minha")

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
                    img_path, pdf_path = gerar_carteirinha(dados[0], re_outro, dados[1], dados[2], dados[3], treinamentos)
                    registrar_atividade(st.session_state["usuario_logado"], nome_usuario_logado, re_outro, dados[0], "Gerar Carteirinha de Outro")
                    st.image(img_path, caption="Carteirinha Digital", use_container_width=True)
                    with open(img_path, "rb") as img_file:
                        st.download_button("📥 Baixar como PNG", img_file, "carteirinha_final.png", "image/png", key="download_png_outro")
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button("📄 Baixar como PDF", pdf_file, "carteirinha_final.pdf", "application/pdf", key="download_pdf_outro")

    # Aba Gerenciar Perfis
    if perfil == "MASTER":
        with tabs[2]:
            st.subheader("Gerenciar Perfis")
            re_alvo = st.text_input("RE para alterar perfil")
            novo_perfil = st.selectbox("Novo perfil", ["USER", "ADM", "MASTER"])
            if st.button("Atualizar perfil"):
                atualizar_perfil(re_alvo, novo_perfil)
                df_id = carregar_id_colaborador()
                nome_alvo = df_id[df_id["COD_FUNCIONARIO"].astype(str) == str(re_alvo)]["NOME"].iloc[0] if not df_id.empty else ""
                registrar_atividade(st.session_state["usuario_logado"], nome_usuario_logado, re_alvo, nome_alvo, "Alteração de perfil", f"Novo perfil: {novo_perfil}")
                st.success(f"Perfil de {re_alvo} atualizado para {novo_perfil}")

            st.write("📥 Baixar Relatório de Atividades")
            if os.path.exists(log_file):
                df_log = pd.read_csv(log_file)
                st.download_button("📥 Baixar Relatório", df_log.to_csv(index=False), "relatorio_atividades.csv", "text/csv")
            else:
                st.info("Nenhuma atividade registrada ainda.")
