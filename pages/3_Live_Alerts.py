# File: pages/3_🚨_Live_Alerts.py
import streamlit as st
import pandas as pd
import gspread
import time
import requests

# --- Page Config ---
st.set_page_config(page_title="Live Alerts", page_icon="🚨", layout="wide")

# --- NEW: Initialize Session State to track resolved items ---
if 'resolved_timestamps' not in st.session_state:
    st.session_state.resolved_timestamps = []

# --- Data Loading Function for Live Status ---
@st.cache_data(ttl=10)
def load_live_status(sheet_name):
    """Loads the last 5 pending issues from the queue."""
    try:
        client = gspread.service_account(filename='gcp_secrets.json')
        sheet = client.open(sheet_name).sheet1
        data = pd.DataFrame(sheet.get_all_records())
        
        # Filter for pending issues
        pending_issues = data[data['Status'] == 'Pending']
        return pending_issues
    except Exception as e:
        st.error(f"Error connecting to Live Issue Queue: {e}")
        return pd.DataFrame()

def resolve_issue(sheet_name, issue_row, is_auto_resolve=False):
    """
    Updates issue status in Google Sheet and triggers the n8n workflow if auto-resolving.
    """
    try:
        # Part 1: Trigger n8n webhook if on Auto-Resolve
        if is_auto_resolve:
            n8n_webhook_url = "https://harsholii.app.n8n.cloud/webhook/a66130ae-58a5-45c9-9562-8d1d52bf4024" # <-- IMPORTANT!
            
            payload = {
                "product": issue_row['Product'],
                "sku": issue_row['SKU'],
                "city": issue_row['City'],
                "issue_type": issue_row['Issue_Type'],
                "details": issue_row['Details']
            }
            requests.post(n8n_webhook_url, json=payload, timeout=10)

        # Part 2: Update the Google Sheet
        client = gspread.service_account(filename='gcp_secrets.json')
        sheet = client.open(sheet_name).sheet1
        cell = sheet.find(str(issue_row['Timestamp'])) 
        
        if cell:
            header_row = sheet.row_values(1)
            status_col_index = header_row.index('Status') + 1
            sheet.update_cell(cell.row, status_col_index, 'Resolved')
        return True
    except Exception as e:
        # Display the actual error to help with debugging
        st.error(f"Could not resolve issue in backend: {e}")
        return False

# --- The Streamlit User Interface ---
st.title("🚨 Live Issue Queue")
st.markdown("This module simulates a real-time agent monitoring for critical campaign issues.")

# Load all pending issues from the Google Sheet
all_pending = load_live_status("ITC_Issue_Queue")

# --- NEW: Filter out issues that were just resolved in this session ---
live_df = all_pending[~all_pending['Timestamp'].isin(st.session_state.resolved_timestamps)].tail(5)

auto_resolve = st.toggle("Enable AI Auto-Resolve", help="When enabled, the AI will automatically resolve issues and dispatch notifications.")
st.divider()

if not live_df.empty:
    st.subheader(f"{len(live_df)} Pending Issues Found")
    
    if auto_resolve:
        top_issue = live_df.iloc[0]
        
        st.info("🤖 AI Auto-Resolve is active. Processing top-priority issue...")
        time.sleep(1) 

        with st.container(border=True):
            status_placeholder = st.empty()
            
            if top_issue['Issue_Type'] == 'OOS':
                status_placeholder.warning(f"**Resolving OOS:** {top_issue['SKU']} in {top_issue['City']}. Pausing ads and dispatching restock email via n8n...")
            else:
                status_placeholder.warning(f"**Resolving Content Issue:** {top_issue['SKU']} in {top_issue['City']}. Flagging issue and dispatching ticket email via n8n...")
            
            time.sleep(2) 
            
            if resolve_issue("ITC_Issue_Queue", top_issue, is_auto_resolve=True):
                status_placeholder.success(f"**Resolved:** {top_issue['SKU']} in {top_issue['City']}. Moving to next issue...")
                # --- NEW: Add the resolved timestamp to our session's memory ---
                st.session_state.resolved_timestamps.append(top_issue['Timestamp'])
                time.sleep(1.5)
                st.rerun()
            else:
                status_placeholder.error("Failed to resolve issue in the backend.")
    
    else: # Manual mode
        # --- NEW: Reset the session memory when switching back to manual mode ---
        st.session_state.resolved_timestamps = []
        for index, row in live_df.iterrows():
            issue_type = row['Issue_Type']
            
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    if issue_type == 'OOS':
                        st.error(f"**High Priority: Out of Stock**")
                        st.markdown(f"**Product:** {row['Product']} - {row['SKU']}\n\n**City:** {row['City']}")
                    elif issue_type == 'Content':
                        st.warning(f"**Medium Priority: Content Discrepancy**")
                        st.markdown(f"**Product:** {row['Product']} - {row['SKU']}\n\n**Details:** {row['Details']}")
                with col2:
                    if st.button("Mark as Resolved", key=f"resolve_{row['Timestamp']}"):
                        if resolve_issue("ITC_Issue_Queue", row, is_auto_resolve=False):
                            st.toast(f"Issue for {row['SKU']} resolved!", icon="✅")
                            st.rerun()
else:
    st.success("✅ All clear! No pending issues found in the queue.")