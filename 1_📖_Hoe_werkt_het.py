import streamlit as st

st.set_page_config(
    page_title="Hoe werkt het?",
    page_icon="📖",
    layout="centered"
)

st.title("📖 Hoe werkt deze Wiskundebijles-app?")
st.caption("Sint-Lodewijkscollege Brugge — 2de jaar ASO")

st.markdown("""
Welkom! Deze app is jouw persoonlijke digitale bijlesleraar. Het is nadrukkelijk **geen antwoordmachine** die je huiswerk zomaar overneemt, maar een hulpmiddel om te leren en te controleren.

---

### 🎯 Wat is de opzet?
* **Zelf nadenken staat centraal:** De AI-bijlesleraar geeft je nooit zomaar het eindantwoord. Die helpt je op weg door slimme vragen te stellen en je stapsgewijs te begeleiden.
* **Geen rekenfouten:** Alle rekentools en grafieken worden berekend door strakke Python-logica. Wat daaruit komt, klopt altijd exact.

---

### 🛠️ Hoe gebruik je de tools?
In de zijbalk kun je het **huidige onderwerp** kiezen waar je mee bezig bent. De app toont dan automatisch de tool die daarbij hoort:
1. **Functies & Grafieken:** Controleer rechten ($y = ax + b$) en parabolen.
2. **Statistiek & Centrummaten:** Bereken snel het gemiddelde, de mediaan en de modus van een reeks getallen.
3. **Procenten & Prijscontrole:** Handig voor BTW-berekeningen en procentuele toename of afname.
4. **Algebra & Merkwaardige Producten:** Bekijk de belangrijkste formules als geheugensteuntje.

---

### 🚀 Stappenplan voor je huiswerk:
1. **Upload je taak:** Maak een foto van je oefeningenblad of upload een PDF via de zijbalk.
2. **Typ je poging:** Zet in de chat wat je al geprobeerd hebt (bijvoorbeeld: *"Ik denk dat ik hier de haakjes moet wegwerken, maar ik loop vast"*).
3. **Check en leer:** Gebruik de rekentools in de zijbalk om je eigen antwoorden te controleren.
4. **Test je kennis:** Klik in de zijbalk op de knop om een korte oefentoets te maken en te kijken of je het echt snapt!
""")