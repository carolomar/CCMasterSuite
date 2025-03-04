import streamlit as st
import json
import openai
import gspread
import smtplib
import os
from email.mime.text import MIMEText
from oauth2client.service_account import ServiceAccountCredentials

# Single SMTP configuration (removed duplicates)
SMTP_SERVER = "localhost"
SMTP_PORT = 1025  # Local debug SMTP
SMTP_EMAIL = "test@example.com"
SMTP_PASSWORD = ""  # Not needed for local test


# Create an email draft (removed actual sending functionality for local testing)
def create_email_draft(from_email, to_email, subject, body):
    """
    Creates an email draft structure but doesn't send it.
    Returns the email components for display.
    """
    return {
        "from": from_email,
        "to": to_email,
        "subject": subject,
        "body": body
    }


# For compatibility with existing code (not used but kept for reference)
def send_email(smtp_server, smtp_port, smtp_email, smtp_password, to_email, subject, body):
    # Just create and return the draft instead of sending
    draft = create_email_draft(smtp_email, to_email, subject, body)
    return True  # Always return success since we're just creating a draft


# Load Blueprint.json
def load_blueprint(file_path="blueprint1.json"):
    try:
        # Check if file exists first
        if not os.path.exists(file_path):
            st.error(f"❌ Blueprint file not found: {file_path}")
            return None

        with open(file_path, "r", encoding="utf-8-sig") as file:  # Ensure correct encoding
            return json.load(file)
    except FileNotFoundError:
        st.error(f"❌ Blueprint file not found: {file_path}")
        return None
    except json.JSONDecodeError:
        st.error(f"❌ Invalid JSON in blueprint file: {file_path}")
        return None
    except Exception as e:
        st.error(f"❌ Error loading blueprint: {e}")
        return None


# Google Sheets Authentication
def authenticate_google_sheets(credentials_file, sheet_name):
    try:
        # Check if credentials file exists
        if not os.path.exists(credentials_file):
            st.error(f"❌ Google Sheets credentials file not found: {credentials_file}")
            return None

        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
        return client.open(sheet_name).sheet1
    except Exception as e:
        st.error(f"❌ Google Sheets authentication failed: {e}")
        return None


# AI Recommendation
def generate_ai_recommendation(api_key, inquiry):
    try:
        openai.api_key = api_key
        prompt = f"User Inquiry: {inquiry}. Generate a short, personalized recommendation."

        response = openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "system", "content": "You are a helpful assistant."},
                      {"role": "user", "content": prompt}]
        )

        return response.choices[0].message.content
    except Exception as e:
        st.error(f"❌ Failed to generate AI recommendation: {e}")
        return "Unable to generate recommendation at this time."


# Streamlit UI
st.title("🚀 AI-Powered Form Execution from Blueprint.json")

# Load Blueprint
blueprint = load_blueprint()

# Only proceed if blueprint loaded successfully
if blueprint:
    # Try to extract form fields from the blueprint
    try:
        form_node = next((node for node in blueprint["nodes"] if node["type"] == "trigger"), None)
        if not form_node:
            st.error("❌ Form trigger node not found in Blueprint.json")
            form_node = {"config": {"fields": []}}  # Empty default to prevent errors
    except Exception as e:
        st.error(f"❌ Error extracting form fields: {e}")
        form_node = {"config": {"fields": []}}  # Empty default to prevent errors

    # Generate Form from Blueprint.json
    with st.form("dynamic_form"):
        form_data = {}

        # Only try to populate fields if fields exist in the form node
        if "config" in form_node and "fields" in form_node["config"]:
            for field in form_node["config"]["fields"]:
                field_type = field.get("type", "string")
                field_name = field.get("name", "Unknown")

                if field_type == "string":
                    form_data[field_name] = st.text_input(field_name)
                elif field_type == "email":
                    form_data[field_name] = st.text_input(field_name, type="default")
                elif field_type == "text":
                    form_data[field_name] = st.text_area(field_name)
        else:
            st.warning("⚠️ No form fields found in Blueprint.json")

        submit_button = st.form_submit_button("Submit")

    # On Submit, Process the Automation
    if submit_button:
        st.info("✅ Processing Submission...")

        # Save to Google Sheets
        google_sheet_node = next((node for node in blueprint["nodes"] if node["type"] == "google_sheets"), None)
        if google_sheet_node:
            sheet = authenticate_google_sheets("credentials.json", google_sheet_node["config"]["sheetName"])
            if sheet:
                try:
                    # Make sure all required fields exist
                    if all(field in form_data for field in ["Full Name", "Email", "Inquiry"]):
                        sheet.append_row([form_data["Full Name"], form_data["Email"], form_data["Inquiry"]])
                        st.success("📌 Data saved to Google Sheets")
                    else:
                        st.error("❌ Missing required form fields for Google Sheets")
                except Exception as e:
                    st.error(f"❌ Failed to save to Google Sheets: {e}")
        else:
            st.warning("⚠️ Google Sheets node not found in Blueprint.json")

        # Generate AI Recommendation
        ai_node = next((node for node in blueprint["nodes"] if node["type"] == "openai_api"), None)

        # Initialize ai_recommendation variable to avoid NameError later
        ai_recommendation = ""

        if ai_node:
            try:
                # Try to get API key from secrets
                try:
                    api_key = st.secrets["OPENAI_API_KEY"]
                except Exception as e:
                    st.error(f"❌ Error accessing OpenAI API key: {e}")
                    api_key = ""

                if api_key and "Inquiry" in form_data:
                    ai_recommendation = generate_ai_recommendation(api_key, form_data["Inquiry"])
                    st.subheader("📌 AI Recommendation")
                    st.write(ai_recommendation)
                else:
                    st.error("🚨 Missing OpenAI API key or inquiry text")
            except Exception as e:
                st.error(f"🚨 Error generating AI recommendation: {e}")
        else:
            st.error("🚨 AI recommendation node missing in Blueprint.json")
            # For testing purposes, you might want to continue with a placeholder
            ai_recommendation = "No AI recommendation available - node missing in Blueprint.json"

        # Send Email
        email_node = next((node for node in blueprint["nodes"] if node["type"] == "email"), None)
        if email_node:
            try:
                email_body = email_node["config"]["body"]

                # Replace placeholders in email body only if they exist in form_data
                for placeholder, field in [
                    ("{{Full Name}}", "Full Name"),
                    ("{{Inquiry}}", "Inquiry")
                ]:
                    if field in form_data:
                        email_body = email_body.replace(placeholder, form_data[field])

                # Replace AI recommendation placeholder
                email_body = email_body.replace("{{AI_Recommendation}}", ai_recommendation)

                # Try to get email credentials from secrets
                # For local development, just use the email from the form
                to_email = form_data.get("Email", st.secrets["EMAIL_ADDRESS"])
                # Add a placeholder if email is empty
                if not to_email or to_email.strip() == "":
                    to_email = st.secrets["EMAIL_ADDRESS"]

                    # Instead of sending, display the email content as a draft for copy/paste
                    st.subheader("📧 Email Draft")
                    st.write("**To:** " + to_email)
                    st.write("**From:** " + email_node["config"]["fromEmail"])
                    st.write("**Subject:** " + email_node["config"]["subject"])
                    st.write("**Body:**")
                    st.text_area("Email Body (Copy/Paste)", email_body, height=250)
                    st.success("✅ Email draft created! You can copy and paste the content.")
                else:
                    st.error("❌ No recipient email address found")
            except Exception as e:
                st.error(f"❌ Error processing email node: {e}")
            else:
                st.warning("⚠️ No Email node found in Blueprint.json")
        else:
            st.error("Please create a valid Blueprint.json file before continuing.")

            # Display example blueprint structure
            with st.expander("Example Blueprint.json Structure"):
                st.code('''{
              "id": "form-automation-blueprint",
              "name": "Form Automation Blueprint",
              "nodes": [
                {
                  "id": "form1",
                  "type": "trigger",
                  "name": "Contact Form",
                  "config": {
                    "fields": [
                      {
                        "name": "Full Name",
                        "type": "string",
                        "required": true
                      },
                      {
                        "name": "Email",
                        "type": "email",
                        "required": true
                      },
                      {
                        "name": "Inquiry",
                        "type": "text",
                        "required": true
                      }
                    ]
                  }
                },
                {
                  "id": "sheets1",
                  "type": "google_sheets",
                  "name": "Save to Google Sheets",
                  "config": {
                    "sheetName": "Form Responses",
                    "worksheetName": "Responses"
                  }
                },
                {
                  "id": "ai1",
                  "type": "openai_api",
                  "name": "Generate AI Recommendation",
                  "config": {
                    "model": "gpt-4-turbo",
                    "apiKey": ""
                  }
                },
                {
                  "id": "email1",
                  "type": "email",
                  "name": "Send Confirmation Email",
                  "config": {
                    "smtpServer": "localhost",
                    "smtpPort": 1025,
                    "fromEmail": "test@example.com",
                    "subject": "We received your inquiry",
                    "body": "Hello {{Full Name}},\\n\\nThank you for your inquiry: \\"{{Inquiry}}\\"\\n\\nHere\\'s our AI-generated recommendation:\\n{{AI_Recommendation}}\\n\\nBest regards,\\nThe Team"
                  }
                }
              ],
              "connections": [
                {
                  "from": "form1",
                  "to": "sheets1"
                },
                {
                  "from": "form1",
                  "to": "ai1"
                },
                {
                  "from": "form1",
                  "to": "email1"
                }
              ]
        }''', language="json")
