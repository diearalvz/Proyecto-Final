import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import sqlite3
import json
import re

# ==========================
# CONFIG
# ==========================
st.set_page_config(page_title="FactuTrack", layout="wide")

# ==========================
# CSS
# ==========================
def cargar_css():
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass

cargar_css()

# ==========================
# HEADER
# ==========================
st.markdown("""
<div class="header">
    <h2>📊 FactuTrack</h2>
    <div>👤 Usuario</div>
</div>
""", unsafe_allow_html=True)

# ==========================
# API GEMINI
# ==========================
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")
except:
    st.error("⚠️ Configura tu API KEY en secrets")
    st.stop()

# ==========================
# DB
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
usuario = st.text_input("👤 Ingresa tu usuario")

if not usuario:
    st.stop()

# ==========================
# FUNCIONES
# ==========================
def obtener_df():
    return pd.read_sql_query(
        "SELECT id, entidad, fecha, monto, categoria FROM facturas WHERE usuario=? ORDER BY id DESC",
        conn, params=(usuario,)
    )

def guardar(entidad, fecha, monto, categoria):
    c.execute("""
    INSERT INTO facturas (usuario, entidad, fecha, monto, categoria)
    VALUES (?,?,?,?,?)
    """,(usuario, entidad, fecha, monto, categoria))
    conn.commit()

# ==========================
# DATOS
# ==========================
df = obtener_df()

total = float(df["monto"].sum()) if not df.empty else 0.0
cantidad = len(df)

# ==========================
# KPIs (CORREGIDO)
# ==========================
col1, col2 = st.columns(2)

with col1:
    st.markdown(f"""
    <div class="card">
        <h4>💰 Gasto Total</h4>
        <h2>${total:,.0f}</h2>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="card">
        <h4>📄 Facturas</h4>
        <h2>{cantidad}</h2>
    </div>
    """, unsafe_allow_html=True)

# ==========================
# SUBIDA + RESULTADO
# ==========================
col1, col2 = st.columns(2)

imagen = None

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)

    opcion = st.radio("Método", ["Subir imagen", "Tomar foto"])

    if opcion == "Subir imagen":
        file = st.file_uploader("Selecciona imagen", type=["jpg","png","jpeg"])
        if file:
            imagen = Image.open(file)
            st.image(imagen, use_container_width=True)

    else:
        foto = st.camera_input("Tomar foto")
        if foto:
            imagen = Image.open(foto)
            st.image(imagen, use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

# VARIABLES SEGURAS
entidad = "—"
fecha = "—"
monto = 0
categoria = "—"

with col2:

    if imagen and st.button("Analizar y Guardar"):

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
            texto = re.sub(r"```json|```", "", r.text).strip()
            data = json.loads(texto)

            entidad = data.get("entidad","No detectado")
            fecha = data.get("fecha","")
            monto = float(str(data.get("monto","0")).replace(",","."))
            categoria = data.get("categoria","otros")

            guardar(entidad, fecha, monto, categoria)

            st.success("✅ Factura guardada")

        except Exception as e:
            st.error("❌ Error leyendo factura")

    st.markdown(f"""
    <div class="card">
        <h4>📄 Datos detectados</h4>
        <p><b>Entidad:</b> {entidad}</p>
        <p><b>Fecha:</b> {fecha}</p>
        <p><b>Monto:</b> ${monto:,.0f}</p>
        <p><b>Categoría:</b> {categoria}</p>
    </div>
    """, unsafe_allow_html=True)

# ==========================
# HISTORIAL + GRAFICA
# ==========================
col1, col2 = st.columns(2)

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("📄 Historial")

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay datos aún")

    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.write("📊 Gastos por categoría")

    if not df.empty:
        graf = df.groupby("categoria")["monto"].sum()
        st.bar_chart(graf)

    st.markdown('</div>', unsafe_allow_html=True)
