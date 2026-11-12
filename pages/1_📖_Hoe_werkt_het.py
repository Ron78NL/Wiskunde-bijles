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
Bovenaan in de app tik je op **🧰 Meer** en kies je het onderwerp waar je mee bezig bent. De app toont dan de tool die daarbij hoort:
1. **Functies & Grafieken:** Controleer rechten ($y = ax + b$) en parabolen.
2. **Statistiek & Centrummaten:** Bereken snel het gemiddelde, de mediaan en de modus van een reeks getallen.
3. **Procenten & Prijscontrole:** Handig voor BTW-berekeningen en procentuele toename of afname.
4. **Algebra & Merkwaardige Producten:** Bekijk de belangrijkste formules als geheugensteuntje.

---

### 🚀 Stappenplan voor je huiswerk:
1. **Stuur je taak mee:** tik op het ＋-knopje links in het tekstvak onderaan, kies een foto (of maak er meteen een) of een PDF, en typ erbij wat je wil weten. De foto gaat mee met die ene vraag; de bijlesleraar onthoudt hem voor de vervolgvragen.
2. **Typ je poging:** Zet in de chat wat je al geprobeerd hebt (bijvoorbeeld: *"Ik denk dat ik hier de haakjes moet wegwerken, maar ik loop vast"*).
3. **Check en leer:** Gebruik de rekentools onder **🧰 Meer** om je eigen antwoorden te controleren.
4. **Test je kennis:** Kies onder **🧰 Meer** de *Foutenbank-toets* voor een korte oefentoets en kijk of je het echt snapt!

---

### 📚 Terugkijken
* **Mijn gesprekken:** elk gesprek wordt vanzelf bewaard. Tik bovenaan op *📚 Gesprekken* om het terug te lezen, of tik op *Verder praten* om verder te gaan waar je gebleven was.
* **Mijn uitleg-schrift:** heb je een oefening **zelf juist opgelost**? Dan schrijft de bijlesleraar de kern en de uitleg voor je op. Je vindt alles terug bij *📒 Schrift*, per onderwerp en met een zoekvakje. Handig om voor een toets te herhalen!
* **Nieuw gesprek:** met *➕ Nieuw gesprek* (in het zijmenu, ≫ linksboven) begin je opnieuw. Je oude gesprek blijft gewoon bewaard.
""")
