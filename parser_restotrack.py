import pandas as pd
import numpy as np
import re

# --------------------------------------------------
# Convertisseur FR/BE -> float
# --------------------------------------------------
def to_float(x):
    if x is None or pd.isna(x):
        return 0.0

    s = str(x)
    s = s.replace("€", "").replace("%", "").replace("\xa0", "").replace(" ", "").replace("\u202f","")

    # Cas 1 : format FR 1.234,56 → 1234.56
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")

    # Cas 2 : 123,45 → 123.45
    elif "," in s:
        s = s.replace(",", ".")

    try:
        return float(s)
    except:
        return 0.0


# --------------------------------------------------
# Détection du service : matin -> midi
# --------------------------------------------------
def detect_service(s):
    s = str(s).lower()
    if "matin" in s:
        return "Midi"          # tu veux matin fusionné avec midi
    if "déjeuner" in s or "dejeuner" in s or "midi" in s:
        return "Midi"
    if "nuit" in s or "17:00" in s or "00:" in s or "soir" in s:
        return "Soir"
    return None


# --------------------------------------------------
# Catégorisation centre
# --------------------------------------------------
def detect_category(text):
    t = str(text).lower()
    if any(k in t for k in ["rest", "nour", "food", "cuisine", "snack", "encas", "boutique"]):
        return "Nourriture"
    if any(k in t for k in ["boiss", "bar", "cocktail", "bev", "beer"]):
        return "Boissons"
    return None


# --------------------------------------------------
# Extraction date dans les 10 premières lignes
# --------------------------------------------------
def extract_date(df):
    for row in df.values[:10]:
        for v in row:
            d = pd.to_datetime(v, dayfirst=True, errors="ignore")
            if isinstance(d, pd.Timestamp):
                if 2020 < d.year < 2035:
                    return d.date()
    return None


# --------------------------------------------------
# PARSER PRINCIPAL
# --------------------------------------------------
def parse_restotrack(file):

    raw = pd.read_excel(file, header=None)

    report_date = extract_date(raw)

    # Trouver ligne d'en-têtes ("Couverts")
    header_row = None
    for i, row in raw.iterrows():
        if any("couver" in str(c).lower() for c in row):
            header_row = i
            break

    if header_row is None:
        raise Exception("Impossible de trouver ligne des en-têtes.")

    header = raw.iloc[header_row].fillna("")
    df = raw.iloc[header_row+1:].copy()
    df.columns = header

    # Limiter aux colonnes utiles
    cols = [str(c) for c in df.columns]

    # Colonne TTC obligatoire
    ttc_candidates = [c for c in cols if "ttc" in c.lower()]
    if len(ttc_candidates) == 0:
        # fallback : première colonne contenant "total"
        ttc_candidates = [c for c in cols if "total" in c.lower()]
    total_col = ttc_candidates[0]

    # Colonne couverts
    cov_candidates = [c for c in cols if "couver" in c.lower()]
    cov_col = cov_candidates[0]

    # Colonne Label
    label_col = cols[0]

    df = df[[label_col, cov_col, total_col]]

    df["Couverts"] = df[cov_col].apply(to_float)
    df["CA"] = df[total_col].apply(to_float)
    df["label"] = df[label_col].astype(str).str.strip()

    rows = []
    current_center = None

    for _, r in df.iterrows():
        label = str(r["label"]).strip()

        # changement de centre
        if detect_service(label) is None:
            if detect_category(label) is not None:
                current_center = label
            continue

        service = detect_service(label)
        if service is None:
            continue

        category = detect_category(current_center)

        if category is None:
            continue

        rows.append({
            "Date": report_date,
            "Centre": current_center,
            "Categorie": category,
            "ServiceAgg": service,
            "Couverts": r["Couverts"],
            "CA": r["CA"]
        })

    df2 = pd.DataFrame(rows)

    return df2, df2.groupby(["Categorie","ServiceAgg"]) \
                   .agg({"CA":"sum","Couverts":"sum"}) \
                   .reset_index(), report_date

