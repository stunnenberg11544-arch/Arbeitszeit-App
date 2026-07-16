import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Arbeitszeit & Berichte", page_icon="📝")

# API laden
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

if 'kamera_bilder' not in st.session_state:
    st.session_state.kamera_bilder = []

st.title("📝 Wochenübersicht")

kamera_foto = st.camera_input("Kalender abfotografieren")
if kamera_foto is not None:
    if st.button("📸 Dieses Foto speichern", type="primary"):
        st.session_state.kamera_bilder.append(kamera_foto)
        st.rerun()

if st.session_state.kamera_bilder:
    st.success(f"Zwischengespeicherte Fotos: {len(st.session_state.kamera_bilder)}")
    if st.button("🗑️ Leeren"):
        st.session_state.kamera_bilder = []
        st.rerun()

st.divider()

if st.button("📄 Nachweise generieren"):
    if not st.session_state.kamera_bilder:
        st.warning("Bitte knipse zuerst ein Foto!")
    else:
        with st.spinner("Lese Handschrift..."):
            try:
                # Bilder verkleinern
                verarbeitete_bilder = []
                for img_file in st.session_state.kamera_bilder:
                    img = Image.open(img_file)
                    img.thumbnail((1200, 1200)) 
                    verarbeitete_bilder.append(img)
                
                # WIR NUTZEN JETZT EXAKT DEIN NEUES MODELL!
                model = genai.GenerativeModel('gemini-2.5-flash')
                antwort = model.generate_content(
                    ["Bitte lies diese handschriftlichen Kalendereinträge aus. Erstelle eine strukturierte Zusammenfassung der Arbeitszeiten.", *verarbeitete_bilder]
                )
                
                st.success("Erfolgreich ausgewertet!")
                st.write(antwort.text)
                    
            except Exception as e:
                st.error(f"Fehler: {e}")
