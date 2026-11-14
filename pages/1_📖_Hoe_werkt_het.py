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

### 🔥 Eerst de opwarmer
Elke keer dat je begint te studeren, krijg je eerst **3 korte vragen over oude leerstof**: de herhaling van het 1ste jaar (breuken, negatieve getallen, volgorde van bewerkingen) en de rekenregels voor machten.
* **Sommen** kijkt de app zelf na. Let op: een breuk die je nog kan vereenvoudigen, is nog niet af!
* **Regels** zeg of schrijf je eerst zelf; daarna tik je op *Toon het antwoord* en zeg je eerlijk of je het wist.
* Wat je moeilijk vindt, komt **morgen** terug. Wat goed gaat, komt pas na een paar dagen of weken terug.
* Onder **🧰 Meer → 🔁 Herhaling & herinneringen** zie je hoe ver je staat, voeg je eigen kaarten toe (bv. bewijzen uit de les) en download je **herinneringen voor je agenda**, zodat je telefoon je op vaste momenten laat weten dat het tijd is om te studeren.

---

### 🆘 Vast? Toets op komst?
* **Ik zit echt vast:** tik op de knop onder de chat. De bijlesleraar doet dan een gelijkaardige oefening met andere getallen helemaal voor, en daarna probeer jij je eigen oefening opnieuw.
* **Ik heb een toets:** tik in een nieuw gesprek op *📅 Ik heb een toets*, vul het onderwerp en de datum in, en je krijgt een kort oefenplan. Tot de toets zie je bovenaan een knop *Oefen nu*.
* **Overhoor me:** de bijlesleraar stelt je een vraag over iets wat je onlangs geoefend hebt.
* **Openen zonder wachtwoord:** onder *🧰 Meer → Hoe werkt het?* staat je persoonlijke link. Zet die op je beginscherm.

---

### 📚 Terugkijken
* **Mijn gesprekken:** elk gesprek wordt vanzelf bewaard. Tik bovenaan op *📚 Gesprekken* om het terug te lezen, of tik op *Verder praten* om verder te gaan waar je gebleven was.
* **Mijn uitleg-schrift:** heb je een oefening **zelf juist opgelost**? Dan schrijft de bijlesleraar de kern en de uitleg voor je op. Je vindt alles terug bij *📒 Schrift*, per onderwerp en met een zoekvakje. Handig om voor een toets te herhalen!
* **Nieuw gesprek:** met *➕ Nieuw gesprek* (in het zijmenu, ≫ linksboven) begin je opnieuw. Je oude gesprek blijft gewoon bewaard.
""")
