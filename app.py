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
st.markdown("""
<style>
body { background-color: #0e0e0e; color: #FFD700; }
.header h2 { text-align:center; color:#FFD700; font-family:Montserrat; }
.card {
    background-color:#1a1a1a;
    border:1px solid #FFD700;
    border-radius:8px;
    padding:1em;
    margin-bottom:1em;
    box-shadow:0 0 10px rgba(255,215,0,0.3);
}
</style>
""", unsafe_allow_html=True)

# ==========================
# HEADER
# ==========================
st.markdown("<div class='header'><h2>📊 FactuTrack</h2></div>", unsafe_allow_html=True)

# ==========================
# API
# ==========================
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")
except:
    st.warning("⚠️ API no configurada")
    model = None

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
# LOGIN PERSISTENTE
# ==========================
if "usuario" not in st.session_state:
    st.session_state["usuario"] = ""

if not st.session_state["usuario"]:
    usuario = st.text_input("👤 Ingresa tu usuario")
    if st.button("Ingresar"):
        st.session_state["usuario"] = usuario
    st.stop()

usuario = st.session_state["usuario"]

# ==========================
# FUNCIONES
# ==========================
def obtener_df():
    df = pd.read_sql_query(
        "SELECT id, entidad, fecha, monto, categoria FROM facturas WHERE usuario=? ORDER BY rowid DESC",
        conn, params=(usuario,)
    )
    if not df.empty:
        df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    return df

def guardar(entidad, fecha, monto, categoria):
    if not entidad: entidad = "No detectado"
    if not fecha: fecha = "No detectado"
    if not categoria: categoria = "Otros"
    try:
        monto = float(monto)
    except:
        monto = 0
    c.execute("INSERT INTO facturas (usuario, entidad, fecha, monto, categoria) VALUES (?,?,?,?,?)",
              (usuario, entidad, fecha, monto, categoria))
    conn.commit()

def borrar_factura(fid):
    c.execute("DELETE FROM facturas WHERE id=?", (fid,))
    conn.commit()

# ==========================
# DATOS
# ==========================
df = obtener_df()
total = df["monto"].sum() if not df.empty else 0
cantidad = len(df)

# ==========================
# LAYOUT PRINCIPAL
# ==========================
col1, col2 = st.columns([1,1])

# KPIs + HISTORIAL (arriba a la derecha)
with col2:
    st.markdown(f"<div class='card'><h4>💰 Gasto Total</h4><h2>${total:,.0f}</h2></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='card'><h4>📄 Facturas</h4><h2>{cantidad}</h2></div>", unsafe_allow_html=True)
    st.markdown('<div class="card"><h4>📄 Historial</h4>', unsafe_allow_html=True)
    if not df.empty:
        for _, row in df.iterrows():
            cols = st.columns([3,2,2,2,1])
            cols[0].write(row["entidad"].title())
            cols[1].write(row["fecha"])
            cols[2].write(f"${row['monto']:,.0f}")
            cols[3].write(row["categoria"].title())
            if cols[4].button("🗑️", key=f"del_{row['id']}"):
                if st.confirm(f"¿Seguro que deseas borrar la factura de {row['entidad']}?"):
                    borrar_factura(row["id"])
                    st.experimental_rerun()
        st.bar_chart(df.groupby("categoria")["monto"].sum())
    else:
        st.info("Sin registros aún")
    st.markdown('</div>', unsafe_allow_html=True)

# SUBIDA + RESULTADO IA (izquierda)
with col1:
    st.markdown('<div class="card"><h4>📤 Subir Recibo</h4>', unsafe_allow_html=True)
    metodo = st.radio("Selecciona método", ["Archivo", "Foto"])
    imagen = None
    if metodo == "Archivo":
        file = st.file_uploader("Selecciona imagen", type=["jpg","png","jpeg"])
        if file:
            imagen = Image.open(file)
            st.image(imagen, use_container_width=True)
    else:
        foto = st.camera_input("Tomar foto")
        if foto:
            imagen = Image.open(foto)
            st.image(imagen, use_container_width=True)

    if imagen and st.button("Analizar Factura"):
        if not model:
            st.error("API no disponible")
        else:
            try:
                prompt = "Devuelve SOLO JSON con: entidad, fecha, monto, categoria"
                r = model.generate_content([prompt, imagen])
                texto = re.sub(r"```json|```","", r.text).strip()
                data = json.loads(texto)
                entidad = data.get("entidad","No detectado")
                fecha = data.get("fecha","No detectado")
                monto = data.get("monto",0)
                categoria = data.get("categoria","Otros")
                guardar(entidad, fecha, monto, categoria)
                st.success("✅ Guardado correctamente")
                st.markdown(f"""
                <div class="card">
                    <h4>📄 Datos detectados</h4>
                    <p><b>Entidad:</b> {entidad.title()}</p>
                    <p><b>Fecha:</b> {fecha}</p>
                    <p><b>Monto:</b> ${float(monto):,.0f}</p>
                    <p><b>Categoría:</b> {categoria.title()}</p>
                </div>
                """, unsafe_allow_html=True)
            except Exception:
                st.warning("⚠️ Error o límite de uso alcanzado. Intenta de nuevo en unos segundos.")
    st.markdown('</div>', unsafe_allow_html=True)
