import pandas as pd

df_x = pd.read_csv("data_pemilik_perusahaan.csv")

new_data = []

while True:
    code = input("Enter KodeEmiten (press Enter to finish): ").strip()
    if code == "":
        break
    company_name = input("Enter NamaEmiten: ").strip()
    owner_name = input("Enter NamaPemilik: ").strip()

    new_data.append({
        "KodeEmiten": code,
        "NamaEmiten": company_name,
        "NamaPemilik": owner_name
    })

if new_data:
    df_y = pd.DataFrame(new_data)
    print("\nNew Data")
    print(df_y)
    df_z = pd.concat([df_x, df_y], ignore_index=True)
    df_z = df_z.sort_values(by="KodeEmiten").reset_index(drop=True)
    df_z.to_csv("data_pemilik_perusahaan_update.csv", index=False)

    print("Data successfully added and saved to data_pemilik_perusahaan_update.csv")
else:
    print("No new data was added.")
