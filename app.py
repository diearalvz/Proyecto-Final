import streamlit as st
import sqlite3
import pandas as pd
from PIL import Image
import os
import json
import re
import google.generativeai as genai

# ==========================
# CONFIG
# ==========================
st.set_page_config(page_title="FactuTrack", layout="wide")

# ==========================
# CSS con paleta oficial
# ==========================
st.markdown("""
<style>
:root {
    --color-primario: #1E1E2F;
    --color-secundario: #6C63FF;
    --color-acento: #FFD700;
    --color-claro: #F8F9FA;
    --texto-principal: #333333;
    --texto-secundario: #6C757D;
}

body {
    background-color: var(--color-claro);
    color: var(--texto-principal);
    font-family: 'Montserrat', sans-serif;
}

.header {
    display:flex;
    align-items:center;
    margin-bottom:20px;
}

.header img {
    height:60px;
    margin-right:15px;
}

.header h2 {
    color: var(--color-secundario);
    font-weight:700;
    margin:0;
}

.header p {
    color: var(--texto-secundario);
    margin:0;
    font-size:14px;
}

.card {
    border-radius:10px;
    padding:1.2em;
    margin-bottom:1em;
    text-align:center;
    box-shadow:0 2px 8px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

# ==========================
# HEADER CON LOGO
# ==========================
col_logo, col_title = st.columns([1,5])
with col_logo:
    if os.path.exists("logo_factutrack.png"):
        st.image("logo_factutrack.png", use_container_width=False)
    else:
        st.write("📊")  # fallback seguro si no está el logo
with col_title:
    st.markdown("<h2>FactuTrack</h2>", unsafe_allow_html=True)
    st.markdown("<p>Tus gastos, simples y claros</p>", unsafe_allow_html=True)

st.markdown("---")

# ==========================
# LOGIN PERSISTENTE
# ==========================
if "usuario" not in st.session_state:
    st.session_state["usuario"] = ""

if not st.session_state["usuario"]:
    usuario = st.text_input("👤 Ingresa tu nombre")
    if st.button("Ingresar"):
        st.session_state["usuario"] = usuario
    st.stop()

usuario = st.session_state["usuario"]
st.markdown(f"### ¡Hola, {usuario}! 👋 Aquí tienes un resumen simple de tus gastos.")

# ==========================
# API IA
# ==========================
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")
except:
    model = None
    st.warning("⚠️ API no configurada")

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

def obtener_df():
    df = pd.read_sql_query(
        "SELECT entidad, fecha, monto, categoria FROM facturas WHERE usuario=? ORDER BY rowid DESC",
        conn, params=(usuario,)
    )
    if not df.empty:
        df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    return df

df = obtener_df()

# ==========================
# RESUMEN + UPLOAD EN COLUMNAS
# ==========================
col1, col2 = st.columns([1,1])

# SUBIR RECIBO (izquierda)
with col1:
    st.subheader("📤 Subir recibo")
    imagen = st.file_uploader("Selecciona imagen", type=["jpg","png","jpeg"])
    if imagen:
        img = Image.open(imagen)
        st.image(img, width=400)  # compacto
        if st.button("Analizar Factura"):
            if not model:
                st.error("API no disponible")
            else:
                try:
                    prompt = "Devuelve SOLO JSON con: entidad, fecha, monto, categoria"
                    r = model.generate_content([prompt, img])
                    texto = re.sub(r"```json|```","", r.text).strip()
                    data = json.loads(texto)

                    entidad = data.get("entidad","No detectado")
                    fecha = data.get("fecha","No detectado")
                    monto = data.get("monto",0)
                    categoria = data.get("categoria","Otros")

                    # Guardar en DB
                    c.execute("INSERT INTO facturas (usuario, entidad, fecha, monto, categoria) VALUES (?,?,?,?,?)",
                              (usuario, entidad, fecha, monto, categoria))
                    conn.commit()

                    st.success(f"✅ Factura registrada: {entidad} — {fecha} — ${monto:,.0f} — {categoria}")
                except Exception:
                    st.warning("⚠️ Error al analizar la factura. Intenta de nuevo.")

# RESUMEN + HISTORIAL (derecha)
with col2:
    st.subheader("📊 Resumen mensual")
    total = df["monto"].sum() if not df.empty else 0
    cantidad = len(df)
    categoria_principal = df.groupby("categoria")["monto"].sum().idxmax() if not df.empty else "—"

    colA, colB, colC = st.columns(3)
    colA.markdown(f"<div class='card' style='background-color:var(--color-secundario);color:white;'><h4>💰 Total</h4><h2>${total:,.0f}</h2></div>", unsafe_allow_html=True)
    colB.markdown(f"<div class='card' style='background-color:var(--color-secundario);color:white;'><h4>📄 Facturas</h4><h2>{cantidad}</h2></div>", unsafe_allow_html=True)
    colC.markdown(f"<div class='card' style='background-color:var(--color-secundario);color:white;'><h4>📊 Categoría</h4><h2>{categoria_principal}</h2></div>", unsafe_allow_html=True)

    st.subheader("🕓 Mis facturas recientes")
    df = obtener_df()  # refrescar después de inserción
    if not df.empty:
        st.dataframe(df.head(5))
    else:
        st.info("Sin registros aún")
