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
    text = text.lower()

    food_keywords = ["food", "nourriture", "resto", "restaurant", "plat", "meal"]
    drink_keywords = ["boisson", "drink", "bar", "beverage"]

    if any(k in text for k in food_keywords):
        return "nourriture"
    if any(k in text for k in drink_keywords):
        return "boissons"

    # fallback : nourriture
    return "nourriture"


def detect_service(row_label):
    """Analyse du centre de revenu → matin / midi / soir."""
    label = row_label.lower()

    if "04:00" in label and "11:00" in label:
        return "matin"
    if "11:00" in label and "17:00" in label:
        return "midi"
    if "17:00" in label and "04:00" in label:
        return "soir"

    # fallback : midi
    return "midi"


# ---------------------------
# PARSER PRINCIPAL
# ---------------------------

def parse_daily_report(file):
    """
    Parse un fichier Cumulatif_YYYYMMDD.xlsx venant de RestoTrack.
    Retourne :
        - dataframe propre par service
        - totaux midi/soir/nourriture/boissons
    """

    df = pd.read_excel(file)

    # Nettoyage des noms de colonnes
    df.columns = [str(c).strip() for c in df.columns]

    # Détection dynamique des colonnes clés
    col_couverts = next(c for c in df.columns if "couvert" in c.lower())
    col_ca_total = next(c for c in df.columns if ("total" in c.lower() and "ca" in c.lower()) or ("total" == c.lower()))

    # Filtrer les lignes non numériques pour éviter l’erreur "Couverts"
    df_clean = df[df[col_couverts].apply(lambda x: str(x).replace(" ", "").isdigit())].copy()

    df_clean[col_couverts] = df_clean[col_couverts].astype(int)
    df_clean[col_ca_total] = df_clean[col_ca_total].apply(clean_amount)

    # Détection service + catégorie
    df_clean["service"] = df["Revenu par centre de revenus"].apply(detect_service)
    df_clean["categorie"] = df["Revenu par centre de revenus"].apply(detect_category)

    # Regroupement par service + catégorie
    grouped = df_clean.groupby(["service", "categorie"]).agg({
        col_couverts: "sum",
        col_ca_total: "sum"
    }).reset_index()

    # Extraction structurée
    output = {
        "midi_nourriture": 0,
        "midi_boissons": 0,
        "soir_nourriture": 0,
        "soir_boissons": 0,
        "matin_nourriture": 0,
        "matin_boissons": 0,
        "total_couverts": df_clean[col_couverts].sum(),
        "total_ca": df_clean[col_ca_total].sum(),
        "details": df_clean
    }

    for _, row in grouped.iterrows():
        service = row["service"]
        cat = row["categorie"]
        ca = row[col_ca_total]

        key = f"{service}_{cat}"
        if key in output:
            output[key] = ca

    return output
