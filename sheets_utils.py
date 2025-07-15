import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from gspread_dataframe import get_as_dataframe, set_with_dataframe
import google.generativeai as genai
import streamlit as st

def conectar_google_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    cred = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    cliente = gspread.authorize(cred)
    return cliente, cred

def obtener_hoja_unica(cliente):
    return cliente.open("circulo_financiero_unico").sheet1

def cargar_datos_usuario(hoja, correo_usuario):
    df = get_as_dataframe(hoja, evaluate_formulas=True).dropna(how="all")
    if not df.empty and "Usuario" in df.columns:
        df = df[df["Usuario"] == correo_usuario].copy()
        if "Fecha" in df.columns:
            df["Fecha"] = pd.to_datetime(df["Fecha"], errors='coerce')
    else:
        df = pd.DataFrame(columns=["Fecha", "Tipo", "Categoría", "Descripción", "Monto", "Usuario"])
    return df

def guardar_datos_usuario(hoja, df_usuario):
    df_actual = get_as_dataframe(hoja, evaluate_formulas=True).dropna(how="all")
    if df_actual.empty:
        df_actual = pd.DataFrame(columns=["Fecha", "Tipo", "Categoría", "Descripción", "Monto", "Usuario"])

    if not df_usuario.empty and "Usuario" in df_usuario.columns:
        usuario = df_usuario["Usuario"].iloc[0]
        df_actual = df_actual[df_actual["Usuario"] != usuario]

    df_nuevo = pd.concat([df_actual, df_usuario], ignore_index=True)

    hoja.clear()
    set_with_dataframe(hoja, df_nuevo)

def registrar_usuario_activo(correo_usuario, cliente):
    hoja_maestra = cliente.open("usuarios_activos").sheet1
    lista_correos = hoja_maestra.col_values(1)
    if correo_usuario not in lista_correos:
        hoja_maestra.append_row([correo_usuario])

# 🧠 NUEVO: funciones IA
def obtener_recomendacion_financiera(df, objetivo_usuario):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    texto_datos = df.to_csv(index=False)

    prompt = f"""
Eres un asesor financiero inteligente. Un usuario tiene como objetivo "{objetivo_usuario}".
Aquí están sus datos financieros:

{texto_datos}

Analiza sus ingresos, egresos y hábitos financieros.
1. ¿Qué recomendaciones puedes darle para mejorar su situación?
2. ¿Cómo puede optimizar su presupuesto para alcanzar su objetivo?
3. ¿Qué patrones o riesgos ves en sus finanzas?
    """

    model = genai.GenerativeModel("gemini-1.5-flash")
    respuesta = model.generate_content(prompt)
    return respuesta.text

def generar_presupuesto_sugerido(df):
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    texto_datos = df.to_csv(index=False)

    prompt = f"""
Eres un experto en análisis financiero.
Con base en los siguientes registros del usuario:

{texto_datos}

Genera una proyección mensual de sus gastos e ingresos esperados para los próximos 3 meses.
Sugiere un presupuesto realista y metas de ahorro por categoría.
    """

    model = genai.GenerativeModel("gemini-1.5-flash")
    respuesta = model.generate_content(prompt)
    return respuesta.text
