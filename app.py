import os
import re
import sys
import json
import ssl
import base64
import urllib.error
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
API_URL = "https://api.anthropic.com/v1/messages"
GROEI_FILE = ROOT / "student_groei.json"  # oud, alleen nog om over te nemen

# iPhone-foto's (HEIC) leesbaar maken; zonder dit pakket kon de app ze niet openen
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
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


# Model kan je wijzigen met MODEL in de Secrets (bv. claude-sonnet-5-5: leest handschrift beter, duurder)
MODEL = _geheim("MODEL") or "claude-haiku-5-5"


def link_code():
    """Geheime code voor de persoonlijke inloglink, afgeleid van het wachtwoord.
    Verander je APP_PASSWORD, dan werkt een oude link niet meer."""
    import hmac
    import hashlib
    wachtwoord = _geheim("APP_PASSWORD")
    if not wachtwoord:
        return ""
    return hmac.new(wachtwoord.encode(), b"inloglink-wiskunde", hashlib.sha256).hexdigest()[:24]


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
    # Persoonlijke link (?k=...) vanaf het beginscherm: meteen binnen, geen wachtwoord typen
    code = str(st.query_params.get("k", ""))
    if code and hmac.compare_digest(code.encode(), link_code().encode()):
        st.session_state.ingelogd = True
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


import herhaling as hh  # noqa: E402

OPWARMER_AANTAL = 3      # zoveel vragen over oude leerstof bij het begin van elke studiesessie
OPWARMER_PAUZE_UUR = 3   # binnen zoveel uur na een opwarmer hoeft ze er geen nieuwe te doen


def lees_herhaling():
    """Voortgang van de herhaalkaarten (doosjes), één keer per bezoek opgehaald."""
    if "herhaling" not in st.session_state:
        try:
            d = opslag.lees("herhaling.json", {}) or {}
        except Exception as e:
            print(f"herhaling.json niet geladen: {e}", file=sys.stderr)
            d = {}
        if not isinstance(d, dict):
            d = {}
        d.setdefault("kaarten", {})
        d.setdefault("eigen", [])
        d.setdefault("log", [])
        st.session_state.herhaling = d
    return st.session_state.herhaling


def bewaar_herhaling():
    try:
        opslag.schrijf("herhaling.json", st.session_state.herhaling)
    except Exception as e:
        print(f"Herhaling niet bewaard: {e}", file=sys.stderr)


def app_link():
    """De persoonlijke link naar de app (zonder wachtwoord), of het gewone adres."""
    try:
        basis = str(st.context.url).split("?")[0].rstrip("/")
    except Exception:
        basis = ""
    basis = basis or "https://wiskunde-bijles-dochter.streamlit.app"
    if "localhost" in basis or "127.0.0.1" in basis:
        basis = "https://wiskunde-bijles-dochter.streamlit.app"
    return f"{basis}/?k={link_code()}" if link_code() else basis


def melding(tekst, icoon="✅"):
    """Toont een melding, ook als de pagina meteen daarna herladen wordt."""
    st.session_state.setdefault("meldingen", []).append((tekst, icoon))


# ---------------------------------------------------------------- groeiprofiel
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
        "growth_summary": "Nog geen analyse beschikbaar. Oefen eerst wat en klik dan op 'Genereer bijgewerkte analyse'."
    }


def save_persistent_groei(data):
    try:
        opslag.schrijf("groei.json", data)
    except Exception as e:
        print(f"Groeiprofiel niet bewaard: {e}", file=sys.stderr)


# ---------------------------------------------------------------- bijlagen
MAX_FOTO_ZIJDE = 1600  # pixels; groter heeft geen zin en maakt het traag/duur
MAX_PDF_MB = 20
BESTANDSTYPES = ["jpg", "jpeg", "png", "webp", "heic", "heif", "pdf"]
HOUD_FOTOBERICHTEN = 3  # zoveel recente berichten-met-foto's blijft de bijlesleraar 'zien'


def maak_bijlage(bytes_data):
    """Geeft (media_type, base64, jpeg_bytes) terug, of None als het bestand onleesbaar is.
    Het type wordt uit de inhoud bepaald (niet uit de bestandsnaam), iPhone-foto's (HEIC)
    worden omgezet, en foto's worden verkleind: een telefoonfoto is vaak te groot voor de API."""
    if bytes_data[:5] == b"%PDF-":
        if len(bytes_data) > MAX_PDF_MB * 1024 * 1024:
            return None
        return "application/pdf", base64.b64encode(bytes_data).decode("utf-8"), None
    try:
        from PIL import Image, ImageOps
        img = Image.open(BytesIO(bytes_data))
        # Grote JPEG's (bv. 50 MP Motorola) meteen verkleind inlezen: sneller en zuiniger
        img.draft("RGB", (MAX_FOTO_ZIJDE, MAX_FOTO_ZIJDE))
        img = ImageOps.exif_transpose(img)  # telefoonfoto's rechtop zetten
        img = img.convert("RGB")
        img.thumbnail((MAX_FOTO_ZIJDE, MAX_FOTO_ZIJDE))
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        jpeg = buf.getvalue()
        return "image/jpeg", base64.b64encode(jpeg).decode("utf-8"), jpeg
    except Exception:
        return None


def verwerk_bestanden(bestanden):
    """Zet geüploade bestanden om. Geeft (api-delen, foto's als jpeg, namen, mislukte namen)."""
    delen, fotos, namen, mislukt = [], [], [], []
    for f in bestanden or []:
        b = maak_bijlage(f.getvalue())
        if b is None:
            mislukt.append(f.name)
            continue
        media_type, b64, jpeg = b
        namen.append(f.name)
        if jpeg is not None:
            fotos.append(jpeg)
            delen.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}})
        else:
            delen.append({"type": "document", "source": {"type": "base64", "media_type": media_type, "data": b64}})
    return delen, fotos, namen, mislukt


def laad_foto(pad):
    cache = st.session_state.setdefault("foto_cache", {})
    if pad not in cache:
        try:
            cache[pad] = opslag.lees_bytes(pad)
        except Exception:
            cache[pad] = None
    return cache[pad]


def fotos_van(m):
    if m.get("fotos"):
        return m["fotos"]
    return [f for f in (laad_foto(p) for p in m.get("foto_paden") or []) if f]


# ---------------------------------------------------------------- gesprekken bewaren
def tekst_van(m):
    content = m["content"]
    if isinstance(content, list):
        return " ".join(p["text"] for p in content if isinstance(p, dict) and p.get("type") == "text")
    if isinstance(content, dict) and content.get("type") == "image":
        return f"[Grafiek: {content.get('caption')}]"
    return str(content)


def bericht_als_tekst(m):
    """Maakt van een chatbericht iets kleins om te bewaren (foto's staan apart)."""
    uit = {"role": m["role"], "text": tekst_van(m)}
    for sleutel in ("bijlagen", "foto_paden"):
        if m.get(sleutel):
            uit[sleutel] = m[sleutel]
    if m.get("schrift"):
        uit["schrift"] = True
    return uit


def bewaar_gesprek():
    """Bewaart het huidige gesprek, met de foto's (alleen als ze er zelf iets in gevraagd heeft)."""
    berichten = st.session_state.messages
    vragen = [m for m in berichten if m["role"] == "user"]
    if not vragen:
        return
    gid = st.session_state.gesprek_id
    try:
        for i, m in enumerate(berichten):
            if m.get("fotos") and not m.get("foto_paden"):
                paden = []
                for n, jpeg in enumerate(m["fotos"]):
                    pad = f"bijlagen/{gid}/{i}_{n}.jpg"
                    opslag.schrijf_bytes(pad, jpeg)
                    st.session_state.setdefault("foto_cache", {})[pad] = jpeg
                    paden.append(pad)
                m["foto_paden"] = paden
        titel = tekst_van(vragen[0]).strip() or "(foto)"
        titel = titel if len(titel) <= 70 else titel[:67] + "…"
        tijd = nu().strftime("%Y-%m-%d %H:%M")
        opslag.schrijf(f"gesprekken/{gid}.json", {
            "id": gid, "titel": titel, "bijgewerkt": tijd,
            "berichten": [bericht_als_tekst(m) for m in berichten],
        })
        index = [g for g in (opslag.lees("gesprekken/index.json", []) or []) if g.get("id") != gid]
        index.insert(0, {"id": gid, "titel": titel, "bijgewerkt": tijd, "aantal": len(vragen)})
        opslag.schrijf("gesprekken/index.json", index)
    except Exception as e:
        print(f"Gesprek niet bewaard: {e}", file=sys.stderr)
        melding(f"Let op: het gesprek kon niet bewaard worden ({e}).", "⚠️")


# ---------------------------------------------------------------- uitleg-schrift
EXTRA_INSTRUCTIES = """

## Foto's en PDF's van de leerling
Stuurt ze een foto of PDF mee, kijk die dan eerst goed na en verwijs naar wat je ziet
(bijvoorbeeld welke oefening of welk nummer). Kan je iets niet goed lezen (wazig, scheef,
te donker, afgesneden), zeg dat dan duidelijk en vraag om een nieuwe foto van dichterbij.
Doe nooit alsof er geen foto is.

## Het uitleg-schrift (heel belangrijk)
De leerling heeft een uitleg-schrift in de app waarin ze later kan teruglezen hoe een soort oefening werkt.
ALLEEN op het moment dat ze een oefening zelf juist heeft opgelost en jij bevestigt dat het klopt,
zet je helemaal aan het einde van je bericht één blok in exact deze vorm (geldige JSON, op één regel):
<schrift>{"onderwerp": "kort onderwerp, bv. Merkwaardige producten", "opgave": "de opgave zoals ze er stond", "kern": "de kernregel of het idee in één zin", "uitleg": "de stappen zoals zij ze gezet heeft, kort en duidelijk, met het juiste antwoord"}</schrift>
Dit blok ziet ze niet in de chat; de app bewaart het in haar schrift. Omdat ze de oefening zelf al opgelost
heeft, mag de uitleg de volledige uitwerking bevatten. Zet dit blok NOOIT als de oefening nog niet juist
opgelost is, en nooit meer dan één keer per oefening.
"""


def haal_blok_eruit(tekst, naam):
    """Haalt een <naam>{json}</naam>-blok uit een antwoord. Geeft (zichtbare tekst, dict of None)."""
    gevonden = None
    m = re.search(rf"<{naam}>(.*?)(</{naam}>|$)", tekst, re.S)
    if m:
        try:
            ruw = m.group(1).strip()
            ruw = ruw[ruw.find("{"): ruw.rfind("}") + 1]
            d = json.loads(ruw)
            gevonden = d if isinstance(d, dict) else None
        except Exception:
            gevonden = None
        tekst = (tekst[:m.start()] + tekst[m.end():]).strip()
    return tekst, gevonden


def haal_schrift_eruit(tekst):
    tekst, d = haal_blok_eruit(tekst, "schrift")
    if d and (d.get("opgave") or d.get("uitleg")):
        return tekst, {k: str(d.get(k, "")).strip() for k in ("onderwerp", "opgave", "kern", "uitleg")}
    return tekst, None


def lees_lijst(pad):
    """Leest een lijst (schrift, toetsen) één keer per bezoek; daarna uit het geheugen."""
    cache = st.session_state.setdefault("lijsten", {})
    if pad not in cache:
        try:
            cache[pad] = opslag.lees(pad, []) or []
        except Exception as e:
            print(f"{pad} niet geladen: {e}", file=sys.stderr)
            return []
    return cache[pad]


def schrijf_lijst(pad, lijst):
    opslag.schrijf(pad, lijst)
    st.session_state.setdefault("lijsten", {})[pad] = lijst


def bewaar_in_schrift(notitie):
    try:
        schrift = list(lees_lijst("schrift.json"))
        notitie = dict(notitie)
        notitie["datum"] = nu().strftime("%Y-%m-%d")
        notitie["gesprek_id"] = st.session_state.gesprek_id
        notitie["id"] = nu().strftime("%Y%m%d-%H%M%S")
        schrift.insert(0, notitie)
        schrijf_lijst("schrift.json", schrift)
        return True
    except Exception as e:
        print(f"Schrift niet bewaard: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------- Claude
def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def build_system_prompt():
    prompt_file = ROOT / "system-prompt.md"
    prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
    return prompt + EXTRA_INSTRUCTIES


def call_claude(messages, system=None):
    key = _geheim("ANTHROPIC_API_KEY")
    if not key:
        return "Er is nog geen API-sleutel ingesteld (ANTHROPIC_API_KEY in de Secrets). Vraag het aan papa."

    # Het model denkt eerst (onzichtbaar) na, en dat denkwerk telt mee in max_tokens.
    # Met een te lage limiet was die op vóór het antwoord kwam: dan bleef de ballon leeg.
    # Effort "low": korte bijles-antwoorden hebben geen lang nadenken nodig.
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 8000,
        "output_config": {"effort": "low"},
        "system": system if system is not None else build_system_prompt(),
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
        # Details naar het logboek (Streamlit 'Manage app'), een begrijpelijke zin naar haar
        print(f"API-fout {e.code}: {e.read().decode('utf-8', 'ignore')[:2000]}", file=sys.stderr)
        if e.code in (429, 500, 502, 503, 529):
            return "De bijlesleraar is even heel druk. Wacht een halve minuut en stuur je vraag opnieuw."
        if e.code == 400:
            return ("Er ging iets mis met je bericht of je bijlage. Probeer een andere foto, "
                    "of begin een nieuw gesprek.")
        return f"De bijlesleraar kon niet antwoorden (fout {e.code}). Probeer het straks opnieuw."
    except Exception as e:
        print(f"Verbindingsfout: {e}", file=sys.stderr)
        return "Ik kan de bijlesleraar nu niet bereiken. Controleer je internet en probeer opnieuw."


def api_berichten():
    """Bouwt het gesprek voor de API. Foto's van de laatste paar berichten-met-foto's
    gaan mee, zodat de bijlesleraar ze bij vervolgvragen nog ziet; PDF's alleen de laatste."""
    msgs = st.session_state.messages
    met_bijlage = [i for i, m in enumerate(msgs)
                   if m["role"] == "user" and (m.get("delen") or m.get("foto_paden"))]
    houd_fotos = set(met_bijlage[-HOUD_FOTOBERICHTEN:])
    houd_pdf = set(met_bijlage[-1:])
    uit = []
    for i, m in enumerate(msgs):
        tekst = tekst_van(m).strip() or "(zie bijlage)"
        if i in houd_fotos:
            delen = m.get("delen")
            if delen is None:  # ouder gesprek dat verder gezet wordt: foto's terughalen
                delen = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                      "data": base64.b64encode(f).decode("ascii")}}
                         for f in fotos_van(m)]
            if i not in houd_pdf:
                delen = [d for d in delen if d["type"] != "document"]
            uit.append({"role": m["role"], "content": delen + [{"type": "text", "text": tekst}]})
        else:
            if m["role"] == "user" and m.get("bijlagen"):
                tekst = f"[Eerder meegestuurd: {', '.join(m['bijlagen'])}]\n{tekst}"
            uit.append({"role": m["role"], "content": tekst})
    return uit


# ---------------------------------------------------------------- grafieken
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


# ---------------------------------------------------------------- scherm
st.subheader("📐 Wiskundebijles")

for tekst, icoon in st.session_state.pop("meldingen", []):
    st.toast(tekst, icon=icoon)

WELKOM = ("Dag! Welkom bij de bijles. Zorg dat je pen en papier bij de hand hebt. Wat gaan we vandaag bekijken?\n\n"
          "Tip: met het ＋-knopje links in het tekstvak voeg je een foto of PDF van je oefening toe.")

if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": WELKOM}]

if "gesprek_id" not in st.session_state:
    st.session_state.gesprek_id = nu().strftime("%Y%m%d-%H%M%S")

if "groei" not in st.session_state:  # één keer per bezoek ophalen, niet bij elke klik
    st.session_state.groei = load_persistent_groei()
groei_data = st.session_state.groei

HOOFDMENU = ["💬 Chat", "📚 Gesprekken", "📒 Schrift", "🧰 Meer"]
MEER = [
    "📖 Hoe werkt het? (Handleiding)",
    "🔁 Herhaling & herinneringen",
    "🎯 Adaptieve Foutenbank-toets",
    "📈 Permanente Groei- & Methodiek-analyse",
    "Functies & Grafieken (Rechten / Parabolen)",
    "Statistiek & Centrummaten",
    "Procenten & Verhoudingen (BTW / Prijs)",
    "Algebra & Merkwaardige Producten",
]
# Knoppen elders (bv. "Verder praten") kunnen zo terug naar de chat sturen
if st.session_state.pop("naar_chat", False):
    st.session_state.hoofd = HOOFDMENU[0]

# Grote knoppen bovenaan: op een telefoon veel handiger dan het zijmenu
hoofd = st.segmented_control("Menu", HOOFDMENU, key="hoofd", default=HOOFDMENU[0],
                             label_visibility="collapsed") or HOOFDMENU[0]
if hoofd == "🧰 Meer":
    current_topic = st.selectbox("Wat wil je doen?", MEER, key="meer_keuze")
else:
    current_topic = {"💬 Chat": "💬 Chat met Bijlesleraar", "📚 Gesprekken": "📚 Mijn gesprekken",
                     "📒 Schrift": "📒 Mijn uitleg-schrift"}[hoofd]


def nieuw_gesprek(welkom):
    st.session_state.messages = [{"role": "assistant", "content": welkom}]
    st.session_state.gesprek_id = nu().strftime("%Y%m%d-%H%M%S")


with st.sidebar:
    if st.button("➕ Nieuw gesprek", help="Je huidige gesprek blijft bewaard bij 'Mijn gesprekken'.",
                 width="stretch"):
        nieuw_gesprek("Oké, een nieuw gesprek! Je vorige gesprek staat bij 📚 Mijn gesprekken. Wat pakken we aan?")
        st.session_state.naar_chat = True
        st.rerun()

    st.markdown("---")
    st.subheader("🌟 Mijn profiel")
    st.metric(label="Totaal gestelde vragen", value=groei_data.get("total_questions", 0))
    st.markdown(f"**Behandelde onderwerpen:** {len(groei_data.get('topics_covered', []))}")
    st.markdown(f"**Sterke punten:** {len(groei_data.get('strong_points', []))}")
    st.markdown(f"**Aandachtspunten:** {len(groei_data.get('weak_points', []))}")
    _h = lees_herhaling()
    _n = len(hh.te_herhalen(_h["kaarten"], nu().date(), _h["eigen"]))
    st.markdown(f"**🔁 Vandaag te herhalen:** {_n} kaart{'en' if _n != 1 else ''}")


def toon_bericht(m):
    content = m["content"]
    with st.chat_message(m["role"]):
        fotos = fotos_van(m) if m["role"] == "user" else []
        if fotos:
            st.image(fotos, width=160)
        andere = [n for n in (m.get("bijlagen") or []) if n.lower().endswith(".pdf")]
        if andere or (m.get("bijlagen") and not fotos):
            st.caption("📎 " + ", ".join(andere or m["bijlagen"]))
        if isinstance(content, dict) and content.get("type") == "image":
            st.image(content["data"], caption=content.get("caption"))
        else:
            st.write(tekst_van(m))
        if m.get("mislukt"):
            st.warning("Niet meegestuurd (kon ik niet openen): " + ", ".join(m["mislukt"])
                       + ". Probeer een nieuwe foto.")
        if m.get("schrift"):
            st.caption("📒 Uitleg bewaard in je uitleg-schrift")


def profiel_gegevens():
    """Wat we echt weten over haar voortgang, om aan de bijlesleraar te geven."""
    schrift = lees_lijst("schrift.json")
    try:
        index = opslag.lees("gesprekken/index.json", []) or []
    except Exception:
        index = []
    return schrift, index


# ---------------------------------------------------------------- opwarmer (oude leerstof eerst)
def opwarmer_nodig():
    if st.session_state.get("opw_extra"):
        return True
    if st.session_state.get("opwarmer_klaar"):
        return False
    laatst = lees_herhaling().get("laatste_opwarmer")
    if laatst:
        from datetime import datetime, timedelta
        try:
            if nu() - datetime.fromisoformat(laatst) < timedelta(hours=OPWARMER_PAUZE_UUR):
                st.session_state.opwarmer_klaar = True
                return False
        except Exception:
            pass
    return True


def _volgende_kaart(o):
    o.update({"i": o["i"] + 1, "opgave": None, "fase": "vraag", "pogingen": 0, "bijna": False, "boodschap": None})


def _noteer(kaart_id, goed, vandaag, o):
    h = lees_herhaling()
    hh.werk_bij(h["kaarten"], kaart_id, goed, vandaag)
    if goed:
        o["juist"] += 1
    if o["i"] + 1 >= len(o["ids"]):  # laatste kaart: opwarmer is klaar
        h["laatste_opwarmer"] = nu().isoformat(timespec="seconds")
        h["log"] = ([{"datum": nu().strftime("%Y-%m-%d %H:%M"), "juist": o["juist"], "aantal": len(o["ids"])}]
                    + h.get("log", []))[:60]
    bewaar_herhaling()
    _volgende_kaart(o)


def toon_opwarmer(vandaag):
    import random
    from datetime import timedelta
    h = lees_herhaling()
    o = st.session_state.get("opw")
    if o is None:
        voorrang = None
        binnenkort = sorted((t for t in lees_lijst("toetsen.json")
                             if vandaag.isoformat() <= t.get("datum", "") <= (vandaag + timedelta(days=7)).isoformat()),
                            key=lambda t: t["datum"])
        for t in binnenkort:
            voorrang = hh.groep_voor_toets(t.get("onderwerp"))
            if voorrang:
                break
        ids = hh.kies_opwarmer(h["kaarten"], vandaag, OPWARMER_AANTAL, voorrang, h["eigen"])
        o = st.session_state.opw = {"ids": ids, "i": 0, "opgave": None, "fase": "vraag", "pogingen": 0,
                                    "bijna": False, "boodschap": None, "juist": 0}
    kaarten = {k["id"]: k for k in hh.alle_kaarten(h["eigen"])}
    n = len(o["ids"])

    st.markdown("#### 🔥 Opwarmer: eerst even oude leerstof")
    if o["i"] >= n:
        st.success(f"Klaar met de opwarmer! {o['juist']} van de {n} meteen juist. "
                   "Wat je moeilijk vond, komt morgen terug; wat goed ging, pas later.")
        if st.button("💬 Verder naar de bijles", type="primary", width="stretch"):
            st.session_state.opwarmer_klaar = True
            st.session_state.pop("opw_extra", None)
            st.session_state.pop("opw", None)
            st.rerun()
        return

    st.caption("Eerst een paar korte vragen over wat je vroeger leerde. Pak pen en papier. Daarna kan je verder.")
    st.progress(o["i"] / n, text=f"Vraag {o['i'] + 1} van {n}")
    kaart = kaarten.get(o["ids"][o["i"]])
    if kaart is None:  # bv. een eigen kaart die intussen gewist is
        _volgende_kaart(o)
        st.rerun()

    with st.container(border=True):
        st.caption(f"{kaart['groep']} · {kaart['titel']}")
        if kaart["soort"] == "reken":
            if o["opgave"] is None:
                o["opgave"] = hh.maak_opgave(kaart, random.random())
            op = o["opgave"]
            st.markdown(f"**{op['intro']}**")
            st.latex(op["tex"])
            if o["fase"] == "vraag":
                with st.form(f"opw_{o['i']}_{o['pogingen']}"):
                    antw = st.text_input("Jouw antwoord",
                                         placeholder="bv. 7" if op.get("exponent") else "bv. -3/4 (breuk met /)")
                    controleer = st.form_submit_button("Controleer", type="primary")
                if o.get("boodschap"):
                    soort, tekst = o["boodschap"]
                    getattr(st, soort)(tekst)
                if controleer:
                    status, tekst = hh.kijk_na(op, antw)
                    if status == "juist":
                        goed = True if not (o["pogingen"] or o["bijna"]) else (None if not o["pogingen"] else False)
                        melding(tekst if goed else "Juist, goed doorgezet!", "🎉" if goed else "👍")
                        _noteer(kaart["id"], goed, vandaag, o)
                    elif status == "bijna":
                        o["bijna"] = True
                        o["boodschap"] = ("warning", tekst)
                    elif status == "onleesbaar":
                        o["boodschap"] = ("info", tekst)
                    else:
                        o["pogingen"] += 1
                        if o["pogingen"] == 1:
                            o["boodschap"] = ("error", "Nog niet juist. 💡 Tip: " + kaart.get("tip", "kijk goed naar de regel."))
                        else:
                            o["fase"] = "uitleg"
                    st.rerun()
            else:  # twee keer fout: uitleg tonen
                st.error(f"Het juiste antwoord is ${hh.tex_breuk(op['antwoord'])}$.")
                st.markdown(op["uitleg"])
                st.caption("Geen probleem: deze kaart komt morgen terug. Schrijf de regel even op je blad.")
                if st.button("Volgende ➜", type="primary"):
                    _noteer(kaart["id"], False, vandaag, o)
                    st.rerun()
        else:
            st.markdown(f"**{kaart['vraag']}**")
            if o["fase"] == "vraag":
                st.caption("Zeg of schrijf eerst zelf het antwoord. Pas daarna kijken!")
                if st.button("👀 Toon het antwoord", type="primary"):
                    o["fase"] = "antwoord"
                    st.rerun()
            else:
                st.success(kaart["antwoord"])
                c1, c2 = st.columns(2)
                if c1.button("✅ Ik wist het", width="stretch"):
                    _noteer(kaart["id"], True, vandaag, o)
                    st.rerun()
                if c2.button("❌ Nog niet (goed)", width="stretch"):
                    _noteer(kaart["id"], False, vandaag, o)
                    st.rerun()


# ---------------------------------------------------------------- hoofdscherm
if current_topic == "📚 Mijn gesprekken":
    st.header("📚 Mijn gesprekken")
    try:
        index = opslag.lees("gesprekken/index.json", []) or []
    except Exception as e:
        index = []
        st.error(f"De gesprekken konden niet geladen worden: {e}")
    if not index:
        st.info("Nog geen bewaarde gesprekken. Elk gesprek in de chat wordt vanzelf bewaard.")
    else:
        zoek = st.text_input("🔎 Zoek een gesprek", "")
        gefilterd = [g for g in index if zoek.lower() in g.get("titel", "").lower()]
        if not gefilterd:
            st.info("Geen gesprek gevonden met dat woord.")
        else:
            labels = [f"{g.get('bijgewerkt', '')} — {g.get('titel', '')}" for g in gefilterd]
            keuze = st.selectbox("Kies een gesprek", range(len(gefilterd)), format_func=lambda i: labels[i])
            g = gefilterd[keuze]
            try:
                gesprek = opslag.lees(f"gesprekken/{g['id']}.json", {}) or {}
            except Exception as e:
                gesprek = {}
                st.error(f"Dit gesprek kon niet geladen worden: {e}")
            berichten = [{"role": b["role"], "content": b["text"], "bijlagen": b.get("bijlagen"),
                          "foto_paden": b.get("foto_paden"), "schrift": b.get("schrift")}
                         for b in gesprek.get("berichten", [])]
            if berichten and st.button("💬 Verder praten in dit gesprek", type="primary"):
                st.session_state.messages = berichten
                st.session_state.gesprek_id = g["id"]
                st.session_state.naar_chat = True
                st.rerun()
            for b in berichten:
                toon_bericht(b)
    st.caption(f"Bewaard in: {opslag.uitleg}")

elif current_topic == "📒 Mijn uitleg-schrift":
    st.header("📒 Mijn uitleg-schrift")
    st.markdown("Telkens als je een oefening **zelf juist oplost**, schrijft de bijlesleraar hier de kern en de uitleg op. Zo kan je het later terugvinden.")
    schrift = list(lees_lijst("schrift.json"))
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
                        schrijf_lijst("schrift.json", schrift)
                    except Exception as e:
                        st.error(f"Lukte niet: {e}")
                    st.rerun()

elif current_topic == "📖 Hoe werkt het? (Handleiding)":
    st.header("📖 Handleiding")
    st.markdown(
        "- **Vraag stellen:** typ onderaan in het tekstvak.\n"
        "- **Foto of PDF toevoegen:** tik op het ＋-knopje links in het tekstvak, kies je foto en typ erbij wat je wil weten.\n"
        "- **Terugkijken:** al je gesprekken staan bij *📚 Mijn gesprekken*, de uitleg van opgeloste oefeningen bij *📒 Mijn uitleg-schrift*.\n"
        "- **Opwarmer:** elke studiesessie begint met 3 korte vragen over oude leerstof. Zo blijven de rekenregels hangen.\n"
        "- **Vastgelopen?** Tik op *🆘 Ik zit echt vast*: dan doet de bijlesleraar een gelijkaardige oefening voor.\n"
        "- **Toets op komst?** Tik in een nieuw gesprek op *📅 Ik heb een toets*.\n"
        "- **Opnieuw beginnen:** *➕ Nieuw gesprek* onder de chat. Je oude gesprek blijft bewaard.\n\n"
        "Meer uitleg vind je op de pagina *Hoe werkt het* in het zijmenu (≫ linksboven)."
    )
    if link_code():
        st.subheader("📲 Openen zonder wachtwoord")
        st.markdown("Met deze persoonlijke link kom je meteen binnen. Zet hem op het beginscherm van je telefoon:")
        st.code(app_link(), language=None)
        st.markdown(
            "1. Kopieer de link (knopje rechts) en open hem in **Chrome**.\n"
            "2. Tik op **⋮** rechtsboven → **Toevoegen aan startscherm**.\n\n"
            "Deel deze link met niemand: wie hem heeft, kan binnen. Lekt hij toch uit, "
            "laat papa dan het wachtwoord veranderen; dan werkt de oude link niet meer."
        )

elif current_topic == "🔁 Herhaling & herinneringen":
    from datetime import time as dtijd
    st.header("🔁 Herhaling & herinneringen")
    st.markdown(
        "Een regel die je net geleerd hebt, lukt meteen, maar een week later ben je hem vaak vergeten. "
        "Daarom begint elke studiesessie met een **opwarmer**: 3 korte vragen over oude leerstof "
        "(herhaling 1ste jaar en de rekenregels voor machten). Wat je moeilijk vindt, komt snel terug; "
        "wat goed gaat, steeds later."
    )
    h = lees_herhaling()
    vandaag = nu().date()
    alle = hh.alle_kaarten(h["eigen"])
    vk = h["kaarten"]
    vast = sum(1 for k in alle if (vk.get(k["id"]) or {}).get("doos", 0) >= 4)
    bezig = sum(1 for k in alle if 0 < (vk.get(k["id"]) or {}).get("doos", 0) < 4)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vandaag", len(hh.te_herhalen(vk, vandaag, h["eigen"])), help="kaarten die vandaag terugkomen")
    c2.metric("Zit vast", vast, help="al een paar keer na elkaar juist")
    c3.metric("Bezig", bezig)
    c4.metric("Nog nieuw", len(alle) - vast - bezig)

    if st.button("🔥 Extra herhaalrondje", type="primary"):
        st.session_state.opw_extra = True
        st.session_state.pop("opw", None)
        st.session_state.naar_chat = True
        st.rerun()

    for groep in (hh.MACHTEN, hh.H1, hh.EIGEN):
        rijen = []
        for k in alle:
            if k["groep"] != groep:
                continue
            v = vk.get(k["id"]) or {}
            doos = int(v.get("doos", 0))
            rijen.append({
                "Kaart": ("🧮 " if k["soort"] == "reken" else "📝 ") + k["titel"],
                "Niveau": "●" * doos + "○" * (hh.MAX_DOOS - doos) if v else "nieuw",
                "Volgende keer": v.get("volgende", "—"),
                "Fout": v.get("fout", 0),
            })
        if rijen:
            with st.expander(f"{groep} ({len(rijen)} kaarten)"):
                st.dataframe(rijen, hide_index=True, width="stretch")
                st.caption("🧮 = som (de app kijkt na) · 📝 = regel (theorie, zelf eerlijk beoordelen)")

    st.subheader("📝 Eigen kaart toevoegen")
    st.caption("Bv. een bewijs uit de les of een regel uit je bundeltje. Vraag links, antwoord rechts: "
               "net zoals theorie in 2 kolommen. Wiskundetekens mag je typen als a^2 of tussen $-tekens.")
    with st.form("eigen_kaart", clear_on_submit=True):
        vraag_k = st.text_input("Vraag (bv. 'Bewijs dat a⁰ = 1')")
        antw_k = st.text_area("Antwoord")
        if st.form_submit_button("Kaart bewaren"):
            if vraag_k.strip() and antw_k.strip():
                h["eigen"].append({"id": "eigen-" + nu().strftime("%Y%m%d%H%M%S"), "titel": vraag_k.strip()[:50],
                                   "vraag": vraag_k.strip(), "antwoord": antw_k.strip()})
                bewaar_herhaling()
                melding("Kaart bewaard! Ze komt in een volgende opwarmer.", "📝")
                st.rerun()
            else:
                st.warning("Vul zowel de vraag als het antwoord in.")
    for i, e in enumerate(h["eigen"]):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f"• {e.get('vraag', '')}")
        if c2.button("🗑️", key=f"weg_eigen_{e.get('id', i)}", help="Kaart verwijderen"):
            h["eigen"].pop(i)
            h["kaarten"].pop(e.get("id"), None)
            bewaar_herhaling()
            st.rerun()

    st.subheader("⏰ Herinnering op je telefoon")
    st.markdown("Kies vaste momenten om te studeren. Je krijgt een agendabestand: open het op je telefoon en "
                "kies **Toevoegen aan agenda**. Dan krijg je op die momenten een melding, met de link naar de app.")
    dagen = st.multiselect("Op welke dagen?", list(hh.DAGCODES), default=["maandag", "woensdag", "zondag"])
    c1, c2 = st.columns(2)
    tijdstip = c1.time_input("Hoe laat?", value=dtijd(18, 0), step=900)
    duur = c2.selectbox("Hoe lang?", [15, 20, 30, 45], index=1, format_func=lambda m: f"{m} minuten")
    if dagen:
        st.download_button("📅 Download herinneringen (agenda)",
                           hh.maak_ics(dagen, tijdstip.hour, tijdstip.minute, duur, app_link(), vandaag),
                           file_name="wiskunde-herhaling.ics", mime="text/calendar", type="primary")
        st.caption("iPhone: open het bestand in Safari → Voeg alles toe. Android: open het met je "
                   "Agenda-app (of importeer het in Google Agenda via de computer). "
                   "Herinneringen lopen tot het einde van het schooljaar.")

    if h.get("log"):
        st.subheader("📊 Laatste opwarmers")
        st.dataframe([{"Wanneer": r["datum"], "Meteen juist": f"{r['juist']} van {r['aantal']}"}
                      for r in h["log"][:10]], hide_index=True, width="stretch")

elif current_topic == "🎯 Adaptieve Foutenbank-toets":
    st.header("🎯 Adaptieve Foutenbank-toets")
    st.markdown("Een korte oefentoets over wat je moeilijk vond of onlangs geoefend hebt.")
    schrift, index = profiel_gegevens()
    weak_pts = groei_data.get("weak_points", [])
    basis = weak_pts or sorted({n.get("onderwerp") for n in schrift if n.get("onderwerp")}) \
        or [g.get("titel", "") for g in index[:10]]
    if weak_pts:
        st.info(f"Aandachtspunten: {', '.join(weak_pts)}")
    elif basis:
        st.info("Nog geen aandachtspunten bekend; de toets gaat over wat je onlangs geoefend hebt.")
    else:
        st.warning("Oefen eerst wat in de chat, dan kan ik een toets op maat maken.")

    if basis and st.button("Genereer toets nu", type="primary"):
        with st.spinner("De coach stelt een gerichte toets samen..."):
            prompt_toets = ("Maak een korte oefentoets van 3 vragen voor een leerling in het 2de jaar ASO "
                            f"over deze onderwerpen: {'; '.join(basis[:10])}. Geef alleen de vragen, "
                            "genummerd, zonder oplossingen. Zeg erbij dat ze ze één voor één mag oplossen in de chat.")
            res = call_claude([{"role": "user", "content": prompt_toets}])
        nieuw_gesprek(res)
        st.session_state.naar_chat = True
        st.rerun()

elif current_topic == "📈 Permanente Groei- & Methodiek-analyse":
    st.header("📈 Groei- & Methodiek-analyse")
    st.markdown("Overzicht van de leerstof, sterke punten en aandachtspunten over alle sessies heen.")

    for titel, sleutel, leeg in (
        ("📚 Behandelde onderwerpen", "topics_covered", "Nog geen onderwerpen vastgelegd."),
        ("💪 Sterke punten", "strong_points", "Nog geen sterke punten vastgelegd."),
        ("📌 Aandachtspunten", "weak_points", "Nog geen aandachtspunten vastgelegd."),
    ):
        st.subheader(titel)
        lijst = groei_data.get(sleutel, [])
        if lijst:
            st.markdown("\n".join(f"- {t}" for t in lijst))
        else:
            st.write(leeg)

    st.subheader("📝 Voortgangsrapport")
    st.info(groei_data.get("growth_summary", "Nog geen analyse beschikbaar."))

    if st.button("Genereer bijgewerkte analyse", type="primary"):
        schrift, index = profiel_gegevens()
        if not schrift and not index:
            st.warning("Er is nog te weinig om te analyseren. Oefen eerst wat in de chat.")
        else:
            with st.spinner("De coach analyseert je voortgang..."):
                gegevens = {
                    "aantal_vragen": groei_data.get("total_questions", 0),
                    "juist_opgeloste_oefeningen": [
                        {k: n.get(k, "") for k in ("datum", "onderwerp", "opgave", "kern")} for n in schrift[:40]],
                    "recente_gesprekken": [
                        {"datum": g.get("bijgewerkt", ""), "eerste_vraag": g.get("titel", "")} for g in index[:30]],
                }
                analysis_prompt = (
                    "Hieronder staan de echte gegevens over een leerling van het 2de jaar ASO "
                    "(juist opgeloste oefeningen en de eerste vraag van recente bijlesgesprekken).\n\n"
                    + json.dumps(gegevens, ensure_ascii=False, indent=1) +
                    "\n\nSchrijf een kort, bemoedigend voortgangsrapport (max. 150 woorden) in eenvoudig Vlaams, "
                    "gericht aan de leerling. Verzin niets dat niet uit de gegevens blijkt. Zet daarna op het einde "
                    "één blok in exact deze vorm (geldige JSON):\n"
                    '<profiel>{"onderwerpen": ["..."], "sterk": ["..."], "aandacht": ["..."]}</profiel>\n'
                    "Aandachtspunten zijn onderwerpen waar ze vaak vragen over stelt maar weinig oefeningen "
                    "juist oploste. Houd elk punt kort (max. 6 woorden)."
                )
                res = call_claude([{"role": "user", "content": analysis_prompt}],
                                  system="Je bent een vriendelijke wiskundecoach die voortgangsrapporten schrijft.")
                rapport, profiel = haal_blok_eruit(res, "profiel")
                groei_data["growth_summary"] = rapport
                if profiel:
                    groei_data["topics_covered"] = [str(x) for x in profiel.get("onderwerpen", [])][:30]
                    groei_data["strong_points"] = [str(x) for x in profiel.get("sterk", [])][:15]
                    groei_data["weak_points"] = [str(x) for x in profiel.get("aandacht", [])][:15]
                save_persistent_groei(groei_data)
            melding("Analyse bijgewerkt!")
            st.rerun()

elif current_topic == "Functies & Grafieken (Rechten / Parabolen)":
    with st.container(border=True):
        figure_type = st.selectbox("Kies een figuur:", ["Rechte lijn", "Parabool ($ax^2+bx+c$)"])
        if figure_type == "Rechte lijn":
            a_line = st.number_input("Waarde van a:", value=2.0, key="a_line_input")
            b_line = st.number_input("Waarde van b:", value=1.0, key="b_line_input")
            if st.button("Genereer lijn"):
                img_buf = plot_linear(a_line, b_line)
                st.session_state.messages.append({"role": "assistant", "content": {"type": "image", "data": img_buf, "caption": f"Grafiek van y = {a_line}x + {b_line}"}})
                st.session_state.naar_chat = True
                st.rerun()
        elif figure_type == "Parabool ($ax^2+bx+c$)":
            a_para = st.number_input("Waarde van a:", value=1.0, key="a_para_input")
            b_para = st.number_input("Waarde van b:", value=0.0, key="b_para_input")
            c_para = st.number_input("Waarde van c:", value=0.0, key="c_para_input")
            if st.button("Genereer parabool"):
                img_buf = plot_parabola(a_para, b_para, c_para)
                st.session_state.messages.append({"role": "assistant", "content": {"type": "image", "data": img_buf, "caption": f"Grafiek van y = {a_para}x² + {b_para}x + {c_para}"}})
                st.session_state.naar_chat = True
                st.rerun()

elif current_topic == "Statistiek & Centrummaten":
    with st.container(border=True):
        nums_input = st.text_input("Getallen (komma-gescheiden):", "12, 15, 12, 18, 20")
        if st.button("Bereken statistiek"):
            try:
                nums = [float(n.strip().replace(" ", "")) for n in nums_input.replace(";", ",").split(",") if n.strip()]
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
                st.error("Vul geldige getallen in, gescheiden door komma's (kommagetallen met een punt, bv. 2.5).")

elif current_topic == "Procenten & Verhoudingen (BTW / Prijs)":
    with st.container(border=True):
        calc_choice = st.selectbox("Type:", ["Procent van een getal", "Procentuele toename/afname"])
        if calc_choice == "Procent van een getal":
            base_val = st.number_input("Getal:", value=120.0, key="base_v")
            pct_val = st.number_input("Percentage (%):", value=21.0, key="pct_v")
            if st.button("Bereken deel"):
                ans = (base_val * pct_val) / 100
                st.info(f"{pct_val}% van het getal is **{ans:g}**")
        else:
            old_v = st.number_input("Oude waarde:", value=80.0, key="old_val")
            new_v = st.number_input("Nieuwe waarde:", value=100.0, key="new_val")
            if st.button("Bereken verandering"):
                if old_v != 0:
                    diff = ((new_v - old_v) / old_v) * 100
                    st.info(f"Verschil: **{diff:+.2f}%**")
                else:
                    st.error("De oude waarde mag geen 0 zijn.")

elif current_topic == "Algebra & Merkwaardige Producten":
    with st.container(border=True):
        st.latex(r"(a + b)^2 = a^2 + 2ab + b^2")
        st.latex(r"(a - b)^2 = a^2 - 2ab + b^2")
        st.latex(r"(a + b)(a - b) = a^2 - b^2")

else:
    from datetime import date, timedelta
    vandaag = nu().date()
    schrift = lees_lijst("schrift.json")
    onderwerpen_recent = list(dict.fromkeys(n.get("onderwerp") for n in schrift if n.get("onderwerp")))[:5]
    actie = None  # tekst die via een knop verstuurd wordt, alsof ze hem zelf typte

    # --- eerst de opwarmer: oude leerstof herhalen voor ze aan iets nieuws begint
    if opwarmer_nodig():
        toon_opwarmer(vandaag)
        st.stop()

    # --- vooruitgang: kort en niet kinderachtig
    if schrift:
        week = sum(1 for n in schrift if n.get("datum", "") >= (vandaag - timedelta(days=6)).isoformat())
        if week:
            st.caption(f"💪 Deze week {week} oefening{'en' if week != 1 else ''} zelf opgelost · {len(schrift)} in totaal")
        else:
            st.caption(f"💪 Al {len(schrift)} oefening{'en' if len(schrift) != 1 else ''} zelf opgelost")

    # --- toetsen die eraan komen
    toetsen = [t for t in lees_lijst("toetsen.json") if t.get("datum", "") >= vandaag.isoformat()]
    for i, t in enumerate(sorted(toetsen, key=lambda t: t["datum"])[:2]):
        dagen = (date.fromisoformat(t["datum"]) - vandaag).days
        wanneer = "vandaag" if dagen == 0 else "morgen" if dagen == 1 else f"over {dagen} dagen"
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        c1.markdown(f"📅 **Toets {t['onderwerp']}** — {wanneer}")
        if c2.button("Oefen nu", key=f"oefen_{t['datum']}_{i}", type="primary"):
            actie = (f"📅 Oefenen voor mijn toets over {t['onderwerp']} ({wanneer}). "
                     "Geef me één oefenvraag van toetsniveau.")

    for msg in st.session_state.messages:
        toon_bericht(msg)

    heeft_vragen = any(m["role"] == "user" for m in st.session_state.messages)

    if not heeft_vragen and not st.session_state.get("toets_formulier"):
        # --- snelstartknoppen in een leeg gesprek
        def _snel_gekozen():
            st.session_state.snel_actie = st.session_state.get("snel")
            st.session_state.snel = None

        st.pills("Snel starten", ["📷 Help met mijn huiswerk", "🧠 Overhoor me", "❓ Leg iets uit",
                                  "📅 Ik heb een toets"],
                 key="snel", on_change=_snel_gekozen, label_visibility="collapsed")
        keuze = st.session_state.pop("snel_actie", None)
        if keuze == "📷 Help met mijn huiswerk":
            st.session_state.messages.append({"role": "assistant", "content":
                "Top! Tik op **＋** links in het tekstvak, kies een foto van je oefening en typ erbij wat je niet snapt."})
            st.rerun()
        elif keuze == "❓ Leg iets uit":
            st.session_state.messages.append({"role": "assistant", "content":
                "Zeker! Welk onderwerp of welk woord wil je uitgelegd krijgen? Typ het maar."})
            st.rerun()
        elif keuze == "🧠 Overhoor me":
            if onderwerpen_recent:
                over = ", ".join(onderwerpen_recent[:-1]) + (" of " if len(onderwerpen_recent) > 1 else "") \
                    + onderwerpen_recent[-1]
                actie = f"🧠 Overhoor me over {over.lower()}! Kies er één uit en stel me één oefenvraag."
            else:
                actie = "🧠 Overhoor me! Stel me één oefenvraag over de leerstof van het 2de jaar."
        elif keuze == "📅 Ik heb een toets":
            st.session_state.toets_formulier = True
            st.rerun()

    if st.session_state.get("toets_formulier"):
        # --- toetsvoorbereiding
        with st.form("toets"):
            st.markdown("**📅 Over welke toets gaat het?**")
            onderwerp = st.text_input("Onderwerp", placeholder="bv. merkwaardige producten")
            datum = st.date_input("Wanneer?", value=vandaag + timedelta(days=3), min_value=vandaag,
                                  format="DD/MM/YYYY")
            c1, c2 = st.columns(2)
            klaar = c1.form_submit_button("Maak mijn oefenplan", type="primary")
            stop = c2.form_submit_button("Annuleer")
        if stop:
            st.session_state.toets_formulier = False
            st.rerun()
        if klaar:
            if not onderwerp.strip():
                st.warning("Vul eerst het onderwerp in.")
            else:
                st.session_state.toets_formulier = False
                alle = [t for t in lees_lijst("toetsen.json") if t.get("datum", "") >= vandaag.isoformat()]
                alle.append({"onderwerp": onderwerp.strip(), "datum": datum.isoformat()})
                try:
                    schrijf_lijst("toetsen.json", alle)
                except Exception as e:
                    print(f"Toets niet bewaard: {e}", file=sys.stderr)
                dagen = (datum - vandaag).days
                actie = (f"📅 Ik heb {'vandaag' if dagen == 0 else 'morgen' if dagen == 1 else f'over {dagen} dagen'} "
                         f"een toets over {onderwerp.strip()}. Maak een kort oefenplan tot dan "
                         "(hooguit 4 korte punten) en stel me meteen de eerste oefenvraag.")

    if heeft_vragen:
        c1, c2 = st.columns(2)
        if c1.button("🆘 Ik zit echt vast", width="stretch",
                     help="De bijlesleraar doet een gelijkaardige oefening met andere getallen voor."):
            actie = ("🆘 Ik zit echt vast. Kan je een gelijkaardige oefening met andere getallen "
                     "stap voor stap voordoen? Dan probeer ik daarna mijn eigen oefening opnieuw.")
        if c2.button("➕ Nieuw gesprek", key="nieuw_onder", width="stretch",
                     help="Je huidige gesprek blijft bewaard bij 📚 Gesprekken."):
            nieuw_gesprek("Oké, een nieuw gesprek! Je vorige gesprek staat bij 📚 Gesprekken. Wat pakken we aan?")
            st.rerun()

    invoer = st.chat_input(
        "Typ je vraag…  (＋ = foto of PDF)",
        accept_file="multiple",
        file_type=BESTANDSTYPES,
    )

    vraag = None
    if invoer:
        prompt = (invoer.text or "").strip()
        delen, fotos, namen, mislukt = verwerk_bestanden(invoer.files)

        if not prompt and not delen:
            if mislukt:
                st.warning("Dit bestand kon ik niet openen: " + ", ".join(mislukt)
                           + f". Maak een nieuwe foto, of stuur een kleinere PDF (max. {MAX_PDF_MB} MB).")
            st.stop()  # niets bruikbaars om te versturen; de waarschuwing blijft staan
        if not prompt:
            prompt = "Kan je mijn foto bekijken?" if fotos else "Kan je mijn bestand bekijken?"
        vraag = {"role": "user", "content": prompt}
        if delen:
            vraag.update({"delen": delen, "fotos": fotos, "bijlagen": namen})
        if mislukt:
            vraag["mislukt"] = mislukt
    elif actie:
        vraag = {"role": "user", "content": actie}

    if vraag:
        groei_data["total_questions"] = groei_data.get("total_questions", 0) + 1
        save_persistent_groei(groei_data)

        st.session_state.messages.append(vraag)
        toon_bericht(vraag)

        with st.spinner("De coach bekijkt je vraag..."):
            response_text = call_claude(api_berichten())
            response_text, notitie = haal_schrift_eruit(response_text)
            in_schrift = bool(notitie) and bewaar_in_schrift(notitie)

        antwoord = {"role": "assistant", "content": response_text, "schrift": in_schrift}
        st.session_state.messages.append(antwoord)
        toon_bericht(antwoord)
        bewaar_gesprek()
        if in_schrift:
            melding("Bewaard in je uitleg-schrift!", "📒")
        st.rerun()
