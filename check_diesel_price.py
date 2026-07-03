#!/usr/bin/env python3
"""
Récupère le prix du Diesel (B7) d'une station Carbu.com
et envoie une notification push sur iPhone via ntfy.sh.

Configuration : variables d'environnement
- STATION_URL : URL de la fiche station sur carbu.com
- NTFY_TOPIC  : nom du "topic" ntfy (ton canal de notif perso)
"""

import os
import re
import sys
import requests
from bs4 import BeautifulSoup

STATION_URL = os.environ.get(
    "STATION_URL",
    "https://carbu.com/belgique/index.php/station/tourneur/assesse/5330/1070",
)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
FUEL_LABEL = "Diesel (B7)"


def get_diesel_price(url: str) -> tuple[str, str]:
    """Retourne (prix, date_maj) trouvés sur la page de la station."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PriceChecker/1.0)"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    # On parse le texte visible plutôt que le HTML brut : plus robuste
    # si la structure des balises change.
    soup = BeautifulSoup(resp.text, "html.parser")
    text = soup.get_text(separator="\n")

    # On cherche le bloc "Diesel (B7)" suivi *immédiatement* (juste des espaces/
    # retours à la ligne entre les deux) du prix et de la date.
    # Important : le nom du carburant apparaît aussi dans un menu déroulant de
    # filtre en haut de page, donc on ne doit pas matcher n'importe quel texte
    # entre le label et le prix, seulement du whitespace.
    pattern = re.compile(
        re.escape(FUEL_LABEL) + r"\s*([\d,]+)\s*€/L\s*(\d{2}/\d{2}/\d{2})"
    )
    match = pattern.search(text)
    if not match:
        raise ValueError("Prix du diesel introuvable sur la page — le site a peut-être changé de structure.")

    price, date = match.group(1), match.group(2)
    return price, date


def send_notification(title: str, message: str) -> None:
    if not NTFY_TOPIC:
        print("NTFY_TOPIC non défini — notification non envoyée.")
        return
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title.encode("utf-8"),
            "Priority": "default",
            "Tags": "fuelpump",
        },
        timeout=15,
    )


def main() -> None:
    try:
        price, date = get_diesel_price(STATION_URL)
    except Exception as exc:
        send_notification("Erreur suivi diesel", f"Impossible de récupérer le prix : {exc}")
        print(f"Erreur : {exc}", file=sys.stderr)
        sys.exit(1)

    message = f"Diesel (B7) : {price} €/L (maj {date})"
    print(message)
    send_notification("Prix du diesel", message)


if __name__ == "__main__":
    main()
