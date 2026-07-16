import streamlit as st
import google.generativeai as genai
from weasyprint import HTML
import json
import datetime
from PIL import Image
from io import BytesIO
import os

# Seitenkonfiguration (Mobile Friendly)
st.set_page_config(page_title="Arbeitszeitnachweis App", page_icon="📝", layout="centered")

# API Key aus den Streamlit Secrets laden
API_KEY = st.secrets.get("GEMINI_API_KEY")
if not API_KEY:
    st.error("Bitte GEMINI_API_KEY in den Streamlit Secrets hinterlegen.")
    st.stop()

genai.configure(api_key=API_KEY)

# Das Gemini-Modell initialisieren
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("📝 Wochenübersicht & Berichte")
st.write("Lade hier die Fotos deines Kalenders hoch.")

# Datei-Uploader für Bilder (unterstützt auf dem Handy direkten Zugriff auf die Kamera/Galerie)
uploaded_files = st.file_uploader("Kalenderbilder auswählen", accept_multiple_files=True, type=["jpg", "jpeg", "png"])
# Direkte Kamera-Integration
camera_photo = st.camera_input("Oder: Foto direkt hier aufnehmen")

if camera_photo is not None:
    # Fügt das aufgenommene Foto direkt zur Liste der zu verarbeitenden Bilder hinzu
    if uploaded_files is None:
        uploaded_files = []
    uploaded_files.append(camera_photo)

if uploaded_files and st.button("📄 Nachweise generieren"):
    with st.spinner("Bilder werden analysiert und PDFs generiert... Bitte warten."):
        
        # Bilder für die API vorbereiten
        images = []
        for file in uploaded_files:
            img = Image.open(file)
            images.append(img)
        
        # Heutiges Datum für die Unterschrift
        heute_str = datetime.datetime.now().strftime("%d.%m.%Y")
        
        # Der System-Prompt mit all deinen Vorgaben
        prompt = f"""
        Du bist ein Assistent zur Erstellung von Arbeitszeitnachweisen.
        Analysiere die hochgeladenen Kalender-Bilder und erstelle folgende Dokumente im HTML-Format:
        
        1. Eine Wochenübersicht (immer exakt passend auf 1 DIN-A4-Seite).
        2. Separate Arbeitsberichte für jede Tätigkeit, die NICHTS mit Müll zu tun hat (Gartenarbeit, Reparaturen, etc.).
        
        Regeln für die Inhalte:
        - Name: Dirk Stunnenberg-Verhoeven
        - Unterschriftenfeld unten: "Kranenburg, den {heute_str}" und "Unterschrift (Dirk Stunnenberg-Verhoeven)".
        - Vereinbarte Wochenstunden: 20 Stunden (nur in der Wochenübersicht oben rechts).
        - Formatierung Müll: Ignoriere Farben (Grau, Bio etc.). Schreibe IMMER "[Stadt] Mülltonnen Bereitstellung".
        - Fasse Müll-Einträge pro Tag zusammen (z.B. "Müll (X Std): Kalkar Mülltonnen Bereitstellung; Goch Mülltonnen Bereitstellung").
        
        GIB AUSSCHLIESSLICH EIN VALIDES JSON ZURÜCK, das exakt dieses Format hat:
        [
            {{
                "filename": "Arbeitszeitnachweis_KWXX.pdf",
                "html": "<!DOCTYPE html><html>...HTML Code...</html>"
            }},
            {{
                "filename": "Arbeitsbericht_...pdf",
                "html": "<!DOCTYPE html><html>...HTML Code...</html>"
            }}
        ]
        
        Verwende für das HTML einfaches, sauberes CSS, das auf A4 optimiert ist (wie in unseren bisherigen Vorlagen).
        Antworte NUR mit dem JSON Code-Block, keinem anderen Text.
        """
        
        try:
            # Anfrage an die API senden (Prompt + Bilder)
            response = model.generate_content([prompt] + images)
            
            # JSON aus der Antwort extrahieren
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3] # Markdown-Formatierung entfernen
                
            documents = json.loads(response_text)
            
            st.success("✅ Generierung erfolgreich! Hier sind deine PDFs:")
            
            # Für jedes Dokument im JSON ein PDF erstellen und einen Download-Button anzeigen
            for doc in documents:
                filename = doc.get("filename", "Dokument.pdf")
                html_content = doc.get("html", "")
                
                # HTML zu PDF im Arbeitsspeicher umwandeln
                pdf_buffer = BytesIO()
                HTML(string=html_content).write_pdf(pdf_buffer)
                pdf_bytes = pdf_buffer.getvalue()
                
                # Download Button
                st.download_button(
                    label=f"📥 {filename} herunterladen",
                    data=pdf_bytes,
                    file_name=filename,
                    mime="application/pdf"
                )
                
        except Exception as e:
            st.error(f"Fehler bei der Verarbeitung: {e}")

st.divider()
st.caption("📱 Tipp: Füge diese Seite im Browser zu deinem Home-Bildschirm hinzu, um sie wie eine native App zu nutzen.")
