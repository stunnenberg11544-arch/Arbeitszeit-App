import streamlit as st
import google.generativeai as genai
from PIL import Image

# Seitenkonfiguration (muss ganz oben stehen)
st.set_page_config(page_title="Arbeitszeit & Berichte", page_icon="📝", layout="centered")

# API Key laden
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)

# Zwischenspeicher für Kamera-Fotos initialisieren
if 'kamera_bilder' not in st.session_state:
    st.session_state.kamera_bilder = []

st.title("📝 Wochenübersicht & Berichte")
st.write("Erfasse hier deine handschriftlichen Kalendereinträge.")

# --- BEREICH 1: Upload aus der Galerie ---
st.subheader("1. Fotos aus der Galerie hochladen")
uploaded_files = st.file_uploader("Wähle bereits gemachte Bilder aus...", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'])

# --- BEREICH 2: Serien-Aufnahme mit der Kamera ---
st.subheader("2. Bilder nacheinander aufnehmen")
st.info("Klicke nach jedem Foto auf den grünen Button, um es abzuspeichern, bevor du das nächste knipst!")

kamera_foto = st.camera_input("Kalender abfotografieren")

if kamera_foto is not None:
    if st.button("📸 Dieses Foto speichern & nächstes vorbereiten", type="primary"):
        st.session_state.kamera_bilder.append(kamera_foto)
        st.rerun()

# Anzeige der gespeicherten Kamera-Fotos
if st.session_state.kamera_bilder:
    st.success(f"Erfolgreich zwischengespeicherte Kamera-Fotos: {len(st.session_state.kamera_bilder)}")
    if st.button("🗑️ Zwischenspeicher leeren"):
        st.session_state.kamera_bilder = []
        st.rerun()

st.divider()

# Alle Bilder sammeln
alle_bilder = []
if uploaded_files:
    alle_bilder.extend(uploaded_files)
if st.session_state.kamera_bilder:
    alle_bilder.extend(st.session_state.kamera_bilder)

# --- BEREICH 3: Verarbeitung ---
if st.button("📄 Nachweise generieren"):
    if not alle_bilder:
        st.warning("Bitte füge zuerst Bilder (Kamera oder Upload) hinzu!")
    else:
        with st.spinner("Bilder werden optimiert und analysiert (das kann einen Moment dauern)..."):
            try:
                # BILDER KOMPRIMIEREN (Verhindert Abstürze durch zu große Dateien)
                verarbeitete_bilder = []
                for img_file in alle_bilder:
                    img = Image.open(img_file)
                    img.thumbnail((1200, 1200)) # Verkleinert das Bild auf ein sicheres Maß
                    verarbeitete_bilder.append(img)
                
                # ROBUSTE MODELL-ABFRAGE (verhindert den 404 Fehler)
                antwort = None
                letzter_fehler = ""
                modelle = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.5-flash-latest']
                
                for modell_name in modelle:
                    try:
                        model = genai.GenerativeModel(modell_name)
                        antwort = model.generate_content(
                            ["Bitte lies diese handschriftlichen Kalendereinträge aus. Erstelle eine strukturierte Zusammenfassung der dokumentierten Arbeitszeiten und Tätigkeiten.", *verarbeitete_bilder]
                        )
                        break # Wenn erfolgreich, Schleife abbrechen
                    except Exception as e:
                        letzter_fehler = str(e)
                        continue # Wenn Fehler, nächstes Modell probieren
                
                if antwort:
                    st.success("Verarbeitung erfolgreich!")
                    st.write(antwort.text)
                else:
                    st.error("Alle Modelle haben einen Fehler gemeldet. Details:")
                    st.error(letzter_fehler)
                    
            except Exception as e:
                st.error(f"Genereller Fehler: {e}")
