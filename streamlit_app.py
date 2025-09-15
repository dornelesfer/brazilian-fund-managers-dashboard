#!/usr/bin/env python3
"""
Streamlit App for Brazilian Fund Managers Offshore Assets Analysis
Interactive dashboard with filtering capabilities
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import os

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
def load_data():
    """Load and prepare the data"""
    try:
        # Load the main dataset
        df = pd.read_csv('offshore_managers_analysis.csv')
        
        # Convert columns to appropriate types
        df['Total_Offshore_Assets_Market_Value'] = pd.to_numeric(df['Total_Offshore_Assets_Market_Value'], errors='coerce')
        df['Total_Offshore_Assets_Cost_Value'] = pd.to_numeric(df['Total_Offshore_Assets_Cost_Value'], errors='coerce')
        df['Number_of_Funds'] = pd.to_numeric(df['Number_of_Funds'], errors='coerce')
        df['Percentage_of_Total'] = pd.to_numeric(df['Percentage_of_Total'], errors='coerce')
        
        # Fill missing values
        df['Cidade'] = df['Cidade'].fillna('N/A')
        df['UF'] = df['UF'].fillna('N/A')
        df['DENOM_SOCIAL'] = df['DENOM_SOCIAL'].fillna('N/A')
        
        # Add a date column (assuming current data is from August 2025)
        df['Data_Referencia'] = pd.to_datetime('2025-08-31')
        
        return df
    except FileNotFoundError:
        st.error("Data file not found. Please run the analysis script first.")
        return pd.DataFrame()

def format_currency(value):
    """Format currency values"""
    if pd.isna(value) or value == 0:
        return "R$ 0"
    return f"R$ {value:,.0f}"

def format_percentage(value):
    """Format percentage values"""
    if pd.isna(value):
        return "0.0%"
    return f"{value:.1f}%"

def main():
    # Header
    st.markdown('<h1 class="main-header">🇧🇷 Brazilian Fund Managers - Offshore Assets Analysis</h1>', unsafe_allow_html=True)
    
    # Load data
    df = load_data()
    
    if df.empty:
        st.stop()
    
    # Debug info
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Debug Info**")
    st.sidebar.write(f"Total records loaded: {len(df)}")
    st.sidebar.write(f"Managers with assets: {len(df[df['Total_Offshore_Assets_Market_Value'] > 0])}")
    st.sidebar.write(f"Total assets: R$ {df['Total_Offshore_Assets_Market_Value'].sum():,.0f}")
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Date filter
    st.sidebar.subheader("📅 Date Range")
    min_date = df['Data_Referencia'].min().date()
    max_date = df['Data_Referencia'].max().date()
    
    date_range = st.sidebar.date_input(
        "Select date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # State filter
    st.sidebar.subheader("🗺️ Location Filters")
    states = ['All'] + sorted(df['UF'].unique().tolist())
    selected_state = st.sidebar.selectbox("State (UF)", states)
    
    # City filter (dependent on state)
    if selected_state != 'All':
        cities = ['All'] + sorted(df[df['UF'] == selected_state]['Cidade'].unique().tolist())
    else:
        cities = ['All'] + sorted(df['Cidade'].unique().tolist())
    
    selected_city = st.sidebar.selectbox("City", cities)
    
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
    
    # Date filter
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['Data_Referencia'].dt.date >= start_date) &
            (filtered_df['Data_Referencia'].dt.date <= end_date)
        ]
    
    # State filter
    if selected_state != 'All':
        filtered_df = filtered_df[filtered_df['UF'] == selected_state]
    
    # City filter
    if selected_city != 'All':
        filtered_df = filtered_df[filtered_df['Cidade'] == selected_city]
    
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
        fig_bar = px.bar(
            top_10,
            x='Total_Offshore_Assets_Market_Value',
            y='Administrador',
            orientation='h',
            title="Top 10 Managers by Offshore Assets",
            labels={
                'Total_Offshore_Assets_Market_Value': 'Offshore Assets (R$)',
                'Administrador': 'Manager'
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
                names='Administrador',
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
            'Administrador': 'count'
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
    
    # Display table
    display_df = sorted_df[['Administrador', 'Cidade', 'UF', 'Total_Offshore_Assets_Market_Value', 
                           'Number_of_Funds', 'Percentage_of_Total']].copy()
    
    # Format the display
    display_df['Rank'] = range(1, len(display_df) + 1)
    display_df['Offshore Assets'] = display_df['Total_Offshore_Assets_Market_Value'].apply(format_currency)
    display_df['Market Share'] = display_df['Percentage_of_Total'].apply(format_percentage)
    display_df['Funds'] = display_df['Number_of_Funds'].astype(int)
    
    # Reorder columns
    display_df = display_df[['Rank', 'Administrador', 'Cidade', 'UF', 'Offshore Assets', 
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
        file_name=f"offshore_managers_filtered_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>Data Source: CVM (Comissão de Valores Mobiliários) | 
        Analysis Date: August 2025 | 
        Generated by: Offshore Assets Analysis Tool</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
