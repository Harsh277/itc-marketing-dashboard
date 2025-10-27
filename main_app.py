# File: main_app.py
import streamlit as st

# --- Page Config ---
st.set_page_config(
    page_title="Yukti AI - Home",
    page_icon="🤖",
    layout="wide"
)

# --- Header Section ---
with st.container():
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("https://i.imgur.com/EnduringValue.png", width=150) # ITC Logo
    with col2:
        st.title("Yukti AI Marketing Suite")
        st.markdown("An AI-Powered & Agentic Solution for Performance Marketing Optimization")

st.sidebar.success("Select a module from the sidebar to begin.")
st.divider()

# --- NEW: Two-Column Layout ---
col1, col2 = st.columns([2, 1], gap="large")

with col1:
    # --- Main App Description ---
    st.header("Welcome!")
    st.markdown(
        """
        This dashboard is an interactive Proof of Concept.  
        The **Yukti AI Suite** is designed to move beyond simple reporting and provide diagnostics, predictive planning, and agentic, real-time alerting.
        """
    )
    #    This dashboard is an interactive Proof of Concept. for the **ITC Interrobang Season 15** case study 
    
    st.subheader("Application Modules")
    # Using st.info, st.warning, st.success to create colored boxes for each module
    st.info(
        """
        **Diagnostics:** Analyze historical performance with a multi-layered approach, from a high-level geographical map down to AI-driven root cause analysis.
        """,
        icon="📈"
    )
    st.warning(
        """
        **Forecasting:** Use predictive modeling to forecast future trends and leverage the **AI Goal-Seeker** to generate optimal, data-driven budget plans.
        """,
        icon="🔮"
    )
    st.success(
        """
        **Live Alerts:** A simulation of a real-time monitoring agent. View a live "issue queue" and see a demo of the agent taking automated actions.
        """,
        icon="🚨"
    )

with col2:
    # --- Prominent Project & Team Details ---
    with st.container(border=True):
        st.subheader("Project Details")
        st.markdown("##### Made by: [Harsh Singh](https://www.linkedin.com/in/singh-harsh277/)") # Paste your URL here
#        st.markdown("#### ITC Interrobang Season 15")
#        st.divider()
        st.markdown("#### Team: *Acers*")


#with col2:
    # --- Prominent Project & Team Details ---
 #   with st.container(border=True):
 #       st.subheader("Project Details")
 #       st.markdown("##### Made by: Harsh Singh")
 #       st.markdown("#### ITC Interrobang Season 15")
 #       st.divider()
 #       st.markdown("#### Team: *Acers*")
        
        #st.markdown(
         #   """
          #  - *HARSH SINGH*
           # - *MAHAK YADAV*
            #- *SUDARSHAN JAIN*
            #"""

        #)







