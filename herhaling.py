"""Herhaling van oude leerstof: de 'opwarmer' en de herhaalkaarten.

Waarom? Een rekenregel die je net gehoord hebt, lukt meteen. Een week later
denk je er niet meer aan. Daarom begint elke studiesessie met een paar korte
vragen over OUDE leerstof (vooral de herhaling van het 1ste jaar en de
rekenregels voor machten).

Werkwijze (Leitner-systeem, 'doosjes'):
- Elke kaart zit in een doosje 0..6. Nieuw = nog nooit gezien.
- Juist  -> één doosje hoger; de kaart komt pas later terug (1, 2, 4, 8, 16, 30 dagen).
- Fout   -> terug naar doosje 1; morgen komt ze terug.
Zo komt wat moeilijk is vaak terug, en wat vastzit steeds minder.

Twee soorten kaarten:
- 'reken': een som met elke keer andere getallen; de app kijkt zelf na
  (ook of een breuk vereenvoudigd is).
- 'regel': een vraag over de theorie, zoals in 2 kolommen. Eerst zelf
  denken/opschrijven, dan het antwoord tonen en eerlijk zeggen of je het wist.

Dit bestand gebruikt geen Streamlit: alles hier is gewone Python en te testen.
"""
import math
import random
import re
from datetime import date, timedelta
from fractions import Fraction
from decimal import Decimal, InvalidOperation

TUSSENTIJD = [0, 1, 2, 4, 8, 16, 30]  # dagen tot de volgende herhaling, per doosje
MAX_DOOS = len(TUSSENTIJD) - 1

H1 = "Herhaling 1ste jaar"
MACHTEN = "Machten"
EIGEN = "Eigen kaarten"


# ---------------------------------------------------------------- hulpjes voor de opmaak
def tex_breuk(f, haakjes=False):
    """LaTeX van een breuk; met haakjes als ze negatief is en haakjes=True."""
    f = Fraction(f)
    if f.denominator == 1:
        t = str(f.numerator)
    else:
        t = ("-" if f < 0 else "") + rf"\frac{{{abs(f.numerator)}}}{{{f.denominator}}}"
    return rf"\left({t}\right)" if haakjes and f < 0 else t


def tex_getal(n):
    return f"({n})" if n < 0 else str(n)


def _breuk(rng, max_noemer=9, neg=True):
    q = rng.randint(2, max_noemer)
    p = rng.randint(1, 2 * q)
    while math.gcd(p, q) != 1 or p % q == 0:
        p = rng.randint(1, 2 * q)
    f = Fraction(p, q)
    return -f if neg and rng.random() < 0.4 else f


def _opgave(intro, tex, antwoord, uitleg, vorm="getal", vraag_exponent=False):
    return {"intro": intro, "tex": tex, "antwoord": str(Fraction(antwoord)),
            "uitleg": uitleg, "vorm": vorm, "exponent": vraag_exponent}


# ---------------------------------------------------------------- rekenkaarten: herhaling 1ste jaar
def g_vereenvoudig(rng):
    f = abs(_breuk(rng, 9, neg=False))
    k = rng.choice([2, 3, 4, 5, 6, 7, 8, 9, 12])
    teken = -1 if rng.random() < 0.3 else 1
    p, q = teken * f.numerator * k, f.denominator * k
    return _opgave("Vereenvoudig zo ver mogelijk.", rf"\frac{{{p}}}{{{q}}}" if p > 0 else rf"-\frac{{{-p}}}{{{q}}}",
                   Fraction(p, q),
                   f"Teller en noemer zijn allebei deelbaar door {k} (de ggd). "
                   f"Deel ze allebei door {k}: je krijgt ${tex_breuk(Fraction(p, q))}$.", "breuk")


def g_optellen(rng):
    while True:
        a, b = _breuk(rng, 8), _breuk(rng, 8)
        if a.denominator != b.denominator and a + b != 0:
            break
    kgv = a.denominator * b.denominator // math.gcd(a.denominator, b.denominator)
    plus = rf"{tex_breuk(a)} + {tex_breuk(b, True)}"
    return _opgave("Bereken. Vereenvoudig je uitkomst.", plus, a + b,
                   f"Maak eerst dezelfde noemer: het kgv van {a.denominator} en {b.denominator} is {kgv}. "
                   f"Tel dan de tellers op en vereenvoudig: ${tex_breuk(a + b)}$.", "breuk")


def g_aftrekken(rng):
    while True:
        a, b = _breuk(rng, 8), _breuk(rng, 8)
        if a.denominator != b.denominator and a - b != 0:
            break
    return _opgave("Bereken. Vereenvoudig je uitkomst.", rf"{tex_breuk(a)} - {tex_breuk(b, True)}", a - b,
                   "Min een negatief getal wordt plus. Maak dezelfde noemer, trek de tellers af en "
                   f"vereenvoudig: ${tex_breuk(a - b)}$.", "breuk")


def g_vermenigvuldigen(rng):
    # kies getallen die je kruiselings kan vereenvoudigen
    k = rng.choice([2, 3, 4, 5])
    a = Fraction(rng.choice([1, 2, 3, 5, 7]) * k, rng.choice([3, 5, 7, 9, 11]))
    b = Fraction(rng.choice([1, 2, 3, 5, 7]), rng.choice([2, 3, 4]) * k)
    if rng.random() < 0.5:
        a = -a
    if rng.random() < 0.3:
        b = -b
    return _opgave("Bereken. Vereenvoudig je uitkomst.", rf"{tex_breuk(a)} \cdot {tex_breuk(b, True)}", a * b,
                   "Teller maal teller, noemer maal noemer (vereenvoudig liefst eerst kruiselings). "
                   f"Let op het teken. Uitkomst: ${tex_breuk(a * b)}$.", "breuk")


def g_delen(rng):
    a, b = _breuk(rng, 7), _breuk(rng, 7)
    return _opgave("Bereken. Vereenvoudig je uitkomst.", rf"{tex_breuk(a)} : {tex_breuk(b, True)}", a / b,
                   f"Delen door een breuk = vermenigvuldigen met het omgekeerde. "
                   f"Het omgekeerde van ${tex_breuk(b)}$ is ${tex_breuk(1 / b)}$. Uitkomst: ${tex_breuk(a / b)}$.",
                   "breuk")


def g_nulde_macht(rng):
    n = rng.randint(2, 9)
    m = rng.randint(2, 3)
    f = abs(_breuk(rng, 9, neg=False))
    keuzes = [
        (rf"({-rng.randint(2, 99)})^0", 1),
        (rf"{rng.randint(100, 2030)}^0", 1),
        (rf"\left({tex_breuk(f)}\right)^0", 1),
        (rf"{n} \cdot 7^0", n),
        (rf"{n}^0 + {n}", n + 1),
        (rf"{n}^{m} \cdot 5^0", n ** m),
        (rf"-{n}^0", -1),
    ]
    tex, antw = rng.choice(keuzes)
    extra = " Let op: bij $-a^0$ hoort het minteken niet bij het grondtal, dus $-a^0 = -1$." if antw == -1 else ""
    return _opgave("Bereken.", tex, antw,
                   "Elk getal (behalve 0) tot de nulde macht is 1." + extra)


def g_negatief_grondtal(rng):
    a = rng.randint(2, 5)
    n = rng.choice([2, 3, 4]) if a <= 3 else rng.choice([2, 3])
    if rng.random() < 0.5:
        tex, antw = rf"(-{a})^{n}", (-a) ** n
        uitleg = (f"Met haakjes hoort het minteken bij het grondtal: je vermenigvuldigt {n} keer (−{a}). "
                  f"{'Even' if n % 2 == 0 else 'Oneven'} exponent → {'positief' if n % 2 == 0 else 'negatief'}.")
    else:
        tex, antw = rf"-{a}^{n}", -(a ** n)
        uitleg = f"Zonder haakjes hoort het minteken NIET bij het grondtal: eerst {a}^{n} = {a ** n}, dan het min ervoor."
    return _opgave("Bereken.", tex, antw, uitleg)


def g_gehele_getallen(rng):
    a, b, c, d = (rng.randint(-20, 20) for _ in range(4))
    c = c or 7
    tex = rf"{a} - {tex_getal(b)} + {tex_getal(c)} - ({-abs(d) or -3})"
    antw = a - b + c - (-abs(d) or -3)
    return _opgave("Bereken (uit het hoofd).", tex, antw,
                   "Min een negatief getal wordt plus: −(−5) = +5. Werk van links naar rechts.")


def g_volgorde(rng):
    a = rng.randint(2, 20)
    b = rng.randint(2, 5)
    c = -rng.randint(2, 4)
    if rng.random() < 0.5:
        tex, antw = rf"{a} - {b} \cdot ({c})^2", a - b * c ** 2
    else:
        d = rng.randint(2, 4)
        tex, antw = rf"({a} - {a + d * b}) : {d} + {b}^2", Fraction(a - (a + d * b), d) + b ** 2
    return _opgave("Bereken. Let op de volgorde van de bewerkingen.", tex, antw,
                   "Eerst haakjes, dan machten, dan maal en gedeeld door, en pas op het einde plus en min.")


def g_macht_breuk(rng):
    p, q = rng.randint(1, 4), rng.randint(2, 5)
    while math.gcd(p, q) != 1:
        p = rng.randint(1, 4)
    f = Fraction(p, q) * (-1 if rng.random() < 0.5 else 1)
    n = rng.choice([2, 3])
    return _opgave("Bereken.", rf"\left({tex_breuk(f)}\right)^{n}", f ** n,
                   f"Zowel de teller als de noemer tot de {n}de macht. Negatief grondtal: "
                   "even exponent → positief, oneven → negatief.", "breuk")


def g_omgekeerde(rng):
    f = _breuk(rng, 9)
    if rng.random() < 0.5:
        return _opgave("Wat is het OMGEKEERDE van dit getal?", tex_breuk(f), 1 / f,
                       "Omgekeerde: teller en noemer wisselen van plaats, het teken blijft. "
                       "Een getal maal zijn omgekeerde is 1.", "breuk")
    return _opgave("Wat is het TEGENGESTELDE van dit getal?", tex_breuk(f), -f,
                   "Tegengestelde: alleen het teken verandert. Een getal plus zijn tegengestelde is 0.", "breuk")


# ---------------------------------------------------------------- rekenkaarten: machten
LETTERS = "abxy"


def g_product_machten(rng):
    x = rng.choice(LETTERS)
    m, n = rng.randint(2, 9), rng.randint(2, 9)
    keuze = rng.random()
    if keuze < 0.3:
        tex, antw = rf"{x} \cdot {x}^{{{n}}}", 1 + n
        uitleg = f"${x}$ zelf is ${x}^1$. Zelfde grondtal: exponenten optellen, 1 + {n} = {1 + n}."
    elif keuze < 0.6:
        k = rng.randint(2, 5)
        tex, antw = rf"{x}^{{{m}}} \cdot {x}^{{{n}}} \cdot {x}^{{{k}}}", m + n + k
        uitleg = f"Zelfde grondtal: exponenten optellen, {m} + {n} + {k} = {m + n + k}."
    else:
        tex, antw = rf"{x}^{{{m}}} \cdot {x}^{{{n}}}", m + n
        uitleg = f"Zelfde grondtal: exponenten optellen, {m} + {n} = {m + n}."
    return _opgave("Vul de exponent in: wat komt op de plaats van het vraagteken?",
                   tex + rf" = {x}^{{?}}", antw, uitleg, vraag_exponent=True)


def g_quotient_machten(rng):
    x = rng.choice(LETTERS)
    n = rng.randint(2, 8)
    m = n if rng.random() < 0.3 else n + rng.randint(1, 7)
    uitleg = f"Zelfde grondtal: exponenten aftrekken, {m} − {n} = {m - n}."
    if m == n:
        uitleg += f" En ${x}^0 = 1$: daarom is de nulde macht 1!"
    return _opgave("Vul de exponent in.", rf"{x}^{{{m}}} : {x}^{{{n}}} = {x}^{{?}}",
                   m - n, uitleg, vraag_exponent=True)


def g_macht_van_macht(rng):
    x = rng.choice(LETTERS)
    m, n = rng.randint(2, 6), rng.randint(2, 5)
    if rng.random() < 0.4:
        k = rng.randint(2, 6)
        return _opgave("Vul de exponent in.", rf"({x}^{{{m}}})^{{{n}}} \cdot {x}^{{{k}}} = {x}^{{?}}", m * n + k,
                       f"Eerst macht van een macht: {m} · {n} = {m * n}. Dan maal ${x}^{{{k}}}$: "
                       f"{m * n} + {k} = {m * n + k}.", vraag_exponent=True)
    return _opgave("Vul de exponent in.", rf"({x}^{{{m}}})^{{{n}}} = {x}^{{?}}", m * n,
                   f"Macht van een macht: exponenten vermenigvuldigen, {m} · {n} = {m * n}.", vraag_exponent=True)


def g_macht_van_product(rng):
    x = rng.choice(LETTERS)
    c = rng.choice([2, 3, 4, 5, -2, -3])
    n = rng.choice([2, 3]) if abs(c) <= 3 else 2
    return _opgave("Welk getal komt op de plaats van het vraagteken?",
                   rf"({c}{x})^{n} = \;?\; \cdot {x}^{n}", c ** n,
                   f"Macht van een product: ELKE factor tot de macht. Dus ook het getal: "
                   f"$({c})^{n} = {c ** n}$.")


# ---------------------------------------------------------------- de kaartenbank
# Volgorde = volgorde waarin nieuwe kaarten voor het eerst verschijnen.
# Eerst de werkpunten van de leerkracht: nulde macht, vereenvoudigen, rekenen met breuken.
KAARTEN = [
    {"id": "r-nulde", "groep": MACHTEN, "soort": "regel", "titel": "Nulde macht",
     "vraag": r"Hoeveel is $a^0$ (met $a \neq 0$)?",
     "antwoord": r"$a^0 = 1$. Elk getal behalve 0 tot de nulde macht is 1: $(-8)^0 = 1$. "
                 r"Maar let op: $-8^0 = -1$ (het minteken hoort niet bij het grondtal)."},
    {"id": "g-nulde", "groep": MACHTEN, "soort": "reken", "titel": "Rekenen met de nulde macht", "tip": "Wat weet je over een getal tot de nulde macht? En hoort het minteken bij het grondtal?", "maak": g_nulde_macht},
    {"id": "g-vereenvoudig", "groep": H1, "soort": "reken", "titel": "Breuk vereenvoudigen", "tip": "Zoek het grootste getal waardoor teller én noemer deelbaar zijn.", "maak": g_vereenvoudig},
    {"id": "r-vereenvoudig", "groep": H1, "soort": "regel", "titel": "Wanneer vereenvoudigen?",
     "vraag": "Wanneer moet je een breuk vereenvoudigen, en hoe doe je dat?",
     "antwoord": "ALTIJD bij je eindantwoord (en liefst ook tussendoor). Deel teller en noemer door hun "
                 "grootste gemeenschappelijke deler (ggd). Controle: hebben teller en noemer nog een deler "
                 "gemeen? Dan ben je nog niet klaar."},
    {"id": "g-product", "groep": MACHTEN, "soort": "reken", "titel": "Product van machten", "tip": "Zelfde grondtal, maal elkaar: wat doe je met de exponenten? (En een letter zonder exponent heeft exponent 1.)", "maak": g_product_machten},
    {"id": "g-optellen", "groep": H1, "soort": "reken", "titel": "Breuken optellen", "tip": "Eerst dezelfde noemer maken. Op het einde: vereenvoudigen!", "maak": g_optellen},
    {"id": "r-product", "groep": MACHTEN, "soort": "regel", "titel": "Rekenregel product",
     "vraag": r"$a^m \cdot a^n = \;?$", "antwoord": r"$a^{m+n}$: zelfde grondtal → exponenten **optellen**. "
                                                    r"Let op: $a = a^1$."},
    {"id": "g-quotient", "groep": MACHTEN, "soort": "reken", "titel": "Quotiënt van machten", "tip": "Zelfde grondtal, gedeeld door elkaar: wat doe je met de exponenten?", "maak": g_quotient_machten},
    {"id": "g-negatief", "groep": H1, "soort": "reken", "titel": "Macht van een negatief getal", "tip": "Kijk goed: staan er haakjes rond het negatieve getal of niet?",
     "maak": g_negatief_grondtal},
    {"id": "r-quotient", "groep": MACHTEN, "soort": "regel", "titel": "Rekenregel quotiënt",
     "vraag": r"$a^m : a^n = \;?$ (met $a \neq 0$)",
     "antwoord": r"$a^{m-n}$: zelfde grondtal → exponenten **aftrekken**. Daarom is $a^n : a^n = a^0 = 1$."},
    {"id": "g-machtmacht", "groep": MACHTEN, "soort": "reken", "titel": "Macht van een macht", "tip": "Macht van een macht: optellen of vermenigvuldigen?", "maak": g_macht_van_macht},
    {"id": "g-aftrekken", "groep": H1, "soort": "reken", "titel": "Breuken aftrekken", "tip": "Min een negatief getal wordt plus. Daarna dezelfde noemer maken.", "maak": g_aftrekken},
    {"id": "r-machtmacht", "groep": MACHTEN, "soort": "regel", "titel": "Rekenregel macht van een macht",
     "vraag": r"$(a^m)^n = \;?$", "antwoord": r"$a^{m \cdot n}$: exponenten **vermenigvuldigen**."},
    {"id": "g-machtproduct", "groep": MACHTEN, "soort": "reken", "titel": "Macht van een product", "tip": "Bij een macht van een product gaat ELKE factor tot de macht, ook het getal.",
     "maak": g_macht_van_product},
    {"id": "r-machtproduct", "groep": MACHTEN, "soort": "regel", "titel": "Rekenregel macht van een product",
     "vraag": r"$(a \cdot b)^n = \;?$ En $\left(\frac{a}{b}\right)^n = \;?$",
     "antwoord": r"$(a \cdot b)^n = a^n \cdot b^n$ en $\left(\frac{a}{b}\right)^n = \frac{a^n}{b^n}$: "
                 r"**elke** factor (ook het getal ervoor!) tot de macht."},
    {"id": "g-vermenigvuldigen", "groep": H1, "soort": "reken", "titel": "Breuken vermenigvuldigen", "tip": "Teller maal teller, noemer maal noemer. Tel de mintekens voor het teken.",
     "maak": g_vermenigvuldigen},
    {"id": "r-negatief", "groep": H1, "soort": "regel", "titel": "Minteken en machten",
     "vraag": r"Wat is het verschil tussen $(-3)^2$ en $-3^2$?",
     "antwoord": r"$(-3)^2 = (-3)\cdot(-3) = 9$: met haakjes hoort het min bij het grondtal. "
                 r"$-3^2 = -(3 \cdot 3) = -9$: alleen de 3 wordt gekwadrateerd."},
    {"id": "g-delen", "groep": H1, "soort": "reken", "titel": "Delen door een breuk", "tip": "Delen door een breuk = vermenigvuldigen met het omgekeerde.", "maak": g_delen},
    {"id": "r-breuken", "groep": H1, "soort": "regel", "titel": "Rekenen met breuken",
     "vraag": "Hoe tel je twee breuken op met een verschillende noemer? En hoe deel je door een breuk?",
     "antwoord": "Optellen/aftrekken: eerst gelijknamig maken (zelfde noemer, het kgv), dan de tellers "
                 "optellen of aftrekken; de noemer blijft. Delen door een breuk = vermenigvuldigen met het "
                 r"omgekeerde: $\frac{a}{b} : \frac{c}{d} = \frac{a}{b} \cdot \frac{d}{c}$. Daarna vereenvoudigen!"},
    {"id": "g-gehele", "groep": H1, "soort": "reken", "titel": "Rekenen met negatieve getallen", "tip": "Min een negatief getal wordt plus. Werk van links naar rechts.",
     "maak": g_gehele_getallen},
    {"id": "r-tekens", "groep": H1, "soort": "regel", "titel": "Tekenregel",
     "vraag": "Welk teken krijgt een product of quotiënt met mintekens?",
     "antwoord": "Tel de mintekens: een even aantal → plus, een oneven aantal → min."},
    {"id": "g-volgorde", "groep": H1, "soort": "reken", "titel": "Volgorde van bewerkingen", "tip": "Eerst haakjes, dan machten, dan maal/gedeeld door, dan plus/min.", "maak": g_volgorde},
    {"id": "r-volgorde", "groep": H1, "soort": "regel", "titel": "Volgorde van bewerkingen",
     "vraag": "Wat is de volgorde van de bewerkingen?",
     "antwoord": "1. haakjes  2. machten  3. vermenigvuldigen en delen (van links naar rechts)  "
                 "4. optellen en aftrekken (van links naar rechts)."},
    {"id": "g-machtbreuk", "groep": H1, "soort": "reken", "titel": "Macht van een breuk", "tip": "Teller én noemer tot de macht. Even of oneven exponent?", "maak": g_macht_breuk},
    {"id": "g-omgekeerde", "groep": H1, "soort": "reken", "titel": "Omgekeerde en tegengestelde", "tip": "Omgekeerde: teller en noemer wisselen. Tegengestelde: alleen het teken wisselt.",
     "maak": g_omgekeerde},
    {"id": "r-omgekeerde", "groep": H1, "soort": "regel", "titel": "Omgekeerde of tegengestelde?",
     "vraag": "Wat is het verschil tussen het tegengestelde en het omgekeerde van een getal?",
     "antwoord": r"Tegengestelde: ander teken ($\frac{2}{3} \to -\frac{2}{3}$), samen 0. "
                 r"Omgekeerde: teller en noemer wisselen ($\frac{2}{3} \to \frac{3}{2}$), samen vermenigvuldigd 1."},
]
OP_ID = {k["id"]: k for k in KAARTEN}


def alle_kaarten(eigen=None):
    uit = list(KAARTEN)
    for e in eigen or []:
        if e.get("id") and e.get("vraag") and e.get("antwoord"):
            uit.append({"id": e["id"], "groep": EIGEN, "soort": "regel", "titel": e.get("titel") or e["vraag"][:40],
                        "vraag": e["vraag"], "antwoord": e["antwoord"]})
    return uit


def maak_opgave(kaart, seed=None):
    return kaart["maak"](random.Random(seed))


# ---------------------------------------------------------------- nakijken
def lees_getal(tekst):
    """Zet '3/4', '-3/4', '−0,75', '(-2)' ... om. Geeft (Fraction, teller, noemer) of None.
    teller/noemer zijn None als ze geen breuk typte."""
    t = (tekst or "").strip().replace(" ", "").replace("−", "-").replace("–", "-").replace(",", ".")
    while t.startswith("(") and t.endswith(")"):
        t = t[1:-1]
    if t.startswith("+"):
        t = t[1:]
    if not t:
        return None
    m = re.fullmatch(r"(-?)\(?(-?\d+)/(-?\d+)\)?", t)
    if m:
        teller, noemer = int(m.group(2)), int(m.group(3))
        if m.group(1):
            teller = -teller
        if noemer == 0:
            return None
        return Fraction(teller, noemer), teller, noemer
    try:
        return Fraction(Decimal(t)), None, None
    except (InvalidOperation, ValueError):
        return None


def kijk_na(opgave, tekst):
    """Geeft (status, boodschap). status: juist | bijna | fout | onleesbaar.
    'bijna' = de waarde klopt, maar de breuk is niet vereenvoudigd (of niet als breuk geschreven)."""
    gelezen = lees_getal(tekst)
    if gelezen is None:
        if opgave.get("exponent"):
            return "onleesbaar", "Typ alleen de exponent, bijvoorbeeld 7."
        return "onleesbaar", "Typ een getal of een breuk, bijvoorbeeld -3/4."
    waarde, teller, noemer = gelezen
    juist = Fraction(opgave["antwoord"])
    if waarde != juist:
        return "fout", "Dat klopt nog niet."
    if teller is not None and math.gcd(teller, noemer) != 1:
        return "bijna", "De waarde klopt, maar je breuk is nog niet vereenvoudigd. Kan je teller en noemer nog delen?"
    if teller is not None and noemer < 0:
        return "juist", "Juist! (Tip: zet het minteken liever vóór de breuk.)"
    if teller is None and juist.denominator != 1:
        return "bijna", "Het getal klopt, maar schrijf het als (vereenvoudigde) breuk."
    return "juist", "Juist!"


# ---------------------------------------------------------------- doosjes (Leitner)
def _d(s):
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def werk_bij(voortgang, kaart_id, goed, vandaag):
    """Past de voortgang van één kaart aan na een antwoord. Geeft de nieuwe kaart-voortgang terug.
    goed=True: doosje hoger. goed=False: terug naar doosje 1.
    goed=None: 'bijna' (bv. juist, maar pas na de opmerking 'vereenvoudig nog'): doosje blijft, morgen terug."""
    k = dict(voortgang.get(kaart_id) or {"doos": 0, "goed": 0, "fout": 0})
    if goed is None:
        k["doos"] = max(1, int(k.get("doos", 0)))
        k["bijna"] = int(k.get("bijna", 0)) + 1
        k["laatst"] = vandaag.isoformat()
        k["volgende"] = (vandaag + timedelta(days=1)).isoformat()
        voortgang[kaart_id] = k
        return k
    if goed:
        k["doos"] = min(MAX_DOOS, int(k.get("doos", 0)) + 1)
        k["goed"] = int(k.get("goed", 0)) + 1
    else:
        k["doos"] = 1
        k["fout"] = int(k.get("fout", 0)) + 1
    k["laatst"] = vandaag.isoformat()
    k["volgende"] = (vandaag + timedelta(days=TUSSENTIJD[k["doos"]])).isoformat()
    voortgang[kaart_id] = k
    return k


def te_herhalen(voortgang, vandaag, eigen=None):
    """Kaarten die al eens gezien zijn en vandaag (of eerder) terug moeten komen."""
    uit = []
    for k in alle_kaarten(eigen):
        v = voortgang.get(k["id"])
        if v and (_d(v.get("volgende")) or vandaag) <= vandaag:
            uit.append(k)
    return uit


def kies_opwarmer(voortgang, vandaag, aantal=3, voorrang_groep=None, eigen=None, rng=None):
    """Kiest de kaarten voor de opwarmer:
    1. kaarten die vandaag terug moeten komen (laagste doosje eerst),
    2. hooguit één nieuwe kaart (zodat er elke keer ook iets bijkomt),
    3. is er niets meer 'te doen', dan toch oude kaarten (de oudste herhaling eerst).
    Er zit altijd minstens één rekenkaart in."""
    rng = rng or random.Random()
    kaarten = alle_kaarten(eigen)

    def eerst_voorrang(k):
        return 0 if voorrang_groep and k["groep"] == voorrang_groep else 1

    gezien = [k for k in kaarten if voortgang.get(k["id"])]
    nieuw = sorted([k for k in kaarten if not voortgang.get(k["id"])], key=eerst_voorrang)
    tedoen = sorted(te_herhalen(voortgang, vandaag, eigen),
                    key=lambda k: (eerst_voorrang(k), voortgang[k["id"]].get("doos", 0),
                                   voortgang[k["id"]].get("volgende", "")))
    rest = sorted([k for k in gezien if k not in tedoen],
                  key=lambda k: (eerst_voorrang(k), voortgang[k["id"]].get("volgende", ""), rng.random()))

    gekozen = tedoen[:max(aantal - 1, 1)] + nieuw[:1]
    for k in tedoen + nieuw + rest:
        if len(gekozen) >= aantal:
            break
        if k not in gekozen:
            gekozen.append(k)
    gekozen = gekozen[:aantal]
    if gekozen and not any(k["soort"] == "reken" for k in gekozen):
        reken = next((k for k in tedoen + nieuw + rest if k["soort"] == "reken"), None)
        if reken:
            gekozen[-1] = reken
    # Afwisselen: niet twee keer na elkaar hetzelfde soort als het kan
    rng.shuffle(gekozen)
    return [k["id"] for k in gekozen]


def groep_voor_toets(onderwerp):
    o = (onderwerp or "").lower()
    if "macht" in o or "exponent" in o:
        return MACHTEN
    if any(w in o for w in ("breuk", "rationa", "diagnos", "herhaling", "negatie", "bewerking")):
        return H1
    return None


# ---------------------------------------------------------------- agenda-herinnering (.ics)
DAGCODES = {"maandag": "MO", "dinsdag": "TU", "woensdag": "WE", "donderdag": "TH",
            "vrijdag": "FR", "zaterdag": "SA", "zondag": "SU"}

_VTIMEZONE = """BEGIN:VTIMEZONE
TZID:Europe/Brussels
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
TZOFFSETTO:+0200
TZNAME:CEST
DTSTART:19700329T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
TZOFFSETTO:+0100
TZNAME:CET
DTSTART:19701025T030000
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
END:STANDARD
END:VTIMEZONE"""


def _ics_tekst(t):
    return t.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def maak_ics(dagen, uur, minuut, duur_min, link, vandaag, tot=None):
    """Een agendabestand met een wekelijks herhaalmoment op de gekozen dagen, met melding.
    Openen op de telefoon -> 'Toevoegen aan agenda' -> elke keer een melding met de link."""
    from datetime import datetime, timezone
    tot = tot or date(vandaag.year + (1 if vandaag.month >= 7 else 0), 6, 30)
    stempel = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    regels = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//wiskunde-bijles//herhaling//NL",
              "CALSCALE:GREGORIAN", "METHOD:PUBLISH", _VTIMEZONE]
    beschrijving = ("Tijd voor wiskunde! Begin met de opwarmer (oude leerstof) in de bijles-app. "
                    "Daarna: nieuwe leerstof of oefeningen uit de les opnieuw maken, op papier.")
    if link:
        beschrijving += f"\n{link}"
    for naam in dagen:
        code = DAGCODES[naam]
        # eerste keer: de eerstvolgende dag met die naam
        verschil = (list(DAGCODES.values()).index(code) - vandaag.weekday()) % 7
        start = datetime.combine(vandaag + timedelta(days=verschil), datetime.min.time()).replace(hour=uur, minute=minuut)
        einde = start + timedelta(minutes=duur_min)
        regels += [
            "BEGIN:VEVENT",
            f"UID:herhaling-{code}-{uur:02d}{minuut:02d}@wiskunde-bijles",
            f"DTSTAMP:{stempel}",
            f"DTSTART;TZID=Europe/Brussels:{start.strftime('%Y%m%dT%H%M%S')}",
            f"DTEND;TZID=Europe/Brussels:{einde.strftime('%Y%m%dT%H%M%S')}",
            f"RRULE:FREQ=WEEKLY;BYDAY={code};UNTIL={tot.strftime('%Y%m%d')}T220000Z",
            "SUMMARY:" + _ics_tekst("📐 Wiskunde: opwarmer + herhaling"),
            "DESCRIPTION:" + _ics_tekst(beschrijving),
        ]
        if link:
            regels.append("URL:" + link)
        regels += ["BEGIN:VALARM", "ACTION:DISPLAY", "TRIGGER:PT0M",
                   "DESCRIPTION:" + _ics_tekst("Tijd voor wiskunde: eerst de opwarmer!"), "END:VALARM",
                   "END:VEVENT"]
    regels.append("END:VCALENDAR")
    # ICS wil CRLF en regels van max. 75 bytes (langer: vouwen met een spatie)
    uit = []
    for r in "\n".join(regels).split("\n"):
        b = r.encode("utf-8")
        while len(b) > 74:
            knip = 74
            while (b[knip] & 0xC0) == 0x80:  # niet midden in een teken knippen
                knip -= 1
            uit.append(b[:knip].decode("utf-8"))
            b = b" " + b[knip:]
        uit.append(b.decode("utf-8"))
    return "\r\n".join(uit) + "\r\n"
