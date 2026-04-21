import streamlit as st
import psycopg
import pandas as pd

st.set_page_config(page_title="Simulador de Crédito", page_icon="🏦")

# 🔐 Credenciales
DB_HOST = st.secrets["DB_HOST"]
DB_PORT = st.secrets["DB_PORT"]
DB_NAME = st.secrets["DB_NAME"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]

def get_connection():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode="require"
    )

# UI
st.title("🏦 Simulador de Crédito - Banco Regional Andino")
st.write("Obtén una pre-aprobación en minutos")

# Formulario
nombre = st.text_input("Nombre")
edad = st.number_input("Edad", min_value=18, max_value=100, step=1)
ingresos = st.number_input("Ingresos mensuales", min_value=0.0, step=100.0)
deudas = st.number_input("Deudas actuales", min_value=0.0, step=100.0)

if st.button("Evaluar crédito"):
    if not nombre.strip():
        st.warning("Por favor ingresa tu nombre")
        st.stop()

    # Lógica
    if ingresos > 2000 and deudas < 0.3 * ingresos:
        resultado = "Aprobado"
    else:
        resultado = "Rechazado"

    if resultado == "Aprobado":
        st.success("✅ Crédito pre-aprobado")
    else:
        st.error("❌ Requiere evaluación adicional")

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO solicitudes_credito (nombre, edad, ingresos, deudas, resultado)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (nombre, edad, ingresos, deudas, resultado)
                )
        st.success("📌 Solicitud guardada")

    except Exception as e:
        st.error(f"Error: {e}")

# Historial
st.subheader("📋 Historial de solicitudes")

try:
    with get_connection() as conn:
        df = pd.read_sql(
            """
            SELECT nombre, edad, ingresos, deudas, resultado
            FROM solicitudes_credito
            ORDER BY id DESC
            """,
            conn
        )

    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.warning(f"No se pudieron cargar los datos: {e}")