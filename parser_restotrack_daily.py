import pandas as pd

# ---------------------------------------
#  FUNCTIONS USED BY DAILY + N-1 PARSER
# ---------------------------------------

def clean_amount(value):
    """Convertit un montant Excel (ex : '1.234,56 €') en float Python."""
    if value is None:
        return 0.0
    value = str(value).replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return float(value)
    except:
        return 0.0

def detect_category(text):
    """Détecte si une ligne appartient à Nourriture / Boissons."""
    if not isinstance(text, str):
        return None
    t = text.lower()
    if "nourriture" in t or "resta" in t or "food" in t:
        return "food"
    if "boisson" in t or "bar" in t or "drink" in t:
        return "bar"
    return None

# ---------------------------------------
#  PARSER DAILY REPORT
# ---------------------------------------

def parse_daily_report(file):
    df = pd.read_excel(file, header=None)

    # ---------- 1. Extraction date ----------
    report_date = None
    for col in df.columns:
        for row in df[col].dropna().astype(str):
            if "/" in row:
                try:
                    report_date = pd.to_datetime(row, dayfirst=True)
                    break
                except:
                    pass
        if report_date is not None:
            break
    if report_date is None:
        raise ValueError("Impossible de détecter la date du rapport.")

    # ---------- 2. Trouver bloc Total ----------
    idx_total = df[df.astype(str).apply(lambda r: r.str.contains("Total", na=False)).any(axis=1)].index
    if len(idx_total) == 0:
        raise ValueError("Ligne 'Total' introuvable")
    row_total = idx_total[0]

    # ---------- 3. Extraction des couverts ----------
    couverts_total = int(df.iloc[row_total, 1])
    couverts_matin = int(df.iloc[row_total + 1, 1])
    couverts_midi  = int(df.iloc[row_total + 2, 1])
    couverts_soir  = int(df.iloc[row_total + 3, 1])

    # ---------- 4. Extraction CA matin / midi / soir ----------
    ca_matin = clean_amount(df.iloc[row_total + 1, 5])
    ca_midi  = clean_amount(df.iloc[row_total + 2, 5])
    ca_soir  = clean_amount(df.iloc[row_total + 3, 5])

    # ---------- 5. Détection blocs Nourriture / Boissons ----------
    idx_food = df[df.astype(str).apply(lambda r: r.str.contains("Nourriture", na=False)).any(axis=1)].index
    idx_bar  = df[df.astype(str).apply(lambda r: r.str.contains("Boisson",    na=False)).any(axis=1)].index

    food_midi = food_soir = bar_midi = bar_soir = 0.0

    if len(idx_food):
        food_midi = clean_amount(df.iloc[idx_food[0] + 1, 5])
        food_soir = clean_amount(df.iloc[idx_food[0] + 2, 5])

    if len(idx_bar):
        bar_midi = clean_amount(df.iloc[idx_bar[0] + 1, 5])
        bar_soir = clean_amount(df.iloc[idx_bar[0] + 2, 5])

    return pd.DataFrame({
        "Date": [report_date],
        "Couverts_midi": [couverts_midi],
        "Couverts_soir": [couverts_soir],
        "Couverts_total": [couverts_total],

        "Food_midi_TTC": [food_midi],
        "Food_soir_TTC": [food_soir],

        "Bar_midi_TTC": [bar_midi],
        "Bar_soir_TTC": [bar_soir],

        "CA_total_TTC": [food_midi + food_soir + bar_midi + bar_soir],
    })
