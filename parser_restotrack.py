import pandas as pd
import numpy as np

# ---------------------------
# Nettoyage nombre FR → float
# ---------------------------
def to_float(x):
    if x is None or pd.isna(x):
        return 0.0
    s = str(x)
    s = (s.replace("€", "")
           .replace("%", "")
           .replace("\xa0", "")
           .replace(" ", "")
           .replace("\u202f", "")
           .replace(",", ".")
    )
    if s == "":
        return 0.0
    try:
        return float(s)
    except:
        return 0.0


# ---------------------------
# Classificateur Nourriture / Boissons
# ---------------------------
def classify_centre(label):
    lbl = str(label).lower()
    # Boissons
    if any(k in lbl for k in ["bar", "boiss", "bev", "drink"]):
        if "nour" in lbl:  # bar nourriture = nourriture
            return "Nourriture"
        return "Boissons"
    # Nourriture
    if any(k in lbl for k in [
        "rest", "nour", "food", "plat", "cuisine", "encas", "snack"
    ]):
        return "Nourriture"
    return "Autre"


# ---------------------------
# Détection des services
# ---------------------------
def detect_service(label):
    lbl = str(label).lower()
    if "matin" in lbl:
        return "Matin"
    if "déjeuner" in lbl or "dejeuner" in lbl or "midi" in lbl:
        return "Midi"
    if "nuit" in lbl or "17:00" in lbl or "04:00" in lbl:
        return "Soir"
    return None


# ---------------------------
# Extraction de la date
# ---------------------------
def extract_date(df):
    for v in df.iloc[:5, :8].values.flatten():
        try:
            d = pd.to_datetime(v, dayfirst=True, errors="raise")
            return d.date()
        except:
            pass
    return None


# ---------------------------
# Parsing principal
# ---------------------------
def parse_restotrack(file):
    raw = pd.read_excel(file, header=None)

    # ---------------- Date ----------------
    report_date = extract_date(raw)
    if report_date is None:
        raise Exception("Impossible de détecter la date (ex: cellule C1)")

    # ----------- Trouver la ligne d’en-têtes ----------
    header_row = None
    for i, row in raw.iterrows():
        if any(str(c).strip().lower() == "couverts" for c in row):
            header_row = i
            break

    if header_row is None:
        raise Exception("Impossible de trouver les en-têtes")

    headers = raw.iloc[header_row].fillna("")
    df = raw.iloc[header_row+1:].copy()
    df.columns = [str(c).strip() for c in headers]

    # On garde uniquement Label – Couverts – Total
    cols = df.columns
    label_col = cols[0]
    couv_col = [c for c in cols if "couver" in c.lower()][0]
    total_col = [c for c in cols if "total" in c.lower()][0]

    df = df[[label_col, couv_col, total_col]].copy()
    df = df.dropna(how="all")

    df["Couverts"] = df[couv_col].apply(to_float)
    df["CA"] = df[total_col].apply(to_float)

    # ---------- Reconstruire les blocs ----------
    rows = []
    current_centre = None

    for _, r in df.iterrows():
        label = str(r[label_col]).strip()
        if not label:
            continue

        # Ligne centre de revenus
        if detect_service(label) is None:
            current_centre = label
            continue

        # Ligne service
        srv = detect_service(label)
        if srv is None:
            continue

        rows.append({
            "Date": report_date,
            "Centre": current_centre,
            "Categorie": classify_centre(current_centre),
            "Service": srv,
            "Couverts": r["Couverts"],
            "CA": r["CA"],
        })

    df2 = pd.DataFrame(rows)

    # ---------------- AGGRÉGATION ----------------
    # ServiceAgrégé: Matin+Midi → "Midi", Nuit → "Soir"
    df2["ServiceAgg"] = df2["Service"].replace({
        "Matin": "Midi",
        "Midi": "Midi",
        "Soir": "Soir"
    })

    # Summation nourriture et boissons
    total = df2.groupby(["Categorie", "ServiceAgg"], as_index=False)\
               .agg({"CA": "sum", "Couverts": "sum"})

    return df2, total, report_date
