#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# XBRL to JSON & normalized facts CSV
# Input default:  xbrl_missing_data_flat
# Output default: <parent_of_input>/xbrl_missingdata_out/{json,csv}

import argparse, os, json
from pathlib import Path

from lxml import etree
import xmltodict
import pandas as pd

# ---------- args ----------
def parse_args():
    p = argparse.ArgumentParser(description="Convert XBRL/XML to per-file JSON + facts CSV + ALL_facts.csv.")
    p.add_argument('input_path', nargs='?', default='xbrl_missing_data_flat',
                   help="File .xbrl/.xml atau folder berisi file-file tersebut (default: xbrl_missing_data_flat)")
    p.add_argument('--out', default=None,
                   help="Folder output. Jika tidak diisi, akan dibuat di <parent_of_input>/xbrl_missingdata_out")
    return p.parse_args()

# ---------- helpers ----------
def xpath_one(node, xp):
    res = node.xpath(xp)
    return res[0] if res else None

def text_of(node):
    return (node.text or '').strip() if node is not None else None

def load_xml_tree(path):
    parser = etree.XMLParser(remove_comments=True, recover=True, huge_tree=True)
    with open(path, 'rb') as f:
        return etree.parse(f, parser)

def xml_to_json_file(xml_path, out_json_path):
    with open(xml_path, 'rb') as f:
        data = xmltodict.parse(f, process_namespaces=False)
    with open(out_json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ---------- extractors ----------
def build_contexts(tree):
    contexts = {}
    for ctx in tree.xpath('//*[local-name()="context"]'):
        ctx_id = ctx.get('id')
        if not ctx_id:
            continue

        period = xpath_one(ctx, './/*[local-name()="period"]')
        period_type = start = end = instant = None
        if period is not None:
            if xpath_one(period, './/*[local-name()="startDate"]'):
                period_type = 'duration'
                start = text_of(xpath_one(period, './/*[local-name()="startDate"]'))
                end   = text_of(xpath_one(period,  './/*[local-name()="endDate"]'))
            elif xpath_one(period, './/*[local-name()="instant"]'):
                period_type = 'instant'
                instant = text_of(xpath_one(period, './/*[local-name()="instant"]'))

        entity = xpath_one(ctx, './/*[local-name()="entity"]')
        entity_identifier = None
        if entity is not None:
            entity_identifier = text_of(xpath_one(entity, './/*[local-name()="identifier"]'))

        contexts[ctx_id] = {
            'period_type': period_type,
            'start': start, 'end': end, 'instant': instant,
            'entity_identifier': entity_identifier,
        }
    return contexts

def build_units(tree):
    units = {}
    for u in tree.xpath('//*[local-name()="unit"]'):
        uid = u.get('id')
        if not uid:
            continue
        measure = xpath_one(u, './/*[local-name()="measure"]')
        units[uid] = text_of(measure) if measure is not None else None
    return units

def infer_company_info(tree):
    code_tags = ['TradingSymbol','EntityCommonStockTicker','SecuritySymbol','TickerSymbol','EntityCode','EntityShortName']
    name_tags = ['EntityRegistrantName','EntityReportingAddressName','CompanyName','EntityLegalName','EntityCommonName','NameOfReportingEntity']

    def find_first(tags):
        xp = " | ".join([f'//*[local-name()="{t}"]' for t in tags])
        nodes = tree.xpath(xp) if xp else []
        for n in nodes:
            t = (n.text or '').strip()
            if t: return t
        return None

    code = find_first(code_tags)
    name = find_first(name_tags)

    if not code:
        for n in tree.xpath('//*[contains(local-name(),"Symbol")]'):
            t = (n.text or '').strip()
            if t:
                code = t; break

    if not name:
        ident = tree.xpath('//*[local-name()="context"]//*[local-name()="identifier"]')
        if ident:
            name = (ident[0].text or '').strip()

    return code, name

def enumerate_facts(tree):
    contexts = build_contexts(tree)
    units = build_units(tree)
    rows = []

    for el in tree.getroot().iter():
        qn = etree.QName(el.tag)
        if qn is None or qn.localname is None:
            continue
        ln = qn.localname
        ns = qn.namespace or ''

        # skip infra nodes
        if ln in {'schemaRef','context','unit','linkbaseRef','roleRef','arcroleRef'}:
            continue

        has_text = (el.text or '').strip() != ''
        has_attr = any(a in el.attrib for a in ['contextRef','unitRef','decimals','precision','scale'])
        if not (has_text or has_attr):
            continue

        ctx_id = el.get('contextRef')
        unit_id = el.get('unitRef')

        ctx = contexts.get(ctx_id, {}) if ctx_id else {}
        unit = units.get(unit_id) if unit_id else None

        rows.append({
            'concept_qname': f"{{{ns}}}{ln}" if ns else ln,
            'local_name': ln,
            'value': (el.text or '').strip(),
            'unit': unit,
            'decimals': el.get('decimals') or el.get('precision'),
            'period_type': ctx.get('period_type'),
            'period_start': ctx.get('start'),
            'period_end': ctx.get('end'),
            'instant': ctx.get('instant'),
            'context_ref': ctx_id,
            'entity_identifier': ctx.get('entity_identifier'),
        })
    return rows

# ---------- main ----------
def main():
    args = parse_args()
    in_path = Path(args.input_path).resolve()

    # output dir default → <parent_of_input>/xbrl_missingdata_out
    if args.out:
        out_dir = Path(args.out).resolve()
    else:
        base_parent = in_path if in_path.is_dir() else in_path.parent
        out_dir = (base_parent.parent / 'xbrl_missingdata_out').resolve() if in_path.name == 'xbrl_missing_data_flat' else (base_parent / 'xbrl_missingdata_out').resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # subfolder json & csv
    json_dir = (out_dir / 'json'); json_dir.mkdir(parents=True, exist_ok=True)
    csv_dir  = (out_dir / 'csv');  csv_dir.mkdir(parents=True, exist_ok=True)

    # kumpulkan file
    if in_path.is_dir():
        files = [str(p) for p in in_path.rglob('*.xbrl')] + [str(p) for p in in_path.rglob('*.xml')]
    else:
        files = [str(in_path)]

    print("=== XBRL → JSON & CSV ===")
    print(f"Input : {in_path}")
    print(f"Output: {out_dir} (json → {json_dir.name}/, csv → {csv_dir.name}/)")
    if not files:
        print("Tidak menemukan file .xbrl/.xml pada path ini.")
        return

    all_rows = []
    for fp in files:
        try:
            tree = load_xml_tree(fp)
            base = Path(fp).stem

            # JSON per file → ./json
            xml_to_json_file(fp, json_dir / f"{base}.json")

            # Enumerasi fakta per file → ./csv
            rows = enumerate_facts(tree)
            code, name = infer_company_info(tree)
            for r in rows:
                r['file'] = os.path.basename(fp)
                r['emiten_code'] = code
                r['emiten_name'] = name

            pd.DataFrame(rows).to_csv(csv_dir / f"{base}_facts.csv", index=False, encoding='utf-8')
            all_rows.extend(rows)
            print(f"[OK] {fp}")
        except Exception as e:
            print(f"[ERROR] {fp}: {e}")

    # Gabungan semua fakta → ./csv/ALL_facts.csv
    if all_rows:
        pd.DataFrame(all_rows).to_csv(csv_dir / "ALL_facts.csv", index=False, encoding='utf-8')
        print(f"[DONE] ALL_facts.csv -> {csv_dir}")
    else:
        print("No facts extracted.")

if __name__ == "__main__":
    main()
