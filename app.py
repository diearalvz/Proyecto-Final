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
# CARGAR CSS EXTERNO
# ==========================
if os.path.exists("style.css"):
    with open("style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ==========================
# HEADER PREMIUM
# ==========================
st.markdown("""
<div class='header-premium'>
    <img src='logo_factutrack.png' class='logo'>
    <h1 class='titulo'>FactuTrack</h1>
    <p class='slogan'>Facturas claras, finanzas inteligentes</p>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ==========================
# LOGIN (corregido)
# ==========================
if "usuario" not in st.session_state or not st.session_state["usuario"]:
    usuario = st.text_input("👤 Ingresa tu nombre")
    if st.button("Ingresar") and usuario:
        st.session_state["usuario"] = usuario
        st.rerun()   # refresca inmediatamente al primer clic
    st.stop()

usuario = st.session_state["usuario"]
st.markdown(f"### ¡Hola, {usuario}! 👋 Aquí tienes un resumen simple de tus gastos.")

# ==========================
# API IA - DETECCIÓN AUTOMÁTICA DE MODELO
# ==========================
model = None
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    modelos = genai.list_models()
    for m in modelos:
        if "generateContent" in m.supported_generation_methods:
            model = genai.GenerativeModel(m.name)
            break
except:
    model = None
    st.warning("⚠️ API no configurada o sin modelos válidos")

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
        "SELECT id, entidad, fecha, monto, categoria FROM facturas WHERE usuario=? ORDER BY rowid DESC",
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
                st.error("API no disponible. Verifica tu GOOGLE_API_KEY y modelos habilitados.")
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

                    # Mostrar datos extraídos con estilo premium
                    st.subheader("📑 Datos extraídos")
                    colX = st.columns(4)
                    colX[0].markdown(f"<div class='card'><h4>🏢 Entidad</h4><h3>{entidad}</h3></div>", unsafe_allow_html=True)
                    colX[1].markdown(f"<div class='card'><h4>📅 Fecha</h4><h3>{fecha}</h3></div>", unsafe_allow_html=True)
                    colX[2].markdown(f"<div class='card'><h4>💵 Monto</h4><h3>${monto:,.0f}</h3></div>", unsafe_allow_html=True)
                    colX[3].markdown(f"<div class='card'><h4>📊 Categoría</h4><h3>{categoria}</h3></div>", unsafe_allow_html=True)

                    st.success("✅ Factura registrada correctamente")

                except Exception as e:
                    st.error(f"⚠️ Error al analizar la factura: {e}")

# RESUMEN + HISTORIAL (derecha)
with col2:
    st.subheader("📊 Resumen mensual")
    total = df["monto"].sum() if not df.empty else 0
    cantidad = len(df)
    categoria_principal = df.groupby("categoria")["monto"].sum().idxmax() if not df.empty else "—"

    colA, colB, colC = st.columns(3)
    colA.markdown(f"<div class='card'><h4>💰 Total</h4><h2>${total:,.0f}</h2></div>", unsafe_allow_html=True)
    colB.markdown(f"<div class='card'><h4>📄 Facturas</h4><h2>{cantidad}</h2></div>", unsafe_allow_html=True)
    colC.markdown(f"<div class='card'><h4>📊 Categoría</h4><h2>{categoria_principal}</h2></div>", unsafe_allow_html=True)

    st.subheader("🕓 Mis facturas recientes")
    df = obtener_df()  # refrescar después de inserción
    if not df.empty:
        # Tabla estilizada con botón eliminar
        for _, row in df.iterrows():
            cols = st.columns([0.25, 0.25, 0.25, 0.15, 0.1])
            cols[0].write(f"**{row['entidad']}**")
            cols[1].write(row['fecha'])
            cols[2].write(f"${row['monto']:,.0f}")
            cols[3].write(row['categoria'])
            if cols[4].button("🗑️", key=f"del_{row['id']}"):
                c.execute("DELETE FROM facturas WHERE id=?", (row['id'],))
                conn.commit()
                st.rerun()
    else:
        st.info("Sin registros aún")
