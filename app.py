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
c.execute('''CREATE TABLE IF NOT EXISTS trips 
             (id INTEGER PRIMARY KEY, date TEXT, origin TEXT, destination TEXT, 
              vehicle_no TEXT, description TEXT, category TEXT, amount REAL, receipt_path TEXT)''')
conn.commit()

# Ensure all columns exist (Migration handling)
try:
    c.execute("ALTER TABLE trips ADD COLUMN origin TEXT")
    c.execute("ALTER TABLE trips ADD COLUMN destination TEXT")
    c.execute("ALTER TABLE trips ADD COLUMN vehicle_no TEXT")
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
    
    # This line "cleans" the text by removing emojis or symbols 
    # that standard PDFs cannot handle.
    safe_text = itinerary_text.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.multi_cell(0, 10, txt=safe_text)
    pdf_output = "itinerary_export.pdf"
    pdf.output(pdf_output)
    return pdf_output

# --- STREAMLIT UI ---
st.set_page_config(page_title="Blossom Fleet Manager", layout="wide") # Changed to wide for better table viewing
show_header()

tab1, tab2, tab3 = st.tabs(["Daily Trip Logger", "Tour Canvas", "Dashboard"])

with tab1:
    st.subheader("Log New Trip")
    with st.form("trip_form", clear_on_submit=True):
        date = st.date_input("Date", datetime.now())
        v_no = st.text_input("Vehicle Number")
        
        col1, col2 = st.columns(2)
        with col1:
            origin = st.text_input("From (Origin)")
        with col2:
            dest = st.text_input("To (Destination)")
            
        desc = st.text_area("Description / Payment Notes", help="Record vendor payment status or future date promises here.")
        
        col3, col4 = st.columns(2)
        with col3:
            cat = st.selectbox("Category", ["Fuel", "Maintenance", "Food", "Toll", "Other"])
        with col4:
            amt = st.number_input("Amount ($)", min_value=0.0, step=0.01)
        
        camera_photo = st.camera_input("Snap Receipt")
        submit = st.form_submit_button("Save Entry")
        
        if submit:
            img_path = ""
            if camera_photo:
                img_path = f"media/{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                with open(img_path, "wb") as f:
                    f.write(camera_photo.getbuffer())
            
            c.execute("""INSERT INTO trips (date, origin, destination, vehicle_no, description, category, amount, receipt_path) 
                         VALUES (?,?,?,?,?,?,?,?)""",
                      (str(date), origin, dest, v_no, desc, cat, amt, img_path))
            conn.commit()
            st.success("Entry saved successfully!")

with tab2:
    st.subheader("Create Itinerary")
    itinerary_content = st.text_area("Custom Itinerary Details", height=300)
    if st.button("Generate Professional PDF"):
        if itinerary_content:
            pdf_file = generate_pdf(itinerary_content)
            with open(pdf_file, "rb") as f:
                st.download_button("Download PDF", f, file_name="Blossom_Itinerary.pdf")

with tab3:
    st.subheader("Business Summary & Payment Tracking")
    df = pd.read_sql_query("SELECT * FROM trips", conn)
    if not df.empty:
        st.metric("Total Amount Tracked", f"${df['amount'].sum():,.2f}")
        
        # We now include 'description' so you can see your payment notes
        st.dataframe(
            df[['date', 'vehicle_no', 'origin', 'destination', 'amount', 'description']], 
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No data logged yet. Go to the 'Daily Trip Logger' tab to start.")