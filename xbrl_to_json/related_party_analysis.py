#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Related Party Data Analyzer
Menganalisis hasil ekstraksi related party dari JSON XBRL
"""

import json
import pandas as pd
from pathlib import Path
import re
from typing import Dict, List, Any, Optional

class RelatedPartyAnalyzer:
    def __init__(self):
        # Mapping kategori related party berdasarkan tag name
        self.category_mapping = {
            'receivables': [
                'TradeReceivablesRelatedParties',
                'OtherReceivablesRelatedParties', 
                'ReceivablesFromRelatedParties',
                'CurrentCustomerReceivablesRelatedParties',
                'NonCurrentCustomerReceivablesRelatedParties',
                'RetentionReceivablesRelatedParties',
                'UnbilledReceivablesRelatedParties'
            ],
            'payables': [
                'TradePayablesRelatedParties',
                'OtherPayablesRelatedParties',
                'PayablesToRelatedParties',
                'AccruedLiabilitiesRelatedParties'
            ],
            'revenue': [
                'RevenueFromRelatedParties',
                'SalesRelatedParties',
                'RevenueRelatedParties'
            ],
            'expenses': [
                'PurchasesFromRelatedParties',
                'ExpensesRelatedParties',
                'CostsRelatedParties'
            ],
            'loans': [
                'LoansToRelatedParties',
                'LoansFromRelatedParties',
                'AdvancesToRelatedParties',
                'AdvancesFromRelatedParties'
            ],
            'guarantees': [
                'GuaranteesGivenToRelatedParties',
                'GuaranteesReceivedFromRelatedParties'
            ]
        }
        
    def load_extracted_data(self, json_file_path: str) -> List[Dict]:
        """Load hasil ekstraksi related party"""
        with open(json_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def parse_xbrl_value(self, value_data: Any) -> Dict[str, Any]:
        """Parse nilai XBRL dan extract informasi penting"""
        if isinstance(value_data, list):
            parsed_values = []
            for item in value_data:
                if isinstance(item, dict):
                    parsed_item = {
                        'context': item.get('@contextRef', ''),
                        'unit': item.get('@unitRef', ''),
                        'decimals': item.get('@decimals', ''),
                        'value': item.get('#text', None),
                        'is_nil': item.get('@xsi:nil') == 'true',
                        'id': item.get('@id', '')
                    }
                    
                    # Convert nilai ke numeric jika memungkinkan
                    if parsed_item['value'] and not parsed_item['is_nil']:
                        try:
                            numeric_value = float(parsed_item['value'])
                            # Adjust berdasarkan decimals
                            if parsed_item['decimals']:
                                decimals = int(parsed_item['decimals'])
                                if decimals < 0:
                                    numeric_value = numeric_value * (10 ** abs(decimals))
                            parsed_item['numeric_value'] = numeric_value
                        except ValueError:
                            parsed_item['numeric_value'] = None
                    else:
                        parsed_item['numeric_value'] = None
                    
                    parsed_values.append(parsed_item)
            return parsed_values
        else:
            return [{'raw_value': value_data}]
    
    def categorize_transaction(self, key: str) -> str:
        """Kategorikan jenis transaksi related party"""
        key_clean = key.split(':')[-1] if ':' in key else key
        
        for category, patterns in self.category_mapping.items():
            if any(pattern in key_clean for pattern in patterns):
                return category
        return 'other'
    
    def analyze_extracted_data(self, extracted_data: List[Dict]) -> Dict[str, Any]:
        """Analisis data related party yang telah diekstrak"""
        analysis = {
            'summary': {
                'total_records': len(extracted_data),
                'total_companies': len(set(item['file'].split('_')[0] for item in extracted_data)),
                'total_files': len(set(item['file'] for item in extracted_data))
            },
            'by_company': {},
            'by_category': {},
            'detailed_records': []
        }
        
        for record in extracted_data:
            # Extract company dan tahun dari filename
            file_parts = record['file'].split('_')
            company = file_parts[0] if len(file_parts) > 0 else 'UNKNOWN'
            year = file_parts[1] if len(file_parts) > 1 else 'UNKNOWN'
            
            # Parse nilai XBRL
            parsed_values = self.parse_xbrl_value(record['value'])
            
            # Kategorikan
            category = self.categorize_transaction(record['key'])
            
            # Build detailed record
            detailed_record = {
                'company': company,
                'year': year,
                'file': record['file'],
                'path': record['path'],
                'key': record['key'],
                'category': category,
                'raw_value': record['value'],
                'parsed_values': parsed_values
            }
            
            # Extract current vs prior values
            current_value = None
            prior_value = None
            
            for pv in parsed_values:
                if 'current' in pv.get('context', '').lower():
                    current_value = pv.get('numeric_value')
                elif 'prior' in pv.get('context', '').lower():
                    prior_value = pv.get('numeric_value')
            
            detailed_record['current_year_value'] = current_value
            detailed_record['prior_year_value'] = prior_value
            detailed_record['value_change'] = None
            detailed_record['change_percentage'] = None
            
            if current_value is not None and prior_value is not None:
                detailed_record['value_change'] = current_value - prior_value
                if prior_value != 0:
                    detailed_record['change_percentage'] = (detailed_record['value_change'] / prior_value) * 100
            
            analysis['detailed_records'].append(detailed_record)
            
            # Aggregate by company
            if company not in analysis['by_company']:
                analysis['by_company'][company] = {
                    'total_records': 0,
                    'categories': {},
                    'years': set()
                }
            
            analysis['by_company'][company]['total_records'] += 1
            analysis['by_company'][company]['years'].add(year)
            
            if category not in analysis['by_company'][company]['categories']:
                analysis['by_company'][company]['categories'][category] = 0
            analysis['by_company'][company]['categories'][category] += 1
            
            # Aggregate by category
            if category not in analysis['by_category']:
                analysis['by_category'][category] = {
                    'total_records': 0,
                    'companies': set()
                }
            
            analysis['by_category'][category]['total_records'] += 1
            analysis['by_category'][category]['companies'].add(company)
        
        # Convert sets to lists for JSON serialization
        for company_data in analysis['by_company'].values():
            company_data['years'] = list(company_data['years'])
        
        for category_data in analysis['by_category'].values():
            category_data['companies'] = list(category_data['companies'])
        
        return analysis
    
    def create_summary_report(self, analysis: Dict[str, Any]) -> str:
        """Buat laporan ringkasan"""
        report = []
        report.append("=== RELATED PARTY TRANSACTION ANALYSIS ===")
        report.append(f"Total Records: {analysis['summary']['total_records']}")
        report.append(f"Total Companies: {analysis['summary']['total_companies']}")
        report.append(f"Total Files: {analysis['summary']['total_files']}")
        
        report.append("\n=== BY CATEGORY ===")
        for category, data in analysis['by_category'].items():
            report.append(f"{category.upper()}: {data['total_records']} records from {len(data['companies'])} companies")
        
        report.append("\n=== BY COMPANY ===")
        for company, data in analysis['by_company'].items():
            years_str = ', '.join(sorted(data['years']))
            report.append(f"{company}: {data['total_records']} records across years {years_str}")
            
            # Show categories for this company
            for cat, count in data['categories'].items():
                report.append(f"  - {cat}: {count} records")
        
        report.append("\n=== TOP TRANSACTIONS BY VALUE ===")
        # Sort by current year value
        valued_records = [r for r in analysis['detailed_records'] if r['current_year_value'] is not None]
        top_records = sorted(valued_records, key=lambda x: x['current_year_value'], reverse=True)[:10]
        
        for i, record in enumerate(top_records, 1):
            value_str = f"Rp {record['current_year_value']:,.0f}" if record['current_year_value'] else "N/A"
            report.append(f"{i:2d}. {record['company']} {record['year']} - {record['category']}: {value_str}")
        
        return '\n'.join(report)
    
    def export_to_excel(self, analysis: Dict[str, Any], output_file: str):
        """Export analisis ke Excel dengan multiple sheets"""
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            # Summary sheet
            summary_data = []
            for company, data in analysis['by_company'].items():
                for category, count in data['categories'].items():
                    summary_data.append({
                        'company': company,
                        'category': category,
                        'record_count': count,
                        'years': ', '.join(sorted(data['years']))
                    })
            
            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
            
            # Detailed records sheet
            df_detailed = pd.DataFrame(analysis['detailed_records'])
            # Select important columns
            columns_to_export = [
                'company', 'year', 'category', 'key', 
                'current_year_value', 'prior_year_value', 
                'value_change', 'change_percentage'
            ]
            df_export = df_detailed[columns_to_export]
            df_export.to_excel(writer, sheet_name='Detailed_Records', index=False)
            
            # Category analysis
            category_analysis = []
            for category, data in analysis['by_category'].items():
                category_analysis.append({
                    'category': category,
                    'total_records': data['total_records'],
                    'companies_count': len(data['companies']),
                    'companies': ', '.join(data['companies'])
                })
            
            df_categories = pd.DataFrame(category_analysis)
            df_categories.to_excel(writer, sheet_name='Category_Analysis', index=False)

def main():
    """Main function"""
    # Path file hasil ekstraksi
    input_json = Path(r"D:\Tugas_Akhir\xbrl_to_jason\related_party_from_json.json")
    
    analyzer = RelatedPartyAnalyzer()
    
    print("Loading extracted related party data...")
    extracted_data = analyzer.load_extracted_data(str(input_json))
    
    print("Analyzing data...")
    analysis = analyzer.analyze_extracted_data(extracted_data)
    
    # Generate report
    report = analyzer.create_summary_report(analysis)
    print(report)
    
    # Save results
    output_dir = Path(r"D:\Tugas_Akhir\xbrl_to_jason")
    
    # Save detailed analysis as JSON
    analysis_json = output_dir / "related_party_analysis.json"
    with open(analysis_json, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    
    # Save report as text
    report_txt = output_dir / "related_party_report.txt"
    with open(report_txt, 'w', encoding='utf-8') as f:
        f.write(report)
    
    # Export to Excel
    excel_file = output_dir / "related_party_analysis.xlsx"
    analyzer.export_to_excel(analysis, str(excel_file))
    
    print(f"\n=== OUTPUT FILES ===")
    print(f"Analysis JSON: {analysis_json}")
    print(f"Report TXT: {report_txt}")
    print(f"Excel Analysis: {excel_file}")

if __name__ == "__main__":
    main()