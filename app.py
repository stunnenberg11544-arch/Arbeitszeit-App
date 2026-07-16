import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Arbeitszeit & Berichte", page_icon="📝")

# API laden
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# Zwischenspeicher für Kamera
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
                
                # ALLE erlaubten Modelle deines Schlüssels abfragen
                verfuegbare_modelle = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                
                # Automatisches Aussuchen des besten Modells
                ziel_modell = None
                
                # 1. Priorität: Das schnelle 1.5 Flash Modell
                for m in verfuegbare_modelle:
                    if "1.5-flash" in m:
                        ziel_modell = m
                        break
                        
                # 2. Priorität: Das große 1.5 Pro Modell
                if not ziel_modell:
                    for m in verfuegbare_modelle:
                        if "1.5-pro" in m:
                            ziel_modell = m
                            break
                            
                # 3. Priorität: Das alte Vision Modell als Notnagel
                if not ziel_modell:
                    for m in verfuegbare_modelle:
                        if "vision" in m:
                            ziel_modell = m
                            break
                
                if ziel_modell:
                    st.info(f"System-Info: Nutze Modell '{ziel_modell}'")
                    model = genai.GenerativeModel(ziel_modell)
                    antwort = model.generate_content(
                        ["Bitte lies diese handschriftlichen Kalendereinträge aus. Erstelle eine strukturierte Zusammenfassung der Arbeitszeiten.", *verarbeitete_bilder]
                    )
                    st.success("Erfolgreich ausgewertet!")
                    st.write(antwort.text)
                else:
                    st.error("Dein API-Schlüssel hat leider keine Berechtigung für Bild-Modelle.")
                    st.write("Verfügbare Modelle laut Schlüssel:", verfuegbare_modelle)
                    
            except Exception as e:
                st.error(f"Fehler: {e}")
