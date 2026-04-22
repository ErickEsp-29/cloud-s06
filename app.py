import streamlit as st
import psycopg2
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Simulador de Crédito", page_icon="🏦", layout="wide")

# ─── Tasas por plazo ──────────────────────────────────────────────────────────
TASAS_POR_CUOTAS = {
    6:  15.50,
    12: 18.02,
    18: 20.50,
    24: 22.80,
    36: 26.40,
}

# ─── Score: rangos y etiquetas ────────────────────────────────────────────────
def score_info(score: int) -> dict:
    if score < 400:
        return {"label": "Muy bajo", "color": "#e74c3c", "emoji": "🔴"}
    elif score < 550:
        return {"label": "Bajo", "color": "#e67e22", "emoji": "🟠"}
    elif score < 650:
        return {"label": "Regular", "color": "#f1c40f", "emoji": "🟡"}
    elif score < 750:
        return {"label": "Bueno", "color": "#2ecc71", "emoji": "🟢"}
    else:
        return {"label": "Excelente", "color": "#1abc9c", "emoji": "⭐"}

def gauge_score(score: int) -> go.Figure:
    info = score_info(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        number={"font": {"size": 48, "color": info["color"], "family": "Georgia"}},
        delta={"reference": 600, "increasing": {"color": "#2ecc71"}, "decreasing": {"color": "#e74c3c"}},
        gauge={
            "axis": {
                "range": [300, 900],
                "tickwidth": 2,
                "tickcolor": "#555",
                "tickvals": [300, 400, 550, 650, 750, 900],
                "ticktext": ["300", "400\nMuy bajo", "550\nBajo", "650\nRegular", "750\nBueno", "900\nExcelente"],
                "tickfont": {"size": 11},
            },
            "bar": {"color": info["color"], "thickness": 0.25},
            "bgcolor": "#f8f9fa",
            "borderwidth": 2,
            "bordercolor": "#dee2e6",
            "steps": [
                {"range": [300, 400], "color": "#fdecea"},
                {"range": [400, 550], "color": "#fef3e2"},
                {"range": [550, 650], "color": "#fefce8"},
                {"range": [650, 750], "color": "#eafaf1"},
                {"range": [750, 900], "color": "#d5f5ef"},
            ],
            "threshold": {
                "line": {"color": "#2c3e50", "width": 3},
                "thickness": 0.8,
                "value": 600,
            },
        },
        title={
            "text": f"Tu Score Crediticio<br><span style='font-size:16px;color:{info['color']}'>{info['emoji']} {info['label']}</span>",
            "font": {"size": 20, "family": "Georgia"},
        },
    ))
    fig.update_layout(
        height=320,
        margin={"t": 80, "b": 20, "l": 40, "r": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"family": "Georgia"},
    )
    return fig

# ─── Conexión BD ──────────────────────────────────────────────────────────────
def get_connection():
    return psycopg2.connect(
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        host=st.secrets["DB_HOST"],
        port=st.secrets["DB_PORT"],
        dbname=st.secrets["DB_NAME"],
        connect_timeout=5,
    )

# ─── Cálculo financiero ───────────────────────────────────────────────────────
def calcular_cuota(monto: float, tea: float, n: int) -> dict:
    tem = (1 + tea / 100) ** (1 / 12) - 1
    cuota = monto * (tem * (1 + tem) ** n) / ((1 + tem) ** n - 1)
    total = cuota * n
    return {"tem": tem * 100, "cuota": cuota, "total": total, "intereses": total - monto}

def tabla_amortizacion(monto: float, tea: float, n: int) -> pd.DataFrame:
    tem = (1 + tea / 100) ** (1 / 12) - 1
    cuota = monto * (tem * (1 + tem) ** n) / ((1 + tem) ** n - 1)
    rows, saldo = [], monto
    for i in range(1, n + 1):
        interes = saldo * tem
        amort = cuota - interes
        saldo -= amort
        rows.append({"Cuota N°": i, "Pago mensual (S/)": round(cuota, 2),
                     "Interés (S/)": round(interes, 2), "Amortización (S/)": round(amort, 2),
                     "Saldo restante (S/)": round(max(saldo, 0), 2)})
    return pd.DataFrame(rows)

# ─── CSS personalizado ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .score-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        border-radius: 16px;
        padding: 24px;
        color: white;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .tc-box {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 10px;
        padding: 20px;
        max-height: 220px;
        overflow-y: auto;
        font-size: 13px;
        line-height: 1.7;
        color: #444;
        margin-bottom: 12px;
    }
    .tc-box h4 { color: #2c3e50; margin-top: 12px; }
    .stMetric { background: #f0f4ff; border-radius: 10px; padding: 12px; }
</style>
""", unsafe_allow_html=True)

# ─── UI Principal ─────────────────────────────────────────────────────────────
st.title("🏦 Banco Regional Andino")
st.subheader("Simulador de Crédito Inteligente")

# Estado de sesión
for key, val in [("cliente", None), ("aprobado", False), ("tc_aceptado", False)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Buscar cliente ─────────────────────────────────────────────────────────────
dni = st.text_input("Ingresa tu DNI")

if st.button("Consultar crédito"):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT edad, ingreso_mensual, tipo_empleo,
                   antiguedad_laboral, score_crediticio,
                   deudas_actuales, ratio_deuda_ingreso, historial_pagos
            FROM ml.credito WHERE dni = %s LIMIT 1
        """, (dni,))
        row = cur.fetchone()
        cur.close(); conn.close()

        if row:
            st.session_state.cliente = row
            _, _, _, _, score, _, ratio, historial = row
            st.session_state.aprobado = (score >= 600 and ratio < 0.4 and historial != "malo")
            st.session_state.tc_aceptado = False   # reset al consultar nuevo DNI
        else:
            st.session_state.cliente = None
            st.error("❌ DNI no encontrado")
    except Exception as e:
        st.error(f"Error de conexión: {e}")

# ── Mostrar resultado ──────────────────────────────────────────────────────────
if st.session_state.cliente:

    # ── Botón regresar ─────────────────────────────────────────────────────
    if st.button("← Consultar otro cliente"):
        st.session_state.cliente = None
        st.session_state.aprobado = False
        st.session_state.tc_aceptado = False
        st.rerun()

    edad, ingreso, empleo, antiguedad, score, deudas, ratio, historial = st.session_state.cliente
    info = score_info(score)

    st.success("✅ Cliente encontrado")
    st.markdown("---")

    # ── SCORE GAUGE ────────────────────────────────────────────────────────────
    col_gauge, col_datos = st.columns([1.2, 1])

    with col_gauge:
        st.plotly_chart(gauge_score(score), use_container_width=True, config={"displayModeBar": False})
        st.markdown(
            f"""<div style='text-align:center; padding: 8px 0;'>
                <span style='font-size:15px; color:#555;'>Rango mínimo para aprobación: </span>
                <strong style='color:#2c3e50;'>600 puntos</strong>
            </div>""",
            unsafe_allow_html=True
        )

    with col_datos:
        st.markdown("#### 📋 Perfil del cliente")
        st.markdown(f"""
        | Campo | Valor |
        |---|---|
        | Edad | {edad} años |
        | Ingreso mensual | S/ {ingreso:,.2f} |
        | Tipo de empleo | {empleo} |
        | Antigüedad laboral | {antiguedad} meses |
        | Deudas actuales | S/ {deudas:,.2f} |
        | Ratio deuda/ingreso | {ratio:.2%} |
        | Historial de pagos | {historial.capitalize()} |
        """)

        # Leyenda de scores
        st.markdown("#### 📊 Escala de puntajes")
        for rango, etq, col, bg in [
            ("750 – 900", "Excelente ⭐ — Score ideal, acceso a los mejores productos y tasas.", "#1abc9c", "#eafaf1"),
            ("650 – 749", "Bueno 🟢 — Buen perfil, crédito aprobado con condiciones estándar.", "#2ecc71", "#eafaf1"),
            ("550 – 649", "Regular 🟡 — Perfil medio, puede requerir garantías adicionales.", "#f1c40f", "#fefce8"),
            ("400 – 549", "Bajo 🟠 — Alto riesgo, crédito generalmente restringido.", "#e67e22", "#fef3e2"),
            ("300 – 399", "Muy bajo 🔴 — Crédito no disponible, historial crítico.", "#e74c3c", "#fdecea"),
        ]:
            st.markdown(
                f"<div style='background:{bg}; border-left:4px solid {col}; "
                f"padding:6px 12px; border-radius:4px; margin:4px 0; font-size:13px; color:#222;'>"
                f"<strong>{rango}</strong> — {etq}</div>",
                unsafe_allow_html=True
            )

    st.markdown("---")

    # ── RESULTADO DE CRÉDITO ───────────────────────────────────────────────────
    if st.session_state.aprobado:
        st.success("✅ Crédito APROBADO")

        st.markdown("### 📊 Simulador de Cuotas")
        col1, col2 = st.columns(2)

        with col1:
            monto = st.selectbox("💵 Monto solicitado (S/)", [1000, 3000, 5000, 10000, 20000], key="monto")
        with col2:
            cuotas = st.selectbox("📅 Número de cuotas (meses)", list(TASAS_POR_CUOTAS.keys()), index=1, key="cuotas")

        tea = TASAS_POR_CUOTAS[cuotas]
        res = calcular_cuota(monto, tea, cuotas)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TEA aplicada", f"{tea:.2f}%")
        m2.metric("TEM", f"{res['tem']:.4f}%")
        m3.metric("Cuota mensual", f"S/ {res['cuota']:,.2f}")
        m4.metric("Total a pagar", f"S/ {res['total']:,.2f}")

        st.info(f"💰 Pagarás **S/ {res['intereses']:,.2f}** en intereses sobre un préstamo de **S/ {monto:,}** en **{cuotas} meses** a TEA **{tea}%**.")

        with st.expander("📋 Ver comparativa de tasas"):
            filas = []
            for n, t in TASAS_POR_CUOTAS.items():
                r = calcular_cuota(monto, t, n)
                filas.append({"Plazo (meses)": n, "TEA (%)": f"{t:.2f}%", "TEM (%)": f"{r['tem']:.4f}%",
                               "Cuota mensual (S/)": f"S/ {r['cuota']:,.2f}",
                               "Total intereses (S/)": f"S/ {r['intereses']:,.2f}",
                               "Total a pagar (S/)": f"S/ {r['total']:,.2f}"})
            st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)

        with st.expander("📅 Ver tabla de amortización mes a mes"):
            st.dataframe(tabla_amortizacion(monto, tea, cuotas), hide_index=True, use_container_width=True)

        # ── TÉRMINOS Y CONDICIONES ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📄 Términos y Condiciones")

        st.markdown("""
        <div class="tc-box">
            <strong>CONTRATO DE CRÉDITO PERSONAL — BANCO REGIONAL ANDINO</strong><br><br>

            <h4>1. Partes del contrato</h4>
            El presente contrato se celebra entre <strong>Banco Regional Andino S.A.</strong>
            (en adelante "el Banco") y el cliente identificado mediante DNI ingresado en el sistema
            (en adelante "el Prestatario").

            <h4>2. Condiciones del crédito</h4>
            El Banco otorgará al Prestatario el monto seleccionado bajo las condiciones de tasa,
            plazo y cuotas presentadas en el simulador. La Tasa Efectiva Anual (TEA) varía según
            el plazo elegido y es fija durante toda la vida del crédito.

            <h4>3. Pago de cuotas</h4>
            El Prestatario se compromete a pagar puntualmente cada cuota mensual en la fecha
            acordada. El incumplimiento de pago generará intereses moratorios del 2% mensual
            adicional sobre el saldo vencido.

            <h4>4. Prepago</h4>
            El Prestatario podrá realizar pagos adelantados parciales o totales en cualquier
            momento sin penalidad adicional, previa comunicación al Banco con 5 días hábiles
            de anticipación.

            <h4>5. Seguros obligatorios</h4>
            El crédito incluye un seguro de desgravamen equivalente al 0.05% mensual sobre
            el saldo deudor, deducido automáticamente de cada cuota.

            <h4>6. Central de riesgos</h4>
            El Prestatario autoriza al Banco a reportar el comportamiento de pago ante la
            Superintendencia de Banca, Seguros y AFP (SBS) y centrales de riesgo privadas.

            <h4>7. Protección de datos</h4>
            Los datos personales serán tratados conforme a la Ley N° 29733 — Ley de Protección
            de Datos Personales del Perú. El Prestatario autoriza su uso exclusivamente para
            fines relacionados con este crédito.

            <h4>8. Jurisdicción</h4>
            Cualquier controversia será sometida a los jueces y tribunales de Lima Metropolitana,
            renunciando el Prestatario a cualquier otro fuero que pudiera corresponderle.
        </div>
        """, unsafe_allow_html=True)

        # Checkbox de aceptación
        acepta = st.checkbox(
            "✅ He leído y acepto los Términos y Condiciones del crédito",
            value=st.session_state.tc_aceptado,
            key="tc_check"
        )
        st.session_state.tc_aceptado = acepta

        if not acepta:
            st.warning("⚠️ Debes aceptar los Términos y Condiciones para continuar.")

        st.markdown("---")

        # ── BOTÓN ACEPTAR CRÉDITO (bloqueado si no acepta T&C) ────────────────
        btn_disabled = not st.session_state.tc_aceptado

        if btn_disabled:
            st.button("🔒 Aceptar crédito", disabled=True, help="Acepta los Términos y Condiciones primero")
        else:
            if st.button("✅ Aceptar crédito", type="primary"):
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
                    cur.close(); conn.close()
                    st.success("🎉 ¡Crédito desembolsado correctamente!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error: {e}")

    else:
        st.error("❌ Crédito rechazado")
        st.markdown(f"""
        > Tu score actual es **{score} puntos** ({info['emoji']} {info['label']}).
        > Para ser elegible necesitas un mínimo de **600 puntos** y un ratio deuda/ingreso menor a **40%**.
        """)