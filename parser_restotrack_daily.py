import pandas as pd
import re

# ---------------------------
# Utilitaires
# ---------------------------

def clean_amount(value):
    """Nettoie un montant TTC ou HT (€, virgules, espaces...)."""
    if pd.isna(value):
        return 0.0
    value = str(value)
    value = value.replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(value)
    except:
        return 0.0


def detect_category(text):
    """Retourne 'nourriture' ou 'boissons' selon la nature du poste."""
    text = str(text).lower()

    food_keywords = ["food", "nourriture", "resto", "restaurant", "plat", "meal"]
    drink_keywords = ["boisson", "drink", "bar", "beverage"]

    if any(k in text for k in drink_keywords):
        return "boissons"
    if any(k in text for k in food_keywords):
        return "nourriture"

    return "nourriture"


def detect_service(text):
    """Analyse du centre de revenu → matin / midi / soir."""
    t = str(text).lower()

    if "04:00" in t and "11:00" in t:
        return "matin"
    if "11:00" in t and "17:00" in t:
        return "midi"
    if "17:00" in t and "04:00" in t:
        return "soir"

    # fallback : midi
    return "midi"


# ---------------------------
# PARSER PRINCIPAL
# ---------------------------

def parse_daily_report(file):
    """
    Parse un fichier Cumulatif_YYYYMMDD.xlsx venant de RestoTrack.
    Retourne un dictionnaire structuré contenant :
        - CA par service
        - CA par catégorie
        - total CA
        - total couverts
        - dataframe détaillé nettoyé
    """

    df = pd.read_excel(file)

    # Nettoyage des noms de colonnes
    df.columns = [str(c).strip() for c in df.columns]

    # Détections automatiques des colonnes
    col_couverts = next(c for c in df.columns if "couvert" in c.lower())
    col_ca = next(c for c in df.columns if "total" in c.lower() and "ca" in c.lower())

    # Colonne libellés centre de revenu
    col_label = df.columns[0]   # "Revenu par centre de revenus"

    # Nettoyage de la colonne couverts
    df[col_couverts] = (
        df[col_couverts]
        .astype(str)
        .str.replace(" ", "")
        .str.extract(r"(\d+)", expand=False)
    )

    df = df.dropna(subset=[col_couverts])

    df[col_couverts] = df[col_couverts].astype(int)

    # Nettoyage CA
    df[col_ca] = df[col_ca].apply(clean_amount)

    # Détection service + catégorie
    df["service"] = df[col_label].apply(detect_service)
    df["categorie"] = df[col_label].apply(detect_category)

    # Groupement
    grouped = df.groupby(["service", "categorie"]).agg({
        col_couverts: "sum",
        col_ca: "sum"
    }).reset_index()

    out = {
        "midi_nourriture": 0,
        "midi_boissons": 0,
        "soir_nourriture": 0,
        "soir_boissons": 0,
        "matin_nourriture": 0,
        "matin_boissons": 0,
        "total_couverts": df[col_couverts].sum(),
        "total_ca": df[col_ca].sum(),
        "details": df
    }

    for _, row in grouped.iterrows():
        key = f"{row['service']}_{row['categorie']}"
        if key in out:
            out[key] = row[col_ca]

    return out
