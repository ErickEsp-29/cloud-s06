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

def get_connection():
    return psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
        connect_timeout=5
    )

st.title("🏦 Banco Regional Andino")
st.subheader("Simulador de Crédito Inteligente")

# 🧠 Inicializar estado
if "cliente" not in st.session_state:
    st.session_state.cliente = None

if "aprobado" not in st.session_state:
    st.session_state.aprobado = False


# 🔎 BUSCAR CLIENTE
dni = st.text_input("Ingresa tu DNI")

if st.button("Consultar crédito"):

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT edad, ingreso_mensual, tipo_empleo,
                   antiguedad_laboral, score_crediticio,
                   deudas_actuales, ratio_deuda_ingreso,
                   historial_pagos
            FROM ml.credito
            WHERE dni = %s
            LIMIT 1
        """, (dni,))

        row = cur.fetchone()

        cur.close()
        conn.close()

        if row:
            st.session_state.cliente = row

            edad, ingreso, empleo, antiguedad, score, deudas, ratio, historial = row

            # 🧠 decisión
            if score >= 600 and ratio < 0.4 and historial != "malo":
                st.session_state.aprobado = True
            else:
                st.session_state.aprobado = False

        else:
            st.session_state.cliente = None
            st.error("❌ DNI no encontrado")

    except Exception as e:
        st.error(f"Error: {e}")


# 📌 MOSTRAR CLIENTE SI EXISTE
if st.session_state.cliente:

    edad, ingreso, empleo, antiguedad, score, deudas, ratio, historial = st.session_state.cliente

    st.success("Cliente encontrado")

    if st.session_state.aprobado:
        st.success("✅ Crédito APROBADO")

        monto = st.selectbox(
            "Selecciona monto",
            [1000, 3000, 5000, 10000, 20000],
            key="monto"
        )

        cuotas = st.selectbox(
            "Número de cuotas",
            [6, 12, 18, 24, 36],
            key="cuotas"
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

                st.success("🎉 Crédito desembolsado correctamente")

            except Exception as e:
                st.error(f"Error: {e}")

    else:
        st.error("❌ Crédito rechazado")