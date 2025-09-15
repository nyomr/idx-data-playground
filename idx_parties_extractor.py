import json
import os

base_folder = "data_perusahaan_json/json"
current_year = 2024
prior_year = current_year - 1
year_folder = os.path.join(base_folder, str(current_year))
output_file = f"pihak_berelasi_{current_year}.json"

# Set target fields
target_fields = [
    "idx-cor:PartyName",
    "idx-cor:CounterpartyName",
    "idx-cor:CounterpartyNameTradePayable"
]

results = []


def normalize_name(name: str) -> str:
    lower_name = name.lower().strip()

    if lower_name.startswith("lain-lain") or lower_name.startswith("lainnya"):
        return "Lain-lain"

    return name.strip()


def extract_entities(items, label, kodeEmiten):
    for item in items:
        context_ref = item.get("@contextRef", "")
        name = item.get("#text", "").strip()
        entity_id = item.get("@id", "")

        # Skip empty name
        if not name:
            continue

        # Normalize "Lain-lain" / "Lainnya"
        name = normalize_name(name)

        year = None
        if context_ref.startswith("CurrentYearDuration"):
            year = current_year
        elif context_ref.startswith("PriorEndYearDuration") or context_ref.startswith("PriorYearDuration"):
            year = prior_year

        results.append({
            "kodeEmiten": kodeEmiten,
            "field": label,
            "year": year,
            "contextRef": context_ref,
            "id": entity_id,
            "name": name
        })


# Loop each file
for fname in os.listdir(year_folder):
    if not fname.endswith("_instance.json"):
        continue

    filepath = os.path.join(year_folder, fname)
    kodeEmiten = fname.split("_")[0]

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Check namespace
        namespaces = [v for k, v in data.get(
            "xbrl", {}).items() if k.startswith("@xmlns")]
        if "http://www.idx.co.id/xbrl/taxonomy/2020-01-01/cor" not in namespaces:
            print(f"Namespace 'idx-cor' not found in {fname}, skipped.")
            continue

        xbrl = data.get("xbrl", {})

        # Extract each target field
        for field in target_fields:
            items = xbrl.get(field, [])
            if isinstance(items, dict):
                items = [items]
            if isinstance(items, list):
                extract_entities(items, field, kodeEmiten)

    except Exception as e:
        print(f"Failed to process {fname}: {e}")


# Save to json
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Result with {len(results)} entities saved to {output_file}")
