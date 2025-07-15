import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

from sheets_utils import (
    conectar_google_sheets,
    obtener_hoja_unica,
    cargar_datos_usuario,
    guardar_datos_usuario,
    registrar_usuario_activo,
    obtener_recomendacion_financiera,
    generar_presupuesto_sugerido
)

st.set_page_config(page_title="Círculo Financiero", layout="wide")
st.title("💼 Círculo Financiero – Registro y Análisis de Finanzas")

st.markdown("💰 Registro de Ingresos y Egresos")

correo_usuario = st.text_input("Correo electrónico del usuario:")

if correo_usuario:
    cliente, cred = conectar_google_sheets()
    registrar_usuario_activo(correo_usuario, cliente)
    hoja = obtener_hoja_unica(cliente)
    df_usuario = cargar_datos_usuario(hoja, correo_usuario)

    CATEGORIAS = {
        "Ingreso": ["Ventas", "Nómina", "Préstamos", "Intereses", "Otros"],
        "Egreso": ["Mercancías", "Gastos generales", "Gastos financieros", "Gastos personales", "combustibles","Otros"]
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
                "Monto": monto,
                "Usuario": correo_usuario
            }
            df_usuario = pd.concat([df_usuario, pd.DataFrame([nuevo])], ignore_index=True)
            guardar_datos_usuario(hoja, df_usuario)
            st.success("✅ Movimiento registrado y guardado en tu Google Sheet")

    if not df_usuario.empty:
        st.subheader("📋 Movimientos registrados")
        df_usuario["Fecha"] = pd.to_datetime(df_usuario["Fecha"])
        st.dataframe(df_usuario, use_container_width=True)

        st.subheader("🗑️ Eliminar movimientos con error")
        index_borrar = st.number_input("Escribe el número de fila a eliminar (empezando desde 0)", min_value=0, max_value=len(df_usuario) - 1, step=1)
        if st.button("Eliminar fila"):
            df_usuario = df_usuario.drop(index=index_borrar).reset_index(drop=True)
            guardar_datos_usuario(hoja, df_usuario)
            st.success(f"✅ Fila {index_borrar} eliminada correctamente.")

        df_usuario["Mes"] = pd.to_datetime(df_usuario["Fecha"]).dt.to_period("M").astype(str)
        meses_disponibles = sorted(df_usuario["Mes"].unique())
        mes_seleccionado = st.selectbox("📅 Selecciona un mes para análisis:", meses_disponibles)

        df_mes = df_usuario[df_usuario["Mes"] == mes_seleccionado]
        ingresos = df_mes[df_mes["Tipo"] == "Ingreso"]["Monto"].sum()
        egresos = df_mes[df_mes["Tipo"] == "Egreso"]["Monto"].sum()
        balance = ingresos - egresos

        st.subheader(f"📊 Resumen de {mes_seleccionado}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Ingresos", f"${ingresos:,.2f}")
        col2.metric("Total Egresos", f"${egresos:,.2f}")
        col3.metric("Balance", f"${balance:,.2f}")

        st.subheader("📈 Visualizaciones")

        df_ingresos = df_usuario[df_usuario["Tipo"] == "Ingreso"]
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

        # 🔮 SECCIÓN NUEVA: Asistente con IA
        st.subheader("🤖 Asistente Financiero con IA")

        objetivo_usuario = st.text_input("¿Cuál es tu objetivo financiero?", "Ahorrar para un viaje")

        colA, colB = st.columns(2)
        if colA.button("🔍 Obtener recomendaciones personalizadas"):
            with st.spinner("Analizando tus datos financieros..."):
                recomendaciones = obtener_recomendacion_financiera(df_usuario, objetivo_usuario)
                st.markdown("### 📌 Recomendaciones")
                st.write(recomendaciones)

        if colB.button("📈 Generar proyección de presupuesto"):
            with st.spinner("Generando proyección..."):
                presupuesto = generar_presupuesto_sugerido(df_usuario)
                st.markdown("### 📅 Presupuesto Sugerido")
                st.write(presupuesto)

    else:
        st.info("No hay movimientos registrados aún.")
else:
    st.warning("👤 Por favor, ingresa tu correo para comenzar.")
