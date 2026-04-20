import streamlit as st
import google.generativeai as genai
from PIL import Image
import altair as alt
import pandas as pd

# ==========================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================
st.set_page_config(page_title="FactuTrack", layout="wide")
st.markdown(
    """
    <style>
    /* Fondo y texto */
    body {
        background-color: #0e0e0e;
        color: #FFD700;
    }

    /* Botones */
    .stButton>button {
        background-color: #FFD700;
        color: #000;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.6em 1.2em;
    }

    /* Encabezados */
    h1, h2, h3 {
        color: #FFD700;
        text-shadow: 0 0 10px #FFD700;
    }

    /* Métricas */
    .stMetric {
        background-color: #1a1a1a;
        border-radius: 10px;
        padding: 1em;
        box-shadow: 0 0 10px rgba(255, 215, 0, 0.3);
    }

    /* Gráficos */
    .vega-embed {
        background-color: #1a1a1a;
        border-radius: 10px;
        padding: 1em;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================
# TÍTULO Y DESCRIPCIÓN
# ==========================
st.title("FactuTrack")
st.write("De recibos a datos útiles con IA")

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
                    datos = eval(texto)  # convierte el JSON en diccionario

                    st.success("✅ Datos extraídos con éxito")

                    colA, colB = st.columns(2)
                    with colA:
                        st.metric("🏢 Entidad", datos["entidad"])
                        st.metric("📅 Fecha", datos["fecha"])
                    with colB:
                        st.metric("💵 Monto", datos["monto"])
                        st.metric("📂 Categoría", datos["categoria"])

                    # Gráfico de resumen
                    st.subheader("📈 Resumen de Gastos")
                    data = pd.DataFrame({
                        'Categoría': [datos["categoria"]],
                        'Monto': [float(str(datos["monto"]).replace(",", "").replace(".", ""))]
                    })
                    chart = alt.Chart(data).mark_bar(color='#FFD700').encode(
                        x='Categoría',
                        y='Monto'
                    )
                    st.altair_chart(chart, use_container_width=True)

                    # Botones de acción
                    st.download_button("⬇️ Descargar CSV", data.to_csv(index=False), "factura.csv")
                    st.button("🕓 Historial de Facturas")

                except Exception as e:
                    st.error(f"Error al procesar la imagen: {e}")

with col2:
    st.subheader("📊 Datos Extraídos")
    st.info("Los resultados aparecerán aquí después del análisis.")
