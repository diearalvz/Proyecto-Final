import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import sqlite3

# ==========================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================
st.set_page_config(page_title="FactuTrack", layout="wide")

# ==========================
# ESTILO VISUAL PREMIUM
# ==========================
st.markdown(
    """
    <style>
    body {
        background-color: #0e0e0e;
        color: #FFD700;
    }
    .stButton>button {
        background-color: #FFD700;
        color: #000;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.6em 1.2em;
    }
    .titulo-principal {
        font-size: 3em;
        color: #FFD700;
        text-align: center;
        text-shadow: 0 0 20px #FFD700, 0 0 40px #FFA500;
        font-weight: bold;
        margin-bottom: 0.1em;
        font-family: 'Montserrat', sans-serif;
    }
    .subtitulo {
        font-size: 1.5em;
        color: #FFD700;
        text-align: center;
        font-style: italic;
        font-family: 'Georgia', serif;
        margin-top: 0;
        margin-bottom: 1em;
    }
    h2, h3 {
        color: #FFD700;
    }
    .stMetric {
        background-color: #1a1a1a;
        border-radius: 10px;
        padding: 1em;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================
# TÍTULO Y SUBTÍTULO
# ==========================
st.markdown(
    """
    <div class="titulo-principal">💰 FactuTrack</div>
    <div class="subtitulo">De recibos a datos útiles con IA</div>
    """,
    unsafe_allow_html=True
)

# ==========================
# CONFIGURACIÓN DE LA API
# ==========================
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)

    modelos = list(genai.list_models())
    modelo_valido = None
    for m in modelos:
        if "generateContent" in m.supported_generation_methods:
            modelo_valido = m.name
            break

    if not modelo_valido:
        st.error("No hay modelos disponibles que soporten generateContent en tu cuenta.")
        st.stop()

    model = genai.GenerativeModel(model_name=modelo_valido)
except Exception as e:
    st.error(f"Error al configurar la API: {e}")
    st.stop()

# ==========================
# BASE DE DATOS LOCAL
# ==========================
conn = sqlite3.connect("facturas.db")
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS facturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entidad TEXT,
        fecha TEXT,
        monto TEXT,
        categoria TEXT
    )
''')
conn.commit()

def guardar_factura(entidad, fecha, monto, categoria):
    c.execute('''
        SELECT * FROM facturas
        WHERE entidad=? AND fecha=? AND monto=?
    ''', (entidad, fecha, monto))
    duplicado = c.fetchone()

    if duplicado:
        st.warning("⚠️ Factura duplicada detectada: mismo día, mismo lugar y mismo valor.")
    else:
        c.execute('''
            INSERT INTO facturas (entidad, fecha, monto, categoria)
            VALUES (?, ?, ?, ?)
        ''', (entidad, fecha, monto, categoria))
        conn.commit()
        st.success("✅ Factura guardada en el historial.")

def mostrar_historial():
    c.execute("SELECT id, entidad, fecha, monto, categoria FROM facturas")
    rows = c.fetchall()
    if rows:
        df = pd.DataFrame(rows, columns=["ID", "Entidad", "Fecha", "Monto", "Categoría"])
        try:
            df["Monto"] = df["Monto"].apply(
                lambda x: float(str(x).replace(".", "").replace(",", "."))
            )
        except Exception as e:
            st.warning(f"Error al convertir montos: {e}")
        total = df["Monto"].sum()
        st.subheader("🕓 Historial de Facturas")
        st.dataframe(df.drop(columns=["ID"]))  # mostramos sin ID

        st.info(f"💵 Total acumulado: {total:,.2f}")

        # Selección para borrar factura
        factura_id = st.selectbox("Selecciona el ID de la factura a borrar:", df["ID"])
        if st.button("🗑️ Borrar Factura"):
            c.execute("DELETE FROM facturas WHERE id=?", (factura_id,))
            conn.commit()
            st.success("✅ Factura eliminada correctamente.")
    else:
        st.info("No hay facturas registradas aún.")

# ==========================
# INTERFAZ PRINCIPAL
# ==========================
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Sube tu recibo")
    uploaded_file = st.file_uploader("Arrastra o sube una imagen (JPG, PNG)", type=['png', 'jpg', 'jpeg'])
    if uploaded_file:
        imagen = Image.open(uploaded_file)
        st.image(imagen, caption='Recibo subido', use_column_width=True)
        if st.button("Analizar Factura"):
            with st.spinner("Leyendo factura..."):
                prompt = """
                Actúa como un experto contable. Analiza esta factura y devuelve la información en formato JSON válido.
                Usa estas claves exactas: "entidad", "fecha", "monto", "categoria".
                Si no encuentras un dato, pon "No detectado".
                IMPORTANTE: Devuelve solo el JSON, sin explicaciones, sin texto adicional, sin bloques de código.
                """
                try:
                    response = model.generate_content([prompt, imagen])
                    texto = response.text.strip()
                    if texto.startswith("```"):
                        texto = texto.strip("`").replace("json", "").strip()
                    datos = eval(texto)

                    st.success("✅ Datos extraídos con éxito")

                    colA, colB = st.columns(2)
                    with colA:
                        st.metric("🏢 Entidad", datos["entidad"])
                        st.metric("📅 Fecha", datos["fecha"])
                    with colB:
                        st.metric("💵 Monto", datos["monto"])
                        st.metric("📂 Categoría", datos["categoria"])

                    guardar_factura(datos["entidad"], datos["fecha"], datos["monto"], datos["categoria"])

                except Exception as e:
                    st.error(f"Error al procesar la imagen: {e}")

with col2:
    mostrar_historial()
