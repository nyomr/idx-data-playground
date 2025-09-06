#!/usr/bin/env python3
"""
Structured XBRL File Collector
For directory structure: Year/Company/instance/file.xbrl
"""

import os
import shutil
from pathlib import Path
import json
from typing import List, Dict, Any
import re
from datetime import datetime

class StructuredXBRLCollector:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.xbrl_extensions = ['.xbrl', '.xml']
        
    def scan_structured_directory(self) -> Dict[str, Any]:
        """
        Scan the structured directory (Year/Company/instance/file.xbrl)
        """
        print(f"Scanning structured directory: {self.base_path}")
        
        collected_data = {
            'scan_date': datetime.now().isoformat(),
            'base_path': str(self.base_path),
            'years': {},
            'companies': {},
            'all_files': [],
            'statistics': {
                'total_files': 0,
                'total_companies': 0,
                'total_years': 0,
                'companies_per_year': {},
                'files_per_company': {}
            }
        }
        
        if not self.base_path.exists():
            print(f"Error: Base path does not exist: {self.base_path}")
            return collected_data
        
        # Scan year directories
        for year_dir in self.base_path.iterdir():
            if not year_dir.is_dir():
                continue
                
            year_name = year_dir.name
            print(f"Processing year: {year_name}")
            
            collected_data['years'][year_name] = {
                'companies': {},
                'file_count': 0
            }
            
            # Scan company directories within year
            for company_dir in year_dir.iterdir():
                if not company_dir.is_dir():
                    continue
                    
                company_name = company_dir.name
                print(f"  Processing company: {company_name}")
                
                # Look for instance directory
                instance_dir = company_dir / 'instance'
                if not instance_dir.exists() or not instance_dir.is_dir():
                    print(f"    Warning: No 'instance' directory found in {company_dir}")
                    continue
                
                # Find XBRL files in instance directory
                xbrl_files = self.find_xbrl_files_in_instance(instance_dir)
                
                if xbrl_files:
                    # Initialize company data if not exists
                    if company_name not in collected_data['companies']:
                        collected_data['companies'][company_name] = {}
                    
                    collected_data['companies'][company_name][year_name] = xbrl_files
                    collected_data['years'][year_name]['companies'][company_name] = xbrl_files
                    collected_data['years'][year_name]['file_count'] += len(xbrl_files)
                    
                    # Add to all_files list
                    for file_info in xbrl_files:
                        file_info['year'] = year_name
                        file_info['company'] = company_name
                        collected_data['all_files'].append(file_info)
                    
                    print(f"    Found {len(xbrl_files)} XBRL files")
                else:
                    print(f"    No XBRL files found in {instance_dir}")
        
        # Calculate statistics
        collected_data['statistics']['total_files'] = len(collected_data['all_files'])
        collected_data['statistics']['total_companies'] = len(collected_data['companies'])
        collected_data['statistics']['total_years'] = len(collected_data['years'])
        
        for year, year_data in collected_data['years'].items():
            collected_data['statistics']['companies_per_year'][year] = len(year_data['companies'])
        
        for company, company_data in collected_data['companies'].items():
            collected_data['statistics']['files_per_company'][company] = sum(
                len(files) for files in company_data.values()
            )
        
        return collected_data
    
    def find_xbrl_files_in_instance(self, instance_dir: Path) -> List[Dict[str, Any]]:
        """
        Find all XBRL files in an instance directory
        """
        xbrl_files = []
        
        for file_path in instance_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in self.xbrl_extensions:
                file_info = {
                    'filename': file_path.name,
                    'full_path': str(file_path),
                    'size': file_path.stat().st_size,
                    'modified_date': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    'extension': file_path.suffix.lower()
                }
                xbrl_files.append(file_info)
        
        return xbrl_files
    
    def create_flat_copy(self, collected_data: Dict[str, Any], output_dir: str) -> str:
        """
        Create a flat copy of all XBRL files organized by company-year
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print(f"Creating flat copy in: {output_path}")
        
        copied_files = []
        
        for file_info in collected_data['all_files']:
            company = file_info['company']
            year = file_info['year']
            original_path = Path(file_info['full_path'])
            
            # Create new filename: COMPANY_YEAR_original_filename.xbrl
            new_filename = f"{company}_{year}_{original_path.name}"
            new_path = output_path / new_filename
            
            # Handle duplicates
            counter = 1
            while new_path.exists():
                name_parts = original_path.stem, counter, original_path.suffix
                new_filename = f"{company}_{year}_{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                new_path = output_path / new_filename
                counter += 1
            
            try:
                shutil.copy2(original_path, new_path)
                copied_files.append({
                    'original': str(original_path),
                    'new': str(new_path),
                    'company': company,
                    'year': year
                })
                print(f"Copied: {company} {year} -> {new_filename}")
            except Exception as e:
                print(f"Error copying {original_path}: {e}")
        
        # Save copy log
        copy_log_path = output_path / "copy_log.json"
        with open(copy_log_path, 'w', encoding='utf-8') as f:
            json.dump({
                'copy_date': datetime.now().isoformat(),
                'total_copied': len(copied_files),
                'copied_files': copied_files
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Copied {len(copied_files)} files")
        print(f"Copy log saved to: {copy_log_path}")
        
        return str(output_path)
    
    def create_organized_copy(self, collected_data: Dict[str, Any], output_dir: str) -> str:
        """
        Create organized copy maintaining company/year structure
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print(f"Creating organized copy in: {output_path}")
        
        for company, years_data in collected_data['companies'].items():
            company_dir = output_path / company
            company_dir.mkdir(exist_ok=True)
            
            for year, files in years_data.items():
                year_dir = company_dir / year
                year_dir.mkdir(exist_ok=True)
                
                for file_info in files:
                    original_path = Path(file_info['full_path'])
                    new_path = year_dir / original_path.name
                    
                    # Handle duplicates
                    counter = 1
                    while new_path.exists():
                        name_parts = original_path.stem, counter, original_path.suffix
                        new_filename = f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                        new_path = year_dir / new_filename
                        counter += 1
                    
                    try:
                        shutil.copy2(original_path, new_path)
                        print(f"Copied: {company}/{year}/{new_path.name}")
                    except Exception as e:
                        print(f"Error copying {original_path}: {e}")
        
        return str(output_path)
    
    def generate_report(self, collected_data: Dict[str, Any], output_file: str = "xbrl_scan_report.json"):
        """
        Generate detailed report of the scan
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(collected_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== SCAN REPORT ===")
        print(f"Total XBRL files found: {collected_data['statistics']['total_files']}")
        print(f"Total companies: {collected_data['statistics']['total_companies']}")
        print(f"Total years: {collected_data['statistics']['total_years']}")
        
        print(f"\n=== Files per Year ===")
        for year, year_data in collected_data['years'].items():
            print(f"{year}: {year_data['file_count']} files from {len(year_data['companies'])} companies")
        
        print(f"\n=== Files per Company ===")
        for company, count in collected_data['statistics']['files_per_company'].items():
            years = list(collected_data['companies'][company].keys())
            print(f"{company}: {count} files across years {', '.join(sorted(years))}")
        
        print(f"\nDetailed report saved to: {output_file}")
        
        return collected_data

def main():
    """Main function"""
    # Your specific path
    base_directory = r"D:/Tugas_Akhir/xbrl_to_jason/data_perusahaan"
    
    print("=== Structured XBRL File Collector ===")
    print(f"Scanning: {base_directory}")
    
    collector = StructuredXBRLCollector(base_directory)
    
    # Scan the directory
    scan_results = collector.scan_structured_directory()
    
    if scan_results['statistics']['total_files'] == 0:
        print("No XBRL files found!")
        return
    
    # Generate report
    collector.generate_report(scan_results, "xbrl_scan_report.json")
    
    # Ask user what they want to do
    print(f"\n=== Options ===")
    print("1. Create flat copy (all files in one folder with company-year names)")
    print("2. Create organized copy (maintain company/year folder structure)")
    print("3. Both")
    print("4. Just generate report (done)")
    
    choice = input("Select option (1-4): ").strip()
    
    if choice in ['1', '3']:
        flat_output = "flat_xbrl_files"
        collector.create_flat_copy(scan_results, flat_output)
        print(f"Flat copy created in: {flat_output}")
    
    if choice in ['2', '3']:
        organized_output = "organized_xbrl_files"
        collector.create_organized_copy(scan_results, organized_output)
        print(f"Organized copy created in: {organized_output}")
    
    print(f"\n=== Summary ===")
    print(f"Found {scan_results['statistics']['total_files']} XBRL files")
    print(f"From {scan_results['statistics']['total_companies']} companies")
    print(f"Across {scan_results['statistics']['total_years']} years")
    print("Report saved as: xbrl_scan_report.json")

if __name__ == "__main__":
    main()