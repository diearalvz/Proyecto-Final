import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import sqlite3
import json
import re
import plotly.express as px
import io

# ==========================
# CONFIGURACIÓN GENERAL
# ==========================
st.set_page_config(page_title="FactuTrack", layout="wide")

# ==========================
# CARGAR ESTILOS PREMIUM
# ==========================
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ==========================
# HEADER CON NAVEGACIÓN
# ==========================
col1, col2, col3, col4, col5 = st.columns([2,1,1,1,1])
with col1:
    st.markdown('<div class="titulo">📊 FactuTrack</div>', unsafe_allow_html=True)
with col2:
    st.button("Inicio")
with col3:
    st.button("Reportes")
with col4:
    st.button("Admin")
with col5:
    st.button("Perfil")

st.markdown('<div class="sub">De recibos a datos útiles</div>', unsafe_allow_html=True)

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
usuario = st.text_input("👤 Ingresa tu usuario o correo:")
if not usuario:
    st.warning("Por favor ingresa tu usuario para continuar.")
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
# TARJETAS RESUMEN (CORREGIDAS)
# ==========================
df = obtener_df()

if not df.empty and "monto" in df.columns:
    total = pd.to_numeric(df["monto"], errors="coerce").sum()
else:
    total = 0.0

count = len(df) if not df.empty else 0

col1, col2 = st.columns(2)
with col1:
    st.markdown(
        f'<div class="card"><h3 style="color:#D4AF37;">💰 Gasto Total</h3>'
        f'<p style="font-size:1.5em;">${total:,.0f}</p></div>',
        unsafe_allow_html=True
    )
with col2:
    st.markdown(
        f'<div class="card"><h3 style="color:#D4AF37;">📄 Facturas</h3>'
        f'<p style="font-size:1.5em;">{count}</p></div>',
        unsafe_allow_html=True
    )

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
# SECCIÓN: RESUMEN DE GASTOS
# ==========================
st.markdown("### 📊 Resumen de Gastos")

if not df.empty:
    col1, col2 = st.columns([2,1])
    with col1:
        st.dataframe(df[["entidad","fecha","categoria","monto"]], use_container_width=True)
    with col2:
        fig = px.pie(df, names="categoria", values="monto", title="Gastos por Categoría",
                     color_discrete_sequence=px.colors.sequential.Gold)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 📤 Exportar o Ver Reporte Completo")

    # Exportar a CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Exportar a CSV",
        data=csv,
        file_name="facturas.csv",
        mime="text/csv"
    )

    # Exportar a Excel
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Facturas")
    st.download_button(
        label="⬇️ Exportar a Excel",
        data=excel_buffer.getvalue(),
        file_name="facturas.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.button("Ver Reporte Completo")
else:
    st.info("Aún no tienes facturas registradas.")
