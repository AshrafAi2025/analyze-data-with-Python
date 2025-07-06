import pandas as pd
df = pd.read_csv("jobs.csv")

# تنظيف أعمدة التاريخ والراتب
df["salary_clean"] = (
    df["salary"].str.extract(r"(\d[\d,]*)")
                .replace(",", "", regex=True)
                .astype(float)
)

# إحصائيات وصفية
print(df["location"].value_counts().head())
print(df["salary_clean"].describe())