import streamlit as st
import pandas as pd
import plotly.express as px
import time
import analytics_engine as ae
import db_query_service as db

st.set_page_config(page_title="AI Product Analyst Copilot", layout="wide", page_icon="🤖")
st.title("🤖 AI Product Analyst Copilot")
#---------------------------------------------------------------
#---- Initialize Session State---------------------
#---------------------------------------------------------------
if 'stage' not in st.session_state:
    st.session_state.stage= 0
if 'selected category' not in st.session_state:
    st.session_state.selected_category= None
if 'sql_query' not in st.session_state:
    st.session_state.sql_query= None
if 'sql_results' not in st.session_state:
    st.session_state.sql_results= None
if 'insights' not in st.session_state:
    st.session_state.insights=None
if 'mode' not in st.session_state:
    st.session_state.mode= "Demo"

def auto_advance_button(next_stage, text, delay=12):
    """ Creates a stable button with a separate countdown text to prevent click-dropping. """
    timer_placeholder = st.empty()
    
    # 1. The button text and key are now STATIC. Streamlit will instantly register clicks.
    if st.button(text, type="primary", width="stretch", key=f"btn_stage_{next_stage}"):
        st.session_state.stage = next_stage
        st.rerun()
        
    # 2. The countdown loop updates the text above the button, NOT the button itself.
    for i in range(delay, 0, -1):
        timer_placeholder.caption(f"⏳ Auto-advancing in {i} seconds...")
        time.sleep(1)
        
    # 3. If the loop finishes naturally, advance the stage.
    st.session_state.stage = next_stage
    st.rerun()

# ==========================================
# STAGE 0: LANDING & TRANSPARENCY
# ==========================================
st.markdown("This AI agent translates unstructured qualitative user feedback into deterministic SQL to find quantitative backend root causes.")
st.info("ℹ️ Architecture Notice: Because production databases are highly confidential and schema metrics vary violently between companies, this Copilot is engineered against a fixed, highly-normalized synthetic database (fintech_product.db).")

if st.session_state.stage== 0:
    st.markdown("### 📥 Raw Input Data Preview (raw_fintech_reviews.csv)")
    try:
        raw_df= pd.read_csv("raw_fintech_reviews.csv")
        st.dataframe(raw_df,width="stretch")
    except FileNotFoundError:
        st.warning("Ensure raw_fintech_reviews.csv is in your directory.")
    st.divider()

    col1,col2= st.columns(2)

    with col1:
        st.subheader("Option 1: Live AI Pipeline")
        st.markdown("Runs full LLM categorizaton line by line.")
        if st.button("🚀 Run Live Pipeline (~30 mins)",width="stretch"):
            st.session_state.mode= "Live"
            st.session_state.stage=1
            st.rerun()

    with col2:
        st.subheader("Option 2: Enterprise Demo Mode")
        st.markdown("Bypasses 30-min ETL bottleneck using pre-processsed data.")
        if st.button("⚡ Run Demo Mode (Instant)",width="stretch", type="primary"):
            st.session_state.mode= "Demo"
            st.session_state.stage= 1
            st.rerun()
# ==========================================
# STAGE 1: ETL PROCESSING
# ==========================================
elif st.session_state.stage== 1:
    st.subheader("🔄 Extract, Transform, Load (ETL) Pipeline")
    # --- PATH A: DEMO MODE ---
    if st.session_state.mode== "Demo":
        progress_bar= st.progress(0)
        status_text= st.empty()

        for i in range(100):
            time.sleep(0.02)
            progress_bar.progress(i+1)
            status_text.text(f"Demo Mode: Loading AI categorized batch....{i+1}%")
        st.success("✅ Categorization Complete!")
        time.sleep(1)
        st.session_state.stage= 2
        st.rerun()
   #----------PATH B LIVE MODE----------
    elif st.session_state.mode== "Live":
        try:
            raw_df = pd.read_csv("raw_fintech_reviews.csv")
            total_reviews = len(raw_df)
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            live_table = st.empty()

            status_text.info("⏳ Waking up LLM... Initiating maximum-speed inference.")
            
            categories = []
            display_data = []

            for index, row in raw_df.iterrows():
                review_text = row.get("content")
                
                # --- TRUE EXPONENTIAL BACKOFF LOOP ---
                max_retries = 6
                success = False
                
                for attempt in range(max_retries):
                    try:
                        category = ae.categorize_review(review_text)
                        success = True
                        break # It worked! Immediately exit the retry loop and move to the next row.
                        
                    except Exception as api_error:
                        if "429" in str(api_error) or "rate" in str(api_error).lower():
                            # Math: Wait 2s, 4s, 8s, 16s, 32s, 64s depending on the attempt
                            wait_time = 2 ** (attempt + 1) 
                            status_text.warning(f"🚦 API Limit Hit. Resuming in {wait_time}s... (Retry {attempt+1}/{max_retries})")
                            time.sleep(wait_time) 
                        else:
                            raise api_error
                
                # If the server is totally dead after 6 escalating retries, fail safely.
                if not success:
                    st.error("❌ The AI API is currently overloaded. Please use Enterprise Demo Mode instead.")
                    st.stop()
                # -------------------------------------

                categories.append(category)
                short_text= review_text[:75]+'...' if len(review_text)>75 else review_text
                display_data.append({"Raw Review": review_text, "AI Category": category})

                # Update UI
                progress_pct = int(((index+1)/total_reviews)*100)
                progress_bar.progress(progress_pct)
                status_text.text(f"Live Mode: Classifying review {index+1} of {total_reviews}....")
                
                # Only render the last 5 rows so the web browser doesn't lag
                live_table.dataframe(pd.DataFrame(display_data[-5:]), width="stretch")

            raw_df['ai_complaint_category']= categories
            raw_df.to_csv("categorized_reviews.csv", index=False)

            st.success("✅ Live Categorization of all 500 rows Complete!")
            time.sleep(2)
            st.session_state.stage= 2
            st.rerun()
            
        except Exception as e:
            st.error(f"Categorization Error in Pipeline: {e}")
            if st.button("Restart"):
                st.session_state.stage= 0
                st.rerun()
# ==========================================
# STAGE 2: CATEGORY SELECTOR
# ==========================================
if st.session_state.stage>= 2:
    try:
        df= pd.read_csv("categorized_reviews.csv")
        category_counts= df["ai_complaint_category"].value_counts().reset_index()
        category_counts.columns=['Category','Count']
        top_issue= category_counts["Category"].iloc[0]

        col_chart, col_actions= st.columns([2,1])
        with col_chart:

            fig= px.bar(category_counts,x= "Category",y= "Count", title="AI Categorized User Friction", color= "Category")
            st.plotly_chart(fig,width="stretch")
        
        with col_actions:
            st.subheader("🕵️‍♂️ Root Cause Diagnostics")
            st.markdown("Select a category to investigate backend telemetry:")

            categories_list= category_counts["Category"].tolist()

            st.session_state.selected_category= st.selectbox(
                "Friction Point:",
                categories_list,
                index=categories_list.index(top_issue)
            )

            if st.session_state.stage==2:
                st.markdown("<br>",unsafe_allow_html= True)
                auto_advance_button(3,f"🔍 Diagnose {st.session_state.selected_category}", delay= 15)
    except Exception as e:
        st.error(f"Faied to load categorization data: {e}")
# ==========================================
# STAGE 3: SQL GENERATION
# ==========================================

if st.session_state.stage>=3:
    st.divider()
    st.subheader(f"🧠 AI Copilot SQL Generation: {st.session_state.selected_category}")
    # Only hit the LLM if we haven't already generated the query for this session
    if st.session_state.sql_query is None:
        with st.spinner("Translating complaint theme into deterministic SQLite query..."): 
          # Call your Business Logic module
          st.session_state.sql_query= ae.generate_diagnostic_sql(st.session_state.selected_category)
    st.code(st.session_state.sql_query, language='sql',wrap_lines= True)

    if st.session_state.stage== 3:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            auto_advance_button(4,"⚙️ Execute Database Query",delay=12)

# ==========================================
# STAGE 4: EXECUTION & INSIGHTS
# ==========================================
if st.session_state.stage >= 4:
    st.divider()
    st.subheader("📈 Database Execution Result (fintech_product.db)")
    # Only hit the Database if we haven't already fetched the results
    if st.session_state.sql_results is None:
        with st.spinner("Querying fintech_product.db....."):
            st.session_state.sql_results= db.execute_sql_query("fintech_product.db",st.session_state.sql_query)
    
    st.dataframe(st.session_state.sql_results, width="stretch", hide_index= True)

    if st.session_state.stage==4:
        col1,col2,col3= st.columns([1,2,1])
        with col2:
            auto_advance_button(5,"📝 Generate Executive Summary", delay=12)

# ==========================================
# STAGE 5: FINAL BOARDROOM SUMMARY
# ==========================================
if st.session_state.stage == 5:
    st.divider()

    # Only hit the LLM if we haven't generated the insights yet
    if st.session_state.insights is None:
        with st.spinner("Analyzing telemetry metrics and generating business recommendations..."):
            st.session_state.insights= ae.generate_business_insight(st.session_state.selected_category, st.session_state.sql_results)

    st.markdown(st.session_state.insights)
    st.divider()
    col_a, col_b, col_c= st.columns([1,2,1])
    with col_b:
        if st.button("🔄 Diagnose Another Category",width="stretch"):
            st.session_state.stage=2
            st.session_state.sql_query= None
            st.session_state.sql_results= None
            st.session_state.insights= None
            st.session_state.selected_category= None
            st.rerun()
