import pandas as pd
import os

HISTORIQUE_PATH = "historique.csv"

def save_daily_to_history(parsed_day):
    """
    Enregistre les données du jour dans historique.csv
    parsed_day = dict retourné par parse_daily_report()
    """

    # Extraire la date depuis le dataframe détail
    df_details = parsed_day["details"]
    raw_date = df_details.iloc[0, 0]  # la date est dans la première colonne
    date = pd.to_datetime(raw_date, errors="coerce")

    row = {
        "Date": date,
        "CA_total_TTC": parsed_day["total_ca"],
        "Couverts_total": parsed_day["total_couverts"],

        "CA_midi_food": parsed_day["midi_nourriture"],
        "CA_midi_drink": parsed_day["midi_boissons"],
        "CA_soir_food": parsed_day["soir_nourriture"],
        "CA_soir_drink": parsed_day["soir_boissons"],

        "CA_matin_food": parsed_day["matin_nourriture"],
        "CA_matin_drink": parsed_day["matin_boissons"],
    }

    new_df = pd.DataFrame([row])

    # Si le fichier existe → append
    if os.path.exists(HISTORIQUE_PATH):
        old = pd.read_csv(HISTORIQUE_PATH)
        combined = pd.concat([old, new_df], ignore_index=True)
    else:
        combined = new_df

    # Sauvegarde
    combined.to_csv(HISTORIQUE_PATH, index=False)


def load_history():
    """Charge le fichier historique s’il existe."""
    if os.path.exists(HISTORIQUE_PATH):
        return pd.read_csv(HISTORIQUE_PATH)
    return pd.DataFrame()
