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
import csv
import re
from io import StringIO

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

def robust_csv_parser(file_content, encoding='latin-1', sep=';'):
    """
    Robust CSV parser that can handle severely corrupted CSV files
    """
    try:
        # Decode the content
        if isinstance(file_content, bytes):
            text_content = file_content.decode(encoding, errors='ignore')
        else:
            text_content = file_content
        
        # Split into lines
        lines = text_content.split('\n')
        
        # Find the header line (usually the first non-empty line)
        header_line = None
        data_start = 0
        for i, line in enumerate(lines):
            if line.strip() and ';' in line:
                header_line = line.strip()
                data_start = i + 1
                break
        
        if not header_line:
            return pd.DataFrame()
        
        # Parse header
        header_reader = csv.reader([header_line], delimiter=sep)
        headers = next(header_reader)
        
        # Clean headers
        headers = [h.strip() for h in headers]
        
        # Parse data rows with error handling
        data_rows = []
        corrupted_rows = 0
        max_corrupted = 100  # Stop if too many corrupted rows
        
        for i, line in enumerate(lines[data_start:], data_start):
            if corrupted_rows >= max_corrupted:
                st.sidebar.write(f"⚠️ Stopping after {max_corrupted} corrupted rows")
                break
                
            if not line.strip():
                continue
                
            try:
                # Try to parse the line
                reader = csv.reader([line], delimiter=sep)
                row = next(reader)
                
                # Ensure row has same number of columns as header
                if len(row) == len(headers):
                    data_rows.append(row)
                elif len(row) > len(headers):
                    # Truncate extra columns
                    data_rows.append(row[:len(headers)])
                else:
                    # Pad with empty strings
                    padded_row = row + [''] * (len(headers) - len(row))
                    data_rows.append(padded_row)
                    
            except Exception as e:
                corrupted_rows += 1
                if corrupted_rows <= 5:  # Only show first few errors
                    st.sidebar.write(f"⚠️ Skipping corrupted row {i}: {str(e)[:50]}...")
                continue
        
        if not data_rows:
            st.sidebar.write("❌ No valid data rows found")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame(data_rows, columns=headers)
        
        # Clean up the data
        df = df.replace('', np.nan)
        df = df.dropna(how='all')  # Remove completely empty rows
        
        st.sidebar.write(f"✅ Successfully parsed {len(df)} rows (skipped {corrupted_rows} corrupted)")
        return df
        
    except Exception as e:
        st.sidebar.write(f"❌ Robust CSV parser failed: {str(e)}")
        return pd.DataFrame()

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
            # Look for registro_fundo.csv specifically (contains fund-manager mapping)
            fund_files = [f for f in zip_file.namelist() if f.endswith('.csv') and 'fundo' in f.lower()]
            if not fund_files:
                st.error("No fund CSV files found in Fund Registry zip")
                return None, None
            
            with zip_file.open(fund_files[0]) as f:
                # Use robust CSV parser
                st.sidebar.write("🔄 Using robust CSV parser for Fund Registry...")
                file_content = f.read()
                fund_df = robust_csv_parser(file_content, encoding='latin-1', sep=';')
                
                if fund_df.empty:
                    st.sidebar.write("🔄 Trying alternative encoding...")
                    fund_df = robust_csv_parser(file_content, encoding='cp1252', sep=';')
                
                if fund_df.empty:
                    st.error("Failed to parse Fund Registry with robust parser")
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
                # Use robust CSV parser
                st.sidebar.write("🔄 Using robust CSV parser for Manager Registry...")
                file_content = f.read()
                manager_df = robust_csv_parser(file_content, encoding='latin-1', sep=';')
                
                if manager_df.empty:
                    st.sidebar.write("🔄 Trying alternative encoding...")
                    manager_df = robust_csv_parser(file_content, encoding='cp1252', sep=';')
                
                if manager_df.empty:
                    st.error("Failed to parse Manager Registry with robust parser")
                    return None, None
        
        st.sidebar.write("✅ Static data downloaded successfully!")
        return fund_df, manager_df
        
    except Exception as e:
        st.error(f"Error downloading static data: {str(e)}")
        return None, None

def process_cda_data(cda_zip_content, fund_df, manager_df, investment_types=None):
    """Process CDA data and cross-reference with other datasets"""
    try:
        st.sidebar.write("🔍 Starting process_cda_data function...")
        st.sidebar.write(f"🔍 Fund_df shape: {fund_df.shape if fund_df is not None else 'None'}")
        st.sidebar.write(f"🔍 Manager_df shape: {manager_df.shape if manager_df is not None else 'None'}")
        st.sidebar.write(f"🔍 Investment types: {investment_types}")
        # Extract CDA data from zip
        with zipfile.ZipFile(io.BytesIO(cda_zip_content)) as zip_file:
            # Find the Bloco 7 file
            bloco7_files = [f for f in zip_file.namelist() if 'BLC_7' in f]
            if not bloco7_files:
                st.error("Bloco 7 file not found in CDA data")
                return pd.DataFrame()
            
            # Read Bloco 7 data
            with zip_file.open(bloco7_files[0]) as f:
                # Use robust CSV parser
                st.sidebar.write("🔄 Using robust CSV parser for CDA data...")
                file_content = f.read()
                cda_df = robust_csv_parser(file_content, encoding='latin-1', sep=';')
                
                if cda_df.empty:
                    st.sidebar.write("🔄 Trying alternative encoding...")
                    cda_df = robust_csv_parser(file_content, encoding='cp1252', sep=';')
                
                if cda_df.empty:
                    st.error("Failed to parse CDA data with robust parser")
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
        
        # Group by fund CNPJ to get total offshore assets per fund
        try:
            st.sidebar.write("🔍 Starting groupby operation...")
            
            # Build aggregation dictionary dynamically based on available columns
            agg_dict = {
                'VL_MERC_POS_FINAL': 'sum',
                'VL_CUSTO_POS_FINAL': 'sum'
            }
            
            # Add optional columns if they exist
            if 'DENOM_SOCIAL' in offshore_df.columns:
                agg_dict['DENOM_SOCIAL'] = 'first'  # This is the fund name from CDA
                st.sidebar.write("🔍 Including DENOM_SOCIAL (fund name) in groupby")
            if 'DT_COMPTC' in offshore_df.columns:
                agg_dict['DT_COMPTC'] = 'first'
                st.sidebar.write("🔍 Including DT_COMPTC in groupby")
            
            fund_offshore = offshore_df.groupby('CNPJ_FUNDO_CLASSE').agg(agg_dict).reset_index()
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
        # Find the correct CNPJ column names
        cda_cnpj_col = 'CNPJ_FUNDO_CLASSE'  # This should exist in CDA data
        fund_cnpj_col = None
        
        # Look for CNPJ columns in Fund Registry
        # The registro_fundo.csv should have CNPJ_Fundo
        if 'CNPJ_Fundo' in fund_df.columns:
            fund_cnpj_col = 'CNPJ_Fundo'
        elif 'CNPJ_Classe' in fund_df.columns:
            fund_cnpj_col = 'CNPJ_Classe'
        else:
            # Fallback to any CNPJ column
            for col in fund_df.columns:
                if 'CNPJ' in col.upper():
                    fund_cnpj_col = col
                    break
        
        if not fund_cnpj_col:
            st.error(f"CNPJ column not found in Fund Registry. Available columns: {list(fund_df.columns)}")
            return pd.DataFrame()
        
        st.sidebar.write(f"Using Fund Registry CNPJ column: {fund_cnpj_col}")
        
        # Clean CNPJs: remove all non-numeric characters and keep as STRINGS
        fund_offshore['CNPJ_FUNDO_CLASSE_clean'] = fund_offshore[cda_cnpj_col].astype(str).str.replace('[^0-9]', '', regex=True)
        fund_df['CNPJ_Fundo_clean'] = fund_df[fund_cnpj_col].astype(str).str.replace('[^0-9]', '', regex=True)
        
        # Pad CNPJs to 14 characters with leading zeros
        fund_offshore['CNPJ_FUNDO_CLASSE_clean'] = fund_offshore['CNPJ_FUNDO_CLASSE_clean'].str.zfill(14)
        fund_df['CNPJ_Fundo_clean'] = fund_df['CNPJ_Fundo_clean'].str.zfill(14)
        
        # Keep as STRINGS - NO numeric conversion!
        fund_offshore['CNPJ_FUNDO_CLASSE_clean'] = fund_offshore['CNPJ_FUNDO_CLASSE_clean'].astype(str)
        fund_df['CNPJ_Fundo_clean'] = fund_df['CNPJ_Fundo_clean'].astype(str)
        
        # Debug: Show sample CNPJs
        st.sidebar.write(f"CDA CNPJ samples: {fund_offshore['CNPJ_FUNDO_CLASSE_clean'].head(3).tolist()}")
        st.sidebar.write(f"Fund Registry CNPJ samples: {fund_df['CNPJ_Fundo_clean'].head(3).tolist()}")
        
        # Check what manager-related columns are available in Fund Registry
        manager_cols = [col for col in fund_df.columns if 'GESTOR' in col.upper() or 'ADMIN' in col.upper() or 'CPF' in col.upper() or 'CNPJ' in col.upper()]
        st.sidebar.write(f"Manager-related columns in Fund Registry: {manager_cols}")
        
        # Merge with fund registry to get manager CNPJ
        st.sidebar.write("🔍 Starting fund registry merge...")
        # Use the correct columns for CNPJ chain: CNPJ_FUNDO_CLASSE → CNPJ_Fundo → CPF_CNPJ_Gestor
        merge_cols = ['CNPJ_Fundo_clean']
        if 'CPF_CNPJ_Gestor' in fund_df.columns:
            merge_cols.append('CPF_CNPJ_Gestor')
        if 'Gestor' in fund_df.columns:
            merge_cols.append('Gestor')
        
        merged_df = fund_offshore.merge(
            fund_df[merge_cols], 
            left_on='CNPJ_FUNDO_CLASSE_clean', 
            right_on='CNPJ_Fundo_clean', 
            how='left'
        )
        st.sidebar.write(f"🔍 Fund registry merge complete! Columns: {list(merged_df.columns)}")
        st.sidebar.write(f"🔍 CPF_CNPJ_Gestor exists after fund merge: {'CPF_CNPJ_Gestor' in merged_df.columns}")
        
        # Now use CNPJ chain: CPF_CNPJ_Gestor → Manager Registry CNPJ
        st.sidebar.write("🔍 Starting CNPJ-based manager registry merge...")
        
        # Check if we have manager CNPJ from fund registry
        if 'CPF_CNPJ_Gestor' not in merged_df.columns:
            st.sidebar.write("❌ CPF_CNPJ_Gestor not found in fund registry merge!")
            st.sidebar.write(f"🔍 Available columns after fund merge: {list(merged_df.columns)}")
            # Fallback to name-based matching
            st.sidebar.write("🔄 Falling back to name-based matching...")
            
            # Look for manager name column in merged_df
            gestor_col = None
            for col in merged_df.columns:
                if 'GESTOR' in col.upper():
                    gestor_col = col
                    break
            
            if gestor_col:
                st.sidebar.write(f"✅ Found manager name column: {gestor_col}")
                # Clean manager names for matching
                merged_df['Gestor_clean'] = merged_df[gestor_col].astype(str).str.strip().str.upper()
            else:
                st.sidebar.write("❌ No manager name column found in fund registry merge")
                # If no manager data, create dummy columns
                merged_df['Gestor'] = 'Unknown Manager'
                merged_df['Gestor_clean'] = 'UNKNOWN MANAGER'
            
            # Clean manager names for matching
            manager_df['DENOM_SOCIAL_clean'] = manager_df['DENOM_SOCIAL'].astype(str).str.strip().str.upper()
            
            # Debug: Show sample names
            st.sidebar.write(f"Gestor name samples: {merged_df['Gestor_clean'].dropna().head(3).tolist()}")
            st.sidebar.write(f"Manager Registry name samples: {manager_df['DENOM_SOCIAL_clean'].head(3).tolist()}")
            
            # Check for matches (name-based)
            gestor_names = set(merged_df['Gestor_clean'].dropna())
            manager_names = set(manager_df['DENOM_SOCIAL_clean'].dropna())
            matches = gestor_names.intersection(manager_names)
            st.sidebar.write(f"🔍 Name matches found: {len(matches)} out of {len(gestor_names)} gestor names")
            if len(matches) > 0:
                st.sidebar.write(f"🔍 Sample matches: {list(matches)[:3]}")
            else:
                st.sidebar.write("❌ No name matches found between gestor and manager registries!")
            
            # Merge with manager registry using NAME-BASED matching
            final_df = merged_df.merge(
                manager_df[['DENOM_SOCIAL_clean', 'DENOM_SOCIAL', 'MUN', 'UF', 'LOGRADOURO', 'BAIRRO', 'CEP']], 
                left_on='Gestor_clean', 
                right_on='DENOM_SOCIAL_clean', 
                how='left'
            )
            
            # Debug: Check name-based matching results
            name_matches = final_df['DENOM_SOCIAL'].notna().sum()
            st.sidebar.write(f"🔍 Name-based matches found: {name_matches} out of {len(final_df)} records")
            if name_matches > 0:
                st.sidebar.write(f"🔍 Sample matched manager names: {final_df['DENOM_SOCIAL'].dropna().head(3).tolist()}")
            else:
                st.sidebar.write("❌ No name-based matches found - all managers will be 'Unknown Manager'")
        else:
            # Use CNPJ-based matching
            st.sidebar.write("✅ Using CNPJ-based matching for manager registry...")
            
            # Clean manager CNPJs - keep as STRINGS to preserve leading zeros
            merged_df['CPF_CNPJ_Gestor_clean'] = merged_df['CPF_CNPJ_Gestor'].astype(str).str.replace('[^0-9]', '', regex=True)
            manager_df['CNPJ_clean'] = manager_df['CNPJ'].astype(str).str.replace('[^0-9]', '', regex=True)
            
            # Pad CNPJs to 14 characters with leading zeros
            merged_df['CPF_CNPJ_Gestor_clean'] = merged_df['CPF_CNPJ_Gestor_clean'].str.zfill(14)
            manager_df['CNPJ_clean'] = manager_df['CNPJ_clean'].str.zfill(14)
            
            # Keep as STRINGS - NO numeric conversion!
            merged_df['CPF_CNPJ_Gestor_clean'] = merged_df['CPF_CNPJ_Gestor_clean'].astype(str)
            manager_df['CNPJ_clean'] = manager_df['CNPJ_clean'].astype(str)
            
            # Debug: Show sample CNPJs
            st.sidebar.write(f"Manager CNPJ samples from fund registry: {merged_df['CPF_CNPJ_Gestor_clean'].dropna().head(3).tolist()}")
            st.sidebar.write(f"Manager Registry CNPJ samples: {manager_df['CNPJ_clean'].head(3).tolist()}")
            
            # Check if we have valid CNPJ values (14 digits and not all zeros)
            gestor_cnpj_series = merged_df['CPF_CNPJ_Gestor_clean'].fillna('')
            valid_cnpj_mask = gestor_cnpj_series.str.fullmatch(r"\d{14}") & ~gestor_cnpj_series.eq('00000000000000')
            valid_cnpj_count = valid_cnpj_mask.sum()
            st.sidebar.write(f"🔍 Valid (non-empty, 14-digit, non-zero) manager CNPJs: {valid_cnpj_count} out of {len(merged_df)}")
            
        if valid_cnpj_count > 0:
            # Filter to rows with valid CNPJ to improve merge quality
            merged_df_valid = merged_df.copy()
            merged_df_valid['__valid_cnpj__'] = valid_cnpj_mask
            
            # Merge with manager registry using CNPJ matching, keep suffixes to avoid collisions
            final_df = merged_df_valid.merge(
                manager_df[['CNPJ_clean', 'DENOM_SOCIAL', 'MUN', 'UF', 'LOGRADOURO', 'BAIRRO', 'CEP']],
                left_on='CPF_CNPJ_Gestor_clean',
                right_on='CNPJ_clean',
                how='left',
                suffixes=('', '_mgr')
            )
            
            # Normalize manager columns after merge
            manager_name_source = None
            if 'DENOM_SOCIAL_mgr' in final_df.columns:
                manager_name_source = 'DENOM_SOCIAL_mgr'
            elif 'DENOM_SOCIAL_y' in final_df.columns:
                manager_name_source = 'DENOM_SOCIAL_y'
            elif 'DENOM_SOCIAL' in final_df.columns:
                manager_name_source = 'DENOM_SOCIAL'
            
            if manager_name_source is not None:
                final_df['DENOM_SOCIAL'] = final_df[manager_name_source]
            else:
                final_df['DENOM_SOCIAL'] = np.nan
            
            # Normalize location columns (prefer manager registry values)
            for _col in ['MUN', 'UF', 'LOGRADOURO', 'BAIRRO', 'CEP']:
                mgr_col = f"{_col}_mgr"
                if mgr_col in final_df.columns:
                    final_df[_col] = final_df[mgr_col]
            
            # Debug: Check CNPJ matching results
            cnpj_matches = final_df['DENOM_SOCIAL'].notna().sum()
            st.sidebar.write(f"🔍 CNPJ-based matches found: {cnpj_matches} out of {len(final_df)} records")
            if cnpj_matches > 0:
                st.sidebar.write(f"🔍 Sample matched manager names: {final_df['DENOM_SOCIAL'].dropna().head(3).tolist()}")
            else:
                st.sidebar.write("❌ No CNPJ matches found - falling back to name-based matching")
                # Fall back to name-based matching
                final_df = _fallback_to_name_matching(merged_df, manager_df)
        else:
            st.sidebar.write("❌ No valid manager CNPJs found - falling back to name-based matching")
            # Fall back to name-based matching
            final_df = _fallback_to_name_matching(merged_df, manager_df)
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
        
        # Filter out records without managers
        # Check which manager identification method was used
        if 'Gestor_clean' in final_df.columns:
            # Name-based matching path
            valid_df = final_df[
                (final_df['Gestor_clean'].notna() & (final_df['Gestor_clean'] != 'UNKNOWN MANAGER'))
            ]
            st.sidebar.write("🔍 Using Gestor_clean for filtering (name-based matching)")
        elif 'DENOM_SOCIAL' in final_df.columns:
            # CNPJ-based matching path - filter by DENOM_SOCIAL
            valid_df = final_df[
                (final_df['DENOM_SOCIAL'].notna() & (final_df['DENOM_SOCIAL'] != 'UNKNOWN MANAGER'))
            ]
            st.sidebar.write("🔍 Using DENOM_SOCIAL for filtering (CNPJ-based matching)")
        else:
            # Fallback - use all records
            valid_df = final_df
            st.sidebar.write("⚠️ No manager identification column found - using all records")
        
        # Debug: Show columns in valid_df
        st.sidebar.write(f"🔍 Valid_df columns: {list(valid_df.columns)}")
        st.sidebar.write(f"🔍 Valid_df shape: {valid_df.shape}")
        st.sidebar.write(f"🔍 DENOM_SOCIAL exists in valid_df: {'DENOM_SOCIAL' in valid_df.columns}")
        
        if len(valid_df) == 0:
            st.sidebar.write("❌ No valid records found!")
            return pd.DataFrame()
        
        # Use manager names from the CNPJ chain matching
        # The manager name should come from DENOM_SOCIAL after the CNPJ-based merge
        st.sidebar.write(f"🔍 Available columns in valid_df: {list(valid_df.columns)}")
        st.sidebar.write(f"🔍 DENOM_SOCIAL exists in valid_df: {'DENOM_SOCIAL' in valid_df.columns}")
        
        if 'DENOM_SOCIAL' in valid_df.columns:
            # Check if DENOM_SOCIAL has actual values (not just NaN)
            denom_social_count = valid_df['DENOM_SOCIAL'].notna().sum()
            st.sidebar.write(f"🔍 DENOM_SOCIAL non-null count: {denom_social_count} out of {len(valid_df)}")
            
            if denom_social_count > 0:
                valid_df['Manager_Name'] = valid_df['DENOM_SOCIAL']
                st.sidebar.write("🔍 Using DENOM_SOCIAL for Manager_Name (from CNPJ chain)")
            else:
                st.sidebar.write("⚠️ DENOM_SOCIAL exists but has no values - falling back to Gestor")
                # Fallback to Gestor if DENOM_SOCIAL has no values
                gestor_col = None
                for col in valid_df.columns:
                    if 'Gestor' in col.upper():
                        gestor_col = col
                        break
                
                if gestor_col:
                    valid_df['Manager_Name'] = valid_df[gestor_col]
                    st.sidebar.write(f"🔍 Using {gestor_col} for Manager_Name (fallback)")
                else:
                    st.sidebar.write("⚠️ No Gestor column found - using 'Unknown Manager'")
                    valid_df['Manager_Name'] = 'Unknown Manager'
        else:
            # Fallback to Gestor if DENOM_SOCIAL is not available
            gestor_col = None
            for col in valid_df.columns:
                if 'Gestor' in col.upper():
                    gestor_col = col
                    break
            
            st.sidebar.write(f"🔍 Found Gestor column: {gestor_col}")
            
            if gestor_col:
                valid_df['Manager_Name'] = valid_df[gestor_col]
                st.sidebar.write(f"🔍 Using {gestor_col} for Manager_Name (fallback)")
            else:
                st.sidebar.write("⚠️ No Gestor column found - using 'Unknown Manager'")
                valid_df['Manager_Name'] = 'Unknown Manager'
        
        # Group by manager to get total offshore assets per manager
        manager_offshore = valid_df.groupby('Manager_Name').agg({
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
            # Don't add Manager_Name to agg_dict since it's already the groupby key
        
        st.sidebar.write(f"🔍 Aggregation dictionary: {agg_dict}")
        
        location_data = valid_df.groupby(['Manager_Name']).agg(agg_dict).reset_index()
        
        # Merge location data
        manager_offshore = manager_offshore.merge(location_data, on='Manager_Name', how='left')
        
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
        st.sidebar.write(f"🔍 Full error details: {type(e).__name__}: {str(e)}")
        import traceback
        st.sidebar.write(f"🔍 Traceback: {traceback.format_exc()}")
        return pd.DataFrame()

def _fallback_to_name_matching(merged_df, manager_df):
    """Fallback to name-based matching when CNPJ matching fails"""
    st.sidebar.write("🔄 Starting name-based matching fallback...")
    
    # Look for manager name column in merged_df
    gestor_col = None
    for col in merged_df.columns:
        if 'GESTOR' in col.upper():
            gestor_col = col
            break
    
    if gestor_col:
        st.sidebar.write(f"✅ Found manager name column: {gestor_col}")
        # Clean manager names for matching
        merged_df['Gestor_clean'] = merged_df[gestor_col].astype(str).str.strip().str.upper()
    else:
        st.sidebar.write("❌ No manager name column found in fund registry merge")
        # If no manager data, create dummy columns
        merged_df['Gestor'] = 'Unknown Manager'
        merged_df['Gestor_clean'] = 'UNKNOWN MANAGER'
    
    # Clean manager names for matching
    manager_df['DENOM_SOCIAL_clean'] = manager_df['DENOM_SOCIAL'].astype(str).str.strip().str.upper()
    
    # Debug: Show sample names
    st.sidebar.write(f"Gestor name samples: {merged_df['Gestor_clean'].dropna().head(3).tolist()}")
    st.sidebar.write(f"Manager Registry name samples: {manager_df['DENOM_SOCIAL_clean'].head(3).tolist()}")
    
    # Check for matches (name-based)
    gestor_names = set(merged_df['Gestor_clean'].dropna())
    manager_names = set(manager_df['DENOM_SOCIAL_clean'].dropna())
    matches = gestor_names.intersection(manager_names)
    st.sidebar.write(f"🔍 Name matches found: {len(matches)} out of {len(gestor_names)} gestor names")
    if len(matches) > 0:
        st.sidebar.write(f"🔍 Sample matches: {list(matches)[:3]}")
    else:
        st.sidebar.write("❌ No name matches found between gestor and manager registries!")
    
    # Merge with manager registry using NAME-BASED matching
    final_df = merged_df.merge(
        manager_df[['DENOM_SOCIAL_clean', 'DENOM_SOCIAL', 'MUN', 'UF', 'LOGRADOURO', 'BAIRRO', 'CEP']], 
        left_on='Gestor_clean', 
        right_on='DENOM_SOCIAL_clean', 
        how='left',
        suffixes=('', '_mgr')
    )
    
    # Normalize columns after merge
    if 'DENOM_SOCIAL_mgr' in final_df.columns:
        final_df['DENOM_SOCIAL'] = final_df['DENOM_SOCIAL_mgr']
    for _col in ['MUN', 'UF', 'LOGRADOURO', 'BAIRRO', 'CEP']:
        mgr_col = f"{_col}_mgr"
        if mgr_col in final_df.columns:
            final_df[_col] = final_df[mgr_col]
    
    # Debug: Check name-based matching results
    if 'DENOM_SOCIAL' in final_df.columns:
        name_matches = final_df['DENOM_SOCIAL'].notna().sum()
        st.sidebar.write(f"🔍 Name-based matches found: {name_matches} out of {len(final_df)} records")
        if name_matches > 0:
            st.sidebar.write(f"🔍 Sample matched manager names: {final_df['DENOM_SOCIAL'].dropna().head(3).tolist()}")
        else:
            st.sidebar.write("❌ No name-based matches found - all managers will be 'Unknown Manager'")
    else:
        st.sidebar.write("❌ DENOM_SOCIAL column not found in final_df - all managers will be 'Unknown Manager'")
        # Add DENOM_SOCIAL column with Unknown Manager values
        final_df['DENOM_SOCIAL'] = 'Unknown Manager'
    
    return final_df

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
        # Use the correct manager name column (same logic as other parts of the code)
        manager_name_col = None
        if 'DENOM_SOCIAL' in filtered_df.columns:
            manager_name_col = 'DENOM_SOCIAL'
        elif 'Manager_Name_x' in filtered_df.columns:
            manager_name_col = 'Manager_Name_x'
        elif 'Manager_Name_y' in filtered_df.columns:
            manager_name_col = 'Manager_Name_y'
        elif 'Manager_Name' in filtered_df.columns:
            manager_name_col = 'Manager_Name'
        else:
            st.error(f"No manager name column found for geographic distribution! Available columns: {list(filtered_df.columns)}")
            return
        
        state_dist = filtered_df.groupby('UF').agg({
            'Total_Offshore_Assets_Market_Value': 'sum',
            manager_name_col: 'count'  # Use the correct manager name column for counting managers
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
