# File: pages/1_Diagnostics.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
import numpy as np
from datetime import timedelta

# --- Page Config ---
st.set_page_config(page_title="Performance Diagnostics", page_icon="📈", layout="wide")

# --- City Coordinates Helper ---
CITY_COORDINATES = {
    "Mumbai": [19.0760, 72.8777],
    "Delhi": [28.7041, 77.1025],
    "Bengaluru": [12.9716, 77.5946],
    "Pune": [18.5204, 73.8567],
    "Jaipur": [26.9124, 75.7873],
    "Indore": [22.7196, 75.8577]
}

# --- Data Loading Function ---
# --- NEW: Final, Corrected Data Loading Function ---
# --- FINAL Data Loading Function for Deployment ---
@st.cache_data(ttl=600)
def load_data_from_gsheet(sheet_name):
    """
    Loads data from Google Sheets using a service account.
    Uses Streamlit's secrets for authentication when deployed.
    """
    try:
        # Check if running in Streamlit Cloud and use secrets (nested under 'connections')
        if "connections" in st.secrets and "gcs" in st.secrets["connections"]:
            creds_dict = dict(st.secrets["connections"]["gcs"])
            creds_dict["type"] = "service_account"  # Override to match gspread expectation
            client = gspread.service_account_from_dict(creds_dict)
        # Fallback to local file for local development
        else:
            client = gspread.service_account(filename='gcp_secrets.json')
        
        sheet = client.open(sheet_name).sheet1
        data = pd.DataFrame(sheet.get_all_records())
        
        # --- Data Cleaning ---
        df = pd.DataFrame(data)
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], format='%d-%b-%y')
        numeric_cols = [
            'Target_ROAS', 'Actual_ROAS', 'Target_CTR', 'Actual_CTR', 
            'Target_CPC', 'Actual_CPC', 'Impressions', 'Conversions', 'NTB_Rate'
        ]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('%', ''), errors='coerce')
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# --- Charting Helper Function ---
def create_sparkline(data, y_axis_col, target_value=None):
    """Creates a sparkline with conditional shading against a target."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data['Date'], y=data[y_axis_col], mode='lines', line=dict(color='#00b0f0', width=2), name="Actual"))
    if target_value is not None and not pd.isna(target_value):
        fig.add_hline(y=target_value, line_dash="dash", line_color="gray")
        fig.add_trace(go.Scatter(x=data['Date'], y=np.maximum(data[y_axis_col], target_value), mode='lines', line=dict(width=0), fillcolor='rgba(0, 255, 0, 0.2)', fill='tonexty'))
        fig.add_trace(go.Scatter(x=data['Date'], y=np.minimum(data[y_axis_col], target_value), mode='lines', line=dict(width=0), fillcolor='rgba(255, 0, 0, 0.2)', fill='tonexty'))
    else:
        fig.add_trace(go.Scatter(x=data['Date'], y=data[y_axis_col], mode='lines', line=dict(width=0), fillcolor='rgba(0, 176, 240, 0.2)', fill='tozeroy'))
    fig.update_layout(width=200, height=80, showlegend=False, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False))
    return fig

df = load_data_from_gsheet("ITC_Campaign_Data_Live")

# --- NEW/UPDATED: AI Insight Engine that calls n8n ---
import requests
import json

def generate_ai_insight(df, start_date, end_date):
    """Generates a deep, multi-step insight based on the provided dataframe."""
    if df.empty or len(df) < 1:
        return "Not enough data for this selection.", "", ""

    avg_roas = df['Actual_ROAS'].mean()
    target_roas = df['Target_ROAS'].mean()
    roas_performance = avg_roas / target_roas if target_roas and not pd.isna(target_roas) else 0
    date_str = f"For the period **{start_date.strftime('%d %b')} to {end_date.strftime('%d %b')}**"
    symptom_text = f"The average ROAS (**{avg_roas:.2f}**) is at **{roas_performance:.0%}** of its target (**{target_roas:.2f}**)."

    avg_cpc = df['Actual_CPC'].mean()
    target_cpc = df['Target_CPC'].mean()
    cpc_performance = target_cpc / avg_cpc if avg_cpc and not pd.isna(avg_cpc) else 0 
    avg_ctr = df['Actual_CTR'].mean()
    target_ctr = df['Target_CTR'].mean()
    ctr_performance = avg_ctr / target_ctr if target_ctr and not pd.isna(target_ctr) else 0

    cause_text = ""
    if roas_performance < 0.95:
        if cpc_performance < 0.95:
            cause_text = f"The primary cause is a high Cost Per Click (CPC), which is only **{cpc_performance:.0%}** cost-efficient. CTR performance is adequate."
        elif ctr_performance < 0.95:
            cause_text = f"The primary cause is a low Click-Through Rate (CTR), at **{ctr_performance:.0%}** of target. This suggests the ad creative may not be resonating."
        else:
            cause_text = "Underlying metrics (CPC, CTR) are on target. Low ROAS may be due to a poor conversion rate post-click."
    else:
        cause_text = "Performance is strong across key metrics."
        
    recommendation_text = ""
    if roas_performance < 0.95:
        recommendation_text = "Consider reallocating budget to higher-performing creatives or ad types to improve ROAS."
    else:
        recommendation_text = "Performance is strong. Consider increasing budget for the highest-performing campaigns to maximize returns."
    
    return symptom_text, cause_text, recommendation_text

df = load_data_from_gsheet("ITC_Campaign_Data_Live")


# --- The Streamlit User Interface ---
st.title("📈 Mission Control: Diagnostics")
st.markdown("A high-level overview of campaign performance across geographies.")
st.divider()

if not df.empty:
    st.sidebar.header("Filter Scenario")
    default_start_date = df['Date'].max() - pd.Timedelta(days=29)
    default_end_date = df['Date'].max()
    date_range = st.sidebar.date_input("Select Date Range", value=(default_start_date, default_end_date), min_value=df['Date'].min(), max_value=df['Date'].max())
    
    # --- FILTERS UPDATED WITH MORE GRANULARITY ---
    city_list = ["All Cities"] + sorted(df['City'].unique())
    selected_city = st.sidebar.selectbox("Select City", options=city_list)
    
    product_list = ["All Products"] + sorted(df['Product'].unique())
    selected_product = st.sidebar.selectbox("Select Product", options=product_list)
    
    if selected_product != "All Products":
        sku_list = ["All SKUs"] + sorted(df[df['Product'] == selected_product]['SKU'].unique())
    else:
        sku_list = ["All SKUs"] + sorted(df['SKU'].unique())
    selected_sku = st.sidebar.selectbox("Select SKU", options=sku_list)

    time_list = ["All Day"] + sorted(df['Time'].unique())
    selected_time = st.sidebar.selectbox("Select Time Slot", options=time_list)

    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range)
        
        # --- MASTER FILTERING LOGIC FOR THE ENTIRE PAGE ---
        page_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        if selected_city != "All Cities":
            page_df = page_df[page_df['City'] == selected_city]
        if selected_product != "All Products":
            page_df = page_df[page_df['Product'] == selected_product]
        if selected_sku != "All SKUs":
            page_df = page_df[page_df['SKU'] == selected_sku]
        if selected_time != "All Day":
            page_df = page_df[page_df['Time'] == selected_time]

        # --- Tier 1: The Geographical Map ---
        st.subheader(f"City Performance Overview ({start_date.strftime('%d %b')} to {end_date.strftime('%d %b')})")
        map_base_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
        # Map is filtered by product/sku/time but NOT by city
        if selected_product != "All Products": map_base_df = map_base_df[map_base_df['Product'] == selected_product]
        if selected_sku != "All SKUs": map_base_df = map_base_df[map_base_df['SKU'] == selected_sku]
        if selected_time != "All Day": map_base_df = map_base_df[map_base_df['Time'] == selected_time]
        
        city_performance = map_base_df.groupby('City').agg(Actual_ROAS=('Actual_ROAS', 'mean'), Target_ROAS=('Target_ROAS', 'mean'), Total_Conversions=('Conversions', 'sum')).reset_index()
        city_performance['Performance'] = (city_performance['Actual_ROAS'] / city_performance['Target_ROAS']).fillna(1)
        city_performance['lat'] = city_performance['City'].map(lambda city: CITY_COORDINATES.get(city, [None, None])[0])
        city_performance['lon'] = city_performance['City'].map(lambda city: CITY_COORDINATES.get(city, [None, None])[1])
        min_size, max_size = 20, 40 
        min_conv, max_conv = city_performance['Total_Conversions'].min(), city_performance['Total_Conversions'].max()
        if max_conv == min_conv: city_performance['Bubble_Size'] = max_size
        else: city_performance['Bubble_Size'] = ((city_performance['Total_Conversions'] - min_conv) / (max_conv - min_conv)) * (max_size - min_size) + min_size
        fig_map = go.Figure(go.Scattergeo(lon=city_performance['lon'], lat=city_performance['lat'], text=city_performance['City'] + '<br>Performance vs Target: ' + (city_performance['Performance']).apply(lambda p: f"{p:.0%}"), mode='markers', marker=dict(color=city_performance['Performance'], colorscale='RdYlGn', cmin=0.7, cmax=1.3, colorbar=dict(title='ROAS vs. Target'), size=city_performance['Bubble_Size'], opacity=1.0, sizemode='diameter', line=dict(width=1, color='rgba(255,255,255,0.5)'))))
        fig_map.update_layout(title_text='City Performance: ROAS (Color) vs. Conversions (Size)', geo=dict(scope='asia', landcolor='rgb(50, 50, 50)', oceancolor='rgb(25, 25, 35)', showocean=True, showland=True, lataxis_range=[6, 30], lonaxis_range=[68, 90], subunitcolor='rgb(70, 70, 70)'), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'), margin={"r":0,"t":40,"l":0,"b":0}, height=500)
        st.plotly_chart(fig_map, use_container_width=True)
        st.divider()

        # --- Tier 2: Performance Summary Cards ---
        st.subheader(f"Performance Summary")
        available_metrics = ["Average ROAS", "Total Conversions", "Average CPC", "Average CTR", "Total Impressions", "Average NTB Rate"]
        selected_metrics = st.multiselect("Select summary metrics to display:", options=available_metrics, default=["Average ROAS", "Total Conversions", "Average CPC"])
        if selected_metrics:
            period_duration = (end_date - start_date).days
            prev_start_date = start_date - timedelta(days=period_duration + 1)
            prev_end_date = start_date - timedelta(days=1)
            prev_period_df = df[(df['Date'] >= prev_start_date) & (df['Date'] <= prev_end_date)]
            if selected_city != "All Cities": prev_period_df = prev_period_df[prev_period_df['City'] == selected_city]
            if selected_product != "All Products": prev_period_df = prev_period_df[prev_period_df['Product'] == selected_product]
            if selected_sku != "All SKUs": prev_period_df = prev_period_df[prev_period_df['SKU'] == selected_sku]
            if selected_time != "All Day": prev_period_df = prev_period_df[prev_period_df['Time'] == selected_time]
            
            cols = st.columns(len(selected_metrics))
            for i, metric in enumerate(selected_metrics):
                with cols[i]:
                    if metric == "Average ROAS":
                        avg_roas = page_df['Actual_ROAS'].mean()
                        prev_avg_roas = prev_period_df['Actual_ROAS'].mean()
                        roas_delta = 0 if pd.isna(prev_avg_roas) or prev_avg_roas == 0 else ((avg_roas - prev_avg_roas) / prev_avg_roas) * 100
                        target_roas = page_df['Target_ROAS'].mean()
                        st.metric(label=f"Average ROAS", value=f"{avg_roas:.2f}", delta=f"{roas_delta:.1f}%")
                        daily_data = page_df.groupby('Date')['Actual_ROAS'].mean().reset_index()
                        if not daily_data.empty: st.plotly_chart(create_sparkline(daily_data, 'Actual_ROAS', target_roas), use_container_width=True)

                    elif metric == "Total Conversions":
                        total_conv = page_df['Conversions'].sum()
                        prev_total_conv = prev_period_df['Conversions'].sum()
                        conv_delta = 0 if pd.isna(prev_total_conv) or prev_total_conv == 0 else ((total_conv - prev_total_conv) / prev_total_conv) * 100
                        st.metric(label="Total Conversions", value=f"{total_conv:,}", delta=f"{conv_delta:.1f}%")
                        daily_data = page_df.groupby('Date')['Conversions'].sum().reset_index()
                        if not daily_data.empty: st.plotly_chart(create_sparkline(daily_data, 'Conversions'), use_container_width=True)
                        
                    elif metric == "Average CPC":
                        avg_cpc = page_df['Actual_CPC'].mean()
                        prev_avg_cpc = prev_period_df['Actual_CPC'].mean()
                        cpc_delta = 0 if pd.isna(prev_avg_cpc) or prev_avg_cpc == 0 else ((avg_cpc - prev_avg_cpc) / prev_avg_cpc) * 100
                        target_cpc = page_df['Target_CPC'].mean()
                        st.metric(label=f"Average CPC", value=f"₹{avg_cpc:.2f}", delta=f"{cpc_delta:.1f}%", delta_color="inverse")
                        daily_data = page_df.groupby('Date')['Actual_CPC'].mean().reset_index()
                        if not daily_data.empty: st.plotly_chart(create_sparkline(daily_data, 'Actual_CPC', target_cpc), use_container_width=True)

                    elif metric == "Average CTR":
                        avg_ctr = page_df['Actual_CTR'].mean()
                        prev_avg_ctr = prev_period_df['Actual_CTR'].mean()
                        ctr_delta = 0 if pd.isna(prev_avg_ctr) or prev_avg_ctr == 0 else ((avg_ctr - prev_avg_ctr) / prev_avg_ctr) * 100
                        target_ctr = page_df['Target_CTR'].mean()
                        st.metric(label=f"Average CTR", value=f"{avg_ctr:.2f}%", delta=f"{ctr_delta:.1f}%")
                        daily_data = page_df.groupby('Date')['Actual_CTR'].mean().reset_index()
                        if not daily_data.empty: st.plotly_chart(create_sparkline(daily_data, 'Actual_CTR', target_ctr), use_container_width=True)
                        
                    elif metric == "Total Impressions":
                        total_imp = page_df['Impressions'].sum()
                        prev_total_imp = prev_period_df['Impressions'].sum()
                        imp_delta = 0 if pd.isna(prev_total_imp) or prev_total_imp == 0 else ((total_imp - prev_total_imp) / prev_total_imp) * 100
                        st.metric(label="Total Impressions", value=f"{total_imp:,}", delta=f"{imp_delta:.1f}%")
                        daily_data = page_df.groupby('Date')['Impressions'].sum().reset_index()
                        if not daily_data.empty: st.plotly_chart(create_sparkline(daily_data, 'Impressions'), use_container_width=True)

                    elif metric == "Average NTB Rate":
                        avg_ntb = page_df['NTB_Rate'].mean()
                        prev_avg_ntb = prev_period_df['NTB_Rate'].mean()
                        ntb_delta = 0 if pd.isna(prev_avg_ntb) or prev_avg_ntb == 0 else ((avg_ntb - prev_avg_ntb) / prev_avg_ntb) * 100
                        st.metric(label="Average NTB Rate", value=f"{avg_ntb:.1f}%", delta=f"{ntb_delta:.1f}%")
                        daily_data = page_df.groupby('Date')['NTB_Rate'].mean().reset_index()
                        if not daily_data.empty: st.plotly_chart(create_sparkline(daily_data, 'NTB_Rate'), use_container_width=True)

        # --- NEW: Tier 3: Deep AI Insights ---
        st.divider()
        # --- Tier 3: Deep AI Insights ---
        st.subheader("🤖 Deep AI Insights")
        symptom, cause, recommendation = generate_ai_insight(page_df, start_date, end_date)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            with st.container(border=True):
                st.markdown("##### ⚠️ Primary Symptom")
                st.markdown(symptom)
        with col2:
            with st.container(border=True):
                st.markdown("##### 🔎 Root Cause Analysis")
                st.warning(cause)
        with col3:
            with st.container(border=True):
                st.markdown("##### 💡 Actionable Recommendation")
                st.success(recommendation)
    else:
        st.warning("Please select a valid date range.")
else:
    st.error("Failed to load data.")




