import streamlit as st
import google.generativeai as genai
from PIL import Image

modelle = ['gemini-3-flash', 'gemini-3.1-flash-lite']
antwort = None
fehler_liste = []

for m_name in modelle:
    try:
        model = genai.GenerativeModel(m_name)
        antwort = model.generate_content(["Lies diese Arbeitszeiten aus.", *imgs])
        break
    except Exception as e:
        fehler_liste.append(f"{m_name}: {e}")
        continue

if antwort:
    st.write(antwort.text)
else:
    st.error("Kein Modell hat funktioniert. Details:")
    for f in fehler_liste:
        st.code(f)

st.set_page_config(page_title="Arbeitszeit & Berichte", page_icon="📝")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if 'kamera_bilder' not in st.session_state:
    st.session_state.kamera_bilder = []

st.title("📝 Wochenübersicht")
kamera_foto = st.camera_input("Kalender abfotografieren")

if kamera_foto is not None:
    if st.button("📸 Speichern"):
        st.session_state.kamera_bilder.append(kamera_foto)
        st.rerun()

if st.button("📄 Nachweise generieren"):
    with st.spinner("Lese Handschrift..."):
        try:
            imgs = [Image.open(f).convert('RGB') for f in st.session_state.kamera_bilder]
            
            # Liste von Modellen zum Durchprobieren
            modelle = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-2.0-flash-lite']
            antwort = None
            
            for m_name in modelle:
                try:
                    model = genai.GenerativeModel(m_name)
                    antwort = model.generate_content(["Lies diese Arbeitszeiten aus.", *imgs])
                    break # Wenn eins funktioniert, stoppen
                except Exception:
                    continue # Wenn blockiert, nächstes probieren
            
            if antwort:
                st.write(antwort.text)
            else:
                st.error("Alle Modelle sind aktuell durch dein Kontingent blockiert. Bitte versuche es später.")
        except Exception as e:
            st.error(f"Fehler: {e}")
