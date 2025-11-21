import pandas as pd

def load_budget(file):
    df = pd.read_excel(file)

    month_col = [c for c in df.columns if "MOIS" in c.upper()][0]
    ca_food   = [c for c in df.columns if "NOURRITURE" in c.upper()][0]
    ca_drink  = [c for c in df.columns if "BOISSON" in c.upper()][0]

    df["CA_TOTAL"] = df[ca_food] + df[ca_drink]

    return df[[month_col, ca_food, ca_drink, "CA_TOTAL"]]
