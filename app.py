import os
import json
import ssl
import urllib.request
from pathlib import Path
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
from collections import Counter

# Pagina configuratie
st.set_page_config(
    page_title="Wiskundebijles - 2de jaar ASO",
    page_icon="📐",
    layout="centered"
)

ROOT = Path(__file__).resolve().parent
MODEL = "claude-haiku-5-5"
API_URL = "https://api.anthropic.com/v1/messages"
GROEI_FILE = ROOT / "student_groei.json"

def load_persistent_groei():
    data = None
    try:
        data = opslag.lees("groei.json")
    except Exception:
        pass
    if data is None and GROEI_FILE.exists():  # oud bestand van vroeger
        try:
            data = json.loads(GROEI_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = None
    if isinstance(data, dict):
        data.setdefault("weak_points", [])
        data.setdefault("strong_points", [])
        data.setdefault("topics_covered", [])
        return data
    return {
        "total_questions": 0, 
        "topics_covered": [], 
        "weak_points": [],
        "strong_points": [],
        "growth_summary": "Nog geen historische analyse beschikbaar. Begin met oefenen en analyseer de voortgang."
    }

def save_persistent_groei(data):
    try:
        opslag.schrijf("groei.json", data)
    except Exception:
        pass

def load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

load_env()


# ---------------------------------------------------------------- wachtwoord
def _geheim(naam):
    try:
        if naam in st.secrets:
            return str(st.secrets[naam])
    except Exception:
        pass
    return os.environ.get(naam, "")


def controleer_toegang():
    import hmac
    import time
    wachtwoord = _geheim("APP_PASSWORD")
    lokaal = str(st.get_option("server.address") or "") in ("127.0.0.1", "localhost", "::1")
    if not wachtwoord:
        if lokaal:
            return
        st.error("Er is nog geen wachtwoord ingesteld (APP_PASSWORD in de Secrets).")
        st.stop()
    if st.session_state.get("ingelogd"):
        return
    st.title("📐 Wiskundebijles")
    pogingen = st.session_state.get("pogingen", 0)
    if pogingen >= 5 and time.time() - st.session_state.get("laatste_poging", 0) < 60:
        st.warning("Te veel pogingen. Wacht een minuutje en probeer opnieuw.")
        st.stop()
    with st.form("login"):
        invoer = st.text_input("Wachtwoord", type="password")
        if st.form_submit_button("Inloggen", type="primary"):
            if hmac.compare_digest(invoer.encode(), wachtwoord.encode()):
                st.session_state.ingelogd = True
                st.session_state.pogingen = 0
                st.rerun()
            st.session_state.pogingen = pogingen + 1
            st.session_state.laatste_poging = time.time()
            st.error("Dat wachtwoord klopt niet.")
    st.stop()


controleer_toegang()


# ---------------------------------------------------------------- blijvende opslag
from opslag import Opslag  # noqa: E402


@st.cache_resource
def _maak_opslag(token, repo):
    return Opslag(token, repo, ROOT / "bewaard")


opslag = _maak_opslag(_geheim("GITHUB_TOKEN"), _geheim("DATA_REPO"))


def nu():
    from datetime import datetime
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Brussels"))
    except Exception:
        return datetime.now()


def bericht_als_tekst(m):
    """Maakt van een chatbericht iets kleins om te bewaren (zonder foto-data)."""
    content = m["content"]
    if isinstance(content, list):
        tekst = " ".join(p["text"] for p in content if isinstance(p, dict) and p.get("type") == "text")
    elif isinstance(content, dict) and content.get("type") == "image":
        tekst = f"[Grafiek: {content.get('caption')}]"
    else:
        tekst = str(content)
    uit = {"role": m["role"], "text": tekst}
    if m.get("bijlagen"):
        uit["bijlagen"] = m["bijlagen"]
    if m.get("schrift"):
        uit["schrift"] = True
    return uit


def bewaar_gesprek():
    """Bewaart het huidige gesprek (alleen als ze er zelf iets in gevraagd heeft)."""
    berichten = [bericht_als_tekst(m) for m in st.session_state.messages]
    vragen = [b for b in berichten if b["role"] == "user"]
    if not vragen:
        return
    gid = st.session_state.gesprek_id
    titel = vragen[0]["text"].strip() or "(foto)"
    titel = titel if len(titel) <= 70 else titel[:67] + "…"
    tijd = nu().strftime("%Y-%m-%d %H:%M")
    try:
        opslag.schrijf(f"gesprekken/{gid}.json", {"id": gid, "titel": titel, "bijgewerkt": tijd, "berichten": berichten})
        index = [g for g in (opslag.lees("gesprekken/index.json", []) or []) if g.get("id") != gid]
        index.insert(0, {"id": gid, "titel": titel, "bijgewerkt": tijd, "aantal": len(vragen)})
        opslag.schrijf("gesprekken/index.json", index)
    except Exception as e:
        st.toast(f"Let op: het gesprek kon niet bewaard worden ({e}).", icon="⚠️")


SCHRIFT_INSTRUCTIE = """

## Het uitleg-schrift (heel belangrijk)
De leerling heeft een uitleg-schrift in de app waarin ze later kan teruglezen hoe een soort oefening werkt.
ALLEEN op het moment dat ze een oefening zelf juist heeft opgelost en jij bevestigt dat het klopt,
zet je helemaal aan het einde van je bericht één blok in exact deze vorm (geldige JSON, op één regel):
<schrift>{"onderwerp": "kort onderwerp, bv. Merkwaardige producten", "opgave": "de opgave zoals ze er stond", "kern": "de kernregel of het idee in één zin", "uitleg": "de stappen zoals zij ze gezet heeft, kort en duidelijk, met het juiste antwoord"}</schrift>
Dit blok ziet ze niet in de chat; de app bewaart het in haar schrift. Omdat ze de oefening zelf al opgelost
heeft, mag de uitleg de volledige uitwerking bevatten. Zet dit blok NOOIT als de oefening nog niet juist
opgelost is, en nooit meer dan één keer per oefening.
"""


def haal_schrift_eruit(tekst):
    """Haalt het <schrift>-blok uit het antwoord. Geeft (zichtbare tekst, notitie of None)."""
    import re
    notitie = None
    m = re.search(r"<schrift>(.*?)(</schrift>|$)", tekst, re.S)
    if m:
        try:
            ruw = m.group(1).strip()
            ruw = ruw[ruw.find("{"): ruw.rfind("}") + 1]
            d = json.loads(ruw)
            if isinstance(d, dict) and (d.get("opgave") or d.get("uitleg")):
                notitie = {k: str(d.get(k, "")).strip() for k in ("onderwerp", "opgave", "kern", "uitleg")}
        except Exception:
            notitie = None
        tekst = (tekst[:m.start()] + tekst[m.end():]).strip()
    return tekst, notitie


def bewaar_in_schrift(notitie):
    try:
        schrift = opslag.lees("schrift.json", []) or []
        notitie = dict(notitie)
        notitie["datum"] = nu().strftime("%Y-%m-%d")
        notitie["gesprek_id"] = st.session_state.gesprek_id
        notitie["id"] = nu().strftime("%Y%m%d-%H%M%S")
        schrift.insert(0, notitie)
        opslag.schrijf("schrift.json", schrift)
        return True
    except Exception:
        return False


def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()

def build_system_prompt():
    prompt_file = ROOT / "system-prompt.md"
    prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
    return prompt + SCHRIFT_INSTRUCTIE

def call_claude(messages):
    key = ""
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            key = st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
        
    if not key:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        
    if not key:
        return "Fout: Geen API-sleutel gevonden. Controleer of de ANTHROPIC_API_KEY is ingesteld in de Streamlit Secrets."
        
    # Het model denkt eerst (onzichtbaar) na, en dat denkwerk telt mee in max_tokens.
    # Met een te lage limiet was die op vóór het antwoord kwam: dan bleef de ballon leeg.
    # Effort "low": korte bijles-antwoorden hebben geen lang nadenken nodig.
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 8000,
        "output_config": {"effort": "low"},
        "system": build_system_prompt(),
        "messages": messages
    }).encode("utf-8")
    
    req = urllib.request.Request(
        API_URL,
        data=payload,
        method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    )
    
    try:
        with urllib.request.urlopen(req, timeout=180, context=ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        tekst = "\n".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
        if not tekst:
            return ("Oei, ik kreeg geen antwoord klaar. Stel je vraag nog eens, "
                    "of maak ze wat kleiner (bijvoorbeeld één oefening tegelijk).")
        return tekst
    except urllib.error.HTTPError as e:
        error_detail = e.read().decode("utf-8", "ignore")
        return f"API Fout ({e.code}): {error_detail}"
    except Exception as e:
        return f"Er ging iets mis bij het verbinden met de bijlesleraar: {e}"

MAX_FOTO_ZIJDE = 1600  # pixels; groter heeft geen zin en maakt het traag/duur


def maak_bijlage(bytes_data):
    """Geeft (media_type, base64) terug, of None als het bestand onleesbaar is.
    Het type wordt uit de inhoud bepaald (niet uit de bestandsnaam), en foto's
    worden verkleind: een telefoonfoto kan groter zijn dan wat de API aanneemt."""
    import base64
    if bytes_data[:5] == b"%PDF-":
        return "application/pdf", base64.b64encode(bytes_data).decode("utf-8")
    try:
        from PIL import Image, ImageOps
        img = Image.open(BytesIO(bytes_data))
        img = ImageOps.exif_transpose(img)  # telefoonfoto's rechtop zetten
        img = img.convert("RGB")
        img.thumbnail((MAX_FOTO_ZIJDE, MAX_FOTO_ZIJDE))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return "image/jpeg", base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        return None


# Vaste Python-logica voor grafieken
def plot_linear(a, b):
    x = np.linspace(-10, 10, 400)
    y = a * x + b
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(x, y, label=f'$y = {a}x + {b}$')
    ax.axhline(0, color='black', linewidth=1)
    ax.axvline(0, color='black', linewidth=1)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend()
    ax.set_title(f"Grafiek van y = {a}x + {b}")
    buf = BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return buf

def plot_parabola(a, b, c):
    x = np.linspace(-10, 10, 400)
    y = a * x**2 + b * x + c
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(x, y, label=f'$y = {a}x^2 + {b}x + {c}$')
    ax.axhline(0, color='black', linewidth=1)
    ax.axvline(0, color='black', linewidth=1)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend()
    ax.set_title(f"Grafiek van y = {a}x² + {b}x + {c}")
    buf = BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    return buf

# --- Streamlit Interface ---
st.title("📐 Wiskundebijles")
st.caption("Sint-Lodewijkscollege Brugge — 2de jaar ASO")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Dag! Welkom bij de bijles. Zorg dat je pen en papier bij de hand hebt. Wat gaan we vandaag kritisch bekijken?"}
    ]

if "active_documents" not in st.session_state:
    st.session_state.active_documents = []

if "gesprek_id" not in st.session_state:
    st.session_state.gesprek_id = nu().strftime("%Y%m%d-%H%M%S")

MENU = [
    "💬 Chat met Bijlesleraar",
    "📚 Mijn gesprekken",
    "📒 Mijn uitleg-schrift",
    "📖 Hoe werkt het? (Handleiding)",
    "🎯 Adaptieve Foutenbank-toets",
    "📈 Permanente Groei- & Methodiek-analyse",
    "Functies & Grafieken (Rechten / Parabolen)",
    "Statistiek & Centrummaten",
    "Procenten & Verhoudingen (BTW / Prijs)",
    "Algebra & Merkwaardige Producten",
]
# Knoppen elders (bv. "Verder praten") kunnen zo terug naar de chat sturen
if st.session_state.pop("naar_chat", False):
    st.session_state.menu_keuze = MENU[0]

groei_data = load_persistent_groei()

with st.sidebar:
    st.header("📂 Oefeningen of Toetsen")
    # Nieuwe sleutel = leeg upload-vak (anders zette Streamlit de oude bestanden er meteen terug)
    st.session_state.setdefault("upload_sleutel", 0)
    uploaded_files = st.file_uploader(
        "Upload hier meerdere foto's of PDF's",
        type=["jpg", "jpeg", "png", "webp", "pdf"],
        accept_multiple_files=True,
        key=f"upload_{st.session_state.upload_sleutel}",
    )

    if uploaded_files:
        docs_list = []
        schoolwerk_dir = ROOT / "schoolwerk"
        schoolwerk_dir.mkdir(exist_ok=True)

        for uploaded_file in uploaded_files:
            bytes_data = uploaded_file.getvalue()
            try:
                (schoolwerk_dir / uploaded_file.name).write_bytes(bytes_data)
            except Exception:
                pass
            bijlage = maak_bijlage(bytes_data)
            if bijlage is None:
                st.warning(f"'{uploaded_file.name}' kon ik niet lezen. Probeer een andere foto of PDF.")
                continue
            media_type, b64_data = bijlage
            docs_list.append({
                "name": uploaded_file.name,
                "type": media_type,
                "data": b64_data
            })
        st.session_state.active_documents = docs_list
        if docs_list:
            st.success(f"{len(docs_list)} bestand(en) geladen.")
    else:
        st.session_state.active_documents = []

    if st.session_state.active_documents:
        if st.button("🗑️ Alle bijlagen wissen"):
            st.session_state.active_documents = []
            st.session_state.upload_sleutel += 1
            st.rerun()

    st.markdown("---")
    st.subheader("🛠️ Modus & Hulpmiddel")
    
    current_topic = st.selectbox("Kies wat je wilt doen:", MENU, key="menu_keuze")

    if current_topic == "Functies & Grafieken (Rechten / Parabolen)":
        with st.expander("📈 Grafiek Generator", expanded=True):
            figure_type = st.selectbox("Kies een figuur:", ["Rechte lijn", "Parabool ($ax^2+bx+c$)"])
            if figure_type == "Rechte lijn":
                a_line = st.number_input("Waarde van a:", value=2.0, key="a_line_input")
                b_line = st.number_input("Waarde van b:", value=1.0, key="b_line_input")
                if st.button("Genereer lijn"):
                    img_buf = plot_linear(a_line, b_line)
                    st.session_state.messages.append({"role": "assistant", "content": {"type": "image", "data": img_buf, "caption": f"Grafiek van y = {a_line}x + {b_line}"}})
                    st.rerun()
            elif figure_type == "Parabool ($ax^2+bx+c$)":
                a_para = st.number_input("Waarde van a:", value=1.0, key="a_para_input")
                b_para = st.number_input("Waarde van b:", value=0.0, key="b_para_input")
                c_para = st.number_input("Waarde van c:", value=0.0, key="c_para_input")
                if st.button("Genereer parabool"):
                    img_buf = plot_parabola(a_para, b_para, c_para)
                    st.session_state.messages.append({"role": "assistant", "content": {"type": "image", "data": img_buf, "caption": f"Grafiek van y = {a_para}x² + {b_para}x + {c_para}"}})
                    st.rerun()

    elif current_topic == "Statistiek & Centrummaten":
        with st.expander("📊 Statistiek Checker", expanded=True):
            nums_input = st.text_input("Getallen (komma-gescheiden):", "12, 15, 12, 18, 20")
            if st.button("Bereken statistiek"):
                try:
                    nums = [float(n.strip()) for n in nums_input.split(",") if n.strip()]
                    if nums:
                        mean_val = np.mean(nums)
                        median_val = np.median(nums)
                        counts = Counter(nums)
                        max_count = max(counts.values())
                        modes = [k for k, v in counts.items() if v == max_count]
                        res_text = (
                            f"**Statistiek Resultaten:**\n"
                            f"- Aantal: {len(nums)}\n"
                            f"- Gemiddelde: {mean_val:.2f}\n"
                            f"- Mediaan: {median_val}\n"
                            f"- Modus: {', '.join(map(str, modes)) if max_count > 1 else 'Geen unieke modus'}"
                        )
                        st.success(res_text)
                except Exception:
                    st.error("Vul geldige getallen in.")

    elif current_topic == "Procenten & Verhoudingen (BTW / Prijs)":
        with st.expander("📉 Procenten & Prijscontrole", expanded=True):
            calc_choice = st.selectbox("Type:", ["Procent van een getal", "Procentuele toename/afname"])
            if calc_choice == "Procent van een getal":
                base_val = st.number_input("Getal:", value=120.0, key="base_v")
                pct_val = st.number_input("Percentage (%):", value=21.0, key="pct_v")
                if st.button("Bereken deel"):
                    ans = (base_val * pct_val) / 100
                    st.info(f"{pct_val}% van het getal is **{ans}**")
            else:
                old_v = st.number_input("Oude waarde:", value=80.0, key="old_val")
                new_v = st.number_input("Nieuwe waarde:", value=100.0, key="new_val")
                if st.button("Bereken verandering"):
                    if old_v != 0:
                        diff = ((new_v - old_v) / old_v) * 100
                        st.info(f"Verschil: **{diff:+.2f}%**")

    elif current_topic == "Algebra & Merkwaardige Producten":
        with st.expander("🧩 Formules & Geheugensteun", expanded=True):
            st.latex(r"(a + b)^2 = a^2 + 2ab + b^2")
            st.latex(r"(a - b)^2 = a^2 - 2ab + b^2")
            st.latex(r"(a + b)(a - b) = a^2 - b^2")

    st.markdown("---")
    st.subheader("🌟 Permanente Profiel")
    st.metric(label="Totaal gestelde vragen", value=groei_data.get("total_questions", 0))
    st.markdown(f"**Behandelde onderwerpen:** {len(groei_data.get('topics_covered', []))}")
    st.markdown(f"**Sterke punten:** {len(groei_data.get('strong_points', []))}")
    st.markdown(f"**Aandachtspunten:** {len(groei_data.get('weak_points', []))}")

    st.markdown("---")
    if st.button("➕ Nieuw gesprek", help="Dit gesprek blijft bewaard bij 'Mijn gesprekken'."):
        st.session_state.messages = [
            {"role": "assistant", "content": "Oké, een nieuw gesprek! Je vorige gesprek staat bij 📚 Mijn gesprekken. Wat pakken we aan?"}
        ]
        st.session_state.gesprek_id = nu().strftime("%Y%m%d-%H%M%S")
        st.session_state.active_documents = []
        st.session_state.upload_sleutel += 1
        st.rerun()

def toon_bericht(rol, tekst, bijlagen=None, schrift=False):
    with st.chat_message(rol):
        if bijlagen:
            st.caption("📎 Bijlagen: " + ", ".join(bijlagen))
        st.write(tekst)
        if schrift:
            st.caption("📒 Uitleg bewaard in je uitleg-schrift")


# Hoofdscherm logica
if current_topic == "📚 Mijn gesprekken":
    st.title("📚 Mijn gesprekken")
    try:
        index = opslag.lees("gesprekken/index.json", []) or []
    except Exception as e:
        index = []
        st.error(f"De gesprekken konden niet geladen worden: {e}")
    if not index:
        st.info("Nog geen bewaarde gesprekken. Elk gesprek in de chat wordt vanzelf bewaard.")
    zoek = st.text_input("🔎 Zoek in de titels", "") if len(index) > 5 else ""
    for g in index:
        if zoek and zoek.lower() not in g.get("titel", "").lower():
            continue
        with st.expander(f"{g.get('bijgewerkt', '')} — {g.get('titel', '')}"):
            try:
                gesprek = opslag.lees(f"gesprekken/{g['id']}.json", {}) or {}
            except Exception:
                gesprek = {}
            berichten = gesprek.get("berichten", [])
            for b in berichten:
                toon_bericht(b["role"], b["text"], b.get("bijlagen"), b.get("schrift"))
            if berichten and st.button("💬 Verder praten in dit gesprek", key=f"verder_{g['id']}"):
                st.session_state.messages = [
                    {"role": b["role"], "content": b["text"], "bijlagen": b.get("bijlagen"), "schrift": b.get("schrift")}
                    for b in berichten
                ]
                st.session_state.gesprek_id = g["id"]
                st.session_state.naar_chat = True
                st.rerun()
    st.caption(f"Bewaard in: {opslag.uitleg}")

elif current_topic == "📒 Mijn uitleg-schrift":
    st.title("📒 Mijn uitleg-schrift")
    st.markdown("Telkens als je een oefening **zelf juist oplost**, schrijft de bijlesleraar hier de kern en de uitleg op. Zo kan je het later terugvinden.")
    try:
        schrift = opslag.lees("schrift.json", []) or []
    except Exception as e:
        schrift = []
        st.error(f"Het schrift kon niet geladen worden: {e}")
    if not schrift:
        st.info("Je schrift is nog leeg. Los een oefening op in de chat, dan verschijnt de uitleg hier.")
    else:
        onderwerpen = sorted({n.get("onderwerp") or "Overig" for n in schrift})
        c1, c2 = st.columns(2)
        keuze = c1.selectbox("Onderwerp", ["Alle onderwerpen"] + onderwerpen)
        zoek = c2.text_input("🔎 Zoek", "")
        for i, n in enumerate(schrift):
            if keuze != "Alle onderwerpen" and (n.get("onderwerp") or "Overig") != keuze:
                continue
            alles = " ".join(str(v) for v in n.values()).lower()
            if zoek and zoek.lower() not in alles:
                continue
            with st.expander(f"{n.get('onderwerp') or 'Overig'} — {n.get('opgave', '')[:60]}"):
                st.markdown(f"**Opgave:** {n.get('opgave', '')}")
                st.success(f"**Kern:** {n.get('kern', '')}")
                st.markdown("**Uitleg:**")
                st.write(n.get("uitleg", ""))
                st.caption(f"Bewaard op {n.get('datum', '')}")
                if st.button("🗑️ Uit mijn schrift halen", key=f"weg_{n.get('id', i)}"):
                    schrift.pop(i)
                    try:
                        opslag.schrijf("schrift.json", schrift)
                    except Exception as e:
                        st.error(f"Lukte niet: {e}")
                    st.rerun()

elif current_topic == "📖 Hoe werkt het? (Handleiding)":
    st.title("📖 Handleiding")
    st.markdown("Deze app bewaart de behandelde lesmethodes, sterke vaardigheden en aandachtspunten permanent in een lokaal profiel.")
elif current_topic == "🎯 Adaptieve Foutenbank-toets":
    st.title("🎯 Adaptieve Foutenbank-toets")
    st.markdown("Deze toets is gebaseerd op de opgeslagen zwakke punten en methodieken uit eerdere sessies.")
    
    weak_pts = groei_data.get("weak_points", [])
    if weak_pts:
        st.info(f"Bekende aandachtsgebieden: {', '.join(weak_pts)}")
    else:
        st.warning("Nog geen specifieke zwakke punten geregistreerd.")

    if st.button("Genereer Foutenbank-toets nu"):
        with st.spinner("De coach stelt een gerichte toets samen..."):
            prompt_toets = f"Genereer een gerichte oefentoets van 3 pittige vragen voor een leerling in het 2de jaar ASO, gebaseerd op deze bekende zwakke punten: {weak_pts}. Volg exact de behandelde methodiek."
            res = call_claude([{"role": "user", "content": prompt_toets}])
            st.session_state.messages.append({"role": "assistant", "content": res})
            st.success("Toets gegenereerd! Schakel terug naar 'Chat met Bijlesleraar' om te beginnen.")
elif current_topic == "📈 Permanente Groei- & Methodiek-analyse":
    st.title("📈 Permanente Groei- & Methodiek-analyse")
    st.markdown("Overzicht van de opgeslagen leerstof, methodieken en voortgang over alle sessies heen.")
    
    st.subheader("📚 Behandelde Onderwerpen & Methodieken")
    topics = groei_data.get("topics_covered", [])
    if topics:
        for t in topics:
            st.markdown(f"- {t}")
    else:
        st.write("Nog geen onderwerpen vastgelegd.")

    st.subheader("💪 Geregistreerde Sterke Punten")
    strongs = groei_data.get("strong_points", [])
    if strongs:
        for s in strongs:
            st.markdown(f"- {s}")
    else:
        st.write("Nog geen sterke punten vastgelegd.")

    st.subheader("📌 Uitgebreide Voortgangsrapportage")
    st.info(groei_data.get("growth_summary", "Nog geen analyse beschikbaar."))
    
    if st.button("Genereer bijgewerkte analyse"):
        with st.spinner("De coach analyseert het permanente profiel..."):
            analysis_prompt = (
                "Analyseer de historisch opgeslagen gegevens van de leerling in het 2de jaar ASO en geef een professionele voortgangsrapportage "
                "waarin de juiste methodieken, sterke punten en valkuilen worden vastgelegd."
            )
            res = call_claude([{"role": "user", "content": analysis_prompt}])
            groei_data["growth_summary"] = res
            save_persistent_groei(groei_data)
            st.success("Analyse bijgewerkt!")
            st.rerun()
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            content = msg["content"]
            if msg.get("bijlagen"):
                st.caption("📎 Bijlagen: " + ", ".join(msg["bijlagen"]))
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        st.write(part["text"])
            elif isinstance(content, dict) and content.get("type") == "image":
                st.image(content["data"], caption=content.get("caption"))
            else:
                st.write(content)
            if msg.get("schrift"):
                st.caption("📒 Uitleg bewaard in je uitleg-schrift")

    if prompt := st.chat_input("Schrijf hier je vraag of je uitwerking..."):
        groei_data["total_questions"] = groei_data.get("total_questions", 0) + 1
        
        for doc in st.session_state.active_documents:
            if doc["name"] not in groei_data["topics_covered"]:
                groei_data["topics_covered"].append(doc["name"])
                
        save_persistent_groei(groei_data)

        content_parts = []
        for doc in st.session_state.active_documents:
            if doc["type"].startswith("image/"):
                content_parts.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": doc["type"], "data": doc["data"]}
                })
            elif doc["type"] == "application/pdf":
                content_parts.append({
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf", "data": doc["data"]}
                })
        
        content_parts.append({"type": "text", "text": prompt})
        bijlage_namen = [d["name"] for d in st.session_state.active_documents]
        st.session_state.messages.append({"role": "user", "content": content_parts, "bijlagen": bijlage_namen})
        
        with st.chat_message("user"):
            if st.session_state.active_documents:
                names = ", ".join([d["name"] for d in st.session_state.active_documents])
                st.caption(f"📎 Bijlagen: {names}")
            st.write(prompt)
            
        with st.spinner("De coach analyseert je uitwerking en methode..."):
            api_messages = []
            for i, m in enumerate(st.session_state.messages):
                role = m["role"]
                content = m["content"]
                if isinstance(content, list):
                    texts = [p["text"] for p in content if isinstance(p, dict) and p.get("type", "") == "text"]
                    api_messages.append({"role": role, "content": " ".join(texts)})
                elif isinstance(content, dict) and content.get("type") == "image":
                    api_messages.append({"role": role, "content": f"[Afbeelding getoond: {content.get('caption')}]"})
                else:
                    api_messages.append({"role": role, "content": content})
            api_messages[-1]["content"] = content_parts
            response_text = call_claude(api_messages)
            response_text, notitie = haal_schrift_eruit(response_text)
            in_schrift = bool(notitie) and bewaar_in_schrift(notitie)

        with st.chat_message("assistant"):
            st.write(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text, "schrift": in_schrift})
        bewaar_gesprek()
        if in_schrift:
            st.toast("📒 Bewaard in je uitleg-schrift!")
        st.rerun()