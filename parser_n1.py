import pandas as pd
from parser_restotrack_daily import clean_amount, detect_category

def parse_n1_month(file):
    df = pd.read_excel(file)

    # Normalisation colonnes
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Recherche colonne date
    date_col = [c for c in df.columns if "date" in c][0]

    results = []

    for _, row in df.iterrows():
        date = pd.to_datetime(row[date_col], errors="coerce")
        if pd.isna(date):
            continue

        # Catégorisation automatique
        category = detect_category(str(row.get("centre", "")))

        montant = clean_amount(row.get("ca ttc", 0))

        results.append({
            "Date": date,
            "Category": category,
            "CA_TTC": montant
        })

    df_out = pd.DataFrame(results)
    df_pivot = df_out.pivot_table(
        index="Date",
        columns="Category",
        values="CA_TTC",
        aggfunc="sum"
    ).fillna(0)

    df_pivot["CA_total_TTC"] = df_pivot.sum(axis=1)

    return df_pivot.reset_index()
