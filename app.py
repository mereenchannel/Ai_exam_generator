import streamlit as st
from google import genai
from google.genai import errors # เพิ่มไลบรารีสำหรับดักจับ Error ของ Gemini Direct
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

# --- UI หน้าเว็บ ---
st.markdown("### 1. อัปโหลดเอกสารที่เกี่ยวข้อง")
col_file1, col_file2 = st.columns(2)
with col_file1:
    uploaded_file = st.file_uploader("📥 อัปโหลดเอกสารบทเรียน (PDF)", type=["pdf"], key="pdf_uploader")
with col_file2:
    uploaded_indicator = st.file_uploader("🎯 อัปโหลดตัวชี้วัด/หลักสูตร (PDF)", type=["pdf"], key="indicator_uploader")

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
    if not uploaded_file or not uploaded_indicator:
        st.warning("⚠️ กรุณาอัปโหลดไฟล์ให้ครบถ้วนทั้ง 'เอกสารบทเรียน' และ 'ตัวชี้วัด' ครับ")
    else:
        try:
            # 1. สกัดข้อความจากไฟล์บทเรียน
            reader_content = PyPDF2.PdfReader(uploaded_file)
            raw_text = "".join([page.extract_text() + "\n" for page in reader_content.pages if page.extract_text()])
            
            # 2. สกัดข้อความจากไฟล์ตัวชี้วัด
            reader_indicator = PyPDF2.PdfReader(uploaded_indicator)
            indicator_text = "".join([page.extract_text() + "\n" for page in reader_indicator.pages if page.extract_text()])
            
            # เรียกใช้งาน Client
            client = genai.Client(api_key=api_key)
            
            # 3. ตรวจสอบความสอดคล้อง (ล้อมกรอบดักจับ Server API อย่างหนาแน่น)
            with st.spinner("🧠 ขั้นตอนที่ 1: AI กำลังตรวจสอบความสอดคล้องระหว่างเนื้อหาและตัวชี้วัด..."):
                validation_prompt = f"""คุณคือผู้เชี่ยวชาญด้านการประกันคุณภาพและหลักสูตรการศึกษา จงตรวจสอบความสอดคล้องระหว่าง "เนื้อหาบทเรียน" และ "ตัวชี้วัดหลักสูตร/ผลการเรียนรู้" ที่กำหนดด้านล่างนี้
                วิเคราะห์ว่าเนื้อหาบทเรียนนี้ตรงตามวิชาและสามารถนำไปใช้ออกข้อสอบเพื่อวัดผลตามตัวชี้วัดที่ให้มาได้จริงหรือไม่

                เนื้อหาบทเรียน:
                {raw_text[:4000]}

                ตัวชี้วัดหลักสูตร/ผลการเรียนรู้:
                {indicator_text[:4000]}

                ข้อบังคับการตอบกลับ:
                หากสอดคล้องกันและอยู่ในวิชา/ศาสตร์เดียวกัน ให้ตอบว่า MATCH
                หากขัดแย้งกันอย่างสิ้นเชิง (เช่น เนื้อหาวิทยาศาสตร์ แต่ตัวชี้วัดภาษาไทย) ให้ตอบว่า MISMATCH
                ให้ตอบสั้นๆ เพียงคำเดียวเท่านั้น ห้ามมีคำอธิบายอื่นผสม
                """
                
                try:
                    val_response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=validation_prompt
                    )
                    val_result = val_response.text.strip().replace('"', '').replace("'", "").upper()
                except errors.APIError as e:
                    # 🎯 ดักขัดขวาง Error 503 เปลี่ยนเป็นกล่องแจ้งเตือนสุภาพนุ่มนวล หน้าเว็บไม่พัง
                    st.error("⚠️ เซิร์ฟเวอร์ระบบ AI ของ Google กำลังหนาแน่นชั่วคราว (503 Unavailable) กรุณารอสัก 10 วินาทีแล้วกดปุ่มเริ่มใหม่อีกครั้งครับนายน้อย")
                    st.stop() # สั่งหยุดสคริปต์ทันทีอย่างปลอดภัย
            
            # 🎯 ตรวจสอบจับคำว่า MATCH เป็นด่านเปิดทางหลัก
            if "MATCH" in val_result and "MISMATCH" not in val_result:
                st.toast("✅ ตรวจสอบความสอดคล้องผ่าน! กำลังเริ่มออกแบบข้อสอบ...", icon="🧠")
                
                with st.spinner("✍️ ขั้นตอนที่ 2: AI กำลังสังเคราะห์และออกแบบข้อสอบตามตัวชี้วัด..."):
                    prompt = f"""จากเนื้อหาบทเรียน จงสร้างชุดข้อสอบและใบงาน โดยอ้างอิงและวัดผลให้ตรงตาม "ตัวชี้วัดหลักสูตร/ผลการเรียนรู้" ที่กำหนดไว้อย่างเคร่งครัด

                    เงื่อนไขโครงสร้างข้อสอบ:
                    1. สร้างข้อสอบปรนัยจำนวน {num_questions} ข้อ (ตัวเลือก ก, ข, ค, ง)
                    2. กำหนดระดับความยากระดับที่ {difficulty_level}/5 ซึ่งมีลักษณะคือ: {difficulty_desc[difficulty_level]}
                    
                    ข้อบังคับสำคัญที่สุด:
                    1. ข้อสอบแต่ละข้อต้องมีการระบุรหัสตัวชี้วัดหรือผลการเรียนรู้ที่ใช้วัดผลกำกับไว้ด้วยเสมอ (เช่น ตัวชี้วัด/ผลการเรียนรู้: ...)
                    2. ห้ามใช้เครื่องหมายดอกจัน (**) หรือสัญลักษณ์ Markdown ใดๆ ในการตกแต่งข้อความเด็ดขาด ให้ใช้การขึ้นบรรทัดใหม่ธรรมดาเท่านั้น
                    3. คุณต้องแบ่ง 'ส่วนข้อสอบ' และ 'ส่วนเฉลย' ออกจากกัน โดยพิมพ์คำว่า ---SPLIT--- คั่นกลางระหว่างสองส่วนนี้เท่านั้น

                    ตัวชี้วัดหลักสูตรอ้างอิง:
                    {indicator_text[:3000]}

                    เนื้อหาบทเรียนอ้างอิง:
                    {raw_text[:6000]}
                    """
                    
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt
                        )
                        result_text = response.text
                    except errors.APIError as e:
                        st.error("⚠️ เซิร์ฟเวอร์ระบบ AI ของ Google กำลังหนาแน่นในขั้นตอนการ Gen ข้อสอบ กรุณารอสักครู่แล้วลองกดใหม่อีกครั้งครับ")
                        st.stop()

                    if "---SPLIT---" in result_text:
                        questions, answers = result_text.split("---SPLIT---")
                    else:
                        questions = result_text
                        answers = "AI ไม่ได้แบ่งหน้าเฉลยตามคำสั่ง โปรดลองกดใหม่อีกครั้ง"

                    st.success("🎉 ดำเนินการสร้างข้อสอบตามตัวชี้วัดสำเร็จ!")
                    
                    with st.expander("👀 ตรวจสอบความถูกต้องของข้อสอบก่อนปรินต์"):
                        st.subheader("ส่วนหน้าข้อสอบ")
                        st.write(questions)
                        st.markdown("---")
                        st.subheader("<h3>ส่วนหน้าเฉลย</h3>", unsafe_allow_html=True)
                        st.write(answers)

                    # --- กระบวนการสร้างไฟล์ PDF ---
                    pdf = FPDF()
                    pdf.add_font("THSarabun", "", "THSarabunNew.ttf")
                    
                    pdf.add_page()
                    pdf.set_font("THSarabun", size=20)
                    pdf.cell(0, 15, text=f"ชุดข้อสอบอิงตัวชี้วัด (ระดับความยาก: {difficulty_level}/5)", align="C", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("THSarabun", size=16)
                    pdf.multi_cell(0, 8, text=questions.strip())
                    
                    pdf.add_page()
                    pdf.set_font("THSarabun", size=20)
                    pdf.cell(0, 15, text="เฉลยข้อสอบอย่างละเอียดอ้างอิงตัวชี้วัด (สำหรับผู้สอน)", align="C", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("THSarabun", size=16)
                    pdf.multi_cell(0, 8, text=answers.strip())
                    
                    pdf_filename = "Smart_exam_indicator_driven.pdf"
                    pdf.output(pdf_filename)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    with open(pdf_filename, "rb") as pdf_file:
                        st.download_button(
                            label="📥 บันทึกเป็นไฟล์ PDF (จัดหน้าพร้อมพิมพ์)",
                            data=pdf_file,
                            file_name=pdf_filename,
                            mime="application/pdf"
                        )
            
            # ❌ เคสตัวชี้วัดไม่ตรงกับเนื้อหาหลักสูตร
            else:
                st.error(f"❌ ไม่สามารถสร้างข้อสอบได้: ระบบตรวจพบว่า 'ตัวชี้วัด' และ 'เอกสารเนื้อหาบทเรียน' ไม่มีความสอดคล้องกัน (ผลวิเคราะห์จาก AI: {val_result}) กรุณาตรวจสอบไฟล์ใหม่อีกครั้งครับ")
        
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดทั่วไปในระบบ: {e}")
            # 1. สกัดข้อความจากไฟล์บทเรียน
            reader_content = PyPDF2.PdfReader(uploaded_file)
            raw_text = "".join([page.extract_text() + "\n" for page in reader_content.pages if page.extract_text()])
            
            # 2. สกัดข้อความจากไฟล์ตัวชี้วัด
            reader_indicator = PyPDF2.PdfReader(uploaded_indicator)
            indicator_text = "".join([page.extract_text() + "\n" for page in reader_indicator.pages if page.extract_text()])
            
            # เรียกใช้งาน Client
            client = genai.Client(api_key=api_key)
            
            # 3. ตรวจสอบความสอดคล้อง (ล้อมกรอบดักจับ Server API อย่างหนาแน่น)
            with st.spinner("🧠 ขั้นตอนที่ 1: AI กำลังตรวจสอบความสอดคล้องระหว่างเนื้อหาและตัวชี้วัด..."):
                validation_prompt = f"""คุณคือผู้เชี่ยวชาญด้านการประกันคุณภาพและหลักสูตรการศึกษา จงตรวจสอบความสอดคล้องระหว่าง "เนื้อหาบทเรียน" และ "ตัวชี้วัดหลักสูตร/ผลการเรียนรู้" ที่กำหนดด้านล่างนี้
                วิเคราะห์ว่าเนื้อหาบทเรียนนี้ตรงตามวิชาและสามารถนำไปใช้ออกข้อสอบเพื่อวัดผลตามตัวชี้วัดที่ให้มาได้จริงหรือไม่

                เนื้อหาบทเรียน:
                {raw_text[:4000]}

                ตัวชี้วัดหลักสูตร/ผลการเรียนรู้:
                {indicator_text[:4000]}

                ข้อบังคับการตอบกลับ:
                หากสอดคล้องกันและอยู่ในวิชา/ศาสตร์เดียวกัน ให้ตอบว่า MATCH
                หากขัดแย้งกันอย่างสิ้นเชิง (เช่น เนื้อหาวิทยาศาสตร์ แต่ตัวชี้วัดภาษาไทย) ให้ตอบว่า MISMATCH
                ให้ตอบสั้นๆ เพียงคำเดียวเท่านั้น ห้ามมีคำอธิบายอื่นผสม
                """
                
                try:
                    val_response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=validation_prompt
                    )
                    val_result = val_response.text.strip().replace('"', '').replace("'", "").upper()
                except errors.APIError as e:
                    # 🎯 ดักขัดขวาง Error 503 เปลี่ยนเป็นกล่องแจ้งเตือนสุภาพนุ่มนวล หน้าเว็บไม่พัง
                    st.error("⚠️ เซิร์ฟเวอร์ระบบ AI ของ Google กำลังหนาแน่นชั่วคราว (503 Unavailable) กรุณารอสัก 10 วินาทีแล้วกดปุ่มเริ่มใหม่อีกครั้งครับนายน้อย")
                    st.stop() # สั่งหยุดสคริปต์ทันทีอย่างปลอดภัย
            
            # 🎯 ตรวจสอบจับคำว่า MATCH เป็นด่านเปิดทางหลัก
            if "MATCH" in val_result and "MISMATCH" not in val_result:
                st.toast("✅ ตรวจสอบความสอดคล้องผ่าน! กำลังเริ่มออกแบบข้อสอบ...", icon="🧠")
                
                with st.spinner("✍️ ขั้นตอนที่ 2: AI กำลังสังเคราะห์และออกแบบข้อสอบตามตัวชี้วัด..."):
                    prompt = f"""จากเนื้อหาบทเรียน จงสร้างชุดข้อสอบและใบงาน โดยอ้างอิงและวัดผลให้ตรงตาม "ตัวชี้วัดหลักสูตร/ผลการเรียนรู้" ที่กำหนดไว้อย่างเคร่งครัด

                    เงื่อนไขโครงสร้างข้อสอบ:
                    1. สร้างข้อสอบปรนัยจำนวน {num_questions} ข้อ (ตัวเลือก ก, ข, ค, ง)
                    2. กำหนดระดับความยากระดับที่ {difficulty_level}/5 ซึ่งมีลักษณะคือ: {difficulty_desc[difficulty_level]}
                    
                    ข้อบังคับสำคัญที่สุด:
                    1. ข้อสอบแต่ละข้อต้องมีการระบุรหัสตัวชี้วัดหรือผลการเรียนรู้ที่ใช้วัดผลกำกับไว้ด้วยเสมอ (เช่น ตัวชี้วัด/ผลการเรียนรู้: ...)
                    2. ห้ามใช้เครื่องหมายดอกจัน (**) หรือสัญลักษณ์ Markdown ใดๆ ในการตกแต่งข้อความเด็ดขาด ให้ใช้การขึ้นบรรทัดใหม่ธรรมดาเท่านั้น
                    3. คุณต้องแบ่ง 'ส่วนข้อสอบ' และ 'ส่วนเฉลย' ออกจากกัน โดยพิมพ์คำว่า ---SPLIT--- คั่นกลางระหว่างสองส่วนนี้เท่านั้น

                    ตัวชี้วัดหลักสูตรอ้างอิง:
                    {indicator_text[:3000]}

                    เนื้อหาบทเรียนอ้างอิง:
                    {raw_text[:6000]}
                    """
                    
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt
                        )
                        result_text = response.text
                    except errors.APIError as e:
                        st.error("⚠️ เซิร์ฟเวอร์ระบบ AI ของ Google กำลังหนาแน่นในขั้นตอนการ Gen ข้อสอบ กรุณารอสักครู่แล้วลองกดใหม่อีกครั้งครับ")
                        st.stop()

                    if "---SPLIT---" in result_text:
                        questions, answers = result_text.split("---SPLIT---")
                    else:
                        questions = result_text
                        answers = "AI ไม่ได้แบ่งหน้าเฉลยตามคำสั่ง โปรดลองกดใหม่อีกครั้ง"

                    st.success("🎉 ดำเนินการสร้างข้อสอบตามตัวชี้วัดสำเร็จ!")
                    
                    with st.expander("👀 ตรวจสอบความถูกต้องของข้อสอบก่อนปรินต์"):
                        st.subheader("ส่วนหน้าข้อสอบ")
                        st.write(questions)
                        st.markdown("---")
                        st.subheader("<h3>ส่วนหน้าเฉลย</h3>", unsafe_allow_html=True)
                        st.write(answers)

                    # --- กระบวนการสร้างไฟล์ PDF ---
                    pdf = FPDF()
                    pdf.add_font("THSarabun", "", "THSarabunNew.ttf")
                    
                    pdf.add_page()
                    pdf.set_font("THSarabun", size=20)
                    pdf.cell(0, 15, text=f"ชุดข้อสอบอิงตัวชี้วัด (ระดับความยาก: {difficulty_level}/5)", align="C", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("THSarabun", size=16)
                    pdf.multi_cell(0, 8, text=questions.strip())
                    
                    pdf.add_page()
                    pdf.set_font("THSarabun", size=20)
                    pdf.cell(0, 15, text="เฉลยข้อสอบอย่างละเอียดอ้างอิงตัวชี้วัด (สำหรับผู้สอน)", align="C", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("THSarabun", size=16)
                    pdf.multi_cell(0, 8, text=answers.strip())
                    
                    pdf_filename = "Smart_exam_indicator_driven.pdf"
                    pdf.output(pdf_filename)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    with open(pdf_filename, "rb") as pdf_file:
                        st.download_button(
                            label="📥 บันทึกเป็นไฟล์ PDF (จัดหน้าพร้อมพิมพ์)",
                            data=pdf_file,
                            file_name=pdf_filename,
                            mime="application/pdf"
                        )
            
            # ❌ เคสตัวชี้วัดไม่ตรงกับเนื้อหาหลักสูตร
            else:
                st.error(f"❌ ไม่สามารถสร้างข้อสอบได้: ระบบตรวจพบว่า 'ตัวชี้วัด' และ 'เอกสารเนื้อหาบทเรียน' ไม่มีความสอดคล้องกัน (ผลวิเคราะห์จาก AI: {val_result}) กรุณาตรวจสอบไฟล์ใหม่อีกครั้งครับ")
        
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดทั่วไปในระบบ: {e}")
                # 1. สกัดข้อความจากไฟล์บทเรียน
                reader_content = PyPDF2.PdfReader(uploaded_file)
                raw_text = "".join([page.extract_text() + "\n" for page in reader_content.pages if page.extract_text()])
                
                # 2. สกัดข้อความจากไฟล์ตัวชี้วัด
                reader_indicator = PyPDF2.PdfReader(uploaded_indicator)
                indicator_text = "".join([page.extract_text() + "\n" for page in reader_indicator.pages if page.extract_text()])
                
                # เรียกใช้งาน Client
                client = genai.Client(api_key=api_key)
                
                # 3. ส่งคำสั่งให้ AI ตรวจสอบความเข้ากันได้
                validation_prompt = f"""คุณคือผู้เชี่ยวชาญด้านการประกันคุณภาพและหลักสูตรการศึกษา จงตรวจสอบความสอดคล้องระหว่าง "เนื้อหาบทเรียน" และ "ตัวชี้วัดหลักสูตร/ผลการเรียนรู้" ที่กำหนดด้านล่างนี้
                วิเคราะห์ว่าเนื้อหาบทเรียนนี้ตรงตามวิชาและสามารถนำไปใช้ออกข้อสอบเพื่อวัดผลตามตัวชี้วัดที่ให้มาได้จริงหรือไม่

                เนื้อหาบทเรียน:
                {raw_text[:4000]}

                ตัวชี้วัดหลักสูตร/ผลการเรียนรู้:
                {indicator_text[:4000]}

                ข้อบังคับการตอบกลับ:
                หากสอดคล้องกันและอยู่ในวิชา/ศาสตร์เดียวกัน ให้ตอบว่า MATCH
                หากขัดแย้งกันอย่างสิ้นเชิง (เช่น เนื้อหาวิทยาศาสตร์ แต่ตัวชี้วัดภาษาไทย) ให้ตอบว่า MISMATCH
                ให้ตอบสั้นๆ เพียงคำเดียวเท่านั้น ห้ามมีคำอธิบายอื่นผสม
                """
                
                val_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=validation_prompt
                )
                
                # ทำความสะอาดข้อมูลสตริง ตัดช่องว่างและเครื่องหมายคำพูดออกทั้งหมด
                val_result = val_response.text.strip().replace('"', '').replace("'", "").upper()
                
                # 🎯 ตรวจสอบจับคำว่า MATCH เป็นด่านเปิดทางหลักเพื่อป้องกันความผิดพลาด
                if "MATCH" in val_result and "MISMATCH" not in val_result:
                    st.toast("✅ ตรวจสอบความสอดคล้องผ่าน! กำลังเริ่มออกแบบข้อสอบ...", icon="🧠")
                    
                    with st.spinner("✍️ ขั้นตอนที่ 2: AI กำลังสังเคราะห์และออกแบบข้อสอบตามตัวชี้วัด..."):
                        prompt = f"""จากเนื้อหาบทเรียน จงสร้างชุดข้อสอบและใบงาน โดยอ้างอิงและวัดผลให้ตรงตาม "ตัวชี้วัดหลักสูตร/ผลการเรียนรู้" ที่กำหนดไว้อย่างเคร่งครัด

                        เงื่อนไขโครงสร้างข้อสอบ:
                        1. สร้างข้อสอบปรนัยจำนวน {num_questions} ข้อ (ตัวเลือก ก, ข, ค, ง)
                        2. กำหนดระดับความยากระดับที่ {difficulty_level}/5 ซึ่งมีลักษณะคือ: {difficulty_desc[difficulty_level]}
                        
                        ข้อบังคับสำคัญที่สุด:
                        1. ข้อสอบแต่ละข้อต้องมีการระบุรหัสตัวชี้วัดหรือผลการเรียนรู้ที่ใช้วัดผลกำกับไว้ด้วยเสมอ (เช่น ตัวชี้วัด/ผลการเรียนรู้: ...)
                        2. ห้ามใช้เครื่องหมายดอกจัน (**) หรือสัญลักษณ์ Markdown ใดๆ ในการตกแต่งข้อความเด็ดขาด ให้ใช้การขึ้นบรรทัดใหม่ธรรมดาเท่านั้น
                        3. คุณต้องแบ่ง 'ส่วนข้อสอบ' และ 'ส่วนเฉลย' ออกจากกัน โดยพิมพ์คำว่า ---SPLIT--- คั่นกลางระหว่างสองส่วนนี้เท่านั้น

                        ตัวชี้วัดหลักสูตรอ้างอิง:
                        {indicator_text[:3000]}

                        เนื้อหาบทเรียนอ้างอิง:
                        {raw_text[:6000]}
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

                        st.success("🎉 ดำเนินการสร้างข้อสอบตามตัวชี้วัดสำเร็จ!")
                        
                        with st.expander("👀 ตรวจสอบความถูกต้องของข้อสอบก่อนปรินต์"):
                            st.subheader("ส่วนหน้าข้อสอบ")
                            st.write(questions)
                            st.markdown("---")
                            st.subheader("ส่วนหน้าเฉลย")
                            st.write(answers)

                        # --- กระบวนการสร้างไฟล์ PDF ---
                        pdf = FPDF()
                        pdf.add_font("THSarabun", "", "THSarabunNew.ttf")
                        
                        pdf.add_page()
                        pdf.set_font("THSarabun", size=20)
                        pdf.cell(0, 15, text=f"ชุดข้อสอบอิงตัวชี้วัด (ระดับความยาก: {difficulty_level}/5)", align="C", new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("THSarabun", size=16)
                        pdf.multi_cell(0, 8, text=questions.strip())
                        
                        pdf.add_page()
                        pdf.set_font("THSarabun", size=20)
                        pdf.cell(0, 15, text="เฉลยข้อสอบอย่างละเอียดอ้างอิงตัวชี้วัด (สำหรับผู้สอน)", align="C", new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("THSarabun", size=16)
                        pdf.multi_cell(0, 8, text=answers.strip())
                        
                        pdf_filename = "Smart_exam_indicator_driven.pdf"
                        pdf.output(pdf_filename)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        with open(pdf_filename, "rb") as pdf_file:
                            st.download_button(
                                label="📥 บันทึกเป็นไฟล์ PDF (จัดหน้าพร้อมพิมพ์)",
                                data=pdf_file,
                                file_name=pdf_filename,
                                mime="application/pdf"
                            )
                
                # ❌ เคสที่ไม่ผ่านการคัดกรอง ขัดแย้งกันชัดเจน
                else:
                    st.error(f"❌ ไม่สามารถสร้างข้อสอบได้: ระบบตรวจพบว่า 'ตัวชี้วัด' และ 'เอกสารเนื้อหาบทเรียน' ไม่มีความสอดคล้องกัน (ผลวิเคราะห์จาก AI: {val_result}) กรุณาตรวจสอบไฟล์ใหม่อีกครั้งครับ")
            
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในระบบ: {e}")
                # 1. สกัดข้อความจากไฟล์บทเรียน
                reader_content = PyPDF2.PdfReader(uploaded_file)
                raw_text = "".join([page.extract_text() + "\n" for page in reader_content.pages if page.extract_text()])
                
                # 2. สกัดข้อความจากไฟล์ตัวชี้วัด
                reader_indicator = PyPDF2.PdfReader(uploaded_indicator)
                indicator_text = "".join([page.extract_text() + "\n" for page in reader_indicator.pages if page.extract_text()])
                
                # เรียกใช้งาน Client
                client = genai.Client(api_key=api_key)
                
                # 3. ส่งคำสั่งให้ AI ตรวจสอบความเข้ากันได้
                validation_prompt = f"""คุณคือผู้เชี่ยวชาญด้านการประกันคุณภาพและหลักสูตรการศึกษา จงตรวจสอบความสอดคล้องระหว่าง "เนื้อหาบทเรียน" และ "ตัวชี้วัดหลักสูตร/ผลการเรียนรู้" ที่กำหนดด้านล่างนี้
                วิเคราะห์ว่าเนื้อหาบทเรียนนี้ตรงตามวิชาและสามารถนำไปใช้ออกข้อสอบเพื่อวัดผลตามตัวชี้วัดที่ให้มาได้จริงหรือไม่

                เนื้อหาบทเรียน:
                {raw_text[:4000]}

                ตัวชี้วัดหลักสูตร/ผลการเรียนรู้:
                {indicator_text[:4000]}

                ข้อบังคับการตอบกลับ:
                หากสอดคล้องกันและอยู่ในวิชา/ศาสตร์เดียวกัน ให้ตอบว่า MATCH
                หากขัดแย้งกันอย่างสิ้นเชิง (เช่น เนื้อหาวิทยาศาสตร์ แต่ตัวชี้วัดภาษาไทย) ให้ตอบว่า MISMATCH
                ให้ตอบสั้นๆ เพียงคำเดียวเท่านั้น ห้ามมีคำอธิบายอื่นผสม
                """
                
                val_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=validation_prompt
                )
                
                # ทำความสะอาดข้อมูลผลลัพธ์ ตัดช่องว่าง/เครื่องหมายคำพูดที่ AI อาจจะแถมมา ออกให้หมด
                val_result = val_response.text.strip().replace('"', '').replace("'", "").upper()
                
                # 🎯 [ปรับปรุงลอจิก] ตรวจสอบเน้นเอาคำว่า MATCH เป็นด่านเปิดทางหลัก เพื่อกัน AI เอ๋อพ่นข้อความยาว
                if "MATCH" in val_result and "MISMATCH" not in val_result:
                    st.toast("✅ ตรวจสอบความสอดคล้องผ่าน! กำลังเริ่มออกแบบข้อสอบ...", icon="🧠")
                    
                    with st.spinner("✍️ ขั้นตอนที่ 2: AI กำลังสังเคราะห์และออกแบบข้อสอบตามตัวชี้วัด..."):
                        prompt = f"""จากเนื้อหาบทเรียน จงสร้างชุดข้อสอบและใบงาน โดยอ้างอิงและวัดผลให้ตรงตาม "ตัวชี้วัดหลักสูตร/ผลการเรียนรู้" ที่กำหนดไว้อย่างเคร่งครัด

                        เงื่อนไขโครงสร้างข้อสอบ:
                        1. สร้างข้อสอบปรนัยจำนวน {num_questions} ข้อ (ตัวเลือก ก, ข, ค, ง)
                        2. 定กำหนดระดับความยากระดับที่ {difficulty_level}/5 ซึ่งมีลักษณะคือ: {difficulty_desc[difficulty_level]}
                        
                        ข้อบังคับสำคัญที่สุด:
                        1. ข้อสอบแต่ละข้อต้องมีการระบุรหัสตัวชี้วัดหรือผลการเรียนรู้ที่ใช้วัดผลกำกับไว้ด้วยเสมอ (เช่น ตัวชี้วัด/ผลการเรียนรู้: ...)
                        2. ห้ามใช้เครื่องหมายดอกจัน (**) หรือสัญลักษณ์ Markdown ใดๆ ในการตกแต่งข้อความเด็ดขาด ให้ใช้การขึ้นบรรทัดใหม่ธรรมดาเท่านั้น
                        3. คุณต้องแบ่ง 'ส่วนข้อสอบ' และ 'ส่วนเฉลย' ออกจากกัน โดยพิมพ์คำว่า ---SPLIT--- คั่นกลางระหว่างสองส่วนนี้เท่านั้น

                        ตัวชี้วัดหลักสูตรอ้างอิง:
                        {indicator_text[:3000]}

                        เนื้อหาบทเรียนอ้างอิง:
                        {raw_text[:6000]}
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

                        st.success("🎉 ดำเนินการสร้างข้อสอบตามตัวชี้วัดสำเร็จ!")
                        
                        with st.expander("👀 ตรวจสอบความถูกต้องของข้อสอบก่อนปรินต์"):
                            st.subheader("ส่วนหน้าข้อสอบ")
                            st.write(questions)
                            st.markdown("---")
                            st.subheader("ส่วนหน้าเฉลย")
                            st.write(answers)

                        # --- กระบวนการสร้างไฟล์ PDF ---
                        pdf = FPDF()
                        pdf.add_font("THSarabun", "", "THSarabunNew.ttf")
                        
                        pdf.add_page()
                        pdf.set_font("THSarabun", size=20)
                        pdf.cell(0, 15, text=f"ชุดข้อสอบอิงตัวชี้วัด (ระดับความยาก: {difficulty_level}/5)", align="C", new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("THSarabun", size=16)
                        pdf.multi_cell(0, 8, text=questions.strip())
                        
                        pdf.add_page()
                        pdf.set_font("THSarabun", size=20)
                        pdf.cell(0, 15, text="เฉลยข้อสอบอย่างละเอียดอ้างอิงตัวชี้วัด (สำหรับผู้สอน)", align="C", new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("THSarabun", size=16)
                        pdf.multi_cell(0, 8, text=answers.strip())
                        
                        pdf_filename = "Smart_exam_indicator_driven.pdf"
                        pdf.output(pdf_filename)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        with open(pdf_filename, "rb") as pdf_file:
                            st.download_button(
                                label="📥 บันทึกเป็นไฟล์ PDF (จัดหน้าพร้อมพิมพ์)",
                                data=pdf_file,
                                file_name=pdf_filename,
                                mime="application/pdf"
                            )
                
                # ❌ เคสที่ไม่ผ่านการคัดกรอง ขัดแย้งกันชัดเจน
                else:
                    st.error(f"❌ ไม่สามารถสร้างข้อสอบได้: ระบบตรวจพบว่า 'ตัวชี้วัด' และ 'เอกสารเนื้อหาบทเรียน' ไม่มีความสอดคล้องกัน (ผลวิเคราะห์จาก AI: {val_result}) กรุณาตรวจสอบไฟล์ใหม่อีกครั้งครับ")
            
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในระบบ: {e}")
                # 1. สกัดข้อความจากไฟล์บทเรียน
                reader_content = PyPDF2.PdfReader(uploaded_file)
                raw_text = "".join([page.extract_text() + "\n" for page in reader_content.pages if page.extract_text()])
                
                # 2. สกัดข้อความจากไฟล์ตัวชี้วัด
                reader_indicator = PyPDF2.PdfReader(uploaded_indicator)
                indicator_text = "".join([page.extract_text() + "\n" for page in reader_indicator.pages if page.extract_text()])
                
                # เรียกใช้งาน Client
                client = genai.Client(api_key=api_key)
                
                # 3. ส่งคำสั่งให้ AI ทำการตรวจสอบความเข้ากันได้ (Validation)
                validation_prompt = f"""คุณคือผู้เชี่ยวชาญด้านการประกันคุณภาพการศึกษา จงตรวจสอบความสอดคล้องระหว่าง "เนื้อหาบทเรียน" และ "ตัวชี้วัดหลักสูตร" ที่กำหนดด้านล่างนี้ 
                ว่าเนื้อหาบทเรียนนี้สามารถใช้ออกข้อสอบเพื่อวัดผลตามตัวชี้วัดที่ให้มาได้จริงหรือไม่ (เช่น ไม่ใช่เนื้อหาคนละวิชา หรือคนละระดับชั้นที่ขัดแย้งกันอย่างสิ้นเชิง)

                เนื้อหาบทเรียน:
                {raw_text[:4000]}

                ตัวชี้วัดหลักสูตร:
                {indicator_text[:4000]}

                ข้อบังคับการตอบกลับ:
                ให้ตอบกลับเป็นโครงสร้างรูปแบบนี้คำเดียวเท่านั้น ห้ามมีคำอธิบายอื่นผสม:
                [RESULT]=MATCH หรือ [RESULT]=MISMATCH
                """
                
                val_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=validation_prompt
                )
                
                val_result = val_response.text.strip()
                
                # ❌ เคสตรวจสอบแล้วพบว่าขัดแย้ง ไม่สอดคล้องกัน (เช่น สังคม กับ วิทยาศาสตร์)
                if "[RESULT]=MISMATCH" in val_result or "MISMATCH" in val_result.upper():
                    st.error("❌ ไม่สามารถสร้างข้อสอบได้: เนื่องจาก 'ตัวชี้วัด' และ 'เนื้อหาเอกสารบทเรียน' ไม่มีความสอดคล้องกัน กรุณาตรวจสอบและอัปโหลดไฟล์ใหม่อีกครั้งครับ")
                
                # ✅ ผ่านการคัดกรอง เดินหน้าสร้างข้อสอบต่อทันที
                else:
                    st.toast("✅ ตรวจสอบความสอดคล้องผ่าน! กำลังเริ่มออกแบบข้อสอบ...", icon="🧠")
                    
                    with st.spinner("✍️ ขั้นตอนที่ 2: AI กำลังสังเคราะห์และออกแบบข้อสอบตามตัวชี้วัด..."):
                        prompt = f"""จากเนื้อหาบทเรียน จงสร้างชุดข้อสอบและใบงาน โดยอ้างอิงและวัดผลให้ตรงตาม "ตัวชี้วัดหลักสูตร" ที่กำหนดไว้อย่างเคร่งครัด

                        เงื่อนไขโครงสร้างข้อสอบ:
                        1. สร้างข้อสอบปรนัยจำนวน {num_questions} ข้อ (ตัวเลือก ก, ข, ค, ง)
                        2. กำหนดระดับความยากระดับที่ {difficulty_level}/5 ซึ่งมีลักษณะคือ: {difficulty_desc[difficulty_level]}
                        
                        ข้อบังคับสำคัญที่สุด:
                        1. ข้อสอบแต่ละข้อต้องมีการระบุรหัสตัวชี้วัดหรือหัวข้อตัวชี้วัดกำกับไว้ด้วยเสมอ (เช่น วัดตามตัวชี้วัด: ...)
                        2. ห้ามใช้เครื่องหมายดอกจัน (**) หรือสัญลักษณ์ Markdown ใดๆ ในการตกแต่งข้อความเด็ดขาด ให้ใช้การขึ้นบรรทัดใหม่ธรรมดาเท่านั้น
                        3. คุณต้องแบ่ง 'ส่วนข้อสอบ' และ 'ส่วนเฉลย' ออกจากกัน โดยพิมพ์คำว่า ---SPLIT--- คั่นกลางระหว่างสองส่วนนี้เท่านั้น

                        ตัวชี้วัดหลักสูตรอ้างอิง:
                        {indicator_text[:3000]}

                        เนื้อหาบทเรียนอ้างอิง:
                        {raw_text[:6000]}
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

                        st.success("🎉 ดำเนินการสร้างข้อสอบตามตัวชี้วัดสำเร็จ!")
                        
                        with st.expander("👀 ตรวจสอบความถูกต้องของข้อสอบก่อนปรินต์"):
                            st.subheader("ส่วนหน้าข้อสอบ")
                            st.write(questions)
                            st.markdown("---")
                            st.subheader("ส่วนหน้าเฉลย")
                            st.write(answers)

                        # --- กระบวนการสร้างไฟล์ PDF หลังผ่านด่านตรวจสอบข้อมูล ---
                        pdf = FPDF()
                        pdf.add_font("THSarabun", "", "THSarabunNew.ttf")
                        
                        pdf.add_page()
                        pdf.set_font("THSarabun", size=20)
                        pdf.cell(0, 15, text=f"ชุดข้อสอบอิงตัวชี้วัด (ระดับความยาก: {difficulty_level}/5)", align="C", new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("THSarabun", size=16)
                        pdf.multi_cell(0, 8, text=questions.strip())
                        
                        pdf.add_page()
                        pdf.set_font("THSarabun", size=20)
                        pdf.cell(0, 15, text="เฉลยข้อสอบอย่างละเอียดอ้างอิงตัวชี้วัด (สำหรับผู้สอน)", align="C", new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("THSarabun", size=16)
                        pdf.multi_cell(0, 8, text=answers.strip())
                        
                        pdf_filename = "Smart_exam_indicator_driven.pdf"
                        pdf.output(pdf_filename)
                        
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
                
                prompt = f"""จากเนื้อหาต่อไปนี้ จงสร้างชุดข้อสอบและใบงานตามเงื่อนไขที่กำหนดอย่างเคร่งครัด
                เงื่อนไขข้อสอบ:
                1. สร้างข้อสอบปรนัยจำนวน {num_questions} ข้อ (ตัวเลือก ก, ข, ค, ง)
                2. กำหนดระดับความยากระดับที่ {difficulty_level}/5 ซึ่งมีลักษณะคือ: {difficulty_desc[difficulty_level]}
                ข้อบังคับสำคัญที่สุด:
                1. ห้ามใช้เครื่องหมายดอกจัน (**) หรือสัญลักษณ์ Markdown ใดๆ ในการตกแต่งข้อความเด็ดขาด ให้ใช้การขึ้นบรรทัดใหม่ธรรมดาเท่านั้น
                2. คุณต้องแบ่ง 'ส่วนข้อสอบ' และ 'ส่วนเฉลย' ออกจากกัน โดยพิมพ์คำว่า ---SPLIT--- คั่นกลางระหว่างสองส่วนนี้เท่านั้น
                รูปแบบการตอบกลับ:
                [ส่วนที่ 1: ข้อสอบปรนัยจำนวน {num_questions} ข้อ]
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
                
                pdf_filename = "Smart_exam_generator.pdf"
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

