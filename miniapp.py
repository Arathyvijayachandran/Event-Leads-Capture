import streamlit as st
import pandas as pd
import pytesseract
from PIL import Image
import os
import re
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# 🔧 SET TESSERACT PATH
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\Local\Programs\Tesseract-OCR\tesseract.exe"

st.set_page_config(page_title="Smart Lead Capture", layout="centered")

st.title("📇 AI-Powered Business Card Scanner & Lead Manager")

file = "leads.csv"

# ✅ REQUIRED COLUMNS
required_columns = [
    "Name", "Email", "Phone", "Company", "Source",
    "Owner", "Status", "Timestamp", "LeadScore"
]

# 📂 LOAD DATA SAFELY
if os.path.exists(file):
    df = pd.read_csv(file)

    # Add missing columns if old file
    for col in required_columns:
        if col not in df.columns:
            df[col] = ""
else:
    df = pd.DataFrame(columns=required_columns)

# 📸 Upload Business Card
st.subheader("📸 Upload Business Card")
uploaded_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])

extracted_text = ""

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Card")

    extracted_text = pytesseract.image_to_string(image)

    st.subheader("🧾 Extracted Text")
    st.text(extracted_text)


# 🔍 Extract Email & Phone
def extract_email(text):
    match = re.findall(r'\S+@\S+', text)
    return match[0] if match else ""


def extract_phone(text):
    match = re.findall(r'\d{10}', text)
    return match[0] if match else ""


auto_email = extract_email(extracted_text)
auto_phone = extract_phone(extracted_text)


# ⭐ Lead Scoring
def calculate_score(company, email):
    score = 0
    if isinstance(company, str) and "tech" in company.lower():
        score += 10
    if isinstance(email, str) and "manager" in email.lower():
        score += 5
    if isinstance(email, str) and email.endswith(".com"):
        score += 5
    return score


# 📧 Email Notification (Using secrets.toml)
def send_email(name, email, company, owner):
    try:
        sender = st.secrets["EMAIL_ADDRESS"]
        password = st.secrets["EMAIL_PASSWORD"]

        # Receiver changes based on Owner
        if owner == "Placement Cell":
            receiver = st.secrets["placement"]
        else:
            receiver = st.secrets["sales"]

        msg = MIMEText(f"""
New Lead Assigned

Name: {name}
Email: {email}
Phone: {email}
Company: {company}
Assigned To: {owner}
Source: Business Card Scan
""")

        msg["Subject"] = f"New Lead Assigned: {name}"
        msg["From"] = sender
        msg["To"] = receiver

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.send_message(msg)

        st.success("📧 Notification Email Sent!")

    except Exception as e:
        st.error(f"⚠️ Email not sent. Error: {e}")


# ✏️ Input Form
st.subheader("✏️ Edit / Confirm Details")

name = st.text_input("Name")
company = st.text_input("Company")
email = st.text_input("Email", value=auto_email)
phone = st.text_input("Phone", value=auto_phone)
source = st.text_input("Event Source")

owner = st.selectbox("Assign Owner", ["Placement Cell", "Sales Team"])
status = st.selectbox("Status", ["New", "Contacted"])


# 💾 Save Lead
if st.button("💾 Save Lead"):
    if email.strip() == "":
        st.warning("⚠️ Email is required!")
    else:
        df["Email"] = df["Email"].fillna("").astype(str)

        if email in df["Email"].values:
            st.error("❌ Duplicate Email Found!")
        else:
            timestamp = datetime.now()
            score = calculate_score(company, email)

            new_data = pd.DataFrame([[
                name, email, phone, company, source,
                owner, status, timestamp, score
            ]], columns=required_columns)

            df = pd.concat([df, new_data], ignore_index=True)
            df.to_csv(file, index=False)

            send_email(name, email, company, owner)

            st.success("✅ Lead Saved & Notification Sent!")


# 📊 Dashboard
st.subheader("📊 Dashboard")
st.dataframe(df, use_container_width=True)

# Metrics
st.metric("Total Leads", len(df))
st.metric("Contacted Leads", len(df[df["Status"] == "Contacted"]))

# 📊 Leads by Event
st.subheader("📊 Leads by Event")
if not df.empty:
    df["Source"] = df["Source"].fillna("").astype(str)
    event_counts = df["Source"].value_counts()
    st.bar_chart(event_counts)


# ⏱️ 48-hour Conversion
st.subheader("⏱️ Conversion within 48 Hours")

if "Timestamp" in df.columns:
    df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')

    df["Converted_48h"] = df.apply(
        lambda x: "Yes" if pd.notnull(x["Timestamp"]) and
        x["Status"] == "Contacted" and
        (datetime.now() - x["Timestamp"]).total_seconds() <= 172800
        else "No",
        axis=1
    )

    st.dataframe(df[["Name", "Status", "Converted_48h"]])


# 🔍 Search
st.subheader("🔍 Search Leads")

search = st.text_input("Search by Name or Company")

if search:
    df["Name"] = df["Name"].fillna("").astype(str)
    df["Company"] = df["Company"].fillna("").astype(str)

    filtered_df = df[
        df["Name"].str.contains(search, case=False) |
        df["Company"].str.contains(search, case=False)
    ]

    st.dataframe(filtered_df, use_container_width=True)
