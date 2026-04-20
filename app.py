import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Asistente de Finanzas")
st.title("💰 FactuTrack")
st.write("Sube una foto de tu recibo para extraer los datos automáticamente.")

try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    
    # Inicialización correcta del modelo
    model = genai.GenerativeModel(model_name='gemini-1.5-pro')
except Exception as e:
    st.error(f"Error al configurar la API: {e}")
    st.stop()

uploaded_file = st.file_uploader("Sube tu recibo aquí", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    imagen = Image.open(uploaded_file)
    st.image(imagen, caption='Recibo subido', use_column_width=True)

    if st.button("Analizar Factura"):
        with st.spinner('Leyendo factura...'):
            prompt = """
            Actúa como un experto contable. Analiza esta factura y extrae la información en formato JSON puro.
            Usa estas claves exactas: "entidad", "fecha", "monto", "categoria".
            Si no encuentras un dato, pon "No detectado".
            Devuelve solo el JSON, sin texto adicional.
            """
            try:
                response = model.generate_content([prompt, imagen])
                st.subheader("Datos extraídos:")
                st.json(response.text)
            except Exception as e:
                st.error(f"Error al procesar la imagen: {e}")
