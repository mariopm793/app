import streamlit as st
import pandas as pd
import datetime
import os
import altair as alt

st.set_page_config(page_title="Registro Ingresos y Egresos", layout="centered")
ARCHIVO_CSV = "movimientos.csv"

st.title("💰 Registro de Ingresos y Egresos")

# Texto de bienvenida / onboarding
st.info(
    """
    **¿Cómo usar esta app?**  
    1. Registra tus ingresos y egresos usando el formulario abajo.  
    2. Usa las opciones para seleccionar el año y mes que quieres analizar.  
    3. Visualiza tus ingresos, egresos, balance y flujo de efectivo.  
    4. Si tienes dudas, escríbenos por WhatsApp o correo (en desarrollo).  
    """
)

# Cargar archivo local si existe
columnas_base = ["fecha", "descripcion", "tipo", "categoria", "monto"]

if os.path.exists(ARCHIVO_CSV):
    df = pd.read_csv(ARCHIVO_CSV)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    # Asegurarse de que todas las columnas existan
    for col in columnas_base:
        if col not in df.columns:
            df[col] = None
else:
    df = pd.DataFrame(columns=columnas_base)

# Subir archivo manualmente
st.sidebar.header("📂 Cargar archivo CSV externo")
archivo_subido = st.sidebar.file_uploader("Sube un archivo CSV", type=["csv"])

if archivo_subido is not None:
    df_nuevo = pd.read_csv(archivo_subido)
    df_nuevo["fecha"] = pd.to_datetime(df_nuevo["fecha"], errors="coerce")
    df = pd.concat([df, df_nuevo], ignore_index=True)
    df.drop_duplicates(inplace=True)
    df.to_csv(ARCHIVO_CSV, index=False)
    st.sidebar.success("✅ Archivo cargado y combinado correctamente.")

# Categorías predefinidas
categorias = ["Ventas", "Insumos", "Renta", "Servicios", "Nómina", "Otros"]

# Formulario de nuevo movimiento
st.header("Registrar nuevo movimiento")

with st.form("form_registro"):
    fecha = st.date_input("Fecha del movimiento", value=datetime.date.today())
    descripcion = st.text_input("Descripción")
    tipo = st.selectbox("Tipo de movimiento", ["ingreso", "egreso"])
    categoria = st.selectbox("Categoría", categorias)
    monto = st.number_input("Monto", min_value=0.01, step=0.01, format="%.2f")
    enviar = st.form_submit_button("Registrar")

    if enviar:
        if descripcion.strip() == "":
            st.error("Por favor ingresa una descripción.")
        else:
            nuevo_movimiento = {
                "fecha": pd.Timestamp(fecha),
                "descripcion": descripcion,
                "tipo": tipo,
                "categoria": categoria,
                "monto": monto
            }
            df = pd.concat([df, pd.DataFrame([nuevo_movimiento])], ignore_index=True)
            df.to_csv(ARCHIVO_CSV, index=False)
            st.success("✅ Movimiento registrado y guardado.")

# Preparar columnas año y mes para filtros y gráficos
if not df.empty:
    df["año"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month

    años_disponibles = sorted(df["año"].dropna().unique())
    if len(años_disponibles) == 0:
        st.warning("No hay datos con fecha válida.")
    else:
        año_seleccionado = st.selectbox("Selecciona año", años_disponibles, index=len(años_disponibles)-1)

        meses_disponibles = sorted(df[df["año"] == año_seleccionado]["mes"].dropna().unique())
        if len(meses_disponibles) == 0:
            st.warning("No hay datos para el año seleccionado.")
        else:
            mes_seleccionado = st.selectbox("Selecciona mes", meses_disponibles, index=len(meses_disponibles)-1)

            # Filtrar por año y mes
            df_filtrado = df[(df["año"] == año_seleccionado) & (df["mes"] == mes_seleccionado)]

            # Opcional: filtrar por categoría
            categorias_disponibles = sorted(df_filtrado["categoria"].unique())
            categoria_filtrada = st.multiselect("Filtrar por categoría (opcional)", categorias_disponibles, default=categorias_disponibles)

            df_filtrado = df_filtrado[df_filtrado["categoria"].isin(categoria_filtrada)]

            # Mostrar totales
            total_ingresos = df_filtrado[df_filtrado["tipo"] == "ingreso"]["monto"].sum()
            total_egresos = df_filtrado[df_filtrado["tipo"] == "egreso"]["monto"].sum()
            balance = total_ingresos - total_egresos

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Ingresos", f"${total_ingresos:,.2f}")
            col2.metric("Total Egresos", f"${total_egresos:,.2f}")
            col3.metric("Balance", f"${balance:,.2f}", delta_color="inverse")

            # -------------------------------
            # NUEVO BLOQUE: Saldos y cashflow
            # -------------------------------

            st.subheader("💵 Flujo de efectivo y comparación con banco")

            # Captura de saldo inicial del mes
            saldo_inicial = st.number_input("Saldo inicial del mes (según tu banco)", min_value=0.0, step=0.01, format="%.2f")

            # Captura de saldo final real del banco
            saldo_banco = st.number_input("Saldo final real del banco (opcional)", min_value=0.0, step=0.01, format="%.2f")

            # Cálculo del saldo final estimado
            saldo_estimado = saldo_inicial + total_ingresos - total_egresos

            # Comparación con banco
            diferencia = saldo_banco - saldo_estimado if saldo_banco else None

            st.metric("💰 Saldo estimado", f"${saldo_estimado:,.2f}")
            if saldo_banco:
                st.metric("🏦 Saldo real banco", f"${saldo_banco:,.2f}", delta=f"${diferencia:,.2f}", delta_color="inverse")

            # Generar cashflow acumulado por día
            df_filtrado = df_filtrado.sort_values("fecha")
            df_filtrado["monto_signed"] = df_filtrado.apply(
                lambda row: row["monto"] if row["tipo"] == "ingreso" else -row["monto"], axis=1)
            df_filtrado["cashflow"] = df_filtrado["monto_signed"].cumsum() + saldo_inicial

            line_chart = alt.Chart(df_filtrado).mark_line(point=True).encode(
                x=alt.X('fecha:T', title='Fecha'),
                y=alt.Y('cashflow:Q', title='Saldo acumulado'),
                tooltip=['fecha', 'cashflow']
            ).properties(
                title="📈 Saldo acumulado durante el mes",
                width=700,
                height=300
            )

            st.altair_chart(line_chart, use_container_width=True)

            # Recomendación automática
            st.subheader("📌 Consejo del mes")
            if balance < 0:
                st.warning("⚠️ Este mes gastaste más de lo que ingresaste. Revisa tus egresos.")
            elif balance > 0:
                st.success("✅ ¡Buen trabajo! Tienes un balance positivo este mes.")
            else:
                st.info("ℹ️ Tus ingresos y egresos están equilibrados.")

            st.subheader("Gráficas")

            # Agregar columna "día" para gráfico de barras por día
            df_filtrado["día"] = df_filtrado["fecha"].dt.day

            # Gráfica: Ingresos vs Egresos por día
            chart_data = df_filtrado.groupby(["día", "tipo"])["monto"].sum().reset_index()

            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('día:O', title='Día del mes'),
                y=alt.Y('monto:Q', title='Monto'),
                color=alt.Color('tipo:N', scale=alt.Scale(domain=['ingreso', 'egreso'],
                                                          range=['#2ca02c', '#d62728'])),
                tooltip=['día', 'tipo', 'monto']
            ).properties(
                width=700,
                height=400,
                title=f"Ingresos vs Egresos - {mes_seleccionado}/{año_seleccionado}"
            )

            st.altair_chart(chart, use_container_width=True)

            # Mostrar historial filtrado
            st.subheader("Historial de movimientos")
            st.dataframe(df_filtrado.sort_values(by="fecha", ascending=False), use_container_width=True)

else:
    st.info("No hay datos cargados todavía.")
