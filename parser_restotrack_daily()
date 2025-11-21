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
    )
    if s == "":
        return 0.0
    # gestion éventuelle . et ,
    if "," in s and "." in s:
        # on garde le dernier séparateur comme décimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0


# ---------------------------
# Classificateur Nourriture / Boissons
# ---------------------------
def classify_centre(label: str) -> str:
    """
    Classe le centre de revenus en Nourriture / Boissons / Autre.

    - Tout ce qui contient 'bar' ou 'boiss' = Boissons
      SAUF si on voit aussi 'nour' (bar nourriture) -> Nourriture.
    - 'rest', 'nour', 'food', 'plat', 'cuisine', 'encas', 'snack', 'boutique'
      -> Nourriture
    """
    lbl = str(label).lower()

    # Boissons
    if any(k in lbl for k in ["bar", "boiss", "bev", "drink"]):
        if "nour" in lbl:
            return "Nourriture"
        return "Boissons"

    # Nourriture
    if any(k in lbl for k in [
        "rest", "nour", "food", "plat", "cuisine", "encas", "snack", "boutique"
    ]):
        return "Nourriture"

    return "Autre"


# ---------------------------
# Détection des services
# ---------------------------
def detect_service(label: str):
    """
    Retourne 'Matin', 'Midi', 'Soir' ou None en fonction du texte.
    """
    lbl = str(label).lower()

    if "matin" in lbl:
        return "Matin"
    if "déjeuner" in lbl or "dejeuner" in lbl or "midi" in lbl:
        return "Midi"
    if "nuit" in lbl or "17:00" in lbl or "04:00" in lbl or "soir" in lbl:
        return "Soir"
    return None


# ---------------------------
# Extraction de la date dans les 5 premières lignes
# ---------------------------
def extract_date(df: pd.DataFrame):
    for v in df.iloc[:5, :8].values.flatten():
        try:
            d = pd.to_datetime(v, dayfirst=True, errors="raise")
            return d.date()
        except Exception:
            continue
    return None


# ---------------------------
# Parsing principal Restotrack
# ---------------------------
def parse_restotrack(file):
    raw = pd.read_excel(file, header=None)

    # 1) Date du rapport
    report_date = extract_date(raw)
    if report_date is None:
        raise Exception("Impossible de détecter la date du rapport (ex: cellule C1).")

    # 2) Ligne d'en-têtes (celle où apparaît 'Couverts')
    header_row = None
    for i, row in raw.iterrows():
        if any("couverts" in str(c).lower() for c in row):
            header_row = i
            break

    if header_row is None:
        raise Exception("Impossible de trouver la ligne des en-têtes (Couverts).")

    headers = raw.iloc[header_row].fillna("")
    df = raw.iloc[header_row + 1 :].copy()
    df.columns = [str(c).strip() for c in headers]

    # 3) Colonnes importantes
    cols = list(df.columns)

    # Colonne Label (centre / service)
    label_col = cols[0]

    # Colonne Couverts
    couv_col = [c for c in cols if "couver" in c.lower()][0]

    # Colonnes avec "total"
    total_candidates = [c for c in cols if "total" in c.lower()]

    if not total_candidates:
        raise Exception("Impossible de trouver une colonne 'Total' pour le CA TTC.")

    # On veut le CA TTC → on EXCLUT les colonnes contenant '%' (ex: '% du CA total')
    ttc_candidates = [c for c in total_candidates if "%" not in c.lower()]

    # S'il y en a plusieurs, on prend la dernière (dans ton fichier: 'Total' tout à droite)
    if ttc_candidates:
        total_col = ttc_candidates[-1]
    else:
        # fallback: dernière colonne 'total'
        total_col = total_candidates[-1]

    # 4) Nettoyage des données de base
    df = df[[label_col, couv_col, total_col]].copy()
    df = df.dropna(how="all")

    df["Couverts"] = df[couv_col].apply(to_float)
    df["CA"] = df[total_col].apply(to_float)

    # 5) Reconstruction des blocs Centre / Service
    rows = []
    current_centre = None

    for _, r in df.iterrows():
        label = str(r[label_col]).strip()
        if not label:
            continue

        srv = detect_service(label)

        # Si pas de service détecté -> c'est un centre de revenus
        if srv is None:
            current_centre = label
            continue

        # Si on a bien un centre en cours, on crée la ligne service
        rows.append({
            "Date": report_date,
            "Centre": current_centre,
            "Categorie": classify_centre(current_centre),
            "Service": srv,
            "Couverts": r["Couverts"],
            "CA": r["CA"],
        })

    df2 = pd.DataFrame(rows)

    # 6) Service agrégé (regroupement Matin avec Midi)
    #    -> C’EST ICI que Matin nourriture va dans Midi nourriture,
    #       et Matin boissons dans Midi boissons.
    df2["ServiceAgg"] = df2["Service"].replace({
        "Matin": "Midi",
        "Midi": "Midi",
        "Soir": "Soir"
    })

    # 7) Agrégation finale par Catégorie + ServiceAgg
    total = df2.groupby(["Categorie", "ServiceAgg"], as_index=False)\
               .agg({"CA": "sum", "Couverts": "sum"})

    return df2, total, report_date
