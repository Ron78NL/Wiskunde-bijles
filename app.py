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
    if GROEI_FILE.exists():
        try:
            data = json.loads(GROEI_FILE.read_text(encoding="utf-8"))
            if "weak_points" not in data:
                data["weak_points"] = []
            if "strong_points" not in data:
                data["strong_points"] = []
            if "topics_covered" not in data:
                data["topics_covered"] = []
            return data
        except Exception:
            pass
    return {
        "total_questions": 0, 
        "topics_covered": [], 
        "weak_points": [],
        "strong_points": [],
        "growth_summary": "Nog geen historische analyse beschikbaar. Begin met oefenen en analyseer de voortgang."
    }

def save_persistent_groei(data):
    try:
        GROEI_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
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

def ssl_context():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()

def build_system_prompt():
    prompt_file = ROOT / "system-prompt.md"
    prompt = prompt_file.read_text(encoding="utf-8") if prompt_file.exists() else ""
    return prompt

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
        
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": 1200,
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
        with urllib.request.urlopen(req, timeout=90, context=ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return "\n".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    except urllib.error.HTTPError as e:
        error_detail = e.read().decode("utf-8", "ignore")
        return f"API Fout ({e.code}): {error_detail}"
    except Exception as e:
        return f"Er ging iets mis bij het verbinden met de bijlesleraar: {e}"

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

groei_data = load_persistent_groei()

with st.sidebar:
    st.header("📂 Oefeningen of Toetsen")
    uploaded_files = st.file_uploader(
        "Upload hier meerdere foto's of PDF's", 
        type=["jpg", "jpeg", "png", "webp", "pdf"], 
        accept_multiple_files=True
    )
    
    if uploaded_files:
        import base64
        docs_list = []
        schoolwerk_dir = ROOT / "schoolwerk"
        schoolwerk_dir.mkdir(exist_ok=True)
        
        for uploaded_file in uploaded_files:
            bytes_data = uploaded_file.getvalue()
            b64_data = base64.b64encode(bytes_data).decode("utf-8")
            (schoolwerk_dir / uploaded_file.name).write_bytes(bytes_data)
            docs_list.append({
                "name": uploaded_file.name,
                "type": uploaded_file.type,
                "data": b64_data
            })
        st.session_state.active_documents = docs_list
        st.success(f"{len(uploaded_files)} bestand(en) geladen.")
    
    if st.session_state.active_documents:
        if st.button("🗑️ Alle bijlagen wissen"):
            st.session_state.active_documents = []
            st.rerun()

    st.markdown("---")
    st.subheader("🛠️ Modus & Hulpmiddel")
    
    current_topic = st.selectbox(
        "Kies wat je wilt doen:",
        [
            "💬 Chat met Bijlesleraar",
            "📖 Hoe werkt het? (Handleiding)",
            "🎯 Adaptieve Foutenbank-toets",
            "📈 Permanente Groei- & Methodiek-analyse",
            "Functies & Grafieken (Rechten / Parabolen)",
            "Statistiek & Centrummaten",
            "Procenten & Verhoudingen (BTW / Prijs)",
            "Algebra & Merkwaardige Producten"
        ]
    )

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
    if st.button("🗑️ Wis hele gesprek"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Gesetteld. We beginnen weer met een schone lei. Wat pakken we aan?"}
        ]
        st.session_state.active_documents = []
        st.rerun()

# Hoofdscherm logica
if current_topic == "📖 Hoe werkt het? (Handleiding)":
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
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        st.write(part["text"])
            elif isinstance(content, dict) and content.get("type") == "image":
                st.image(content["data"], caption=content.get("caption"))
            else:
                st.write(content)

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
        st.session_state.messages.append({"role": "user", "content": content_parts})
        
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
            
        with st.chat_message("assistant"):
            st.write(response_text)
        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()
