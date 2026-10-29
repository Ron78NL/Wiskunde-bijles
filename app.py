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
    # Probeer de sleutel te vinden via Streamlit Secrets (online) of os.environ (lokaal)
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
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    
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
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    
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
        {"role": "assistant", "content": "Dag! Leuk dat je er bent. 😊 Waaraan wil je vandaag werken? Je mag een vraag stellen of hieronder een oefening of toets uploaden."}
    ]

if "active_document" not in st.session_state:
    st.session_state.active_document = None

user_messages_count = sum(1 for m in st.session_state.messages if m["role"] == "user")

with st.sidebar:
    st.header("📂 Oefening of Toets")
    uploaded_file = st.file_uploader("Upload hier een foto of PDF", type=["jpg", "jpeg", "png", "webp", "pdf"])
    
    if uploaded_file:
        import base64
        bytes_data = uploaded_file.getvalue()
        b64_data = base64.b64encode(bytes_data).decode("utf-8")
        file_type = uploaded_file.type
        
        schoolwerk_dir = ROOT / "schoolwerk"
        schoolwerk_dir.mkdir(exist_ok=True)
        (schoolwerk_dir / uploaded_file.name).write_bytes(bytes_data)
        
        st.session_state.active_document = {
            "name": uploaded_file.name,
            "type": file_type,
            "data": b64_data
        }
        st.success(f"Geladen: {uploaded_file.name}")
    
    if st.session_state.active_document:
        if st.button("🗑️ Huidige bijlage wissen"):
            st.session_state.active_document = None
            st.rerun()

    st.markdown("---")
    st.subheader("🎯 Test je kennis")
    if st.button("Maak een mini-oefentoets 📝"):
        quiz_prompt = "Geef me een korte oefentoets van 3 leuke, gerichte vragen over de leerstof die we tot nu toe besproken hebben, zodat ik kan testen of ik het echt begrijp. Stel de vragen één voor één of alle drie samen!"
        st.session_state.messages.append({"role": "user", "content": quiz_prompt})
        
        api_messages = []
        for m in st.session_state.messages:
            role = m["role"]
            content = m["content"]
            if isinstance(content, list):
                texts = [p["text"] for p in content if p.get("type") == "text"]
                api_messages.append({"role": role, "content": " ".join(texts)})
            else:
                api_messages.append({"role": role, "content": content})
                
        with st.spinner("De bijlesleraar stelt een toetsje voor je op..."):
            response_text = call_claude(api_messages)
            st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()
            
    st.markdown("---")
    st.subheader("🛠️ Modus & Hulpmiddel")
    
    # Keuzemenu inclusief de handleiding als optie
    current_topic = st.selectbox(
        "Kies wat je wilt doen:",
        [
            "💬 Chat met Bijlesleraar",
            "📖 Hoe werkt het? (Handleiding)",
            "Functies & Grafieken (Rechten / Parabolen)",
            "Statistiek & Centrummaten",
            "Procenten & Verhoudingen (BTW / Prijs)",
            "Algebra & Merkwaardige Producten"
        ]
    )

    # Dynamische weergave van de tool of handleiding
    if current_topic == "Functies & Grafieken (Rechten / Parabolen)":
        with st.expander("📈 Grafiek Generator", expanded=True):
            figure_type = st.selectbox("Kies een figuur:", ["Rechte lijn", "Parabool ($ax^2+bx+c$)"])
            if figure_type == "Rechte lijn":
                st.write("Controleer coëfficiënten voor $y = ax + b$")
                a_line = st.number_input("Waarde van a:", value=2.0, key="a_line_input")
                b_line = st.number_input("Waarde van b:", value=1.0, key="b_line_input")
                if st.button("Genereer lijn"):
                    img_buf = plot_linear(a_line, b_line)
                    st.session_state.messages.append({"role": "assistant", "content": {"type": "image", "data": img_buf, "caption": f"Grafiek van y = {a_line}x + {b_line}"}})
                    st.rerun()
            elif figure_type == "Parabool ($ax^2+bx+c$)":
                st.write("Controleer coëfficiënten voor $y = ax^2 + bx + c$")
                a_para = st.number_input("Waarde van a:", value=1.0, key="a_para_input")
                b_para = st.number_input("Waarde van b:", value=0.0, key="b_para_input")
                c_para = st.number_input("Waarde van c:", value=0.0, key="c_para_input")
                if st.button("Genereer parabool"):
                    img_buf = plot_parabola(a_para, b_para, c_para)
                    st.session_state.messages.append({"role": "assistant", "content": {"type": "image", "data": img_buf, "caption": f"Grafiek van y = {a_para}x² + {b_para}x + {c_para}"}})
                    st.rerun()

    elif current_topic == "Statistiek & Centrummaten":
        with st.expander("📊 Statistiek Checker", expanded=True):
            st.write("Controleer centrummaten van een getallenreeks.")
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
                    st.error("Vul geldige getallen in, gescheiden door komma's.")

    elif current_topic == "Procenten & Verhoudingen (BTW / Prijs)":
        with st.expander("📉 Procenten & Prijscontrole", expanded=True):
            calc_choice = st.selectbox("Type:", ["Procent van een getal", "Procentuele toename/afname"])
            if calc_choice == "Procent van een getal":
                base_val = st.number_input("Getal:", value=120.0, key="base_v")
                pct_val = st.number_input("Percentage (%):", value=21.0, key="pct_v")
                if st.button("Bereken deel"):
                    ans = (base_val * pct_val) / 100
                    st.info(f"{pct_val}% van {base_val} = **{ans}**")
            else:
                old_v = st.number_input("Oude waarde:", value=80.0, key="old_val")
                new_v = st.number_input("Nieuwe waarde:", value=100.0, key="new_val")
                if st.button("Bereken verandering"):
                    if old_v != 0:
                        diff = ((new_v - old_v) / old_v) * 100
                        st.info(f"Verschil: **{diff:+.2f}%**")

    elif current_topic == "Algebra & Merkwaardige Producten":
        with st.expander("🧩 Formules & Geheugensteun", expanded=True):
            st.write("Belangrijke formules:")
            st.latex(r"(a + b)^2 = a^2 + 2ab + b^2")
            st.latex(r"(a - b)^2 = a^2 - 2ab + b^2")
            st.latex(r"(a + b)(a - b) = a^2 - b^2")

    st.markdown("---")
    st.subheader("🌟 Jouw Groei-meter")
    st.metric(label="Stappen gezet vandaag", value=user_messages_count)
    progress_val = min(user_messages_count / 10.0, 1.0)
    st.progress(progress_val)
    if user_messages_count < 5:
        st.success("Goed bezig! Je bent lekker gefocust aan het nadenken. 🚀")
    else:
        st.balloons()
        st.success("Wauw, wat een doorzettingsvermogen! Jij bent echt grotere stappen aan het zetten. ⭐")

    st.markdown("---")
    if st.button("🗑️ Wis hele gesprek (Begin opnieuw)"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Dag! Het gesprek is schoongeveegd. 😊 Waar gaan we nu aan werken?"}
        ]
        st.session_state.active_document = None
        st.rerun()

# Hoofdscherm logica: Toon de handleiding als die is geselecteerd, anders de chat
if current_topic == "📖 Hoe werkt het? (Handleiding)":
    st.title("📖 Hoe werkt deze Wiskundebijles-app?")
    st.markdown("""
    Welkom! Deze app is jouw persoonlijke digitale bijlesleraar. Het is nadrukkelijk **geen antwoordmachine** die je huiswerk zomaar overneemt, maar een hulpmiddel om te leren en te controleren.

    ---

    ### 🎯 Wat is de opzet?
    * **Zelf nadenken staat centraal:** De AI-bijlesleraar geeft je nooit zomaar het eindantwoord. Die helpt je op weg door slimme vragen te stellen en je stapsgewijs te begeleiden.
    * **Geen rekenfouten:** Alle rekentools en grafieken worden berekend door strakke Python-logica. Wat daaruit komt, klopt altijd exact.

    ---

    ### 🛠️ Hoe gebruik je de tools?
    In de zijbalk kun je het **huidige onderwerp** kiezen waar je mee bezig bent. De app toont dan automatisch de tool die daarbij hoort:
    1. **Functies & Grafieken:** Controleer rechten en parabolen.
    2. **Statistiek & Centrummaten:** Bereken snel het gemiddelde, de mediaan en de modus.
    3. **Procenten & Prijscontrole:** Handig voor BTW-berekeningen en procentuele verandering.
    4. **Algebra & Merkwaardige Producten:** Bekijk de belangrijkste formules als geheugensteuntje.

    ---

    ### 🚀 Stappenplan voor je huiswerk:
    1. **Upload je taak:** Maak een foto van je oefeningenblad of upload een PDF via de zijbalk.
    2. **Typ je poging:** Zet in de chat wat je al geprobeerd hebt.
    3. **Check en leer:** Gebruik de rekentools in de zijbalk om je eigen antwoorden te controleren.
    4. **Test je kennis:** Klik in de zijbalk op de knop om een korte oefentoets te maken!
    """)
else:
    # Toon de chatgeschiedenis
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            content = msg["content"]
            if isinstance(content, list):
                for part in content:
                    if part.get("type") == "text":
                        st.write(part["text"])
            elif isinstance(content, dict) and content.get("type") == "image":
                st.image(content["data"], caption=content.get("caption"))
            else:
                st.write(content)

    # Chat invoer onderaan
    if prompt := st.chat_input("Schrijf hier je vraag of je poging..."):
        content_parts = []
        if st.session_state.active_document:
            doc = st.session_state.active_document
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
            if st.session_state.active_document:
                st.caption(f"📎 Bijlage: {st.session_state.active_document['name']}")
            st.write(prompt)
        with st.spinner("De bijlesleraar denkt na..."):
            api_messages = []
            for i, m in enumerate(st.session_state.messages):
                role = m["role"]
                content = m["content"]
                if isinstance(content, list):
                    texts = [p["text"] for p in content if p.get("type") == "text"]
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
