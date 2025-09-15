# 🇧🇷 Brazilian Fund Managers - Offshore Assets Dashboard

A comprehensive Streamlit dashboard for analyzing Brazilian fund managers with the most offshore assets, built using CVM (Comissão de Valores Mobiliários) data.

## 📊 Features

- **Dynamic Data Loading**: Access data on-demand by selecting month and year
- **Manager Rankings**: Top fund managers by offshore assets with market share analysis
- **Geographic Analysis**: Location-based filtering and visualization by state and city
- **Interactive Filtering**: Filter by investment types, asset ranges, and geographic location
- **Real-time Analytics**: Live charts and metrics with Plotly visualizations
- **Data Export**: Download filtered results as CSV

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- pip

### Installation

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd brazilian-fund-managers-dashboard
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python run_dynamic_app.py
```

4. **Open your browser**
Navigate to `http://localhost:8501`

## 📁 Project Structure

```
├── streamlit_app_dynamic.py    # Main Streamlit application
├── run_dynamic_app.py          # Application launcher
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── data/                      # Downloaded CVM data (auto-created)
```

## 🔧 Configuration

The application automatically downloads data from CVM sources:
- **CDA Data**: `https://dados.cvm.gov.br/dados/FI/DOC/CDA/DADOS/`
- **Fund Registry**: `https://dados.cvm.gov.br/dados/FI/CAD/DADOS/`
- **Manager Registry**: `https://dados.cvm.gov.br/dados/ADM_CART/CAD/DADOS/`

## 📈 Data Sources

- **CDA (Cadastro de Administradores)**: Offshore asset positions (Bloco 7)
- **Fund Registry**: Fund-to-manager relationships
- **Manager Registry**: Manager location and company information

## 🎯 Key Metrics

- Total offshore assets under management
- Manager rankings by offshore assets
- Geographic distribution of managers
- Market share analysis
- Investment type breakdown

## 🔍 Filtering Options

- **Time Period**: Select specific month and year
- **Investment Types**: Fundos Offshore, Ação ordinária, DR, etc.
- **Geographic**: Filter by state (UF) and city (MUN)
- **Asset Range**: Minimum offshore assets threshold

## 📊 Visualizations

- **Bar Charts**: Top managers by offshore assets
- **Pie Charts**: Market share distribution
- **Geographic Maps**: State-wise asset distribution
- **Interactive Tables**: Sortable and filterable data

## 🛠️ Technical Details

- **Framework**: Streamlit
- **Data Processing**: Pandas
- **Visualizations**: Plotly Express
- **Data Sources**: CVM APIs
- **Matching Algorithm**: Name-based matching for manager identification

## 📝 Data Processing

The application uses a sophisticated ETL process:
1. **Extract**: Download data from CVM sources
2. **Transform**: Clean and standardize CNPJ formats, match managers by name
3. **Load**: Create interactive visualizations and analytics

## 🔒 Data Privacy

All data is publicly available from CVM (Brazilian Securities Commission) and is used for analytical purposes only.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 📞 Support

For questions or issues, please open an issue in the GitHub repository.

---

**Built with ❤️ for Brazilian financial market analysis**