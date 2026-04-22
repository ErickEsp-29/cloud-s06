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
st.title("🏦 Simulador de Crédito - Banco Regional Andino")
st.write("Evaluación basada en scoring crediticio")

# 📌 FORMULARIO adaptado al dataset real
edad = st.number_input("Edad", min_value=18, max_value=100, step=1)
ingreso_mensual = st.number_input("Ingreso mensual", min_value=0.0, step=100.0)

tipo_empleo = st.selectbox(
    "Tipo de empleo",
    ["empleado", "empresario", "freelance"]
)

antiguedad_laboral = st.number_input("Antigüedad laboral (años)", min_value=0, step=1)

score_crediticio = st.number_input("Score crediticio", min_value=0, max_value=1000, step=1)

deudas_actuales = st.number_input("Deudas actuales", min_value=0.0, step=100.0)

ratio_deuda_ingreso = st.number_input("Ratio deuda/ingreso", min_value=0.0, step=0.01)

historial_pagos = st.selectbox(
    "Historial de pagos",
    ["bueno", "regular", "malo"]
)

monto_solicitado = st.number_input("Monto solicitado", min_value=0.0, step=100.0)

plazo_meses = st.number_input("Plazo (meses)", min_value=1, step=1)

tipo_credito = st.selectbox(
    "Tipo de crédito",
    ["consumo", "hipotecario", "vehiculo"]
)

# 🧠 Lógica simple (puedes mejorar luego con ML)
if st.button("Evaluar crédito"):

    if score_crediticio >= 600 and ratio_deuda_ingreso < 0.4 and historial_pagos != "malo":
        preaprobado = True
    else:
        preaprobado = False

    if preaprobado:
        st.success("✅ Crédito preaprobado")
    else:
        st.error("❌ Crédito rechazado")

    # 💾 Guardar en BD
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO ml.credito (
                edad, ingreso_mensual, tipo_empleo, antiguedad_laboral,
                score_crediticio, deudas_actuales, ratio_deuda_ingreso,
                historial_pagos, monto_solicitado, plazo_meses,
                tipo_credito, preaprobado
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
                edad,
                ingreso_mensual,
                tipo_empleo,
                antiguedad_laboral,
                score_crediticio,
                deudas_actuales,
                ratio_deuda_ingreso,
                historial_pagos,
                monto_solicitado,
                plazo_meses,
                tipo_credito,
                preaprobado
            )
        )

        conn.commit()
        cur.close()
        conn.close()

        st.success("📌 Registro guardado")

    except Exception as e:
        st.error(f"Error al guardar: {e}")

# 📋 HISTORIAL
st.subheader("📋 Historial de créditos")

try:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT edad, ingreso_mensual, tipo_empleo,
               score_crediticio, deudas_actuales,
               preaprobado
        FROM ml.credito
        ORDER BY id DESC
        """
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    df = pd.DataFrame(rows, columns=[
        "edad", "ingreso_mensual", "tipo_empleo",
        "score_crediticio", "deudas_actuales",
        "preaprobado"
    ])

    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.warning(f"No se pudieron cargar los datos: {e}")