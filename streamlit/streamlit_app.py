import streamlit as st
import pandas as pd
import json
from snowflake.snowpark.context import get_active_session

session = get_active_session()

st.set_page_config(page_title="Customer 360 & Loyalty", layout="wide", page_icon="👤")

st.markdown("""
<style>
div[data-testid="stMetric"] {border: 1px solid #e0e0e0; border-radius: 8px; padding: 12px;}
</style>
""", unsafe_allow_html=True)

st.title("Customer 360 & Loyalty Hub")
st.caption("Retail/CPG Demo — Snowflake AI + Amazon Bedrock + SES + QuickSight")

with st.sidebar:
    st.markdown("### Personalization Engine")
    st.markdown("""
    Customer data stays in **Snowflake** — governed, no copies.
    **Cortex AI** scores sentiment. **Snowflake ML** predicts churn.
    **Amazon Bedrock** writes re-engagement messages.
    **Amazon SES** sends them automatically.
    """)
    st.divider()
    tier_filter = st.multiselect("Filter by Tier", ["Gold", "Silver", "Bronze"], default=["Gold", "Silver", "Bronze"])
    country_filter = st.multiselect("Filter by Country", ["Singapore", "Australia", "Japan", "Thailand", "India", "South Korea", "Philippines", "Indonesia", "Malaysia", "New Zealand", "Hong Kong", "Vietnam"])

tier_clause = "','".join(tier_filter) if tier_filter else "Gold','Silver','Bronze"
country_clause = "','".join(country_filter) if country_filter else ""
country_sql = f"AND COUNTRY IN ('{country_clause}')" if country_filter else ""

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Customer 360",
    "Segmentation",
    "Churn Risk",
    "Personalized Actions",
    "Ask Customer"
])

with tab1:
    st.header("Customer 360")

    kpi = session.sql(f"""
        SELECT
            COUNT(*) AS TOTAL_CUSTOMERS,
            ROUND(AVG(LIFETIME_SPEND), 2) AS AVG_CLV,
            ROUND(AVG(AVG_BASKET), 2) AS AVG_BASKET,
            ROUND(AVG(LOYALTY_POINTS), 0) AS AVG_POINTS,
            ROUND(AVG(AVG_FEEDBACK_RATING), 1) AS AVG_RATING,
            COUNT_IF(OPEN_TICKETS > 0) AS WITH_OPEN_TICKETS
        FROM RETAIL_CUSTOMER_360.CURATED.CUSTOMER_PROFILE
        WHERE TIER IN ('{tier_clause}') {country_sql}
    """).to_pandas()

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Customers", f"{kpi['TOTAL_CUSTOMERS'].iloc[0]:,}")
    c2.metric("Avg CLV", f"${kpi['AVG_CLV'].iloc[0]:,.0f}")
    c3.metric("Avg Basket", f"${kpi['AVG_BASKET'].iloc[0]:,.0f}")
    c4.metric("Avg Points", f"{kpi['AVG_POINTS'].iloc[0]:,.0f}")
    c5.metric("Avg Rating", f"{kpi['AVG_RATING'].iloc[0]}/5")
    c6.metric("Open Tickets", f"{kpi['WITH_OPEN_TICKETS'].iloc[0]:,}")

    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Customers by Tier")
        tier_df = session.sql(f"""
            SELECT TIER, COUNT(*) AS CNT FROM RETAIL_CUSTOMER_360.CURATED.CUSTOMER_PROFILE
            WHERE TIER IN ('{tier_clause}') {country_sql} GROUP BY TIER ORDER BY CNT DESC
        """).to_pandas()
        st.bar_chart(tier_df.set_index("TIER")["CNT"])
    with col_r:
        st.subheader("Avg CLV by Country")
        clv_df = session.sql(f"""
            SELECT COUNTRY, ROUND(AVG(LIFETIME_SPEND), 0) AS AVG_CLV
            FROM RETAIL_CUSTOMER_360.CURATED.CUSTOMER_PROFILE
            WHERE TIER IN ('{tier_clause}') {country_sql} GROUP BY COUNTRY ORDER BY AVG_CLV DESC LIMIT 12
        """).to_pandas()
        st.bar_chart(clv_df.set_index("COUNTRY")["AVG_CLV"])

    st.divider()
    st.subheader("Customer Lookup")
    search_name = st.text_input("Search by name or ID:", placeholder="e.g., Wei Chen or CUST-00001")
    if search_name:
        safe_search = search_name.replace("'", "''")
        profile = session.sql(f"""
            SELECT * FROM RETAIL_CUSTOMER_360.CURATED.CUSTOMER_PROFILE
            WHERE CUSTOMER_ID ILIKE '%{safe_search}%' OR FIRST_NAME ILIKE '%{safe_search}%' OR LAST_NAME ILIKE '%{safe_search}%'
            LIMIT 10
        """).to_pandas()
        if profile.empty:
            st.info("No customers found.")
        else:
            st.dataframe(profile, use_container_width=True)


with tab2:
    st.header("Customer Segmentation")

    seg_df = session.sql("""
        SELECT CUSTOMER_SEGMENT, SUM(CUSTOMER_COUNT) AS CUSTOMERS,
               ROUND(AVG(AVG_LIFETIME_SPEND), 0) AS AVG_CLV,
               ROUND(AVG(AVG_TXN_COUNT), 1) AS AVG_TXNS,
               ROUND(AVG(AVG_BASKET_SIZE), 0) AS AVG_BASKET,
               ROUND(AVG(AVG_DAYS_SINCE_LAST_TXN), 0) AS AVG_RECENCY
        FROM RETAIL_CUSTOMER_360.CURATED.CUSTOMER_SEGMENTS
        GROUP BY CUSTOMER_SEGMENT
        ORDER BY CUSTOMERS DESC
    """).to_pandas()

    st.dataframe(seg_df, use_container_width=True)

    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("Segment Distribution")
        st.bar_chart(seg_df.set_index("CUSTOMER_SEGMENT")["CUSTOMERS"])
    with col_r:
        st.subheader("Avg CLV by Segment")
        st.bar_chart(seg_df.set_index("CUSTOMER_SEGMENT")["AVG_CLV"])


with tab3:
    st.header("Churn Risk")
    st.markdown("**Snowflake ML CLASSIFICATION** — predicts churn risk for every customer. No Python, no SageMaker.")
    st.divider()

    churn_df = session.sql("""
        SELECT CUSTOMER_ID, CHURN_LABEL,
               PREDICTION:class::STRING AS PREDICTED,
               ROUND(PREDICTION:probability:CHURNED::FLOAT * 100, 1) AS CHURN_PROB_PCT,
               ROUND(PREDICTION:probability:AT_RISK::FLOAT * 100, 1) AS AT_RISK_PROB_PCT,
               LIFETIME_SPEND, TXN_COUNT, DAYS_SINCE_LAST_TXN, LOYALTY_POINTS, AVG_FEEDBACK_RATING, OPEN_TICKETS
        FROM RETAIL_CUSTOMER_360.ML.CHURN_PREDICTIONS
        ORDER BY CHURN_PROB_PCT DESC
    """).to_pandas()

    pred_counts = churn_df["PREDICTED"].value_counts()
    c1, c2, c3 = st.columns(3)
    c1.metric("Active", pred_counts.get("ACTIVE", 0))
    c2.metric("At Risk", pred_counts.get("AT_RISK", 0), delta="Monitor", delta_color="inverse")
    c3.metric("Churned", pred_counts.get("CHURNED", 0), delta="Action", delta_color="inverse")

    st.divider()
    st.subheader("Top At-Risk Customers")
    at_risk = churn_df[churn_df["PREDICTED"].isin(["AT_RISK", "CHURNED"])].head(30)
    if at_risk.empty:
        st.success("No high-risk customers detected.")
    else:
        st.dataframe(at_risk, use_container_width=True)


with tab4:
    st.header("Personalized Actions")
    st.markdown("Select a customer and generate a **personalized re-engagement message** using **Amazon Bedrock** (Claude).")
    st.divider()

    at_risk_list = session.sql("""
        SELECT cp.CUSTOMER_ID, cp.FIRST_NAME, cp.LAST_NAME, cp.TIER, cp.CITY, cp.COUNTRY,
               cp.LIFETIME_SPEND, cp.AVG_BASKET, cp.DAYS_SINCE_LAST_TXN, cp.LOYALTY_POINTS,
               cp.CUSTOMER_SEGMENT, cp.AVG_FEEDBACK_RATING
        FROM RETAIL_CUSTOMER_360.CURATED.CUSTOMER_PROFILE cp
        WHERE cp.CUSTOMER_SEGMENT IN ('At Risk', 'Hibernating', 'Needs Attention')
        ORDER BY cp.LIFETIME_SPEND DESC
        LIMIT 50
    """).to_pandas()

    if at_risk_list.empty:
        st.info("No at-risk customers to show.")
    else:
        labels = [f"{r['CUSTOMER_ID']} — {r['FIRST_NAME']} {r['LAST_NAME']} ({r['TIER']}, {r['CITY']}) CLV: ${float(r['LIFETIME_SPEND']):,.0f}" for _, r in at_risk_list.iterrows()]
        selected_label = st.selectbox("Select Customer", labels)
        idx = labels.index(selected_label)
        cust = at_risk_list.iloc[idx]

        col_l, col_r = st.columns([2, 1])
        with col_l:
            st.markdown(f"**Name:** {cust['FIRST_NAME']} {cust['LAST_NAME']}")
            st.markdown(f"**Tier:** {cust['TIER']} | **Segment:** {cust['CUSTOMER_SEGMENT']}")
            st.markdown(f"**Location:** {cust['CITY']}, {cust['COUNTRY']}")
            st.markdown(f"**Lifetime Spend:** ${float(cust['LIFETIME_SPEND']):,.2f} | **Avg Basket:** ${float(cust['AVG_BASKET']):,.2f}")
            st.markdown(f"**Last Purchase:** {int(cust['DAYS_SINCE_LAST_TXN'])} days ago")
        with col_r:
            st.metric("Loyalty Points", f"{int(cust['LOYALTY_POINTS']):,}")
            st.metric("Avg Rating", f"{float(cust['AVG_FEEDBACK_RATING']):.1f}/5")

        st.divider()
        if st.button("Generate Personalized NBA with Bedrock", type="primary", use_container_width=True):
            with st.spinner("Amazon Bedrock generating personalized next-best-action..."):
                safe_name = f"{cust['FIRST_NAME']} {cust['LAST_NAME']}"
                prompt = f"""You are a customer retention specialist for an APJ retail company.
Generate a personalized re-engagement strategy for this at-risk customer:

Name: {safe_name}
Tier: {cust['TIER']}
Segment: {cust['CUSTOMER_SEGMENT']}
Location: {cust['CITY']}, {cust['COUNTRY']}
Lifetime Spend: ${float(cust['LIFETIME_SPEND']):,.2f}
Days Since Last Purchase: {int(cust['DAYS_SINCE_LAST_TXN'])}
Loyalty Points: {int(cust['LOYALTY_POINTS'])}
Avg Feedback Rating: {float(cust['AVG_FEEDBACK_RATING']):.1f}/5

Respond in JSON with: recommended_action, offer_type, offer_details, email_subject, email_body (max 3 sentences), urgency (HIGH/MEDIUM/LOW), estimated_retention_probability"""

                safe_prompt = prompt.replace("'", "''").replace("\\", "\\\\")
                result = session.sql(f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-4-sonnet', '{safe_prompt}')
                """).collect()[0][0]

                try:
                    answer = str(result).strip()
                    if answer.startswith('"') and answer.endswith('"'):
                        answer = answer[1:-1]
                    answer = answer.replace("\\n", "\n").replace('\\"', '"')
                    if "```json" in answer:
                        answer = answer.split("```json")[1].split("```")[0].strip()
                    elif "```" in answer:
                        answer = answer.split("```")[1].split("```")[0].strip()
                    nba = json.loads(answer)

                    urgency_color = {"HIGH": "red", "MEDIUM": "orange", "LOW": "green"}.get(nba.get("urgency", ""), "gray")
                    st.markdown(f"### Urgency: :{urgency_color}[{nba.get('urgency', 'N/A')}]")

                    r1, r2, r3 = st.columns(3)
                    r1.metric("Action", nba.get("recommended_action", "N/A"))
                    r2.metric("Offer", nba.get("offer_type", "N/A"))
                    r3.metric("Retention Prob", nba.get("estimated_retention_probability", "N/A"))

                    st.info(f"**Offer:** {nba.get('offer_details', 'N/A')}")

                    st.divider()
                    st.markdown("### Email Preview")
                    st.markdown(f"**Subject:** {nba.get('email_subject', 'N/A')}")
                    body = nba.get("email_body", "N/A").replace('$', '\\$')
                    st.markdown(f"> {body}")
                except Exception as parse_err:
                    st.warning(f"Could not parse structured response. Raw output:")
                    st.markdown(str(result).replace('$', '\\$'))


with tab5:
    st.header("Ask Customer")
    st.markdown("Ask questions in **natural language** — powered by **Snowflake Cortex Agent** via Semantic View.")
    st.divider()

    sample_questions = [
        "How many Gold customers have churn risk?",
        "What is the average CLV by country?",
        "Which campaigns had the highest conversion rate?",
        "Show me customer segments with declining spend",
        "How many customers have open support tickets?",
    ]

    q_cols = st.columns(3)
    selected_q = None
    for i, q in enumerate(sample_questions):
        with q_cols[i % 3]:
            if st.button(q, key=f"agent_{i}", use_container_width=True):
                selected_q = q

    agent_input = st.text_input("Or ask your own question:", placeholder="e.g., Which segments are most at risk?", key="agent_q")
    agent_query = selected_q or agent_input

    if agent_query:
        st.markdown(f"**Question:** {agent_query}")
        with st.spinner("Querying Semantic View..."):
            try:
                safe_aq = agent_query.replace("'", "''")
                result = session.sql(f"""
                    SELECT SNOWFLAKE.CORTEX.COMPLETE('claude-4-sonnet',
                        'You are a customer analytics expert. Generate a SQL query against the semantic view RETAIL_CUSTOMER_360.AI.CUSTOMER_360_SEMANTIC_VIEW. Tables: profile (customer profiles), segments (segment aggregates), campaigns (campaign performance). Return ONLY the SQL.

                        Question: {safe_aq}')
                """).collect()[0][0]
                sql_text = str(result).strip()
                if sql_text.startswith('"'):
                    sql_text = sql_text[1:-1]
                sql_text = sql_text.replace("\\n", "\n")
                if "```sql" in sql_text:
                    sql_text = sql_text.split("```sql")[1].split("```")[0].strip()
                elif "```" in sql_text:
                    sql_text = sql_text.split("```")[1].split("```")[0].strip()

                with st.expander("Generated SQL", expanded=False):
                    st.code(sql_text, language="sql")

                try:
                    answer_df = session.sql(sql_text).to_pandas()
                    st.dataframe(answer_df, use_container_width=True)
                except Exception as sql_err:
                    st.warning(f"Could not execute generated SQL: {sql_err}")
            except Exception as e:
                st.error(f"Agent error: {e}")
