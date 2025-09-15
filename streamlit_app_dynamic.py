#!/usr/bin/env python3
"""
Streamlit App for Brazilian Fund Managers Offshore Assets Analysis
Dynamic data loading with month/year selection
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os
import requests
import zipfile
import io

# Page configuration
st.set_page_config(
    page_title="Brazilian Fund Managers - Offshore Assets",
    page_icon="🇧🇷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def download_cvm_data(year_month):
    """Download CVM data for the specified year and month"""
    base_url = "https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/"
    
    # CDA data
    cda_url = f"{base_url}cda_fi_{year_month}.zip"
    
    try:
        response = requests.get(cda_url, timeout=30)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Failed to download CDA data for {year_month}: HTTP {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error downloading data for {year_month}: {str(e)}")
        return None

@st.cache_data
def download_static_data():
    """Download static data (fund registry and manager registry) from CVM"""
    try:
        # Fund Registry URL
        fund_url = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip"
        
        # Manager Registry URL (PJ - Legal entities)
        manager_url = "https://dados.cvm.gov.br/dados/ADM_CART/CAD/DADOS/cad_adm_cart.zip"
        
        # Download Fund Registry
        st.sidebar.write("📥 Downloading Fund Registry...")
        fund_response = requests.get(fund_url, timeout=60)
        if fund_response.status_code != 200:
            st.error(f"Failed to download Fund Registry: HTTP {fund_response.status_code}")
            return None, None
        
        # Extract Fund Registry
        with zipfile.ZipFile(io.BytesIO(fund_response.content)) as zip_file:
            fund_files = [f for f in zip_file.namelist() if f.endswith('.csv')]
            if not fund_files:
                st.error("No CSV files found in Fund Registry zip")
                return None, None
            
            with zip_file.open(fund_files[0]) as f:
                try:
                    fund_df = pd.read_csv(f, sep=';', encoding='latin-1', low_memory=False, on_bad_lines='skip')
                except Exception as e:
                    st.error(f"Error parsing Fund Registry CSV: {str(e)}")
                    # Try with different encoding
                    f.seek(0)
                    try:
                        fund_df = pd.read_csv(f, sep=';', encoding='utf-8', low_memory=False, on_bad_lines='skip')
                    except Exception as e2:
                        st.error(f"Error parsing Fund Registry with UTF-8: {str(e2)}")
                        return None, None
        
        # Download Manager Registry
        st.sidebar.write("📥 Downloading Manager Registry...")
        manager_response = requests.get(manager_url, timeout=60)
        if manager_response.status_code != 200:
            st.error(f"Failed to download Manager Registry: HTTP {manager_response.status_code}")
            return None, None
        
        # Extract Manager Registry
        with zipfile.ZipFile(io.BytesIO(manager_response.content)) as zip_file:
            manager_files = [f for f in zip_file.namelist() if f.endswith('.csv') and 'pj' in f.lower()]
            if not manager_files:
                st.error("No PJ CSV files found in Manager Registry zip")
                return None, None
            
            with zip_file.open(manager_files[0]) as f:
                try:
                    manager_df = pd.read_csv(f, sep=';', encoding='latin-1', low_memory=False, on_bad_lines='skip')
                except Exception as e:
                    st.error(f"Error parsing Manager Registry CSV: {str(e)}")
                    # Try with different encoding
                    f.seek(0)
                    try:
                        manager_df = pd.read_csv(f, sep=';', encoding='utf-8', low_memory=False, on_bad_lines='skip')
                    except Exception as e2:
                        st.error(f"Error parsing Manager Registry with UTF-8: {str(e2)}")
                        return None, None
        
        st.sidebar.write("✅ Static data downloaded successfully!")
        return fund_df, manager_df
        
    except Exception as e:
        st.error(f"Error downloading static data: {str(e)}")
        return None, None

def process_cda_data(cda_zip_content, fund_df, manager_df, investment_types=None):
    """Process CDA data and cross-reference with other datasets"""
    try:
        # Extract CDA data from zip
        with zipfile.ZipFile(io.BytesIO(cda_zip_content)) as zip_file:
            # Find the Bloco 7 file
            bloco7_files = [f for f in zip_file.namelist() if 'BLC_7' in f]
            if not bloco7_files:
                st.error("Bloco 7 file not found in CDA data")
                return pd.DataFrame()
            
            # Read Bloco 7 data
            with zip_file.open(bloco7_files[0]) as f:
                try:
                    cda_df = pd.read_csv(f, sep=';', encoding='latin-1', low_memory=False, on_bad_lines='skip')
                except Exception as e:
                    st.error(f"Error parsing CDA CSV: {str(e)}")
                    # Try with different encoding
                    f.seek(0)
                    try:
                        cda_df = pd.read_csv(f, sep=';', encoding='utf-8', low_memory=False, on_bad_lines='skip')
                    except Exception as e2:
                        st.error(f"Error parsing CDA with UTF-8: {str(e2)}")
                        return pd.DataFrame()
        
        # Debug: Show available columns
        st.sidebar.write(f"CDA columns: {list(cda_df.columns)}")
        
        # Apply investment type filter if specified
        if investment_types and len(investment_types) > 0:
            offshore_df = cda_df[cda_df['TP_ATIVO'].isin(investment_types)].copy()
            st.sidebar.write(f"🔍 Filtered by investment types: {investment_types}")
        else:
            offshore_df = cda_df.copy()
            st.sidebar.write("🔍 Using all investment types")
        
        # Debug: Check offshore data
        st.sidebar.write(f"🔍 Records after filtering: {len(offshore_df)}")
        st.sidebar.write(f"🔍 Available columns: {list(offshore_df.columns)}")
        st.sidebar.write(f"🔍 DENOM_SOCIAL exists after filtering: {'DENOM_SOCIAL' in offshore_df.columns}")
        
        if len(offshore_df) == 0:
            st.sidebar.write("❌ No records found after filtering!")
            return pd.DataFrame()
        
        # Convert value columns to numeric
        st.sidebar.write("🔍 Converting value columns to numeric...")
        value_cols = ['VL_MERC_POS_FINAL', 'VL_CUSTO_POS_FINAL', 'VL_VENDA_NEGOC', 'VL_AQUIS_NEGOC']
        for col in value_cols:
            if col in offshore_df.columns:
                offshore_df[col] = pd.to_numeric(offshore_df[col], errors='coerce')
        
        # Check if DENOM_SOCIAL exists in offshore data after numeric conversion
        st.sidebar.write(f"🔍 DENOM_SOCIAL exists after numeric conversion: {'DENOM_SOCIAL' in offshore_df.columns}")
        if 'DENOM_SOCIAL' not in offshore_df.columns:
            st.error("DENOM_SOCIAL column not found in offshore data after filtering")
            st.sidebar.write(f"Available columns: {list(offshore_df.columns)}")
            return pd.DataFrame()
        
        # Group by fund CNPJ to get total offshore assets per fund
        try:
            st.sidebar.write("🔍 Starting groupby operation...")
            fund_offshore = offshore_df.groupby('CNPJ_FUNDO_CLASSE').agg({
                'VL_MERC_POS_FINAL': 'sum',
                'VL_CUSTO_POS_FINAL': 'sum',
                'DENOM_SOCIAL': 'first',  # This is the fund name from CDA
                'DT_COMPTC': 'first'
            }).reset_index()
            st.sidebar.write(f"🔍 Groupby successful! Columns: {list(fund_offshore.columns)}")
            st.sidebar.write(f"🔍 DENOM_SOCIAL exists after groupby: {'DENOM_SOCIAL' in fund_offshore.columns}")
        except Exception as e:
            st.error(f"Error in groupby operation: {str(e)}")
            st.sidebar.write(f"Offshore data sample: {offshore_df.head()}")
            return pd.DataFrame()
        
        # Filter out zero values
        fund_offshore = fund_offshore[fund_offshore['VL_MERC_POS_FINAL'] > 0]
        st.sidebar.write(f"🔍 After zero filter: {len(fund_offshore)} records, columns: {list(fund_offshore.columns)}")
        
        # Cross-reference with fund registry
        # Clean CNPJs: remove all non-numeric characters and keep as STRINGS
        fund_offshore['CNPJ_FUNDO_CLASSE_clean'] = fund_offshore['CNPJ_FUNDO_CLASSE'].astype(str).str.replace('[^0-9]', '', regex=True)
        fund_df['CNPJ_Fundo_clean'] = fund_df['CNPJ_Fundo'].astype(str).str.replace('[^0-9]', '', regex=True)
        
        # Keep as STRINGS - NO numeric conversion!
        fund_offshore['CNPJ_FUNDO_CLASSE_clean'] = fund_offshore['CNPJ_FUNDO_CLASSE_clean'].astype(str)
        fund_df['CNPJ_Fundo_clean'] = fund_df['CNPJ_Fundo_clean'].astype(str)
        
        # Debug: Show sample CNPJs
        st.sidebar.write(f"CDA CNPJ samples: {fund_offshore['CNPJ_FUNDO_CLASSE_clean'].head(3).tolist()}")
        st.sidebar.write(f"Fund Registry CNPJ samples: {fund_df['CNPJ_Fundo_clean'].head(3).tolist()}")
        
        # Merge with fund registry to get manager CNPJ
        st.sidebar.write("🔍 Starting fund registry merge...")
        merged_df = fund_offshore.merge(
            fund_df[['CNPJ_Fundo_clean', 'CPF_CNPJ_Gestor', 'Gestor']], 
            left_on='CNPJ_FUNDO_CLASSE_clean', 
            right_on='CNPJ_Fundo_clean', 
            how='left'
        )
        st.sidebar.write(f"🔍 Fund registry merge complete! Columns: {list(merged_df.columns)}")
        st.sidebar.write(f"🔍 DENOM_SOCIAL exists after fund merge: {'DENOM_SOCIAL' in merged_df.columns}")
        
        # Cross-reference with manager registry
        # Clean CNPJs: remove all non-numeric characters and ensure 14 digits
        # Keep as STRINGS throughout to avoid precision loss
        
        # Handle scientific notation first for fund registry
        merged_df['CPF_CNPJ_Gestor_clean'] = merged_df['CPF_CNPJ_Gestor'].astype(str).apply(
            lambda x: f"{float(x):.0f}" if 'e+' in str(x) else str(x)
        )
        merged_df['CPF_CNPJ_Gestor_clean'] = merged_df['CPF_CNPJ_Gestor_clean'].str.replace('[^0-9]', '', regex=True)
        
        manager_df['CNPJ_clean'] = manager_df['CNPJ'].astype(str).str.replace('[^0-9]', '', regex=True)
        
        # Fix data quality issue: Fund registry CNPJs are missing leading zeros
        # Fund registry has 13 digits + .0, manager registry has 14 digits
        def fix_fund_cnpj(cnpj_str):
            if pd.isna(cnpj_str) or cnpj_str == '':
                return cnpj_str
            cnpj_str = str(cnpj_str)
            # Remove decimal point and trailing zero
            if cnpj_str.endswith('.0'):
                cnpj_str = cnpj_str[:-2]
            # Remove any other non-numeric characters
            import re
            cnpj_str = re.sub(r'[^0-9]', '', cnpj_str)
            # If we have exactly 13 digits, add a leading zero to make it 14
            if len(cnpj_str) == 13:
                cnpj_str = '0' + cnpj_str
            return cnpj_str
        
        merged_df['CPF_CNPJ_Gestor_clean'] = merged_df['CPF_CNPJ_Gestor_clean'].apply(fix_fund_cnpj)
        
        # Ensure CNPJs are exactly 14 digits (pad with zeros if needed, truncate if too long)
        merged_df['CPF_CNPJ_Gestor_clean'] = merged_df['CPF_CNPJ_Gestor_clean'].str.zfill(14).str[:14]
        manager_df['CNPJ_clean'] = manager_df['CNPJ_clean'].str.zfill(14).str[:14]
        
        # Keep as strings - NO numeric conversion!
        merged_df['CPF_CNPJ_Gestor_clean'] = merged_df['CPF_CNPJ_Gestor_clean'].astype(str)
        manager_df['CNPJ_clean'] = manager_df['CNPJ_clean'].astype(str)
        
        # Debug: Show sample CNPJs
        st.sidebar.write(f"Gestor CNPJ samples: {merged_df['CPF_CNPJ_Gestor_clean'].dropna().head(3).tolist()}")
        st.sidebar.write(f"Manager Registry CNPJ samples: {manager_df['CNPJ_clean'].head(3).tolist()}")
        
        # Check for matches (string-based)
        gestor_cnpjs = set(merged_df['CPF_CNPJ_Gestor_clean'].dropna())
        manager_cnpjs = set(manager_df['CNPJ_clean'].dropna())
        matches = gestor_cnpjs.intersection(manager_cnpjs)
        st.sidebar.write(f"🔍 CNPJ matches found: {len(matches)} out of {len(gestor_cnpjs)} gestor CNPJs")
        if len(matches) > 0:
            st.sidebar.write(f"🔍 Sample matches: {list(matches)[:3]}")
        else:
            st.sidebar.write("❌ No CNPJ matches found between gestor and manager registries!")
        
        # Merge with manager registry using NAME-BASED matching (more reliable than CNPJ)
        st.sidebar.write("🔍 Starting manager registry merge using NAME-BASED matching...")
        
        # Create clean name columns for matching
        manager_df['DENOM_SOCIAL_clean'] = manager_df['DENOM_SOCIAL'].str.strip().str.upper()
        merged_df['Gestor_clean'] = merged_df['Gestor'].str.strip().str.upper()
        
        # Try name-based matching first
        final_df = merged_df.merge(
            manager_df[['DENOM_SOCIAL_clean', 'DENOM_SOCIAL', 'MUN', 'UF', 'LOGRADOURO', 'BAIRRO', 'CEP']], 
            left_on='Gestor_clean', 
            right_on='DENOM_SOCIAL_clean', 
            how='left'
        )
        st.sidebar.write(f"🔍 Manager registry merge complete! Columns: {list(final_df.columns)}")
        st.sidebar.write(f"🔍 DENOM_SOCIAL exists after manager merge: {'DENOM_SOCIAL' in final_df.columns}")
        st.sidebar.write(f"🔍 MUN exists after manager merge: {'MUN' in final_df.columns}")
        st.sidebar.write(f"🔍 UF exists after manager merge: {'UF' in final_df.columns}")
        
        # Check how many records have location data
        if 'MUN' in final_df.columns:
            mun_count = final_df['MUN'].notna().sum()
            st.sidebar.write(f"🔍 Records with MUN data: {mun_count} out of {len(final_df)}")
            st.sidebar.write(f"🔍 Name-based MUN match rate: {mun_count/len(final_df)*100:.1f}%")
        if 'UF' in final_df.columns:
            uf_count = final_df['UF'].notna().sum()
            st.sidebar.write(f"🔍 Records with UF data: {uf_count} out of {len(final_df)}")
            st.sidebar.write(f"🔍 Name-based UF match rate: {uf_count/len(final_df)*100:.1f}%")
        
        # Filter out records without managers (use only Gestor)
        valid_df = final_df[
            (final_df['CPF_CNPJ_Gestor'].notna() & (final_df['CPF_CNPJ_Gestor'] != 0))
        ]
        
        # Debug: Show columns in valid_df
        st.sidebar.write(f"🔍 Valid_df columns: {list(valid_df.columns)}")
        st.sidebar.write(f"🔍 Valid_df shape: {valid_df.shape}")
        st.sidebar.write(f"🔍 DENOM_SOCIAL exists in valid_df: {'DENOM_SOCIAL' in valid_df.columns}")
        
        if len(valid_df) == 0:
            st.sidebar.write("❌ No valid records found!")
            return pd.DataFrame()
        
        # Use only Gestor fields
        valid_df['Manager_CNPJ'] = valid_df['CPF_CNPJ_Gestor']
        valid_df['Manager_Name'] = valid_df['Gestor']
        
        # Group by manager to get total offshore assets per manager
        manager_offshore = valid_df.groupby(['Manager_CNPJ', 'Manager_Name']).agg({
            'VL_MERC_POS_FINAL': 'sum',
            'VL_CUSTO_POS_FINAL': 'sum',
            'CNPJ_FUNDO_CLASSE': 'count'
        }).reset_index()
        
        # Get location data for each manager
        # Check what columns are available for aggregation
        st.sidebar.write(f"🔍 Available columns for location aggregation: {list(valid_df.columns)}")
        
        # Build aggregation dictionary dynamically based on available columns
        agg_dict = {
            'MUN': 'first', 
            'UF': 'first'
        }
        
        # Add manager name field (prefer DENOM_SOCIAL, fallback to Manager_Name)
        if 'DENOM_SOCIAL' in valid_df.columns:
            agg_dict['DENOM_SOCIAL'] = 'first'
            st.sidebar.write("🔍 Using DENOM_SOCIAL from manager registry for manager names")
        else:
            st.sidebar.write("⚠️ DENOM_SOCIAL not found - will use Manager_Name instead")
            agg_dict['Manager_Name'] = 'first'
        
        st.sidebar.write(f"🔍 Aggregation dictionary: {agg_dict}")
        
        location_data = valid_df.groupby(['Manager_CNPJ']).agg(agg_dict).reset_index()
        
        # Merge location data
        manager_offshore = manager_offshore.merge(location_data, on='Manager_CNPJ', how='left')
        
        # Rename columns
        rename_dict = {
            'VL_MERC_POS_FINAL': 'Total_Offshore_Assets_Market_Value',
            'VL_CUSTO_POS_FINAL': 'Total_Offshore_Assets_Cost_Value',
            'CNPJ_FUNDO_CLASSE': 'Number_of_Funds',
            'MUN': 'MUN',
            'UF': 'UF'
        }
        
        # Add manager name to rename dict
        if 'DENOM_SOCIAL' in manager_offshore.columns:
            rename_dict['DENOM_SOCIAL'] = 'DENOM_SOCIAL'
        elif 'Manager_Name' in manager_offshore.columns:
            rename_dict['Manager_Name'] = 'DENOM_SOCIAL'
        
        manager_offshore = manager_offshore.rename(columns=rename_dict)
        
        # Fill missing values
        manager_offshore['MUN'] = manager_offshore['MUN'].fillna('N/A')
        manager_offshore['UF'] = manager_offshore['UF'].fillna('N/A')
        if 'DENOM_SOCIAL' in manager_offshore.columns:
            manager_offshore['DENOM_SOCIAL'] = manager_offshore['DENOM_SOCIAL'].fillna('N/A')
        elif 'Manager_Name' in manager_offshore.columns:
            manager_offshore['Manager_Name'] = manager_offshore['Manager_Name'].fillna('N/A')
        
        # Sort by market value
        manager_offshore = manager_offshore.sort_values('Total_Offshore_Assets_Market_Value', ascending=False)
        
        # Calculate percentage of total
        total_offshore = manager_offshore['Total_Offshore_Assets_Market_Value'].sum()
        manager_offshore['Percentage_of_Total'] = (manager_offshore['Total_Offshore_Assets_Market_Value'] / total_offshore * 100).round(2)
        
        return manager_offshore
        
    except Exception as e:
        st.error(f"Error processing CDA data: {str(e)}")
        return pd.DataFrame()

def main():
    # Header
    st.markdown('<h1 class="main-header">🇧🇷 Brazilian Fund Managers - Offshore Assets Analysis</h1>', unsafe_allow_html=True)
    
    # Load static data
    with st.spinner("Loading required data files..."):
        fund_df, manager_df = download_static_data()
    
    if fund_df is None or manager_df is None:
        st.error("Failed to load required data files. Please check your internet connection and try again.")
        st.stop()
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Month/Year selection
    st.sidebar.subheader("📅 Select Period")
    
    # Get previous month as default
    today = datetime.now()
    if today.month == 1:
        prev_month = 12
        prev_year = today.year - 1
    else:
        prev_month = today.month - 1
        prev_year = today.year
    
    # Create year and month selectors
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        selected_year = st.selectbox(
            "Year",
            range(2020, today.year + 2),
            index=prev_year - 2020
        )
    
    with col2:
        selected_month = st.selectbox(
            "Month",
            range(1, 13),
            index=prev_month - 1,
            format_func=lambda x: datetime(2024, x, 1).strftime('%B')
        )
    
    # Format year_month for CVM data
    year_month = f"{selected_year}{selected_month:02d}"
    
    # Investment type filter
    st.sidebar.subheader("🏦 Investment Type Filter")
    
    # Get unique investment types from the data
    if 'current_data' in st.session_state and not st.session_state['current_data'].empty:
        # Check if TP_ATIVO column exists in the processed data
        if 'TP_ATIVO' in st.session_state['current_data'].columns:
            available_types = st.session_state['current_data']['TP_ATIVO'].unique()
            available_types = [t for t in available_types if pd.notna(t)]
            st.sidebar.write(f"Available types: {len(available_types)}")
        else:
            # If TP_ATIVO not available, use default options
            available_types = ['Fundos Offshore', 'Outros', 'Ação ordinária', 'Depository Receipt no Exterior(DR)']
            st.sidebar.write("Using default investment types (TP_ATIVO not available in processed data)")
    else:
        # Default options if no data loaded yet
        available_types = ['Fundos Offshore', 'Outros', 'Ação ordinária', 'Depository Receipt no Exterior(DR)']
        st.sidebar.write("No data loaded yet - using default types")
    
    selected_types = st.sidebar.multiselect(
        "Select Investment Types",
        available_types,
        default=['Fundos Offshore'] if 'Fundos Offshore' in available_types else available_types[:1]
    )
    
    # Make filter optional - if nothing selected, use all types
    if not selected_types:
        selected_types = available_types
        st.sidebar.info("ℹ️ No filter selected - using all investment types")
    
    # Load data button
    if st.sidebar.button("🔄 Load Data", type="primary"):
        with st.spinner(f"Loading data for {datetime(selected_year, selected_month, 1).strftime('%B %Y')}..."):
            cda_data = download_cvm_data(year_month)
            if cda_data:
                df = process_cda_data(cda_data, fund_df, manager_df, selected_types)
                if not df.empty:
                    st.session_state['current_data'] = df
                    st.session_state['current_period'] = f"{selected_year}-{selected_month:02d}"
                    st.success(f"✅ Data loaded successfully for {datetime(selected_year, selected_month, 1).strftime('%B %Y')}")
                else:
                    st.error("❌ No data found for the selected period")
            else:
                st.error("❌ Failed to download data")
    
    # Check if we have data loaded
    if 'current_data' not in st.session_state:
        st.info("👆 Please select a period and click 'Load Data' to start the analysis")
        st.stop()
    
    df = st.session_state['current_data']
    current_period = st.session_state.get('current_period', 'Unknown')
    
    # Show current period
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Current Period:** {current_period}")
    st.sidebar.markdown(f"**Total Records:** {len(df)}")
    
    # Location filters
    st.sidebar.subheader("🗺️ Location Filters")
    
    # State filter
    states = ['All'] + sorted(df['UF'].unique().tolist())
    selected_state = st.sidebar.selectbox("State (UF)", states)
    
    # City filter (dependent on state)
    if selected_state != 'All':
        cities = ['All'] + sorted(df[df['UF'] == selected_state]['MUN'].unique().tolist())
    else:
        cities = ['All'] + sorted(df['MUN'].unique().tolist())
    
    selected_city = st.sidebar.selectbox("City (MUN)", cities)
    
    # Asset range filter
    st.sidebar.subheader("💰 Asset Range")
    min_assets = df['Total_Offshore_Assets_Market_Value'].min()
    max_assets = df['Total_Offshore_Assets_Market_Value'].max()
    
    asset_range = st.sidebar.slider(
        "Minimum offshore assets (R$ billions)",
        min_value=0.0,
        max_value=float(max_assets / 1e9),
        value=0.0,
        step=0.1,
        format="R$ %.1fB"
    )
    
    # Apply filters
    filtered_df = df.copy()
    
    # State filter
    if selected_state != 'All':
        filtered_df = filtered_df[filtered_df['UF'] == selected_state]
    
    # City filter
    if selected_city != 'All':
        filtered_df = filtered_df[filtered_df['MUN'] == selected_city]
    
    # Asset range filter
    filtered_df = filtered_df[filtered_df['Total_Offshore_Assets_Market_Value'] >= asset_range * 1e9]
    
    # Main content
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_assets = filtered_df['Total_Offshore_Assets_Market_Value'].sum()
        st.metric(
            "Total Offshore Assets",
            f"R$ {total_assets:,.0f}",
            delta=None
        )
    
    with col2:
        st.metric(
            "Number of Managers",
            f"{len(filtered_df):,}",
            delta=None
        )
    
    with col3:
        st.metric(
            "Total Funds",
            f"{filtered_df['Number_of_Funds'].sum():,}",
            delta=None
        )
    
    # Charts section
    st.header("📊 Analysis Charts")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Top 10 managers bar chart
        top_10 = filtered_df.head(10)
        
        # Determine the correct column name for manager names
        manager_col = None
        if 'DENOM_SOCIAL' in top_10.columns:
            manager_col = 'DENOM_SOCIAL'
        elif 'Manager_Name_x' in top_10.columns:
            manager_col = 'Manager_Name_x'
        elif 'Manager_Name_y' in top_10.columns:
            manager_col = 'Manager_Name_y'
        elif 'Manager_Name' in top_10.columns:
            manager_col = 'Manager_Name'
        else:
            st.error(f"No manager name column found! Available columns: {list(top_10.columns)}")
            return
        
        fig_bar = px.bar(
            top_10,
            x='Total_Offshore_Assets_Market_Value',
            y=manager_col,
            orientation='h',
            title="Top 10 Managers by Offshore Assets",
            labels={
                'Total_Offshore_Assets_Market_Value': 'Offshore Assets (R$)',
                manager_col: 'Manager'
            },
            color='Total_Offshore_Assets_Market_Value',
            color_continuous_scale='Blues'
        )
        fig_bar.update_layout(
            height=500,
            yaxis={'categoryorder': 'total ascending'},
            xaxis={'tickformat': '.0f'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col2:
        # Market share pie chart
        if len(filtered_df) > 0:
            fig_pie = px.pie(
                filtered_df.head(10),
                values='Total_Offshore_Assets_Market_Value',
                names=manager_col,
                title="Market Share - Top 10 Managers"
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_pie, use_container_width=True)
    
    # Geographic distribution
    if selected_state == 'All':
        st.subheader("🗺️ Geographic Distribution")
        
        # State distribution
        state_dist = filtered_df.groupby('UF').agg({
            'Total_Offshore_Assets_Market_Value': 'sum',
            'Manager_CNPJ': 'count'  # Use Manager_CNPJ for counting managers
        }).reset_index()
        state_dist.columns = ['State', 'Total_Assets', 'Number_of_Managers']
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_state = px.bar(
                state_dist,
                x='State',
                y='Total_Assets',
                title="Offshore Assets by State",
                labels={
                    'Total_Assets': 'Offshore Assets (R$)',
                    'State': 'State'
                }
            )
            fig_state.update_layout(xaxis={'tickangle': 45})
            st.plotly_chart(fig_state, use_container_width=True)
        
        with col2:
            fig_managers = px.bar(
                state_dist,
                x='State',
                y='Number_of_Managers',
                title="Number of Managers by State",
                labels={
                    'Number_of_Managers': 'Number of Managers',
                    'State': 'State'
                }
            )
            fig_managers.update_layout(xaxis={'tickangle': 45})
            st.plotly_chart(fig_managers, use_container_width=True)
    
    # Detailed table
    st.header("📋 Detailed Results")
    
    # Sort options
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Manager Rankings")
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ['Total_Offshore_Assets_Market_Value', 'Number_of_Funds', 'Percentage_of_Total'],
            format_func=lambda x: {
                'Total_Offshore_Assets_Market_Value': 'Offshore Assets',
                'Number_of_Funds': 'Number of Funds',
                'Percentage_of_Total': 'Market Share %'
            }[x]
        )
    
    # Sort data
    ascending = sort_by != 'Total_Offshore_Assets_Market_Value'
    sorted_df = filtered_df.sort_values(sort_by, ascending=ascending)
    
    # Display table - use the correct manager name column (same logic as charts)
    manager_name_col = None
    if 'DENOM_SOCIAL' in sorted_df.columns:
        manager_name_col = 'DENOM_SOCIAL'
    elif 'Manager_Name_x' in sorted_df.columns:
        manager_name_col = 'Manager_Name_x'
    elif 'Manager_Name_y' in sorted_df.columns:
        manager_name_col = 'Manager_Name_y'
    elif 'Manager_Name' in sorted_df.columns:
        manager_name_col = 'Manager_Name'
    else:
        st.error(f"No manager name column found for table! Available columns: {list(sorted_df.columns)}")
        return
    
    display_df = sorted_df[[manager_name_col, 'MUN', 'UF', 'Total_Offshore_Assets_Market_Value', 
                           'Number_of_Funds', 'Percentage_of_Total']].copy()
    
    # Format the display
    display_df['Rank'] = range(1, len(display_df) + 1)
    display_df['Offshore Assets'] = display_df['Total_Offshore_Assets_Market_Value'].apply(lambda x: f"R$ {x:,.0f}")
    display_df['Market Share'] = display_df['Percentage_of_Total'].apply(lambda x: f"{x:.1f}%")
    display_df['Funds'] = display_df['Number_of_Funds'].astype(int)
    
    # Reorder columns
    display_df = display_df[['Rank', manager_name_col, 'MUN', 'UF', 'Offshore Assets', 
                           'Market Share', 'Funds']]
    
    # Rename columns for display
    display_df.columns = ['Rank', 'Manager', 'City', 'State', 'Offshore Assets', 'Market Share %', 'Number of Funds']
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )
    
    # Download button
    csv = display_df.to_csv(index=False)
    st.download_button(
        label="📥 Download filtered data as CSV",
        data=csv,
        file_name=f"offshore_managers_{current_period}_filtered_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    # Footer
    st.markdown("---")
    st.markdown(f"""
    <div style='text-align: center; color: #666;'>
        <p>Data Source: CVM (Comissão de Valores Mobiliários) | 
        Analysis Period: {current_period} | 
        Generated by: Offshore Assets Analysis Tool</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
