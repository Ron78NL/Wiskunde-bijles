"""Blijvende opslag voor gesprekken, het uitleg-schrift en het groeiprofiel.

Online (Streamlit Cloud) worden eigen bestanden gewist bij elke herstart of update.
Daarom bewaren we alles in een aparte, PRIVÉ GitHub-repo, als in de Secrets staat:
    GITHUB_TOKEN = "..."                         (sleutel met schrijfrecht op die ene repo)
    DATA_REPO    = "Ron78NL/wiskunde-bijles-data"
Staat dat er niet, dan bewaren we gewoon in de map 'bewaard/' naast de app
(handig op de eigen computer; die map gaat niet naar GitHub).
"""
import base64
import json
import ssl
import urllib.error
import urllib.request
from pathlib import Path


def _ssl():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


class Opslag:
    def __init__(self, token="", repo="", map_lokaal=None):
        self.token = token.strip()
        self.repo = repo.strip().strip("/")
        self.online = bool(self.token and self.repo)
        self.map = Path(map_lokaal) if map_lokaal else Path("bewaard")
        self._sha = {}  # GitHub wil de 'sha' van een bestand kennen om het te overschrijven

    @property
    def uitleg(self):
        return f"privé GitHub-repo {self.repo}" if self.online else f"map {self.map}"

    # ------------------------------------------------------------ GitHub
    def _gh(self, methode, pad, body=None):
        url = f"https://api.github.com/repos/{self.repo}/contents/{pad}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=methode, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "wiskunde-bijles",
        })
        with urllib.request.urlopen(req, timeout=30, context=_ssl()) as r:
            return json.loads(r.read().decode("utf-8"))

    # ------------------------------------------------------------ publiek
    def lees_bytes(self, pad):
        """Leest een bestand als bytes; geeft None als het (nog) niet bestaat."""
        if not self.online:
            f = self.map / pad
            return f.read_bytes() if f.exists() else None
        try:
            d = self._gh("GET", pad)
        except urllib.error.HTTPError as e:
            # 404 = bestand bestaat (nog) niet; 409 = de repo is nog helemaal leeg
            if e.code in (404, 409):
                self._sha.pop(pad, None)
                return None
            raise
        self._sha[pad] = d.get("sha")
        if d.get("content"):
            return base64.b64decode(d["content"])
        # bestanden > 1 MB komen zonder inhoud mee: apart ophalen
        req = urllib.request.Request(d["download_url"], headers={"Authorization": f"Bearer {self.token}"})
        with urllib.request.urlopen(req, timeout=30, context=_ssl()) as r:
            return r.read()

    def lees(self, pad, standaard=None):
        """Leest een JSON-bestand; geeft 'standaard' als het (nog) niet bestaat."""
        data = self.lees_bytes(pad)
        if data is None:
            return standaard
        try:
            return json.loads(data.decode("utf-8"))
        except Exception:
            return standaard

    def schrijf(self, pad, obj):
        self.schrijf_bytes(pad, json.dumps(obj, ensure_ascii=False, indent=1).encode("utf-8"))

    def schrijf_bytes(self, pad, data):
        if not self.online:
            f = self.map / pad
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
            return
        body = {"message": f"bewaar {pad}", "content": base64.b64encode(data).decode("ascii")}
        if pad not in self._sha:
            self.lees(pad)  # sha ophalen als het bestand al bestaat
        if self._sha.get(pad):
            body["sha"] = self._sha[pad]
        try:
            d = self._gh("PUT", pad, body)
        except urllib.error.HTTPError as e:
            if e.code not in (409, 422):
                raise
            self.lees(pad)  # iemand anders schreef ondertussen: nieuwste sha halen en opnieuw
            body["sha"] = self._sha.get(pad)
            d = self._gh("PUT", pad, body)
        self._sha[pad] = d.get("content", {}).get("sha")
