import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Simulador de Crédito", page_icon="🏦")

# 🔐 Credenciales (mejor usar st.secrets en producción)
USER = st.secrets["DB_USER"]          # ejemplo: postgres.xxxxx
PASSWORD = st.secrets["DB_PASSWORD"]
HOST = st.secrets["DB_HOST"]          # aws-1-us-east-1.pooler.supabase.com
PORT = st.secrets["DB_PORT"]          # 6543
DBNAME = st.secrets["DB_NAME"]        # postgres

# 🔌 Conexión (estilo profe - pooler)
def get_connection():
    return psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
        connect_timeout=5  # 👈 evita que se quede cargando infinito
    )

# UI
st.title("🏦 Simulador de Crédito - Banco Regional Andino")
st.write("Obtén una pre-aprobación en minutos")

# Formulario
nombre = st.text_input("Nombre")
edad = st.number_input("Edad", min_value=18, max_value=100, step=1)
ingresos = st.number_input("Ingresos mensuales", min_value=0.0, step=100.0)
deudas = st.number_input("Deudas actuales", min_value=0.0, step=100.0)

# Botón
if st.button("Evaluar crédito"):
    if not nombre.strip():
        st.warning("Por favor ingresa tu nombre")
        st.stop()

    # Lógica simple
    if ingresos > 2000 and deudas < 0.3 * ingresos:
        resultado = "Aprobado"
    else:
        resultado = "Rechazado"

    if resultado == "Aprobado":
        st.success("✅ Crédito pre-aprobado")
    else:
        st.error("❌ Requiere evaluación adicional")

    # Guardar en BD
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO solicitudes_credito (nombre, edad, ingresos, deudas, resultado)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (nombre, edad, ingresos, deudas, resultado)
        )

        conn.commit()
        cur.close()
        conn.close()

        st.success("📌 Solicitud guardada")

    except Exception as e:
        st.error(f"Error al guardar: {e}")

# Historial
st.subheader("📋 Historial de solicitudes")

try:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT nombre, edad, ingresos, deudas, resultado
        FROM solicitudes_credito
        ORDER BY id DESC
        """
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    df = pd.DataFrame(rows, columns=["nombre", "edad", "ingresos", "deudas", "resultado"])

    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.warning(f"No se pudieron cargar los datos: {e}")