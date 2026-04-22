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

# 💰 Tasas de interés por plazo (TEA - Tasa Efectiva Anual)
# Base: 18.02% a 12 meses, escala proporcional
TASAS_POR_CUOTAS = {
    6:  15.50,   # Menos cuotas → menor riesgo → menor tasa
    12: 18.02,   # Tasa base
    18: 20.50,
    24: 22.80,
    36: 26.40,   # Más cuotas → mayor riesgo → mayor tasa
}

def get_connection():
    return psycopg2.connect(
        user=USER,
        password=PASSWORD,
        host=HOST,
        port=PORT,
        dbname=DBNAME,
        connect_timeout=5
    )

def calcular_cuota_mensual(monto: float, tea: float, n_cuotas: int) -> dict:
    """
    Calcula la cuota mensual usando el método francés (sistema de amortización).
    Convierte TEA → TEM (Tasa Efectiva Mensual).
    """
    # TEA → TEM
    tem = (1 + tea / 100) ** (1 / 12) - 1

    # Fórmula de cuota fija (sistema francés)
    if tem == 0:
        cuota = monto / n_cuotas
    else:
        cuota = monto * (tem * (1 + tem) ** n_cuotas) / ((1 + tem) ** n_cuotas - 1)

    total_pagar = cuota * n_cuotas
    total_intereses = total_pagar - monto

    return {
        "tem": tem * 100,
        "cuota_mensual": cuota,
        "total_pagar": total_pagar,
        "total_intereses": total_intereses,
    }

def generar_tabla_amortizacion(monto: float, tea: float, n_cuotas: int) -> pd.DataFrame:
    """Genera la tabla de amortización mes a mes."""
    tem = (1 + tea / 100) ** (1 / 12) - 1
    cuota = monto * (tem * (1 + tem) ** n_cuotas) / ((1 + tem) ** n_cuotas - 1)

    rows = []
    saldo = monto
    for i in range(1, n_cuotas + 1):
        interes = saldo * tem
        amortizacion = cuota - interes
        saldo -= amortizacion
        rows.append({
            "Cuota N°": i,
            "Pago mensual (S/)": round(cuota, 2),
            "Interés (S/)": round(interes, 2),
            "Amortización (S/)": round(amortizacion, 2),
            "Saldo restante (S/)": round(max(saldo, 0), 2),
        })

    return pd.DataFrame(rows)


# ─── UI ───────────────────────────────────────────────────────────────────────

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
            _, _, _, _, score, _, ratio, historial = row
            st.session_state.aprobado = (score >= 600 and ratio < 0.4 and historial != "malo")
        else:
            st.session_state.cliente = None
            st.error("❌ DNI no encontrado")

    except Exception as e:
        st.error(f"Error: {e}")


# 📌 MOSTRAR CLIENTE SI EXISTE
if st.session_state.cliente:
    edad, ingreso, empleo, antiguedad, score, deudas, ratio, historial = st.session_state.cliente
    st.success("✅ Cliente encontrado")

    if st.session_state.aprobado:
        st.success("✅ Crédito APROBADO")

        st.markdown("---")
        st.markdown("### 📊 Simulador de Cuotas")

        col1, col2 = st.columns(2)

        with col1:
            monto = st.selectbox(
                "💵 Monto solicitado (S/)",
                [1000, 3000, 5000, 10000, 20000],
                key="monto"
            )

        with col2:
            cuotas = st.selectbox(
                "📅 Número de cuotas (meses)",
                list(TASAS_POR_CUOTAS.keys()),
                index=1,   # Default: 12 meses
                key="cuotas"
            )

        # ── Calcular y mostrar resultados ──────────────────────────────────
        tea_aplicada = TASAS_POR_CUOTAS[cuotas]
        resultado = calcular_cuota_mensual(monto, tea_aplicada, cuotas)

        st.markdown("---")
        st.markdown("#### 💡 Resumen de tu crédito")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TEA aplicada", f"{tea_aplicada:.2f}%")
        m2.metric("TEM", f"{resultado['tem']:.4f}%")
        m3.metric("Cuota mensual", f"S/ {resultado['cuota_mensual']:,.2f}")
        m4.metric("Total a pagar", f"S/ {resultado['total_pagar']:,.2f}")

        st.info(
            f"💰 Pagarás **S/ {resultado['total_intereses']:,.2f}** en intereses "
            f"sobre un préstamo de **S/ {monto:,}** en **{cuotas} meses** "
            f"a una TEA de **{tea_aplicada}%**."
        )

        # ── Tabla comparativa de tasas ─────────────────────────────────────
        with st.expander("📋 Ver comparativa de tasas y cuotas"):
            filas = []
            for n, tasa in TASAS_POR_CUOTAS.items():
                r = calcular_cuota_mensual(monto, tasa, n)
                filas.append({
                    "Plazo (meses)": n,
                    "TEA (%)": f"{tasa:.2f}%",
                    "TEM (%)": f"{r['tem']:.4f}%",
                    "Cuota mensual (S/)": f"S/ {r['cuota_mensual']:,.2f}",
                    "Total intereses (S/)": f"S/ {r['total_intereses']:,.2f}",
                    "Total a pagar (S/)": f"S/ {r['total_pagar']:,.2f}",
                })
            df_comp = pd.DataFrame(filas)
            # Resaltar la fila seleccionada
            st.dataframe(
                df_comp.style.apply(
                    lambda row: ["background-color: #d4edda" if row["Plazo (meses)"] == cuotas else "" for _ in row],
                    axis=1
                ),
                hide_index=True,
                use_container_width=True
            )

        # ── Tabla de amortización ──────────────────────────────────────────
        with st.expander("📅 Ver tabla de amortización mes a mes"):
            df_amor = generar_tabla_amortizacion(monto, tea_aplicada, cuotas)
            st.dataframe(df_amor, hide_index=True, use_container_width=True)

        # ── Botón aceptar ──────────────────────────────────────────────────
        st.markdown("---")
        if st.button("✅ Aceptar crédito"):
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
                st.success("🎉 ¡Crédito desembolsado correctamente!")
                st.balloons()

            except Exception as e:
                st.error(f"Error: {e}")

    else:
        st.error("❌ Crédito rechazado")