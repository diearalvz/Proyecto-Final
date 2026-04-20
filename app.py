import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configuración inicial
st.set_page_config(page_title="Asistente de Finanzas")
st.title("FactuTrak")
st.write("Sube una foto de tu recibo para extraer los datos automáticamente.")

# 2. Configuración segura de la API (Lee la clave desde los Secrets)
try:
    # Esto busca el nombre GOOGLE_API_KEY en la configuración de Streamlit
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("Error al configurar la API. Verifica que 'GOOGLE_API_KEY' esté en los Secrets de tu App.")
    st.stop()

# 3. Interfaz de usuario
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
                # Aquí enviamos la imagen y el prompt al modelo
                response = model.generate_content([prompt, imagen])
                st.subheader("Datos extraídos:")
                st.json(response.text)
            except Exception as e:
                st.error(f"Ocurrió un error al procesar la imagen: {e}")