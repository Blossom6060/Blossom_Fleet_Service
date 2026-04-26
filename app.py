import streamlit as st
import sqlite3
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import os

# --- INITIAL SETUP ---
if not os.path.exists("media"):
    os.makedirs("media")

conn = sqlite3.connect('fleet_manager.db', check_same_thread=False)
c = conn.cursor()
# Updated Table to include 'days'
c.execute('''CREATE TABLE IF NOT EXISTS trips 
             (id INTEGER PRIMARY KEY, date TEXT, origin TEXT, destination TEXT, 
              vehicle_no TEXT, days INTEGER, description TEXT, category TEXT, amount REAL, receipt_path TEXT)''')
conn.commit()

# Migration: Add 'days' column if it doesn't exist in an old database
try:
    c.execute("ALTER TABLE trips ADD COLUMN days INTEGER DEFAULT 1")
    conn.commit()
except:
    pass 

# --- APP HEADER ---
def show_header():
    st.markdown("<h1 style='text-align: center; color: #2E7D32;'>BLOSSOM FLEET SERVICE</h1>", unsafe_allow_html=True)
    if os.path.exists("logo.png"):
        st.image("logo.png", width=150)
    st.divider()

# --- PDF GENERATION ---
class TripPDF(FPDF):
    def header(self):
        if os.path.exists("logo.png"):
            self.image("logo.png", 80, 8, 50)
        self.set_font('Arial', 'B', 16)
        self.ln(35)
        self.cell(0, 10, 'BLOSSOM FLEET SERVICE', 0, 1, 'C')
        self.ln(5)

def generate_pdf(itinerary_text):
    pdf = TripPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    safe_text = itinerary_text.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=safe_text)
    pdf_output = "itinerary_export.pdf"
    pdf.output(pdf_output)
    return pdf_output

# --- STREAMLIT UI ---
st.set_page_config(page_title="Blossom Fleet Manager", layout="wide")
show_header()

tab1, tab2, tab3 = st.tabs(["Daily Trip Logger", "Tour Canvas", "Dashboard"])

with tab1:
    st.subheader("Log New Trip")
    with st.form("trip_form", clear_on_submit=True):
        col_date, col_veh = st.columns(2)
        with col_date:
            date = st.date_input("Date", datetime.now())
        with col_veh:
            v_no = st.text_input("Vehicle Number")
        
        col1, col2 = st.columns(2)
        with col1:
            origin = st.text_input("From (Origin)")
        with col2:
            dest = st.text_input("To (Destination)")
            
        # Added Number of Days field
        col_days, col_cat, col_amt = st.columns([1, 2, 2])
        with col_days:
            num_days = st.number_input("No. of Days", min_value=1, step=1, value=1)
        with col_cat:
            cat = st.selectbox("Category", ["Tour Revenue", "Fuel", "Maintenance", "Food", "Toll", "Other"])
        with col_amt:
            amt = st.number_input("Amount", min_value=0.0, step=0.01)

        desc = st.text_area("Description / Payment Notes")
        
        submit = st.form_submit_button("Save Entry")

    st.write("---")
    show_camera = st.checkbox("📸 Open Camera to Snap Receipt")
    camera_photo = None
    if show_camera:
        camera_photo = st.camera_input("Take a photo of the receipt")

    if submit:
        img_path = ""
        if camera_photo:
            img_path = f"media/{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            with open(img_path, "wb") as f:
                f.write(camera_photo.getbuffer())
        
        c.execute("""INSERT INTO trips (date, origin, destination, vehicle_no, days, description, category, amount, receipt_path) 
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (str(date), origin, dest, v_no, int(num_days), desc, cat, amt, img_path))
        conn.commit()
        st.success(f"Entry saved for {v_no} ({num_days} days)!")

with tab2:
    st.subheader("Create Itinerary")
    itinerary_content = st.text_area("Custom Itinerary Details", height=300)
    if st.button("Generate Professional PDF"):
        if itinerary_content:
            pdf_file = generate_pdf(itinerary_content)
            with open(pdf_file, "rb") as f:
                st.download_button("Download PDF", f, file_name="Blossom_Itinerary.pdf")

with tab3:
    st.subheader("Business Summary")
    df = pd.read_sql_query("SELECT * FROM trips", conn)
    if not df.empty:
        st.metric("Total Revenue/Expense", f"₹{df['amount'].sum():,.2f}")
        # Added 'days' to the dashboard table
        st.dataframe(
            df[['date', 'vehicle_no', 'days', 'origin', 'destination', 'amount', 'description']], 
            use_container_width=True, 
            hide_index=True
        )
