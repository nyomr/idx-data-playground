import os
import shutil
import pandas as pd

years = ["2021", "2022", "2023", "2024"]

# Load file
df_2021 = pd.read_csv("data_perusahaan_2021.csv")
df_2022 = pd.read_csv("data_perusahaan_2022.csv")
df_2023 = pd.read_csv("data_perusahaan_2023.csv")
df_2024 = pd.read_csv("data_perusahaan_2024.csv")

set_2021 = set(df_2021["KodeEmiten"])
set_2022 = set(df_2022["KodeEmiten"])
set_2023 = set(df_2023["KodeEmiten"])
set_2024 = set(df_2024["KodeEmiten"])

# Find consistent companies
consistent = set_2021 & set_2022 & set_2023 & set_2024

df_consistent = pd.DataFrame({"KodeEmiten": sorted(consistent)})
df_consistent = df_consistent.merge(
    df_2024[["KodeEmiten", "NamaEmiten"]].drop_duplicates(),
    on="KodeEmiten",
    how="left"
)

# Save to CSV
df_consistent.to_csv("data_perusahaan_bersih.csv",
                     index=False, encoding="utf-8-sig")

# Remove inconsistent company folders
for year in years:
    if not os.path.exists(year):
        continue
    for company_code in os.listdir(year):
        folder_path = os.path.join(year, company_code)
        if os.path.isdir(folder_path):
            if company_code not in consistent:
                print(f"Removing {folder_path} ...")
                shutil.rmtree(folder_path)

print("Cleanup completed. Inconsistent folders have been removed.")
print("Number of consistent companies:", len(df_consistent))
