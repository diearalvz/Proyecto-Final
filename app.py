import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configuración de la página
st.set_page_config(page_title="Asistente de Finanzas")
st.title("💰 FactuTrack")
st.write("Sube una foto de tu recibo para extraer los datos automáticamente.")

# 2. Configuración segura de la API
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)

    # Listar modelos disponibles y elegir uno válido
    modelos = list(genai.list_models())
    modelo_valido = None
    for m in modelos:
        if "generateContent" in m.supported_generation_methods:
            modelo_valido = m.name
            break

    if not modelo_valido:
        st.error("No hay modelos disponibles que soporten generateContent en tu cuenta.")
        st.stop()

    # Inicializar con el modelo válido encontrado
    model = genai.GenerativeModel(model_name=modelo_valido)
    st.success(f"Usando el modelo: {modelo_valido}")
except Exception as e:
    st.error(f"Error al configurar la API: {e}")
    st.stop()

# 3. Interfaz de usuario
uploaded_file = st.file_uploader("Sube tu recibo aquí", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
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

                # Limpiar posibles bloques de código que devuelva el modelo
                texto = response.text.strip()
                if texto.startswith("```"):
                    texto = texto.strip("`").replace("json", "").strip()

                st.subheader("Datos extraídos:")
                st.json(texto)
            except Exception as e:
                st.error(f"Error al procesar la imagen: {e}")

