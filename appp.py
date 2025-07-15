import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

from sheets_utils import (
    conectar_google_sheets,
    obtener_hoja_usuario,
    cargar_datos_usuario,
    guardar_datos_usuario
)

# ------------------ ESTILOS ------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #4682B4;
        color: #121212;
    }
    h1, h2, h3, h4 {
        color: #3F51B5;
        font-weight: bold;
    }
    div.stButton > button {
        background-color: #3f51b5;
        color: white;
        border-radius: 6px;
        padding: 0.4em 1em;
        border: #2C3E50;
    }
    div.stButton > button:hover {
        background-color: #2c387e;
    }
    input, select, textarea {
        border: 2px solid #3f51b5 !important;
        border-radius: 5px;
        padding: 0.4em;
        background-color: white !important;
        color: #000 !important;
    }
    input:focus, select:focus, textarea:focus {
        border-color: #283593 !important;
        outline: none !important;
        box-shadow: 0 0 5px #3f51b5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------------ CABECERA ------------------
st.markdown(
    """
    <div style='display:flex; align-items:center; gap:15px; margin-bottom:20px;'>
        <img src='https://cdn-icons-png.flaticon.com/512/190/190411.png' alt='logo' style='width:60px; height:60px;'/>
        <h1>Círculo Financiero</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("💰 Registro de Ingresos y Egresos")

# ------------------ LOGIN / CORREO ------------------
st.info("🔐 Ingresa tu correo para cargar tus datos financieros personales")
correo_usuario = st.text_input("Correo electrónico del usuario:")

if correo_usuario:
    cliente, cred = conectar_google_sheets()
    hoja_usuario = obtener_hoja_usuario(correo_usuario, cliente, cred)
    df = cargar_datos_usuario(hoja_usuario)

    # ------------------ CAPTURA DE MOVIMIENTO ------------------
    CATEGORIAS = {
        "Ingreso": ["Ventas", "Nómina", "Préstamos", "Intereses", "Otros"],
        "Egreso": ["Mercancías", "Gastos generales", "Gastos financieros", "Gastos personales", "Otros"]
    }

    tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])

    with st.form("registro"):
        fecha = st.date_input("Fecha", datetime.today())
        categoria = st.selectbox("Categoría", CATEGORIAS[tipo])
        descripcion = st.text_input("Descripción")
        monto = st.number_input("Monto", min_value=0.0, format="%.2f")
        enviado = st.form_submit_button("Guardar Movimiento")

        if enviado:
            nuevo = {
                "Fecha": pd.to_datetime(fecha),
                "Tipo": tipo,
                "Categoría": categoria,
                "Descripción": descripcion,
                "Monto": monto
            }
            df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
            guardar_datos_usuario(hoja_usuario, df)
            st.success("✅ Movimiento registrado y guardado en tu Google Sheet")

    # ------------------ ANÁLISIS ------------------
    if not df.empty:
        st.subheader("📋 Movimientos registrados")
        df["Fecha"] = pd.to_datetime(df["Fecha"])
        st.dataframe(df, use_container_width=True)

        # Botón para eliminar fila con error
        st.subheader("🗑️ Eliminar movimientos con error")
        index_borrar = st.number_input("Escribe el número de fila a eliminar (empezando desde 0)", min_value=0, max_value=len(df) - 1, step=1)
        if st.button("Eliminar fila"):
            df = df.drop(index=index_borrar).reset_index(drop=True)
            guardar_datos_usuario(hoja_usuario, df)
            st.success(f"✅ Fila {index_borrar} eliminada correctamente.")

        df["Mes"] = pd.to_datetime(df["Fecha"]).dt.to_period("M").astype(str)
        meses_disponibles = sorted(df["Mes"].unique())
        mes_seleccionado = st.selectbox("📅 Selecciona un mes para análisis:", meses_disponibles)

        df_mes = df[df["Mes"] == mes_seleccionado]
        ingresos = df_mes[df_mes["Tipo"] == "Ingreso"]["Monto"].sum()
        egresos = df_mes[df_mes["Tipo"] == "Egreso"]["Monto"].sum()
        balance = ingresos - egresos

        st.subheader(f"📊 Resumen de {mes_seleccionado}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Ingresos", f"${ingresos:,.2f}")
        col2.metric("Total Egresos", f"${egresos:,.2f}")
        col3.metric("Balance", f"${balance:,.2f}")

        st.subheader("📈 Visualizaciones")

        df_ingresos = df[df["Tipo"] == "Ingreso"]
        categorias_ingreso = df_ingresos["Categoría"].unique()
        if len(categorias_ingreso) > 0:
            categoria_seleccionada = st.selectbox("Selecciona una categoría para el histograma:", sorted(categorias_ingreso))
            df_categoria = df_ingresos[df_ingresos["Categoría"] == categoria_seleccionada]

            if not df_categoria.empty:
                fig1 = px.histogram(
                    df_categoria,
                    x="Mes",
                    y="Monto",
                    title=f"📊 Histograma mensual de '{categoria_seleccionada}'",
                    barmode="stack",
                    color_discrete_sequence=["#2ECC71"]
                )
                st.plotly_chart(fig1, use_container_width=True)

        if not df_ingresos.empty:
            fig2 = px.bar(
                df_ingresos,
                x="Mes",
                y="Monto",
                color="Categoría",
                title="📊 Ingresos por Categoría y Mes (Barras Apiladas)",
                barmode="stack"
            )
            st.plotly_chart(fig2, use_container_width=True)

        ingresos_mes = df_mes[df_mes["Tipo"] == "Ingreso"]
        if not ingresos_mes.empty:
            fig3 = px.pie(
                ingresos_mes,
                names="Categoría",
                values="Monto",
                title=f"🥧 Ingresos por Categoría – {mes_seleccionado}"
            )
            st.plotly_chart(fig3, use_container_width=True)

        egresos_mes = df_mes[df_mes["Tipo"] == "Egreso"]
        if not egresos_mes.empty:
            fig4 = px.pie(
                egresos_mes,
                names="Categoría",
                values="Monto",
                title=f"🥧 Egresos por Categoría – {mes_seleccionado}"
            )
            st.plotly_chart(fig4, use_container_width=True)

    else:
        st.info("No hay movimientos registrados aún.")
else:
    st.warning("👤 Por favor, ingresa tu correo para comenzar.")
