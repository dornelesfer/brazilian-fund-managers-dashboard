#!/usr/bin/env python3
"""
Analysis of Brazilian fund managers with the most offshore assets
Based on CVM datasets: CDA (Bloco 7), Fund Registry, and Manager Registry
"""

import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

def load_and_clean_data():
    """Load and clean the three main datasets"""
    print("Loading CVM datasets...")
    
    # Load CDA Bloco 7 (Offshore positions)
    print("Loading CDA Bloco 7 (offshore positions)...")
    cda_df = pd.read_csv('cda_fi_BLC_7_202508.csv', sep=';', encoding='latin-1')
    print(f"CDA Bloco 7: {len(cda_df)} records loaded")
    
    # Load Fund Registry
    print("Loading Fund Registry...")
    fund_df = pd.read_csv('registro_fundo.csv', sep=';', encoding='latin-1')
    print(f"Fund Registry: {len(fund_df)} records loaded")
    
    # Load Manager Registry (PJ - Legal entities)
    print("Loading Manager Registry...")
    manager_df = pd.read_csv('cad_adm_cart_pj.csv', sep=';', encoding='latin-1')
    print(f"Manager Registry: {len(manager_df)} records loaded")
    
    return cda_df, fund_df, manager_df

def analyze_offshore_positions(cda_df):
    """Analyze offshore positions from CDA Bloco 7"""
    print("\nAnalyzing offshore positions...")
    
    # Filter for offshore investments
    offshore_df = cda_df[cda_df['TP_APLIC'] == 'Investimento no Exterior'].copy()
    print(f"Offshore investment records: {len(offshore_df)}")
    
    # Convert value columns to numeric
    value_cols = ['VL_MERC_POS_FINAL', 'VL_CUSTO_POS_FINAL', 'VL_VENDA_NEGOC', 'VL_AQUIS_NEGOC']
    for col in value_cols:
        if col in offshore_df.columns:
            offshore_df[col] = pd.to_numeric(offshore_df[col], errors='coerce')
    
    # Group by fund CNPJ to get total offshore assets per fund
    fund_offshore = offshore_df.groupby('CNPJ_FUNDO_CLASSE').agg({
        'VL_MERC_POS_FINAL': 'sum',
        'VL_CUSTO_POS_FINAL': 'sum',
        'DENOM_SOCIAL': 'first',
        'DT_COMPTC': 'first'
    }).reset_index()
    
    # Filter out zero values and sort by market value
    fund_offshore = fund_offshore[fund_offshore['VL_MERC_POS_FINAL'] > 0]
    fund_offshore = fund_offshore.sort_values('VL_MERC_POS_FINAL', ascending=False)
    
    print(f"Funds with offshore positions: {len(fund_offshore)}")
    print(f"Total offshore assets value: R$ {fund_offshore['VL_MERC_POS_FINAL'].sum():,.2f}")
    
    return fund_offshore

def cross_reference_with_funds(fund_offshore, fund_df):
    """Cross-reference offshore positions with fund registry to get managers"""
    print("\nCross-referencing with fund registry...")
    
    # Clean CNPJ columns for matching - convert to string first
    fund_offshore['CNPJ_FUNDO_CLASSE_clean'] = fund_offshore['CNPJ_FUNDO_CLASSE'].astype(str).str.replace('[^0-9]', '', regex=True)
    fund_df['CNPJ_Fundo_clean'] = fund_df['CNPJ_Fundo'].astype(str).str.replace('[^0-9]', '', regex=True)
    
    # Convert to numeric for matching
    fund_offshore['CNPJ_FUNDO_CLASSE_clean'] = pd.to_numeric(fund_offshore['CNPJ_FUNDO_CLASSE_clean'], errors='coerce')
    fund_df['CNPJ_Fundo_clean'] = pd.to_numeric(fund_df['CNPJ_Fundo_clean'], errors='coerce')
    
    # Merge with fund registry
    merged_df = fund_offshore.merge(
        fund_df[['CNPJ_Fundo_clean', 'CNPJ_Administrador', 'Administrador', 'CPF_CNPJ_Gestor', 'Gestor']], 
        left_on='CNPJ_FUNDO_CLASSE_clean', 
        right_on='CNPJ_Fundo_clean', 
        how='left'
    )
    
    print(f"Successfully matched {merged_df['CNPJ_Administrador'].notna().sum()} funds with administrators")
    print(f"Successfully matched {merged_df['CPF_CNPJ_Gestor'].notna().sum()} funds with managers")
    
    return merged_df

def cross_reference_with_managers(merged_df, manager_df):
    """Cross-reference with manager registry to get manager locations"""
    print("\nCross-referencing with manager registry...")
    
    # Clean CNPJ columns for matching - convert to string first
    merged_df['CNPJ_Administrador_clean'] = merged_df['CNPJ_Administrador'].astype(str).str.replace('[^0-9]', '', regex=True)
    manager_df['CNPJ_clean'] = manager_df['CNPJ'].astype(str).str.replace('[^0-9]', '', regex=True)
    
    # Convert to numeric for matching
    merged_df['CNPJ_Administrador_clean'] = pd.to_numeric(merged_df['CNPJ_Administrador_clean'], errors='coerce')
    manager_df['CNPJ_clean'] = pd.to_numeric(manager_df['CNPJ_clean'], errors='coerce')
    
    # Debug: Check sample values
    print(f"Sample administrator CNPJs: {merged_df['CNPJ_Administrador_clean'].dropna().head()}")
    print(f"Sample manager CNPJs: {manager_df['CNPJ_clean'].dropna().head()}")
    print(f"Manager registry columns: {manager_df.columns.tolist()}")
    
    # Merge with manager registry
    final_df = merged_df.merge(
        manager_df[['CNPJ_clean', 'DENOM_SOCIAL', 'MUN', 'UF', 'LOGRADOURO', 'BAIRRO', 'CEP']], 
        left_on='CNPJ_Administrador_clean', 
        right_on='CNPJ_clean', 
        how='left'
    )
    
    print(f"Final dataframe columns: {final_df.columns.tolist()}")
    print(f"Merge result shape: {final_df.shape}")
    
    # Check if the merge was successful and rename columns
    if 'DENOM_SOCIAL_y' in final_df.columns:
        # Rename the merged columns to avoid conflicts
        final_df = final_df.rename(columns={
            'DENOM_SOCIAL_y': 'DENOM_SOCIAL',
            'DENOM_SOCIAL_x': 'FUNDO_DENOM_SOCIAL'
        })
        print(f"Successfully matched {final_df['DENOM_SOCIAL'].notna().sum()} administrators with location data")
    else:
        print("Warning: Could not merge with manager registry - proceeding without location data")
        # Add empty columns if merge failed
        final_df['DENOM_SOCIAL'] = None
        final_df['MUN'] = None
        final_df['UF'] = None
        final_df['LOGRADOURO'] = None
        final_df['BAIRRO'] = None
        final_df['CEP'] = None
    
    return final_df

def analyze_managers_by_offshore_assets(final_df):
    """Analyze managers by total offshore assets under management"""
    print("\nAnalyzing managers by offshore assets...")
    
    # Filter out records without administrators
    valid_df = final_df[final_df['CNPJ_Administrador'].notna() & (final_df['CNPJ_Administrador'] != 0)]
    print(f"Records with valid administrators: {len(valid_df)}")
    
    if len(valid_df) == 0:
        print("No valid administrator data found!")
        return pd.DataFrame()
    
    # Group by administrator to get total offshore assets per manager
    # First group without location data to ensure we get all managers
    manager_offshore = valid_df.groupby(['CNPJ_Administrador', 'Administrador']).agg({
        'VL_MERC_POS_FINAL': 'sum',
        'VL_CUSTO_POS_FINAL': 'sum',
        'CNPJ_FUNDO_CLASSE': 'count'  # Number of funds
    }).reset_index()
    
    # Add location data if available
    if 'DENOM_SOCIAL' in valid_df.columns and 'MUN' in valid_df.columns and 'UF' in valid_df.columns:
        # Get location data for each administrator
        location_data = valid_df.groupby(['CNPJ_Administrador']).agg({
            'DENOM_SOCIAL': 'first',
            'MUN': 'first', 
            'UF': 'first'
        }).reset_index()
        
        # Merge location data
        manager_offshore = manager_offshore.merge(location_data, on='CNPJ_Administrador', how='left')
    else:
        # Add empty location columns
        manager_offshore['DENOM_SOCIAL'] = None
        manager_offshore['MUN'] = None
        manager_offshore['UF'] = None
    
    # Rename columns for clarity
    manager_offshore = manager_offshore.rename(columns={
        'VL_MERC_POS_FINAL': 'Total_Offshore_Assets_Market_Value',
        'VL_CUSTO_POS_FINAL': 'Total_Offshore_Assets_Cost_Value',
        'CNPJ_FUNDO_CLASSE': 'Number_of_Funds',
        'MUN': 'Cidade'
    })
    
    # Sort by market value
    manager_offshore = manager_offshore.sort_values('Total_Offshore_Assets_Market_Value', ascending=False)
    
    # Calculate percentage of total
    total_offshore = manager_offshore['Total_Offshore_Assets_Market_Value'].sum()
    manager_offshore['Percentage_of_Total'] = (manager_offshore['Total_Offshore_Assets_Market_Value'] / total_offshore * 100).round(2)
    
    return manager_offshore

def generate_report(manager_offshore, top_n=20):
    """Generate a comprehensive report"""
    print(f"\n{'='*80}")
    print(f"TOP {top_n} BRAZILIAN FUND MANAGERS BY OFFSHORE ASSETS")
    print(f"{'='*80}")
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Offshore Assets Analyzed: R$ {manager_offshore['Total_Offshore_Assets_Market_Value'].sum():,.2f}")
    print(f"Number of Managers with Offshore Assets: {len(manager_offshore)}")
    print(f"{'='*80}\n")
    
    # Top managers table
    top_managers = manager_offshore.head(top_n)
    
    print(f"TOP {top_n} MANAGERS:")
    print("-" * 80)
    print(f"{'Rank':<4} {'Manager':<30} {'Location':<20} {'Assets (R$)':<15} {'%':<6} {'Funds':<6}")
    print("-" * 80)
    
    for i, (_, row) in enumerate(top_managers.iterrows(), 1):
        location = f"{row['Cidade']}, {row['UF']}" if pd.notna(row['Cidade']) else "N/A"
        assets = f"R$ {row['Total_Offshore_Assets_Market_Value']:,.0f}"
        percentage = f"{row['Percentage_of_Total']:.1f}%"
        funds = f"{row['Number_of_Funds']:.0f}"
        
        print(f"{i:<4} {row['Administrador'][:29]:<30} {location[:19]:<20} {assets:<15} {percentage:<6} {funds:<6}")
    
    print("-" * 80)
    
    # Summary statistics
    print(f"\nSUMMARY STATISTICS:")
    print(f"Total Offshore Assets: R$ {manager_offshore['Total_Offshore_Assets_Market_Value'].sum():,.2f}")
    print(f"Average Assets per Manager: R$ {manager_offshore['Total_Offshore_Assets_Market_Value'].mean():,.2f}")
    print(f"Median Assets per Manager: R$ {manager_offshore['Total_Offshore_Assets_Market_Value'].median():,.2f}")
    print(f"Top 10 Managers Control: {manager_offshore.head(10)['Percentage_of_Total'].sum():.1f}% of total offshore assets")
    
    # Geographic distribution
    print(f"\nGEOGRAPHIC DISTRIBUTION (Top 20):")
    geo_dist = top_managers.groupby('UF')['Total_Offshore_Assets_Market_Value'].sum().sort_values(ascending=False)
    for state, assets in geo_dist.items():
        if pd.notna(state):
            percentage = (assets / total_offshore * 100)
            print(f"{state}: R$ {assets:,.0f} ({percentage:.1f}%)")
    
    return top_managers

def save_results(manager_offshore, top_managers):
    """Save results to CSV files"""
    print(f"\nSaving results...")
    
    # Save full results
    manager_offshore.to_csv('offshore_managers_analysis.csv', index=False, encoding='utf-8-sig')
    print("Full analysis saved to: offshore_managers_analysis.csv")
    
    # Save top 50 for easier viewing
    top_managers.head(50).to_csv('top_50_offshore_managers.csv', index=False, encoding='utf-8-sig')
    print("Top 50 managers saved to: top_50_offshore_managers.csv")

def main():
    """Main analysis function"""
    print("BRAZILIAN FUND MANAGERS - OFFSHORE ASSETS ANALYSIS")
    print("=" * 60)
    
    try:
        # Load data
        cda_df, fund_df, manager_df = load_and_clean_data()
        
        # Analyze offshore positions
        fund_offshore = analyze_offshore_positions(cda_df)
        
        # Cross-reference with fund registry
        merged_df = cross_reference_with_funds(fund_offshore, fund_df)
        
        # Cross-reference with manager registry
        final_df = cross_reference_with_managers(merged_df, manager_df)
        
        # Analyze managers by offshore assets
        manager_offshore = analyze_managers_by_offshore_assets(final_df)
        
        # Generate report
        top_managers = generate_report(manager_offshore, top_n=20)
        
        # Save results
        save_results(manager_offshore, top_managers)
        
        print(f"\nAnalysis completed successfully!")
        print(f"Check the generated CSV files for detailed results.")
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
