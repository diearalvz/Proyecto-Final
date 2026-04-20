import streamlit as st
import google.generativeai as genai
from PIL import Image

# Configuración segura: Streamlit buscará la clave en sus configuraciones "Secretas"
# Cuando despliegues en Streamlit Cloud, esto leerá la clave de forma privada
api_key = st.secrets["AIzaSyCL9bpfDj13AyqzoI1VWwLnnq8OFQeTN_4"]
genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-1.5-flash')

st.title("💰 Asistente de Finanzas del Hogar")
st.write("Sube una foto de tu recibo para extraer los datos automáticamente.")

archivo = st.file_uploader("Sube la factura (JPG o PNG)", type=['jpg', 'jpeg', 'png'])

if archivo is not None:
    imagen = Image.open(archivo)
    st.image(imagen, caption='Factura cargada', use_column_width=True)
    
    if st.button("Analizar Factura"):
        with st.spinner('Leyendo factura...'):
            prompt = """
            Actúa como un experto contable. Analiza esta factura y extrae la información en formato JSON puro.
            Usa estas claves exactas: "entidad", "fecha", "monto", "categoria".
            Si no encuentras un dato, pon "No detectado".
            Devuelve solo el JSON, sin texto adicional.
            """
            response = model.generate_content([prompt, imagen])
            st.json(response.text)