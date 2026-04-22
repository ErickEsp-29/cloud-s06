import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Simulador de Crédito", page_icon="🏦")

# 🔐 Credenciales
USER = st.secrets["DB_USER"]
PASSWORD = st.secrets["DB_PASSWORD"]
HOST = st.secrets["DB_HOST"]
PORT = st.secrets["DB_PORT"]
DBNAME = st.secrets["DB_NAME"]

# 🔌 Conexión
def get_connection():
    return psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
        connect_timeout=5
    )

# UI
st.title("🏦 Banco Regional Andino")
st.subheader("Simulador de Crédito Inteligente")

# 🔎 SOLO DNI como entrada principal
dni = st.text_input("Ingresa tu DNI")

if st.button("Consultar crédito"):

    if not dni:
        st.warning("Ingresa un DNI")
        st.stop()

    try:
        conn = get_connection()
        cur = conn.cursor()

        # 🔍 Buscar cliente por DNI
        cur.execute("""
            SELECT edad, ingreso_mensual, tipo_empleo,
                   antiguedad_laboral, score_crediticio,
                   deudas_actuales, ratio_deuda_ingreso,
                   historial_pagos
            FROM ml.credito
            WHERE dni = %s
            ORDER BY id DESC
            LIMIT 1
        """, (dni,))

        row = cur.fetchone()

        cur.close()
        conn.close()

        if not row:
            st.error("❌ DNI no encontrado en el sistema")
            st.stop()

        # 📊 Datos del cliente
        edad, ingreso, empleo, antiguedad, score, deudas, ratio, historial = row

        st.success("Cliente encontrado")

        # 🧠 Motor de decisión (simplificado pero realista)
        if score >= 600 and ratio < 0.4 and historial != "malo":
            aprobado = True
        else:
            aprobado = False

        if aprobado:
            st.success("✅ Crédito APROBADO")

            st.write("### 💰 Opciones disponibles")

            monto = st.selectbox(
                "Selecciona monto",
                [1000, 3000, 5000, 10000, 20000]
            )

            cuotas = st.selectbox(
                "Número de cuotas",
                [6, 12, 18, 24, 36]
            )

            if st.button("Aceptar crédito"):

                try:
                    conn = get_connection()
                    cur = conn.cursor()

                    cur.execute("""
                        UPDATE ml.credito
                        SET monto_solicitado = %s,
                            plazo_meses = %s,
                            preaprobado = TRUE
                        WHERE dni = %s
                    """, (monto, cuotas, dni))

                    conn.commit()
                    cur.close()
                    conn.close()

                    st.success("🎉 Operación exitosa: crédito desembolsado en cuenta")

                except Exception as e:
                    st.error(f"Error al registrar desembolso: {e}")

        else:
            st.error("❌ Crédito rechazado")

    except Exception as e:
        st.error(f"Error en consulta: {e}")