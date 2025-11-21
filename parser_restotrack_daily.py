import pandas as pd
import numpy as np

# --------------------------------------------------------
# Détection automatique de catégorie
# --------------------------------------------------------
def detect_category(label: str) -> str:
    if not isinstance(label, str):
        return "unknown"
    label = label.lower()

    food = ["food", "nourriture", "restaurant", "resto", "snack", "boutique"]
    drinks = ["bar", "boisson", "drink", "beverage", "beer", "wine"]

    if any(k in label for k in food):
        return "food"
    if any(k in label for k in drinks):
        return "drinks"
    return "unknown"


def clean_amount(val):
    if pd.isna(val):
        return 0.0
    val = str(val).replace("€", "").replace(" ", "").replace(",", ".")
    try:
        return float(val)
    except:
        return 0.0


# --------------------------------------------------------
# PARSER JOURNALIER RESTOTRACK (premium)
# --------------------------------------------------------
def parse_restotrack_daily(path):

    df = pd.read_excel(path, header=None)

    # -------------- DATE --------------
    try:
        report_date = pd.to_datetime(df.iloc[0, 2])
    except:
        report_date = None

    # -------------- INDEXES MIDI / SOIR / MATIN --------------
    midi_idx = df[df[0].astype(str).str.contains("Déjeuner/midi", case=False, na=False)].index
    soir_idx = df[df[0].astype(str).str.contains("Nuit", case=False, na=False)].index
    matin_idx = df[df[0].astype(str).str.contains("Matin", case=False, na=False)].index

    results = {
        "date": report_date,
        "ca_midi_food": 0,
        "ca_midi_drinks": 0,
        "ca_soir_food": 0,
        "ca_soir_drinks": 0,
        "couverts_midi": 0,
        "couverts_soir": 0,
        "total_ca": 0
    }

    # ----------------------------------------------------
    # BLOC MATIN → ajouté au MIDI
    # ----------------------------------------------------
    for i in matin_idx:
        if "pas de centre" in str(df.loc[i+1, 0]).lower():
            continue

        cat = detect_category(str(df.loc[i+1,0]))
        ca = clean_amount(df.loc[i+1, 5])

        if cat == "food":
            results["ca_midi_food"] += ca
        elif cat == "drinks":
            results["ca_midi_drinks"] += ca

        # couverts matin → midi
        try:
            results["couverts_midi"] += int(df.loc[i,1])
        except:
            pass


    # ----------------------------------------------------
    # BLOC MIDI
    # ----------------------------------------------------
    for i in midi_idx:

        try:
            results["couverts_midi"] += int(df.loc[i,1])
        except:
            pass

        k = i + 1
        while isinstance(df.loc[k,0], str) and df.loc[k,0] != "":
            if "pas de centre" in str(df.loc[k,0]).lower():
                k += 1
                continue

            cat = detect_category(str(df.loc[k,0]))
            ca = clean_amount(df.loc[k,5])

            if cat == "food":
                results["ca_midi_food"] += ca
            elif cat == "drinks":
                results["ca_midi_drinks"] += ca

            k += 1

    # ----------------------------------------------------
    # BLOC SOIR / NUIT
    # ----------------------------------------------------
    for i in soir_idx:

        try:
            results["couverts_soir"] = int(df.loc[i,1])
        except:
            pass

        k = i + 1
        while isinstance(df.loc[k,0], str) and df.loc[k,0] != "":
            if "pas de centre" in str(df.loc[k,0]).lower():
                k += 1
                continue

            cat = detect_category(str(df.loc[k,0]))
            ca = clean_amount(df.loc[k,5])

            if cat == "food":
                results["ca_soir_food"] += ca
            elif cat == "drinks":
                results["ca_soir_drinks"] += ca

            k += 1

    # ----------------------------------------------------
    # TOTAL JOUR
    # ----------------------------------------------------
    results["total_ca"] = (
        results["ca_midi_food"] +
        results["ca_midi_drinks"] +
        results["ca_soir_food"] +
        results["ca_soir_drinks"]
    )

    return results
