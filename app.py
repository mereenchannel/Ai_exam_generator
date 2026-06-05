import streamlit as st
from google import genai
import PyPDF2
from fpdf import FPDF
import os

# --- ตั้งค่าหน้าเว็บให้เต็มจอและใส่ชื่อแอป ---
st.set_page_config(page_title="Smart Exam Pro", page_icon="📝", layout="centered")

# --- ส่วนของการตกแต่งด้วย CSS (UI/UX Design) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {background-color: #f8f9fa;}
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; font-size: 18px; font-weight: bold; border-radius: 12px;
        border: none; padding: 12px 24px; width: 100%; box-shadow: 0 4px 15px rgba(0,0,0,0.1); transition: all 0.3s ease;
    }
    .stButton>button:hover {transform: translateY(-2px); box-shadow: 0 6px 20px rgba(118, 75, 162, 0.4); color: #f0f0f0;}
    [data-testid="stFileUploadDropzone"] {border-radius: 15px; border: 2px dashed #764ba2; background-color: #ffffff; padding: 20px;}
    h1 {color: #2d3748; font-family: 'Helvetica Neue', sans-serif; text-align: center; padding-bottom: 20px;}
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1>📝 Smart Exam Pro<br><span style='font-size: 20px; color: #718096;'>ระบบสร้างข้อสอบและใบงานอัจฉริยะ</span></h1>", unsafe_allow_html=True)

# --- ดึง API Key ---
api_key = st.secrets["GEMINI_API_KEY"]

# --- UI หน้าเว็บ (ใส่ key ให้ uploader เพื่อให้ระบบสั่งล้างความจำได้) ---
st.markdown("### 1. อัปโหลดเอกสารบทเรียน")
uploaded_file = st.file_uploader("", type=["pdf"], key="pdf_uploader")

st.markdown("### 2. ตั้งค่าโครงสร้างข้อสอบ")
col1, col2 = st.columns(2)
with col1:
    num_questions = st.number_input("🔢 จำนวนข้อสอบปรนัย (ข้อ):", min_value=1, max_value=30, value=5, step=1)
with col2:
    difficulty_level = st.slider("🔥 ระดับความยาก (1=ง่าย, 5=วิเคราะห์ขั้นสูง):", min_value=1, max_value=5, value=3)

difficulty_desc = {
    1: "เน้นความจำขั้นพื้นฐานและการจับใจความจากเนื้อหาโดยตรง",
    2: "มีความเข้าใจและการประยุกต์ใช้ความรู้พื้นฐานจากเนื้อหาประกอบกัน",
    3: "ระดับปานกลาง ข้อสอบต้องเริ่มมีการคิดวิเคราะห์และเชื่อมโยงข้อมูลในตารางหรือเนื้อหา",
    4: "ระดับสูง โจทย์มีความซับซ้อน นักเรียนต้องใช้การคิดวิเคราะห์ขั้นสูงเพื่อตัดตัวเลือก",
    5: "ระดับสูงสุด ข้อสอบต้องเน้นการวิเคราะห์คำตอบอย่างลึกซึ้ง (Analytical Thinking) ตัวเลือกต้องมีความลวงสูงมาก นักเรียนไม่สามารถหาคำตอบได้จากการอ่านผ่านๆ แต่ต้องวิเคราะห์สถานการณ์หรือประเมินค่าข้อมูลเชิงลึกจึงจะตอบได้"
}

st.write("") 

# --- ปุ่มหลัก ---
if st.button("✨ เริ่มวิเคราะห์และสร้างข้อสอบ"):
    if not uploaded_file:
        st.warning("⚠️ กรุณาอัปโหลดไฟล์ PDF ให้ครบถ้วนครับ")
    else:
        with st.spinner("🧠 AI กำลังสังเคราะห์เนื้อหาและออกแบบข้อสอบ..."):
            try:
                reader = PyPDF2.PdfReader(uploaded_file)
                raw_text = "".join([page.extract_text() + "\n" for page in reader.pages if page.extract_text()])
                
                client = genai.Client(api_key=api_key)
                
                prompt = f"""จากเนื้อหาต่อไปนี้ จงสร้างชุดข้อสอบและใบงานตามเงื่อนไขที่กำหนดอย่างเคร่งครัด
                เงื่อนไขข้อสอบ:
                1. สร้างข้อสอบปรนัยจำนวน {num_questions} ข้อ (ตัวเลือก ก, ข, ค, ง)
                2. กำหนดระดับความยากระดับที่ {difficulty_level}/5 ซึ่งมีลักษณะคือ: {difficulty_desc[difficulty_level]}
                3. เพิ่มโจทย์ใบงานอัตนัย (โจทย์วิเคราะห์) ตอนท้ายอีก 1 ข้อ
                ข้อบังคับสำคัญที่สุด:
                1. ห้ามใช้เครื่องหมายดอกจัน (**) หรือสัญลักษณ์ Markdown ใดๆ ในการตกแต่งข้อความเด็ดขาด ให้ใช้การขึ้นบรรทัดใหม่ธรรมดาเท่านั้น
                2. คุณต้องแบ่ง 'ส่วนข้อสอบ' และ 'ส่วนเฉลย' ออกจากกัน โดยพิมพ์คำว่า ---SPLIT--- คั่นกลางระหว่างสองส่วนนี้เท่านั้น
                รูปแบบการตอบกลับ:
                [ส่วนที่ 1: ข้อสอบปรนัยจำนวน {num_questions} ข้อ และโจทย์วิเคราะห์ 1 ข้อ]
                ---SPLIT---
                [ส่วนที่ 2: เฉลยอย่างละเอียด พร้อมอธิบายเหตุผลของข้อที่ถูกและข้อที่ลวง]
                เนื้อหาอ้างอิง:
                {raw_text[:8000]}
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt
                )
                
                result_text = response.text
                if "---SPLIT---" in result_text:
                    questions, answers = result_text.split("---SPLIT---")
                else:
                    questions = result_text
                    answers = "AI ไม่ได้แบ่งหน้าเฉลยตามคำสั่ง โปรดลองกดใหม่อีกครั้ง"

                st.success("🎉 ดำเนินการสำเร็จ!")
                with st.expander("👀 ตรวจสอบความถูกต้องของข้อสอบก่อนปรินต์"):
                    st.subheader("ส่วนหน้าข้อสอบ")
                    st.write(questions)
                    st.markdown("---")
                    st.subheader("ส่วนหน้าเฉลย")
                    st.write(answers)

                pdf = FPDF()
                pdf.add_font("THSarabun", "", "THSarabunNew.ttf")
                
                pdf.add_page()
                pdf.set_font("THSarabun", size=20)
                pdf.cell(0, 15, text=f"ชุดข้อสอบและใบงาน (ระดับความยาก: {difficulty_level}/5)", align="C", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("THSarabun", size=16)
                pdf.multi_cell(0, 8, text=questions.strip())
                
                pdf.add_page()
                pdf.set_font("THSarabun", size=20)
                pdf.cell(0, 15, text="เฉลยข้อสอบอย่างละเอียด (สำหรับผู้สอน)", align="C", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("THSarabun", size=16)
                pdf.multi_cell(0, 8, text=answers.strip())
                
                pdf_filename = "Smart_Exam_Pro.pdf"
                pdf.output(pdf_filename)
                
                # --- ส่วนปุ่มดาวน์โหลด ---
                st.markdown("<br>", unsafe_allow_html=True)
                with open(pdf_filename, "rb") as pdf_file:
                    st.download_button(
                        label="📥 บันทึกเป็นไฟล์ PDF (จัดหน้าพร้อมพิมพ์)",
                        data=pdf_file,
                        file_name=pdf_filename,
                        mime="application/pdf"
                    )
            
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในระบบ: {e}")

# --- ปุ่มล้างระบบ (Reset) ---
st.markdown("<hr>", unsafe_allow_html=True)
if st.button("🔄 อัปโหลดไฟล์ใหม่ (ล้างข้อมูลระบบ)"):
    # เลื่อนรหัสกุญแจขึ้น 1 ระดับ ทำให้ Streamlit โยนกล่องอัปโหลดเก่าทิ้งทันที
    st.session_state["uploader_key"] += 1
    st.rerun()
