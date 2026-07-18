import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import re
import io
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, PageBreak)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

st.set_page_config(page_title="Arbeitszeit & Berichte", page_icon="📝")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if 'kamera_bilder' not in st.session_state:
    st.session_state.kamera_bilder = []
if 'pdf_bytes' not in st.session_state:
    st.session_state.pdf_bytes = None
if 'cam_key' not in st.session_state:
    st.session_state.cam_key = 0

st.title("📝 Wochenübersicht")

kamera_foto = st.camera_input("Kalender abfotografieren", key=f"cam_{st.session_state.cam_key}")

# Foto wird sofort nach der Aufnahme gespeichert, das Kamera-Feld wird danach
# durch einen neuen Widget-Key automatisch geleert (kein Klick nötig).
if kamera_foto is not None:
    st.session_state.kamera_bilder.append(kamera_foto)
    st.session_state.cam_key += 1
    st.rerun()

if st.session_state.kamera_bilder:
    st.write(f"Gespeicherte Fotos: {len(st.session_state.kamera_bilder)}")
    if st.button("🗑️ Alle Fotos löschen"):
        st.session_state.kamera_bilder = []
        st.session_state.pdf_bytes = None
        st.rerun()


PROMPT = """Du liest handschriftliche Kalendereinträge zu Arbeitszeiten aus Fotos aus.
Gib AUSSCHLIESSLICH ein JSON-Objekt zurück, ohne Markdown-Codeblock, ohne Erklärtext, in genau diesem Format:

{
  "name": "Name der ausführenden Person, falls erkennbar, sonst leer lassen",
  "zeitraum": "z.B. 29. Juni - 03. Juli 2026",
  "eintraege": [
    {"datum": "Mo, 29.06.", "stunden": 4.75, "taetigkeiten": "Kurzbeschreibung aller Tätigkeiten des Tages inkl. Ort/Adresse"}
  ],
  "einzelauftraege": [
    {"datum": "29.06.2026", "objektadresse": "Straße, Ort (Ansprechpartner falls genannt)", "stunden": 2.5, "taetigkeiten": "Kurzbeschreibung der konkreten Tätigkeit"}
  ]
}

Regeln:
- "eintraege": ein Eintrag pro Kalendertag mit Notizen, für die Wochenübersicht. Enthält ALLE Tätigkeiten des Tages (auch Müllentsorgung).
- "einzelauftraege": ein eigener Eintrag für JEDE Tätigkeit, die KEINE Müllentsorgung/Mülltonnen-Bereitstellung ist (z.B. Montage, Reparatur, Wartung, Rauchmelder, Türen einstellen etc.). Reine Müllentsorgungs-Tätigkeiten NICHT in "einzelauftraege" aufnehmen.
- "stunden" als Dezimalzahl (Komma im Text als Punkt interpretieren, z.B. "2,5 Std" -> 2.5).
- Wenn ein Wert nicht lesbar ist, sinnvoll leer lassen, aber das JSON-Format nicht brechen.
"""


def parse_json_antwort(text):
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return json.loads(text)


def _stile():
    styles = getSampleStyleSheet()
    return {
        'titel': ParagraphStyle('Titel', parent=styles['Title'], fontSize=18, spaceAfter=4),
        'sub': ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10,
                               textColor=colors.grey, alignment=1, spaceAfter=16),
        'zelle': ParagraphStyle('Zelle', parent=styles['Normal'], fontSize=9, leading=12),
        'klein': ParagraphStyle('klein', fontSize=8, textColor=colors.grey),
        'label': ParagraphStyle('label', parent=styles['Normal'], fontSize=10, leading=16),
    }


def _unterschrift_block(name, stile):
    daten = [[
        Paragraph(f"Kranenburg, den {date.today().strftime('%d.%m.%Y')}", stile['zelle']),
        Paragraph("", stile['zelle']),
    ], [
        Paragraph("Ort, Datum", stile['klein']),
        Paragraph(f"Unterschrift ({name})", stile['klein']),
    ]]
    tabelle = Table(daten, colWidths=[8.5*cm, 8.5*cm])
    tabelle.setStyle(TableStyle([
        ('LINEABOVE', (0, 1), (0, 1), 0.5, colors.black),
        ('LINEABOVE', (1, 1), (1, 1), 0.5, colors.black),
        ('TOPPADDING', (0, 1), (-1, 1), 4),
    ]))
    return tabelle


def _wochenuebersicht_story(daten, stile):
    story = [Paragraph("Arbeitszeitnachweis / Wochenübersicht", stile['titel'])]
    if daten.get("zeitraum"):
        story.append(Paragraph(f"Zeitraum: {daten['zeitraum']}", stile['sub']))
    else:
        story.append(Spacer(1, 12))

    kopf = Table([[Paragraph(f"<b>Name:</b> {daten.get('name', '')}", stile['zelle']),
                   Paragraph("<b>Vereinbarte Wochenstunden:</b>", stile['zelle'])]],
                 colWidths=[10*cm, 7*cm])
    kopf.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(kopf)
    story.append(Spacer(1, 16))

    tabellen_daten = [["Datum", "Stunden", "Tätigkeiten"]]
    gesamt = 0.0
    for e in daten.get("eintraege", []):
        stunden = e.get("stunden", 0) or 0
        try:
            gesamt += float(stunden)
        except (TypeError, ValueError):
            pass
        tabellen_daten.append([
            Paragraph(str(e.get("datum", "")), stile['zelle']),
            Paragraph(str(stunden), stile['zelle']),
            Paragraph(str(e.get("taetigkeiten", "")), stile['zelle']),
        ])
    tabellen_daten.append(["", "Gesamtsumme:", f"{gesamt:.2f}".replace(".", ",")])

    tabelle = Table(tabellen_daten, colWidths=[2.5*cm, 2.5*cm, 12*cm], repeatRows=1)
    tabelle.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0e0e0")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#f0f0f0")),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('SPAN', (0, -1), (0, -1)),
    ]))
    story.append(tabelle)
    story.append(Spacer(1, 40))
    story.append(_unterschrift_block(daten.get('name', ''), stile))
    return story


def _einzelnachweis_story(auftrag, name, stile):
    story = [Paragraph("Arbeitsbericht / Leistungsnachweis", stile['titel']), Spacer(1, 16)]

    kopf_daten = [
        [Paragraph("<b>Ausführender:</b>", stile['label']), Paragraph(name, stile['label'])],
        [Paragraph("<b>Objektadresse:</b>", stile['label']), Paragraph(auftrag.get('objektadresse', ''), stile['label'])],
        [Paragraph("<b>Datum der Ausführung:</b>", stile['label']), Paragraph(auftrag.get('datum', ''), stile['label'])],
        [Paragraph("<b>Arbeitszeit (Dauer):</b>", stile['label']), Paragraph(f"{auftrag.get('stunden', '')} Stunden", stile['label'])],
    ]
    kopf = Table(kopf_daten, colWidths=[5*cm, 12*cm])
    kopf.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(kopf)
    story.append(Spacer(1, 16))

    taetigkeit_tabelle = Table([
        [Paragraph("<b>Durchgeführte Tätigkeiten</b>", stile['label'])],
        [Paragraph(auftrag.get('taetigkeiten', ''), stile['zelle'])],
    ], colWidths=[17*cm])
    taetigkeit_tabelle.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.grey),
        ('LINEBELOW', (0, 0), (0, 0), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 10),
        ('MINHEIGHT', (0, 1), (0, 1), 3*cm),
    ]))
    story.append(taetigkeit_tabelle)
    story.append(Spacer(1, 40))
    story.append(_unterschrift_block(name, stile))
    return story


def erstelle_pdf(daten):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             topMargin=2*cm, bottomMargin=2*cm,
                             leftMargin=2*cm, rightMargin=2*cm)
    stile = _stile()
    name = daten.get('name', '')

    story = _wochenuebersicht_story(daten, stile)

    for auftrag in daten.get("einzelauftraege", []):
        story.append(PageBreak())
        story.extend(_einzelnachweis_story(auftrag, name, stile))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


if st.button("📄 Nachweise generieren"):
    if not st.session_state.kamera_bilder:
        st.warning("Bitte zuerst mindestens ein Foto speichern.")
    else:
        with st.spinner("Lese Handschrift..."):
            try:
                imgs = [Image.open(f).convert('RGB') for f in st.session_state.kamera_bilder]

                modelle = ['gemini-3-flash', 'gemini-3.1-flash-lite']
                antwort = None
                fehler_liste = []

                for m_name in modelle:
                    try:
                        model = genai.GenerativeModel(m_name)
                        antwort = model.generate_content([PROMPT, *imgs])
                        break
                    except Exception as e:
                        fehler_liste.append(f"{m_name}: {e}")
                        continue

                if not antwort:
                    st.error("Kein Modell hat funktioniert. Details:")
                    for f in fehler_liste:
                        st.code(f)
                else:
                    try:
                        daten = parse_json_antwort(antwort.text)
                    except json.JSONDecodeError:
                        st.error("Konnte die Antwort nicht als Tabelle interpretieren. Rohtext:")
                        st.write(antwort.text)
                        daten = None

                    if daten:
                        st.session_state.pdf_bytes = erstelle_pdf(daten)
                        anzahl_einzeln = len(daten.get("einzelauftraege", []))
                        st.success(f"PDF erstellt! (Wochenübersicht + {anzahl_einzeln} Einzelnachweis(e))")

            except Exception as e:
                st.error(f"Fehler beim Verarbeiten der Bilder: {e}")

if st.session_state.pdf_bytes:
    st.download_button(
        label="⬇️ PDF herunterladen",
        data=st.session_state.pdf_bytes,
        file_name="arbeitszeitnachweis.pdf",
        mime="application/pdf",
    )
