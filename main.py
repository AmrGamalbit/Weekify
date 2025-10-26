import streamlit as st
import os
import pandas as pd
import numpy as np
import plotly.express as px
from PIL import Image
import io
import base64

deafult_color = "#31333f"
st.set_page_config(
    page_title="Planner",
    page_icon= "🗃️",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "https://Github.com",
        "About": "#about"
    }
)


acv_data_path = os.path.join(os.getcwd(), "static", "acv.csv")
sess_data_path = os.path.join(os.getcwd(), "static", "sess.csv")
free_hours_path = os.path.join(os.getcwd(), "static", "free_hours.csv")
st.title("Planner")

st.header("Add Category")
days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Sidebar initialization
st.sidebar.title("Settings")
st.sidebar.subheader("Select a Preferred Background")
img_uploaded = st.sidebar.file_uploader(label="Add a Cover Image", type=["jpg", "png"], label_visibility="hidden")
bg_options = ["Full Screen", "Cover"]
selection = st.sidebar.segmented_control(
    "Mode", bg_options, selection_mode="single"
)
if img_uploaded is not None:
    image = Image.open(img_uploaded)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode()
    if selection == "Full Screen":

        page_element= f"""
        <style>
        [data-testid="stAppViewContainer"]{{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        }}
        </style>
        """

        st.markdown(page_element, unsafe_allow_html=True)
    else:
        st.image(img_uploaded)
first_day = st.sidebar.selectbox(
    label="Select first day of the week",
    options = days
)
first_day_index = days.index(first_day)
days = days[first_day_index:] + days[:first_day_index]

refresh_btn = st.sidebar.button("Refresh")
if refresh_btn:
    st.rerun()

# Make the dataframes
if os.path.exists(acv_data_path):
    df_acv = pd.read_csv(acv_data_path)
else:
    df_acv = pd.DataFrame(columns=["Activity", "Hours"])

if os.path.exists(sess_data_path):
    df_sess = pd.read_csv(sess_data_path)
else:
    df_sess = pd.DataFrame(columns=["Session", "Duration", "Numbers", "Activity", "Priority", "Total Hours"])

if os.path.exists(free_hours_path):
    df_days = pd.read_csv(free_hours_path)
else:
    df_days = pd.DataFrame({"Day": days, "Hours": [0, 0, 0, 0, 0, 0, 0]})

# Create and display activity form
with st.form(key="activity_form"):
    activity = st.text_input("Enter your activity")
    num_of_hours = st.number_input("How much weekly hours?", step=0.10)
    submit_btn = st.form_submit_button()
    if submit_btn:
        df_acv.loc[len(df_acv)] = [activity, num_of_hours]
        df_acv.to_csv(acv_data_path, index=False)
edited_acv_df = st.data_editor(df_acv)

# Create and display sessions form
with st.form(key="sessions"):
    session = st.text_input("Enter your session")
    duration = st.number_input("Duration?", step=0.5)
    weekly_numbers = st.number_input("Numbers?", step=1)
    session_activity = st.selectbox("Activity", options=df_acv.Activity.values)
    priority = st.select_slider("priority", options=[1,2,3,4,5])
    submit_btn = st.form_submit_button()
    if submit_btn:
        df_sess.loc[len(df_sess)] = [session, duration, weekly_numbers, session_activity, priority, duration*weekly_numbers]
        df_sess.to_csv(sess_data_path, index=False)
edited_sess_df = st.data_editor(df_sess)

# Show hours needed to balance sessions and activity hours
st.subheader("Remaining hours for")
df_grouped = edited_sess_df.groupby("Activity", as_index=False).agg({"Total Hours": "sum"})
if not df_grouped.empty:
    for index, row in edited_acv_df.iterrows():
        matched = df_grouped[df_grouped.Activity == row["Activity"]]
        try:
            total_hours = matched["Total Hours"].iloc[0]
        except IndexError:
            continue

        remaining = row["Hours"] - total_hours
        st.metric(label=row["Activity"], value=remaining)
        st.write(matched)

st.divider()

# Display the hours required to balance free hours with required hours
st.subheader(f"Total Hours need to free this week {all_hours}")
edited = st.data_editor(df_days)
save_changes = st.button("save_changes")
if save_changes:
    edited.to_csv(free_hours_path, index=False)
    edited_sess_df.to_csv(sess_data_path, index=False)
    edited_acv_df.to_csv(acv_data_path, index=False)

st.subheader(f"Remaning hours {all_hours - edited["Hours"].sum()}")
st.divider()

# Create and display the weekly plan
pressed = st.button("Create the Plan of the Week")
if pressed:
    df = df_sess.groupby(["Activity", "Session"], as_index=False).agg({"Total Hours": "sum", "Numbers": "sum", "Duration": "sum", "Priority": "sum"})
    plan = pd.DataFrame(columns=["Day", "Session", "Activity"])
    new = df.groupby("Activity").agg({"Total Hours": "sum"})
    for day in days:
        free_hours = df_days[df_days.Day == day].Hours.iloc[0]

        while free_hours > 0 and not df.empty:
            df["Final Weight"] = df.Numbers * df.Priority
            if df["Duration"].min() > free_hours:
                break
            acv = new.sample(1, weights="Total Hours").index[0]

            available = df[(df.Activity == acv) & (df.Duration <= free_hours)]
            if available.empty:
                continue

            selected = available.sample(n=1, weights="Final Weight")
            selected_index = selected.index[0]
            duration = selected["Duration"].iat[0]

            df.loc[selected_index, "Numbers"] -= 1
            df.loc[selected_index, "Total Hours"] -= duration
            free_hours -= duration

            plan.loc[len(plan)] = [day, selected.Session.iat[0], selected.Activity.iat[0]]
            df = df[df.Numbers > 0]
    st.dataframe(plan)
st.divider()

# Create and display visuals
col1, col2 = st.columns(2)
with col1:
    acv_per_hours = px.pie(df_sess, values="Total Hours", names="Activity", color_discrete_sequence=px.colors.qualitative.Pastel, title="Activity Breakdown by Time")
    acv_per_hours.update_traces(textinfo="label+percent")
    acv_per_hours.update_layout(showlegend=False)
    st.plotly_chart(acv_per_hours)

with col2:
    hours_per_day = px.pie(df_days, values="Hours", names="Day", labels="Day", title="Time You Have Available Each Day")
    hours_per_day.update_traces(textinfo="label+value")
    hours_per_day.update_layout(showlegend=False)
    st.plotly_chart(hours_per_day)

# Drop data button
delete_btn = st.button("Delete all Data")
if delete_btn:
    df_acv.drop(df_acv.index, inplace=True)
    df_sess.drop(df_sess.index, inplace=True)
    df_days = pd.DataFrame({"Day": days, "Hours": [0, 0, 0, 0, 0, 0, 0]})
    df_acv.to_csv(acv_data_path, index=False)
    df_sess.to_csv(sess_data_path, index=False)
    df_days.to_csv(free_hours_path, index=False)
    st.rerun()
