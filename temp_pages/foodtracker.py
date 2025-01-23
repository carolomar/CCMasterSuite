import streamlit as st
from datetime import datetime


# Get the current date
current_date = datetime.now().strftime("%Y-%m-%d")


st.title("Water Intake Tracker")
water = st.number_input("Enter how many glasses of water you drank today:", min_value=1, max_value=100, step=1)
if water > 0:
    st.write(f"Great job! You've logged {water} glasses of water today.")


# Prepare the data string with date and water intake
data_str = f"Date: {current_date}\nWater Intake: {water} glasses"

# Provide a download button to download the log as a .txt file
st.download_button("Download your water log", data_str, "water_log.txt")
