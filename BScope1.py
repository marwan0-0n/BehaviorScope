import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_lottie import st_lottie
import json
import sqlite3
import bcrypt
import base64
import html

import ml_pipeline

# ==========================================
# 1. Page Configuration & Database Setup
# ==========================================
st.set_page_config(layout="wide")


# Initialize SQLite database for user authentication
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users
                (id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                email TEXT UNIQUE,
                password TEXT,
                role TEXT)""")
    conn.commit()
    conn.close()


init_db()


# ==========================================
# 2. Authentication Functions (Security)
# ==========================================
def create_user(username, email, password, role):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    try:
        c.execute(
            "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
            (username, email, hashed, role),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def authenticate_user(email, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT username, password, role FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()
    if user:
        username, hashed_password, role = user
        
        if isinstance(hashed_password, str):
            hashed_password = hashed_password.encode("utf-8")
            
        if bcrypt.checkpw(password.encode("utf-8"), hashed_password):
            return username, role
    return None


# ==========================================
# 3. Global Configurations & Helper Functions
# ==========================================
SEGMENT_COLORS = {
    "Loyal": "#19c544",
    "At Risk": "#D8C602",
    "Champions": "#1D318B",
    "Lost": "#9B0505",
}
CLV_COLORS = {
    "Platinum": "#a55bff",
    "Gold": "#ffbf00",
    "Silver": "#C0C0C0",
    "Bronze": "#A86929",
}


def get_base64_of_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()


def load_lottiefile(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@st.cache_data
def load_data(filepath: str):
    return pd.read_csv(filepath)


def get_current_data(page_key, fallback_csv):
    if (
        "dynamic_data" in st.session_state
        and page_key in st.session_state["dynamic_data"]
    ):
        return st.session_state["dynamic_data"][page_key]
    try:
        return load_data(fallback_csv)
    except FileNotFoundError:
        st.error(
            f"⚠️ Missing default file: '{fallback_csv}'. Please put it back in the folder to view the default charts."
        )
        st.stop()


def set_blue_dynamic_bg():
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(-45deg, #224488, #214284, #204080, #1f3e7c, #1e3c78, #1d3a74, #1c3870, #1b366c, #1a3468, #193264, #183060, #172e5c, #162c58, #152a54, #142850, #13264c, #122448, #112244, #102040, #0f1e3c, #0e1c38, #0d1a34, #0c1830, #0b162c, #0a1428, #091224, #081020, #070e1c, #060c18, #050a14);
            background-size: 17% 17%;
            animation: gradient 200s ease-in-out infinite;
        }
        @keyframes gradient { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def local_css():
    st.markdown(
        """
    <style>
        .stApp { background-color: #ffffff; }
        [data-testid="stSidebar"] { background-color: #06131f; }
        header[data-testid="stHeader"] { background-color: #081b2a !important; }
        h1 { color: #99d5ff !important; }
        h2, h3, p { color: #FFFFFF !important; }
        div[data-baseweb="select"] > div { background-color: #0070C0; color: #ffffff; }
        .stSelectbox div { border-color: rgba(0,0,0,0); }
    </style>
    """,
        unsafe_allow_html=True,
    )


def render_metric_card(title, value, color="#19c544"):
    return f"<div style='text-align: center; background-color: rgba(25, 197, 68, 0.1); padding: 15px; border-radius: 12px; height: 120px; display: flex; flex-direction: column; justify-content: center; align-items: center;'><p style='color: white; font-size: 15px; margin-bottom: 5px;'>{title}</p><p style='color: {color}; font-size: 28px; font-weight: bold; margin: 0;'>{value}</p></div>"


def render_search_card(title, value, color):
    return f"<div style='text-align: center; background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); border-top: 7px solid {color}; height: 120px; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'><div style='color: {color} !important; font-size: 14px; margin-bottom: 5px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;'>{title}</div><div style='color: {color} !important; font-size: 24px; font-weight: bold; margin: 0; text-shadow: 0px 0px 8px {color};'>{value}</div></div>"


set_blue_dynamic_bg()
local_css()

# ==========================================
# 4. Login & Registration System
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    try:
        auth_logo = get_base64_of_image("BSLogo.png")
        st.markdown(
            f"""
            <div style='text-align: center; margin-top: 20px;'>
                <img src='data:image/png;base64,{auth_logo}' width='150' style='margin-bottom: 5px;'>
                <h1 style='font-size: 60px; margin: 0px;'>BehaviorScope</h1>
                <p style='color: #99d5ff; font-size: 18px; margin-top: 10px; margin-bottom: 40px;'>Securely access your AI-powered behavioral analytics dashboard</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except FileNotFoundError:
        st.markdown(
            "<h1 style='text-align: center; font-size: 55px; margin-bottom: 0px;'>BehaviorScope Authentication</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: #99d5ff; font-size: 18px; margin-top: 10px; margin-bottom: 40px;'>Securely access your AI-powered behavioral analytics dashboard</p>",
            unsafe_allow_html=True,
        )

    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

        with tab1:
            st.markdown(
                "<h3 style='text-align: center; margin-bottom: 20px;'>Welcome Back!</h3>",
                unsafe_allow_html=True,
            )
            # Email and password inputs with basic sanitation
            login_email = st.text_input(
                "Email", key="log_email", placeholder="name@company.com"
            )
            login_pass = st.text_input(
                "Password", type="password", key="log_pass", placeholder="••••••••"
            )
            st.write("")

            if st.button("Login", use_container_width=True):
                # ensure email is stripped of whitespace and lowercased for consistent authentication
                clean_email = login_email.strip().lower()
                user_info = authenticate_user(clean_email, login_pass)

                if user_info:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = user_info[0]
                    st.session_state["role"] = user_info[1]
                    st.rerun()
                else:
                    st.error("❌ Invalid Email or Password!")

        with tab2:
            st.markdown(
                "<h3 style='text-align: center; margin-bottom: 20px;'>Create Account</h3>",
                unsafe_allow_html=True,
            )
            # Input sanitation for registration fields
            reg_username = st.text_input(
                "Username", placeholder="e.g. Ammar Yasser"
            ).strip()
            reg_email = (
                st.text_input("Email", placeholder="name@company.com").strip().lower()
            )
            reg_pass = st.text_input(
                "Password",
                type="password",
                placeholder="Create a strong password (Min 5 chars)",
            )

            col_role, col_secret = st.columns(2)
            with col_role:
                reg_role = st.selectbox("Role", ["Manager", "Analyst"])

            with col_secret:
                # Authorization codes for each role to prevent unauthorized registrations
                secret_key = st.text_input(
                    "🔑 Authorization Code",
                    type="password",
                    placeholder="Enter your Authorization code",
                )

            st.write("")

            if st.button("Register", use_container_width=True):
                if reg_username and reg_email and reg_pass and secret_key:
                    if len(reg_pass) < 5:
                        st.error("❌ Password must be at least 5 characters long!")
                    else:
                        if reg_role == "Analyst" and secret_key != "ANA-2026":
                            st.error("❌ Invalid Analyst Invitation Code!")
                        elif reg_role == "Manager" and secret_key != "MGR-2026":
                            st.error("❌ Invalid Manager Invitation Code!")
                        else:
                            if create_user(reg_username, reg_email, reg_pass, reg_role):
                                st.success(
                                    "✅ Account created successfully! Please go to the Login tab."
                                )
                            else:
                                st.error("❌ Email is already registered!")
                else:
                    st.warning(
                        "⚠️ Please fill in all fields including the Invitation Code."
                    )

else:
    # ==========================================
    # 5. Main Application (If Logged In)
    # ==========================================

    # username is already sanitized during login, but we will escape it again before displaying to prevent any XSS issues in case of any edge cases
    safe_username = html.escape(st.session_state["username"])

    st.sidebar.markdown(
        f"<h3 style='color: #99d5ff;'>👋 Hello, {safe_username}</h3>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<p style='color: #a55bff; font-weight: bold;'>Role: {st.session_state['role']}</p>",
        unsafe_allow_html=True,
    )

    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state.pop("dynamic_data", None)
        st.rerun()

    st.sidebar.divider()

    if st.session_state["role"] == "Analyst":
        try:
            img_base64 = get_base64_of_image("Logo.png")
            st.sidebar.markdown(
                f"""
                <div style='display: flex; align-items: center; margin-bottom: 10px;'>
                    <img src='data:image/png;base64,{img_base64}' width='80' style='margin-right: 0px;'>
                    <h3 style='color: white; margin: 0;'>AI Batch Predictor</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )
        except FileNotFoundError:
            st.sidebar.markdown(
                "<h3 style='color: white;'>🧠 AI Batch Predictor</h3>",
                unsafe_allow_html=True,
            )

        st.sidebar.write("Upload the 4 prediction sheets at once:")

        uploaded_files = st.sidebar.file_uploader(
            "Upload CSVs (Segmentation, Churn, Next Purchase, CLV)",
            type=["csv"],
            accept_multiple_files=True,
        )

        if len(uploaded_files) > 0:
            st.sidebar.success(f"{len(uploaded_files)} Files Uploaded!")
            if st.sidebar.button("🚀 Predict & Generate Dashboards"):
                with st.spinner("AI Models are running... Please wait."):
                    try:
                        results_dict = ml_pipeline.process_uploaded_files(
                            uploaded_files
                        )
                        st.session_state["dynamic_data"] = results_dict
                        st.sidebar.success(
                            "✅ Predictions complete! Dashboards are ready."
                        )
                    except Exception as e:
                        st.sidebar.error(f"Error during prediction: {e}")
    else:
        st.sidebar.info(
            "📌 You are viewing as a **Manager**.\n\nData upload & AI execution are restricted to Analysts."
        )

    st.sidebar.divider()

    lottie_paths = ["Segm.json", "Churn.json", "CLV.json", "Next.json"]
    option = st.sidebar.selectbox(
        "Menu",
        [
            "Home",
            "Customer Segmentation",
            "Churn Prediction",
            "Customer Lifetime Value",
            "Next Purchase Prediction",
            "Search by ID",
        ],
    )

    # ----------------- HOME -----------------
    if option == "Home":
        try:
            home_logo = get_base64_of_image("BSLogo.png")
            st.markdown(
                f"""
                <div style='display: flex; align-items: center; margin-bottom: 10px;'>
                    <img src='data:image/png;base64,{home_logo}' width='95' style='margin-right: 20px;'>
                    <h1 style='font-size: 80px; margin: 0;'>BehaviorScope</h1>
                </div>
                """,
                unsafe_allow_html=True,
            )
        except FileNotFoundError:
            st.markdown(
                "<h1 style='font-size: 80px;'>BehaviorScope</h1>",
                unsafe_allow_html=True,
            )

        st.header("What is BehaviorScope?")
        st.write(
            "In today’s competitive business environment, companies generate massive amounts of customer data from multiple sources such as online purchases, feedback forms, and interactions. However, many organizations struggle to transform this raw data into meaningful insights that can help improve marketing strategies and customer retention. With the rise of Artificial Intelligence and Machine Learning, businesses can now analyze customer behavior patterns and predict future actions, enabling smarter decisions and personalized experiences. BehaviorScope focuses on developing an AI-powered system that helps companies understand and predict customer behavior to optimize their marketing and retention strategies."
        )
        st.header("Our 4 Main Crucial outputs:")
        st.divider()

        cols = st.columns(4)
        labels = [
            "Customer Segmentation",
            "Churn Prediction",
            "Customer Lifetime Value",
            "Next Purchase Prediction",
        ]
        for i in range(4):
            with cols[i]:
                lottie_json = load_lottiefile(lottie_paths[i])
                if lottie_json:
                    st_lottie(lottie_json, height=180, key=f"icon_{i}")
                st.markdown(
                    f"<p style='text-align: center; font-weight: bold;'>{labels[i]}</p>",
                    unsafe_allow_html=True,
                )

    # ----------------- CUSTOMER SEGMENTATION -----------------
    elif option == "Customer Segmentation":
        st.markdown(
            "<h1 style='font-size: 50px;'>Customer Segmentation</h1>",
            unsafe_allow_html=True,
        )
        st.write("Segmenting customers based on their past purchasing behavior.")
        st.divider()

        try:
            df_raw = get_current_data("segmentation", "customer_segmentation.csv")
            df_raw.columns = df_raw.columns.str.strip()

            if "Customer ID" in df_raw.columns:
                df_raw["Customer ID"] = (
                    df_raw["Customer ID"].astype(str).str.replace(".0", "", regex=False)
                )

            monetary_col = (
                "Monetary"
                if "Monetary" in df_raw.columns
                else "M"
                if "M" in df_raw.columns
                else df_raw.columns[3]
            )
            freq_col = (
                "Frequency"
                if "Frequency" in df_raw.columns
                else "F"
                if "F" in df_raw.columns
                else df_raw.columns[2]
            )
            rec_col = (
                "Recency"
                if "Recency" in df_raw.columns
                else "R"
                if "R" in df_raw.columns
                else df_raw.columns[1]
            )

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(
                    render_metric_card("Total Customers", f"{len(df_raw):,}"),
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    render_metric_card(
                        "Total Revenue", f"${df_raw[monetary_col].sum():,.0f}"
                    ),
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    render_metric_card(
                        "Avg Orders/Customer", f"{df_raw[freq_col].mean():.0f}"
                    ),
                    unsafe_allow_html=True,
                )
            with col4:
                st.markdown(
                    render_metric_card(
                        "Avg Recency (Days)", f"{df_raw[rec_col].mean():.0f}"
                    ),
                    unsafe_allow_html=True,
                )
            st.divider()

            df_counts = df_raw["Segment"].value_counts().reset_index()
            df_counts.columns = ["Segment", "Value"]

            fig = px.pie(
                df_counts,
                values="Value",
                names="Segment",
                title="Real-time Customer Segmentation",
                color="Segment",
                color_discrete_map=SEGMENT_COLORS,
            )
            fig.update_traces(
                textposition="inside",
                textinfo="percent+label",
                insidetextorientation="horizontal",
                pull=[0.03] * len(df_counts),
                marker=dict(line=dict(color="#FFFFFF", width=2)),
                textfont=dict(size=15, color="white"),
            )
            fig.update_layout(
                height=600,
                width=600,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white", size=14),
                showlegend=True,
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5
                ),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.divider()

            st.subheader("Behavioral Analysis")
            col_left, col_right = st.columns(2)

            with col_left:
                fig_scatter = px.scatter(
                    df_raw,
                    x=freq_col,
                    y=monetary_col,
                    color="Segment",
                    color_discrete_map=SEGMENT_COLORS,
                    opacity=0.7,
                    title="(Value View): Frequency vs. Monetary",
                    hover_data=[rec_col],
                )
                fig_scatter.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

            with col_right:
                fig_box = px.box(
                    df_raw,
                    x="Segment",
                    y=rec_col,
                    color="Segment",
                    color_discrete_map=SEGMENT_COLORS,
                    title="(Engagement View): Recency by Segment",
                )
                fig_box.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    showlegend=False,
                )
                st.plotly_chart(fig_box, use_container_width=True)

            st.divider()
            st.subheader("Targeting tool")
            st.write(
                "Select a customer segment to view and download their details for targeted campaigns."
            )

            selected_segment = st.selectbox(
                "Choose Segment to Target:", df_raw["Segment"].unique()
            )
            target_df = df_raw[df_raw["Segment"] == selected_segment]
            st.info(
                f"💡 Found **{len(target_df)}** customers in the **{selected_segment}** segment."
            )

            if "Customer ID" in target_df.columns:
                cols = ["Customer ID"] + [
                    col for col in target_df.columns if col != "Customer ID"
                ]
                st.dataframe(target_df[cols], hide_index=True, use_container_width=True)
            else:
                st.dataframe(target_df, hide_index=True, use_container_width=True)

            csv_export = target_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label=f"📥 Download {selected_segment} List (CSV)",
                data=csv_export,
                file_name=f"Targeting_{selected_segment}_Customers.csv",
                mime="text/csv",
            )

        except Exception as e:
            st.error(f"Error: {e}")

    # ----------------- CHURN PREDICTION -----------------
    elif option == "Churn Prediction":
        st.markdown(
            "<h1 style='font-size: 50px;'>Churn Prediction</h1>", unsafe_allow_html=True
        )
        st.write(
            "Analyzing customer behavior and identifying at-risk segments to take proactive action."
        )
        st.divider()

        try:
            df_churn = get_current_data("churn", "churn_prediction.csv")
            if "Customer ID" in df_churn.columns:
                df_churn["Customer ID"] = (
                    df_churn["Customer ID"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                )

            st.subheader("Overview Statistics")
            col1, col2 = st.columns(2)

            with col1:
                df_churn["Status"] = df_churn["is_churn"].map(
                    {0: "Retained", 1: "At Risk"}
                )
                churn_counts = df_churn["Status"].value_counts().reset_index()
                fig_pie = px.pie(
                    churn_counts,
                    values="count",
                    names="Status",
                    hole=0.5,
                    color="Status",
                    color_discrete_map={"Retained": "#19c544", "At Risk": "#9B0505"},
                )
                fig_pie.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white")
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col2:
                fig_hist = px.histogram(
                    df_churn,
                    x="churn_prediction_rate",
                    nbins=30,
                    color_discrete_sequence=["#99d5ff"],
                )
                fig_hist.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                    xaxis_title="Churn Probability (%)",
                    yaxis_title="Count",
                )
                st.plotly_chart(fig_hist, use_container_width=True)

            st.divider()
            st.subheader("Targeting tool")
            st.write(
                "Move the slider to identify customers within a specific risk range (e.g., 60% to 100%)."
            )

            risk_range = st.slider(
                "Select Risk Probability Range (%)", 0, 100, (60, 100), step=5
            )
            target_df = df_churn[
                (df_churn["churn_prediction_rate"] >= risk_range[0])
                & (df_churn["churn_prediction_rate"] <= risk_range[1])
            ]
            st.info(
                f"💡 Found **{len(target_df)}** customers matching this risk profile."
            )

            if not target_df.empty:
                cols_to_show = ["Customer ID"] + [
                    c
                    for c in ["Frequency", "Monetary", "churn_prediction_rate"]
                    if c in df_churn.columns
                ]
                st.dataframe(
                    target_df[cols_to_show].sort_values(
                        by="churn_prediction_rate", ascending=False
                    ),
                    hide_index=True,
                    use_container_width=True,
                )
                csv_data = target_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download List",
                    data=csv_data,
                    file_name=f"churn_risk_{risk_range[0]}_{risk_range[1]}.csv",
                    mime="text/csv",
                )
            else:
                st.warning(
                    "No customers found in this range. Try lowering the threshold."
                )

        except Exception as e:
            st.error(f"Error: {e}")

    # ----------------- CUSTOMER LIFETIME VALUE -----------------
    elif option == "Customer Lifetime Value":
        st.markdown(
            "<h1 style='font-size: 50px;'>Customer Lifetime Value (CLV)</h1>",
            unsafe_allow_html=True,
        )
        st.write(
            "Predicting the long-term value of customers and identifying high-priority segments."
        )
        st.divider()

        try:
            df_clv = get_current_data("clv", "clv_segment.csv")
            if "Customer ID" in df_clv.columns:
                df_clv["Customer ID"] = (
                    df_clv["Customer ID"].astype(str).str.replace(".0", "", regex=False)
                )

            avg_clv = df_clv["CLV"].mean()
            total_future_value = df_clv["CLV"].sum()
            top_segment = df_clv["CLV_segment"].mode()[0]

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    render_metric_card("Average CLV", f"${avg_clv:,.2f}"),
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    render_metric_card(
                        "Total Projected Value", f"${total_future_value:,.0f}"
                    ),
                    unsafe_allow_html=True,
                )
            with col3:
                seg_color = CLV_COLORS.get(top_segment, "white")
                st.markdown(
                    f"<div style='text-align: center; background-color: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 12px; height: 120px; display: flex; flex-direction: column; justify-content: center; align-items: center; border: 2px solid {seg_color};'><p style='color: white; font-size: 15px; margin-bottom: 5px;'>Top Segment</p><p style='color: {seg_color}; font-size: 28px; font-weight: bold; margin: 0;'>{top_segment}</p></div>",
                    unsafe_allow_html=True,
                )

            st.divider()
            col_left, col_right = st.columns(2)

            with col_left:
                st.subheader("Value Range per Segment")
                fig_seg = px.box(
                    df_clv,
                    x="CLV_segment",
                    y="CLV",
                    color="CLV_segment",
                    color_discrete_map=CLV_COLORS,
                    title="CLV Range Across Segments",
                )
                fig_seg.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                )
                st.plotly_chart(fig_seg, use_container_width=True)

            with col_right:
                st.subheader("Value vs. Risk Exposure")
                y_axis_col = (
                    "Churn_Prediction_Rate"
                    if "Churn_Prediction_Rate" in df_clv.columns
                    else "CLV"
                )
                fig_scatter = px.scatter(
                    df_clv,
                    x="CLV",
                    y=y_axis_col,
                    color="CLV_segment",
                    color_discrete_map=CLV_COLORS,
                    hover_data=["Customer ID"],
                    title="Value vs. Risk Exposure",
                )
                fig_scatter.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="white"),
                )
                st.plotly_chart(fig_scatter, use_container_width=True)

            st.divider()
            st.subheader("High-Value Strategic Targets")
            if "Churn_Risk" in df_clv.columns:
                st.write(
                    "Customers with high CLV but also high Churn Risk (Platinum Only)."
                )
                at_risk_vips = df_clv[
                    (df_clv["CLV_segment"] == "Platinum")
                    & (df_clv["Churn_Risk"] == "High Risk")
                ].sort_values(by="CLV", ascending=False)

                if not at_risk_vips.empty:
                    st.dataframe(
                        at_risk_vips[
                            ["Customer ID", "CLV_segment", "CLV", "Customer_Segment"]
                        ],
                        hide_index=True,
                        use_container_width=True,
                    )
                    csv_vips = at_risk_vips.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Download High-Risk VIP List",
                        data=csv_vips,
                        file_name="at_risk_platinum_customers.csv",
                        mime="text/csv",
                    )
                else:
                    st.success(
                        "No Platinum customers are currently in the High-Risk zone."
                    )
            else:
                st.info("Churn Risk data is required to view strategic targets.")

        except Exception as e:
            st.error(f"Error: {e}")

    # ----------------- NEXT PURCHASE PREDICTION -----------------
    elif option == "Next Purchase Prediction":
        st.markdown(
            "<h1 style='font-size: 50px;'>Next Purchase Prediction</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "Anticipate customer return dates to optimize inventory and marketing campaigns."
        )
        st.divider()

        try:
            df_next = get_current_data("next_purchase", "next_purchase_data.csv")
            if "Customer ID" in df_next.columns:
                df_next["Customer ID"] = (
                    df_next["Customer ID"]
                    .astype(str)
                    .str.replace(".0", "", regex=False)
                )

            avg_pred = df_next["predictions"].mean()
            min_pred = df_next["predictions"].min()
            total_customers = len(df_next)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    render_metric_card("Avg. Days to Return", f"{avg_pred:.0f} Days"),
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    render_metric_card(
                        "Shortest Expected Return", f"{min_pred:.0f} Days"
                    ),
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    render_metric_card(
                        "Total Customers Forecasted", f"{total_customers:,}"
                    ),
                    unsafe_allow_html=True,
                )

            st.divider()

            bins = [0, 30, 60, 90, 120, float("inf")]
            labels = [
                "0-30 Days",
                "31-60 Days",
                "61-90 Days",
                "91-120 Days",
                "120+ Days",
            ]
            df_next["Return_Timeframe"] = pd.cut(
                df_next["predictions"], bins=bins, labels=labels
            )

            timeframe_counts = df_next["Return_Timeframe"].value_counts().reset_index()
            timeframe_counts.columns = ["Timeframe", "Number of Customers"]

            st.subheader("Expected Return Timeline")
            custom_timeline_colors = [
                "#840c0c",
                "#71FF49",
                "#ffcb31",
                "#dd7600",
                "#317819",
            ]

            fig_bar = px.bar(
                timeframe_counts,
                x="Timeframe",
                y="Number of Customers",
                text="Number of Customers",
                color="Timeframe",
                color_discrete_sequence=custom_timeline_colors,
                title="When will customers buy again?",
            )
            fig_bar.update_layout(
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white"),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

            st.divider()

            col_left, col_right = st.columns(2)
            with col_left:
                if "Recency" in df_next.columns:
                    st.subheader("Recency vs. Next Purchase")
                    fig_bubble = px.scatter(
                        df_next,
                        x="Recency",
                        y="predictions",
                        color_continuous_scale="Viridis",
                        labels={
                            "predictions": "Predicted Days to Return",
                            "Recency": "Days Since Last Purchase",
                        },
                        hover_data=["Customer ID"],
                    )
                    fig_bubble.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="white"),
                    )
                    st.plotly_chart(fig_bubble, use_container_width=True)

            with col_right:
                if "labels" in df_next.columns:
                    st.subheader("Model Accuracy Check")
                    fig_scatter = px.scatter(
                        df_next,
                        x="labels",
                        y="predictions",
                        opacity=0.6,
                        color_discrete_sequence=["#19c544"],
                        labels={
                            "labels": "Actual Days",
                            "predictions": "Predicted Days",
                        },
                    )
                    max_val = max(df_next["labels"].max(), df_next["predictions"].max())
                    fig_scatter.add_shape(
                        type="line",
                        line=dict(dash="dash", color="white", width=1),
                        x0=0,
                        y0=0,
                        x1=max_val,
                        y1=max_val,
                    )
                    fig_scatter.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="white"),
                    )
                    st.plotly_chart(fig_scatter, use_container_width=True)

            st.divider()
            st.subheader("Targeting Tool")
            st.write("Filter customers based on when they are expected to return.")

            selected_bucket = st.selectbox(
                "Select a timeframe to view customers:", labels
            )
            target_customers = df_next[
                df_next["Return_Timeframe"] == selected_bucket
            ].sort_values(by="predictions")

            if not target_customers.empty:
                st.info(
                    f"💡 Found **{len(target_customers)}** customers expected to return in **{selected_bucket}**."
                )
                st.dataframe(
                    target_customers, hide_index=True, use_container_width=True
                )

                csv_data = target_customers.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label=f"📥 Download {selected_bucket} List",
                    data=csv_data,
                    file_name=f"upcoming_purchases_{selected_bucket}.csv",
                    mime="text/csv",
                )
            else:
                st.info("No customers found in this timeframe.")

        except Exception as e:
            st.error(f"Error processing Next Purchase data: {e}")

    # ----------------- SEARCH BY ID -----------------
    elif option == "Search by ID":
        st.markdown(
            "<h1 style='font-size: 50px;'>Search by Customer ID</h1>",
            unsafe_allow_html=True,
        )

        try:
            df = get_current_data("search_id", "Results ID.csv")
            df["Customer ID"] = df["Customer ID"].astype(str).str.strip()

            customer_id = st.text_input("Enter Customer ID")

            if st.button("Search"):
                if customer_id == "":
                    st.warning("Please enter a Customer ID")
                else:
                    # 🔴 حماية XSS لرقم العميل 🔴
                    safe_customer_id = html.escape(customer_id.strip())
                    customer = df[df["Customer ID"] == safe_customer_id]

                    if customer.empty:
                        st.error("Customer not found")
                    else:
                        customer = customer.iloc[0]
                        title_color = "#99d5ff"

                        st.markdown(
                            f"<h3 style='color:{title_color} !important; margin-bottom:20px; font-weight:700;'>Customer {safe_customer_id} Details</h3>",
                            unsafe_allow_html=True,
                        )

                        segment = str(customer.get("Segmentation", "N/A")).strip()
                        segment_color = SEGMENT_COLORS.get(segment, "#FFFFFF")

                        churn = customer.get("Churn", 0)
                        churn_color = "#DF2121" if churn == 1 else "#19c544"

                        clv = str(customer.get("CLV", "N/A")).strip()
                        clv_color = "#00bd12"
                        for level, color in CLV_COLORS.items():
                            if level.lower() in clv.lower():
                                clv_color = color
                                break

                        next_purchase = customer.get("Next_purchase_predictions", "N/A")
                        if isinstance(next_purchase, (int, float)):
                            next_purchase = f"{int(next_purchase)} days"
                        next_purchase_color = "#00bd12"

                        c1, c2, c3, c4 = st.columns(4)
                        with c1:
                            st.markdown(
                                render_search_card(
                                    "Segmentation", segment, segment_color
                                ),
                                unsafe_allow_html=True,
                            )
                        with c2:
                            st.markdown(
                                render_search_card("Churn Risk", churn, churn_color),
                                unsafe_allow_html=True,
                            )
                        with c3:
                            st.markdown(
                                render_search_card(
                                    "Next Purchase", next_purchase, next_purchase_color
                                ),
                                unsafe_allow_html=True,
                            )
                        with c4:
                            st.markdown(
                                render_search_card("CLV Status", clv, clv_color),
                                unsafe_allow_html=True,
                            )
                        st.divider()

        except Exception as e:
            st.error(f"Error: {e}")
