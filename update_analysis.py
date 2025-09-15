#!/usr/bin/env python3
"""
Script to update the offshore managers analysis with new CVM data
Usage: python3 update_analysis.py [YYYYMM]
Example: python3 update_analysis.py 202509
"""

import sys
import os
from datetime import datetime
import requests
import zipfile

def download_cvm_data(year_month):
    """Download CVM data for the specified year and month"""
    base_url = "https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/"
    
    # CDA data
    cda_url = f"{base_url}cda_fi_{year_month}.zip"
    cda_file = f"cda_fi_{year_month}.zip"
    
    # Fund registry (this doesn't change monthly, but we'll check)
    fund_url = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"
    fund_file = "registro_fundo_classe.zip"
    
    # Manager registry (this doesn't change monthly, but we'll check)
    manager_url = "https://dados.cvm.gov.br/dados/ADM_CART/CAD/DADOS/cad_adm_cart.zip"
    manager_file = "cad_adm_cart.zip"
    
    print(f"Downloading CVM data for {year_month}...")
    
    # Download CDA data
    print(f"Downloading CDA data from {cda_url}")
    response = requests.get(cda_url)
    if response.status_code == 200:
        with open(cda_file, 'wb') as f:
            f.write(response.content)
        print(f"✓ Downloaded {cda_file}")
    else:
        print(f"✗ Failed to download CDA data: {response.status_code}")
        return False
    
    # Download fund registry (if not exists)
    if not os.path.exists(fund_file):
        print(f"Downloading fund registry from {fund_url}")
        response = requests.get(fund_url)
        if response.status_code == 200:
            with open(fund_file, 'wb') as f:
                f.write(response.content)
            print(f"✓ Downloaded {fund_file}")
        else:
            print(f"✗ Failed to download fund registry: {response.status_code}")
    
    # Download manager registry (if not exists)
    if not os.path.exists(manager_file):
        print(f"Downloading manager registry from {manager_url}")
        response = requests.get(manager_url)
        if response.status_code == 200:
            with open(manager_file, 'wb') as f:
                f.write(response.content)
            print(f"✓ Downloaded {manager_file}")
        else:
            print(f"✗ Failed to download manager registry: {response.status_code}")
    
    return True

def extract_data(year_month):
    """Extract the downloaded zip files"""
    print("Extracting data files...")
    
    files_to_extract = [
        f"cda_fi_{year_month}.zip",
        "registro_fundo_classe.zip",
        "cad_adm_cart.zip"
    ]
    
    for zip_file in files_to_extract:
        if os.path.exists(zip_file):
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall()
            print(f"✓ Extracted {zip_file}")
        else:
            print(f"✗ {zip_file} not found")

def run_analysis():
    """Run the analysis script"""
    print("Running offshore managers analysis...")
    os.system("python3 analyze_offshore_managers.py")

def main():
    """Main function"""
    if len(sys.argv) > 1:
        year_month = sys.argv[1]
    else:
        # Default to current month
        year_month = datetime.now().strftime("%Y%m")
    
    print(f"Updating analysis for {year_month}")
    
    # Download data
    if not download_cvm_data(year_month):
        print("Failed to download data. Exiting.")
        return
    
    # Extract data
    extract_data(year_month)
    
    # Run analysis
    run_analysis()
    
    print("\n✓ Analysis completed!")
    print("Check the generated CSV files and markdown report for results.")

if __name__ == "__main__":
    main()
