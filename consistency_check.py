import os
import pandas as pd

target_year = "2023"

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

# Count for each year
print("2021:", len(set_2021))
print("2022:", len(set_2022))
print("2023:", len(set_2023))
print("2024:", len(set_2024))
print("Consistent:", len(consistent))

sets_by_year = {
    "2021": set_2021,
    "2022": set_2022,
    "2023": set_2023,
    "2024": set_2024,
}

consistent_codes = set(df_consistent["KodeEmiten"])

folders_target = set(os.listdir(target_year))

missing = consistent - sets_by_year[target_year]
missing_folders = consistent_codes - folders_target

print("Expected consistent companies:", len(consistent_codes))
print(f"Actual folders in {target_year}:", len(folders_target))
print(f"Missing in {target_year}: {missing if missing else 0}")
print(f"Missing in {target_year} folder: {missing_folders if missing_folders else 0}")
