# -*- coding: utf-8 -*-
"""
Carteirinha de Treinamento — Streamlit App
@author: gabriel.oliveira
"""

import streamlit as st
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Carteirinha de Treinamento", page_icon="🎓")

st.title("🎓 Carteirinha de Treinamento")

st.markdown("""
Preencha **RE** e **Data de Admissão** para ver a carteirinha.  
Formato da data: **DD/MM/AAAA** (ex: 15/03/2022)
""")

# Caminho do arquivo padrão (deve estar no mesmo diretório do app.py)
LOCAL_PATH = "Treinamentos Normativos.xlsx"

# Carregar a planilha
try:
    df = pd.read_excel(LOCAL_PATH)
except FileNotFoundError:
    st.error("Arquivo padrão não encontrado. Certifique-se de que 'Treinamentos Normativos.xlsx' está no repositório.")
    st.stop()

# Mostrar primeiras linhas (opcional)
if st.checkbox("Mostrar primeiras linhas da planilha (verificar colunas)"):
    st.dataframe(df.head())

# Mapeamento automático de colunas
possible_cod = ["COD_FUNCIONARIO", "RE", "Cod", "cod_funcionario", "cod"]
possible_adm = ["DATA_ADMISSAO", "Admissao", "admissao", "DataAdmissao", "DATA_ADM"]
possible_nome = ["NOME", "Nome", "nome"]
possible_cargo = ["CARGO", "Cargo", "cargo"]
possible_trein = ["TREINAMENTO_&_DATA", "TREINAMENTO", "DESCRICAO", "CURSO", "Treinamento"]
possible_venc = ["DATA_VENCIMENTO", "VENCIMENTO", "DataVencimento", "Data Vencimento"]

def find_col(possible):
    for c in possible:
        if c in df.columns:
            return c
    return None

col_cod = find_col(possible_cod)
col_adm = find_col(possible_adm)
col_nome = find_col(possible_nome)
col_cargo = find_col(possible_cargo)
col_trein = find_col(possible_trein)
col_venc = find_col(possible_venc)

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

        # Converter coluna de admissão para date
        try:
            df[col_adm] = pd.to_datetime(df[col_adm]).dt.date
        except Exception as e:
            st.error(f"Erro ao converter a coluna de admissão: {e}")
            st.stop()

        # Filtrar os dados
        filtro = df[(df[col_cod].astype(str) == str(re_input)) & (df[col_adm] == adm_date)]

        if filtro.empty:
            st.warning(f"Nenhum registro encontrado para RE {re_input} e admissão {admissao_input}.")
        else:
            nome = filtro.iloc[0][col_nome]
            cargo = filtro.iloc[0][col_cargo] if col_cargo in filtro.columns else ""
            st.success(f"{nome} — {cargo}")
            st.write(f"RE: **{re_input}** | Admissão: **{adm_date.strftime('%d/%m/%Y')}**")

            if col_trein and col_trein in filtro.columns:
                st.subheader("Treinamentos:")

                df_display = filtro[[col_trein]].copy()

                # Se houver coluna de vencimento, colocar na frente
                if col_venc:
                    df_display.insert(
                        0, 
                        "Data de Vencimento", 
                        pd.to_datetime(filtro[col_venc]).dt.strftime("%d/%m/%Y")
                    )

                # Garantir que a coluna de treinamento esteja como texto
                df_display[col_trein] = df_display[col_trein].astype(str)

                st.dataframe(df_display.rename(columns={col_trein: "Treinamento"}))
            else:
                st.subheader("Registros encontrados:")
                st.dataframe(filtro)
