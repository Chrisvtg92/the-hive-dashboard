import pandas as pd
from parser_restotrack_daily import detect_category, clean_amount

def parse_restotrack_month_n1(path):

    df = pd.read_excel(path, header=None)

    total_ca = 0

    for i in range(len(df)):
        try:
            total_ca += clean_amount(df.iloc[i,5])
        except:
            pass

    return {
        "total": total_ca
    }
