import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import sqlite3
import json
import re
from datetime import datetime
import plotly.express as px

# ==========================
# CONFIGURACIÓN GENERAL
# ==========================
st.set_page_config(page_title="FactuTrack", layout="wide")

# ==========================
# ESTILO PREMIUM
# ==========================
st.markdown("""
<style>
body {
    background-color: #0E0E10;
    color: #E5E5E5;
    font-family: 'Segoe UI', sans-serif;
}

header, .css-18e3th9, .css-1d391kg {
    background-color: #0E0E10 !important;
}

.titulo {
    text-align:center;
    font-size:2.4em;
    font-weight:bold;
    color:#D4AF37;
    margin-bottom:5px;
}

.sub {
    text-align:center;
    color:#A0A0A0;
    margin-bottom:30px;
}

.card {
    background:#1A1A1D;
    padding:1em;
    border-radius:12px;
    box-shadow:0 2px 8px rgba(212,175,55,0.2);
    margin-bottom:10px;
}

.total {
    text-align:center;
    font-size:1.8em;
    font-weight:bold;
    color:#D4AF37;
    margin:20px 0;
}

.stButton>button {
    background:#D4AF37;
    color:#0E0E10;
    border-radius:10px;
    width:100%;
    padding:0.6em;
    font-weight:bold;
}

.stRadio>div {
    justify-content:center;
}

input, select, textarea {
    background-color:#1A1A1D !important;
    color:#E5E5E5 !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================
# HEADER
# ==========================
st.markdown('<div class="titulo">📊 FactuTrack</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Controla tus gastos de manera inteligente</div>', unsafe_allow_html=True)

# ==========================
# API GEMINI
# ==========================
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("gemini-1.5-flash")

# ==========================
# BASE DE DATOS
# ==========================
conn = sqlite3.connect("facturas.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS facturas (
id INTEGER PRIMARY KEY AUTOINCREMENT,
usuario TEXT,
entidad TEXT,
fecha TEXT,
monto REAL,
categoria TEXT
)
""")
conn.commit()

# ==========================
# LOGIN
# ==========================
usuario = st.text_input("👤 Ingresa tu nombre o correo")
if not usuario:
    st.stop()

# ==========================
# FUNCIONES
# ==========================
def limpiar_monto(valor):
    try:
        return float(str(valor).replace(",", "").replace("$",""))
    except:
        return 0.0

def limpiar_fecha(fecha):
    return str(fecha).replace("/", "-")

def obtener_df():
    return pd.read_sql_query(
        "SELECT * FROM facturas WHERE usuario=? ORDER BY id DESC",
        conn, params=(usuario,)
    )

def guardar(entidad, fecha, monto, categoria):
    c.execute("""
    INSERT INTO facturas (usuario, entidad, fecha, monto, categoria)
    VALUES (?,?,?,?,?)
    """,(usuario, entidad, fecha, monto, categoria))
    conn.commit()

# ==========================
# SECCIÓN: AGREGAR FACTURA
# ==========================
st.markdown("### 📸 Agregar Nueva Factura")
col1, col2 = st.columns([1,1])

with col1:
    opcion = st.radio("", ["📁 Subir Imagen", "📸 Tomar Foto"], horizontal=True)
    imagen = None
    if opcion == "📁 Subir Imagen":
        file = st.file_uploader("Selecciona tu recibo", type=["png","jpg","jpeg"])
        if file:
            imagen = Image.open(file)
            st.image(imagen, width=250)
    else:
        foto = st.camera_input("Toma una foto")
        if foto:
            imagen = Image.open(foto)
            st.image(imagen, width=250)

with col2:
    st.markdown("#### 🧠 Datos Detectados")
    entidad = st.text_input("Entidad")
    fecha = st.text_input("Fecha (YYYY-MM-DD)")
    monto = st.text_input("Monto")
    categoria = st.text_input("Categoría")

    if imagen and st.button("Analizar y Guardar"):
        with st.spinner("Analizando factura..."):
            prompt = """
            Devuelve SOLO JSON válido:
            {
            "entidad":"",
            "fecha":"YYYY-MM-DD",
            "monto":"",
            "categoria":""
            }
            """
            try:
                r = model.generate_content([prompt, imagen])
                texto = re.sub(r"```json|```","", r.text).strip()
                data = json.loads(texto)

                entidad = data.get("entidad","No detectado")
                fecha = limpiar_fecha(data.get("fecha"))
                monto = limpiar_monto(data.get("monto"))
                categoria = data.get("categoria","otros")

                guardar(entidad, fecha, monto, categoria)
                st.success("✅ Factura guardada correctamente")
            except:
                st.error("❌ No se pudo analizar la factura")

# ==========================
# SECCIÓN: RESUMEN
# ==========================
st.markdown("### 📊 Resumen de Gastos")
df = obtener_df()

if not df.empty:
    total = df["monto"].sum()
    st.markdown(f'<div class="total">💰 Total: ${total:,.0f}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2,1])
    with col1:
        st.dataframe(df[["entidad","fecha","categoria","monto"]], use_container_width=True)
    with col2:
        fig = px.pie(df, names="categoria", values="monto", title="Gastos por Categoría",
                     color_discrete_sequence=px.colors.sequential.Gold)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 📤 Exportar o Ver Reporte Completo")
    st.button("Exportar")
    st.button("Ver Reporte Completo")
else:
    st.info("Aún no tienes facturas registradas.")
