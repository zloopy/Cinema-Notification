#!/usr/bin/env python3
"""
Vérifie si des films "surveillés" (films.txt) ont des séances programmées
à Paris / en Île-de-France, et envoie une notification push (ntfy.sh)
pour toute nouvelle séance jamais vue.

Basé sur la librairie communautaire non-officielle "allocine-seances"
(scraping du site allocine.fr — pas d'API officielle publique).
"""

import json
import os
import sys
import unicodedata
from datetime import date, timedelta

import requests
from allocineAPI.allocineAPI import allocineAPI

# --- Configuration ---------------------------------------------------

FILMS_FILE = "films.txt"
STATE_FILE = "state.json"
# Noms de départements Allociné à surveiller (voir README pour étendre à toute la France)
DEPARTEMENTS_A_SURVEILLER = ["Paris", "Hauts-de-Seine", "Seine-Saint-Denis", "Val-de-Marne"]
JOURS_A_VERIFIER = 3  # aujourd'hui + les 2 jours suivants
NTFY_TOPIC = os.environ.get("NTFY_TOPIC")  # défini en secret GitHub Actions


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.lower().strip()


def load_films() -> list[str]:
    if not os.path.exists(FILMS_FILE):
        print(f"⚠️  {FILMS_FILE} introuvable.")
        return []
    with open(FILMS_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def load_state() -> set:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_state(state: set) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(state), f, ensure_ascii=False, indent=2)


def notify(title: str, message: str) -> None:
    if not NTFY_TOPIC:
        print("⚠️  NTFY_TOPIC non défini, notification affichée seulement :")
        print(f"  {title} — {message}")
        return
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            data=message.encode("utf-8"),
            headers={"Title": title.encode("utf-8"), "Priority": "default", "Tags": "clapper"},
            timeout=10,
        )
    except Exception as e:
        print(f"⚠️  Échec envoi notif: {e}")


def main() -> None:
    films = load_films()
    if not films:
        print("Aucun film à surveiller (films.txt vide). Arrêt.")
        return
    films_norm = [normalize(f) for f in films]

    state = load_state()
    api = allocineAPI()

    try:
        deps = api.get_departements()
    except Exception as e:
        print(f"❌ ÉCHEC get_departements(): {e!r}")
        return
    print(f"DEBUG: {len(deps)} départements reçus. Exemples: {deps[:5]}")

    cibles = [d for d in deps if d["name"] in DEPARTEMENTS_A_SURVEILLER]
    print(f"DEBUG: départements ciblés trouvés: {cibles}")
    if not cibles:
        print("⚠️  Aucun département correspondant trouvé sur Allociné.")
        return

    dates = [(date.today() + timedelta(days=i)).isoformat() for i in range(JOURS_A_VERIFIER)]
    nouvelles = 0
    total_cinemas = 0
    total_seances_vues = 0
    erreurs = 0
    titres_vus = set()
    indices_diagnostic = ["bebop", "odyssee", "odyssée"]
    titres_proches = set()

    for dep in cibles:
        try:
            cinemas = api.get_cinema(dep["id"])
        except Exception as e:
            erreurs += 1
            print(f"❌ Erreur cinémas pour {dep['name']}: {e!r}")
            continue
        print(f"DEBUG: {len(cinemas)} cinémas trouvés pour {dep['name']}")
        total_cinemas += len(cinemas)

        for cinema in cinemas:
            for d in dates:
                try:
                    seances = api.get_showtime(cinema["id"], d)
                except Exception as e:
                    erreurs += 1
                    if erreurs <= 5:
                        print(f"❌ Erreur séances pour {cinema['name']} ({d}): {e!r}")
                    continue
                total_seances_vues += len(seances)

                for s in seances:
                    titre_brut = s.get("title", "")
                    titre_norm = normalize(titre_brut)
                    titres_vus.add(titre_brut)
                    if any(ind in titre_norm for ind in [normalize(x) for x in indices_diagnostic]):
                        titres_proches.add(titre_brut)

                for s in seances:
                    titre_norm = normalize(s.get("title", ""))
                    match = next((f for f, fn in zip(films, films_norm) if fn in titre_norm), None)
                    if not match:
                        continue

                    print(f"DEBUG MATCH BRUT: cinema={cinema['name']!r} date={d!r} data={s!r}")

                    horaires = (s.get("VF") or []) + (s.get("VO") or [])
                    for h in horaires:
                        key = f"{match}|{cinema['id']}|{h}"
                        if key in state:
                            continue
                        state.add(key)
                        nouvelles += 1
                        notify(
                            f"🎬 {match} ressort en salle !",
                            f"{cinema['name']} ({cinema['address']})\n{h}",
                        )
                        print(f"Nouvelle séance: {match} — {cinema['name']} — {h}")

    save_state(state)
    print(f"DEBUG: {len(titres_vus)} titres uniques vus au total.")
    print(f"DEBUG: titres contenant 'bebop'/'odyssee': {sorted(titres_proches)}")
    print(
        f"DEBUG résumé: {total_cinemas} cinémas parcourus, "
        f"{total_seances_vues} lignes de séances vues (tous films confondus), "
        f"{erreurs} erreur(s) de requête."
    )
    print(f"Terminé. {nouvelles} nouvelle(s) séance(s) notifiée(s).")


if __name__ == "__main__":
    sys.exit(main())
