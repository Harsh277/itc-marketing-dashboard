# File: pages/2_Forecaster.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from prophet import Prophet
from prophet.plot import plot_plotly, plot_components_plotly
import plotly.graph_objects as go

# --- Page Config ---
st.set_page_config(page_title="Campaign Forecaster", page_icon="🔮", layout="wide")

# --- Data Loading Function ---
@st.cache_data(ttl=600)
def load_data_from_gsheet(sheet_name):
    """Loads and processes data from the specified Google Sheet."""
    try:
        # Check if running in Streamlit Cloud
        if 'gcs' in st.secrets:
            creds_dict = st.secrets.gcs
            client = gspread.service_account_from_dict(creds_dict)
        else:
            client = gspread.service_account(filename='gcp_secrets.json')
        sheet = client.open(sheet_name).sheet1
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
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

# --- AI Budget Allocation Engine ---
@st.cache_data(ttl=600)
def allocate_budget_based_on_goal(goal, total_budget, df, scenario_filters):
    """
    Forecasts performance for each Ad Type and allocates budget based on a selected goal.
    """
    results = []
    
    # Filter data based on the scenario selected in the sidebar (city, product, sku)
    base_df = df[
        (df['City'] == scenario_filters['city']) &
        (df['Product'] == scenario_filters['product']) &
        (df['SKU'] == scenario_filters['sku'])
    ]
    
    ad_types_to_forecast = base_df['AdType'].unique()

    metric_map = {
        "Maximize overall ROAS": "Actual_ROAS",
        "Maximize Total Conversions": "Conversions",
        "Maximize New-to-Brand (NTB) Rate": "NTB_Rate"
    }
    metric_to_optimize = metric_map[goal]

    for ad_type in ad_types_to_forecast:
        ad_type_df = base_df[base_df['AdType'] == ad_type]
        
        if len(ad_type_df) < 5:
            continue # Skip if not enough data

        # Prepare and run forecast
        prophet_df = ad_type_df[['Date', metric_to_optimize]].rename(columns={'Date': 'ds', metric_to_optimize: 'y'})
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=7)
        forecast = m.predict(future)
        
        # Get the average predicted value for the next 7 days
        predicted_performance = forecast.iloc[-7:]['yhat'].mean()
        results.append({'AdType': ad_type, 'Predicted_Performance': predicted_performance})

    if not results:
        return None

    # Create a DataFrame from the results
    results_df = pd.DataFrame(results)
    
    # Allocate budget proportionally to the predicted performance score
    total_performance_score = results_df['Predicted_Performance'].sum()
    if total_performance_score > 0:
        results_df['Recommended_Budget'] = (results_df['Predicted_Performance'] / total_performance_score) * total_budget
    else:
        results_df['Recommended_Budget'] = total_budget / len(results_df)

    return results_df.sort_values(by="Recommended_Budget", ascending=False)

df = load_data_from_gsheet("ITC_Campaign_Data_Live")

# --- The Streamlit User Interface ---
st.title("🔮 Strategic Planning & Forecasting")

if not df.empty:
    st.sidebar.header("Select Scenario to Forecast")
    selected_city = st.sidebar.selectbox("Select City", options=sorted(df['City'].unique()), key="fc_city")
    selected_product = st.sidebar.selectbox("Select Product", options=sorted(df['Product'].unique()), key="fc_prod")
    available_skus = sorted(df[df['Product'] == selected_product]['SKU'].unique())
    selected_sku = st.sidebar.selectbox("Select SKU", options=available_skus, key="fc_sku")
    selected_ad_type = st.sidebar.selectbox("Select Ad Type", options=sorted(df['AdType'].unique()), key="fc_ad")
    metric_to_forecast = st.sidebar.selectbox(
        "Select Metric to Forecast:",
        options=['Actual_ROAS', 'Actual_CTR', 'Actual_CPC', 'Impressions', 'Conversions']
    )
    
    # --- Part 1: The Predictive Forecast ---
    st.header(f"Part 1: Predictive Forecast for {metric_to_forecast}")
    st.write(f"This forecast shows the expected performance for a single campaign combination if current trends continue.")
    st.write(f"**Scenario:** {selected_product} | {selected_sku} | {selected_city} | {selected_ad_type}")

    scenario_df = df[
        (df['City'] == selected_city) &
        (df['Product'] == selected_product) &
        (df['SKU'] == selected_sku) &
        (df['AdType'] == selected_ad_type)
    ]

    if len(scenario_df) < 10:
        st.warning("Not enough historical data for this specific scenario to generate a reliable forecast.")
    else:
        prophet_df = scenario_df[['Date', metric_to_forecast]].rename(columns={'Date': 'ds', metric_to_forecast: 'y'})
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=7)
        forecast = m.predict(future)

        st.markdown("#### Forecasted Trend")
        fig1 = plot_plotly(m, forecast)
        fig1.update_layout(title=f"{metric_to_forecast} Forecast", xaxis_title="Date", yaxis_title=metric_to_forecast)
        
        # --- NEW: Change the color of the historical data points ---
        fig1.update_traces(
            marker=dict(color='rgba(255,255,255,0.4)', size=3), # Light grey, semi-transparent
            selector=dict(mode='markers') # Apply only to the scatter plot trace
        )
        
        st.plotly_chart(fig1, use_container_width=True)

        st.markdown("#### Forecast Components")
        fig2 = plot_components_plotly(m, forecast)
        st.plotly_chart(fig2, use_container_width=True)
    
    st.divider()

    # --- Part 2: AI Goal-Seeker ---
    st.header("Part 2: AI-Powered Budget Allocator")
    st.write(f"Based on forecasts for **all Ad Types** for **{selected_product} ({selected_sku})** in **{selected_city}**, this tool recommends an optimal budget split to meet your primary goal.")

    goal = st.radio(
        "1. What is your primary goal for the next 7 days?",
        options=["Maximize overall ROAS", "Maximize Total Conversions", "Maximize New-to-Brand (NTB) Rate"],
        horizontal=True
    )

    budget = st.number_input("2. What is your total budget?", min_value=10000, value=100000, step=10000)

    if st.button("Generate AI Budget Plan", use_container_width=True, type="primary"):
        scenario_filters = {'city': selected_city, 'product': selected_product, 'sku': selected_sku}
        
        with st.spinner("AI is running forecasts and calculating the optimal budget..."):
            allocation_df = allocate_budget_based_on_goal(goal, budget, df, scenario_filters)

        if allocation_df is not None and not allocation_df.empty:
            st.subheader("Recommended Budget Allocation by Ad Type")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                fig_donut = go.Figure(data=[go.Pie(
                    labels=allocation_df['AdType'],
                    values=allocation_df['Recommended_Budget'],
                    hole=.4,
                    hovertemplate="<b>%{label}</b><br>Budget: ₹%{value:,.0f}<extra></extra>"
                )])
                fig_donut.update_layout(
                    showlegend=True, paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)', font=dict(color='white'),
                    margin=dict(l=10, r=10, t=50, b=10)
                )
                st.plotly_chart(fig_donut, use_container_width=True)

            with col2:
                st.dataframe(allocation_df.style.format({
                    "Predicted_Performance": "{:.2f}",
                    "Recommended_Budget": "₹{:,.0f}"
                }))
        else:
            st.error("Could not generate a budget plan. Not enough historical data for the selected product/SKU/city combination.")
else:
    st.error("Failed to load data. Please ensure your Google Sheet is set up correctly and shared.")
