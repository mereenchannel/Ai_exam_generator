import streamlit as st
from google import genai
from google.genai import errors
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

# --- ฟังก์ชันหลักในการสกัดข้อความออกจากไฟล์ PDF ---
def get_pdf_text(uploaded_pdf):
    if not uploaded_pdf:
        return ""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_pdf)
        text_content = []
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content.append(page_text + "\n")
        return "".join(text_content)
    except Exception:
        return ""

# --- UI หน้าเว็บหลัก ---
st.markdown("### 1. อัปโหลดเอกสารที่เกี่ยวข้อง")
col_file1, col_file2 = st.columns(2)
with col_file1:
    uploaded_file = st.file_uploader("📥 อัปโหลดเอกสารบทเรียน (PDF) *จำเป็น", type=["pdf"], key="pdf_uploader")
with col_file2:
    uploaded_indicator = st.file_uploader("🎯 อัปโหลดตัวชี้วัด/หลักสูตร (PDF) *ไม่บังคับ", type=["pdf"], key="indicator_uploader")

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

# --- ปุ่มประมวลผลหลัก ---
if st.button("✨ เริ่มวิเคราะห์และสร้างข้อสอบ"):
    if not uploaded_file:
        st.warning("⚠️ กรุณาอัปโหลดไฟล์ 'เอกสารบทเรียน' เพื่อใช้เป็นฐานข้อมูลในการออกข้อสอบครับ")
    else:
        try:
            # สกัดเนื้อหาบทเรียนหลัก
            raw_text = get_pdf_text(uploaded_file)
            client = genai.Client(api_key=api_key)
            
            # ตั้งค่า flag สำหรับตรวจสอบผ่านด่านเปิดทาง
            should_generate = False
            val_result = "NONE"
            indicator_text = ""

            # 🧭 ตรวจสอบสถานะการอัปโหลดไฟล์ตัวชี้วัด
            if uploaded_indicator:
                # ─── โหมดที่ 1: มีการอัปโหลดไฟล์ตัวชี้วัด -> ต้องผ่านด่านตรวจความสอดคล้องกันก่อน ───
                indicator_text = get_pdf_text(uploaded_indicator)
                
                with st.spinner("🧠 มีการแนบไฟล์ตัวชี้วัด: AI กำลังตรวจสอบความสอดคล้องเชิงลึก..."):
                    validation_prompt = f"""คุณคืออาจารย์ผู้เชี่ยวชาญด้านหลักสูตรและการศึกษา จงวิเคราะห์ความเชื่อมโยงระหว่าง "เนื้อหาบทเรียน" และ "ตัวชี้วัดหลักสูตร/ผลการเรียนรู้" ด้านล่างนี้

                    เนื้อหาบทเรียน:
                    {raw_text[:5000]}

                    ตัวชี้วัดหลักสูตร/ผลการเรียนรู้:
                    {indicator_text[:4000]}

                    เกณฑ์การตัดสินใจอย่างยืดหยุ่น:
                    1. หากเนื้อหาเอกสารและตัวชี้วัดเป็นวิชาเดียวกัน หรือศาสตร์เดียวกัน และเนื้อหาบทเรียนสามารถนำไปใช้ออกข้อสอบเพื่อวัดผล "หัวข้อใดหัวข้อหนึ่ง" ในตัวชี้วัดได้ ให้ถือว่าสอดคล้องกัน ทันที
                    2. จะตัดสินว่าเป็น MISMATCH ก็ต่อเมื่อ เป็นการอัปโหลดไฟล์ผิดวิชาอย่างชัดเจนและร้ายแรงเท่านั้น (เช่น เนื้อหาคณิตศาสตร์ แต่ตัวชี้วัดเป็นภาษาไทย)

                    ข้อบังคับการตอบกลับ:
                    หากเข้าเกณฑ์ข้อ 1 (ผ่าน) ให้ตอบสั้นๆ คำเดียวว่า: MATCH
                    หากเข้าเกณฑ์ข้อ 2 (ปฏิเสธ) ให้ตอบสั้นๆ คำเดียวว่า: MISMATCH
                    ห้ามพิมพ์คำอธิบายอื่นใดเพิ่มเติมเด็ดขาด
                    """
                    
                    try:
                        val_response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=validation_prompt
                        )
                        val_result = val_response.text.strip().replace('"', '').replace("'", "").upper()
                    except errors.APIError:
                        st.error("⚠️ เซิร์ฟเวอร์ระบบ AI ของ Google กำลังหนาแน่นชั่วคราว (503 Unavailable) กรุณารอสัก 10 วินาทีแล้วกดปุ่มเริ่มใหม่อีกครั้งครับ")
                        st.stop()
                
                if "MATCH" in val_result and "MISMATCH" not in val_result:
                    should_generate = True
                    st.toast("✅ ตัวชี้วัดสอดคล้องกับเนื้อหา! ผ่านเกณฑ์", icon="🧠")
                else:
                    should_generate = False
            else:
                # ─── โหมดที่ 2: ไม่ได้ใส่ไฟล์ตัวชี้วัด -> ปล่อยผ่านให้วิ่งออกจากเนื้อหาตรงๆ เลย ทันที ───
                should_generate = True
                st.toast("📝 ไม่พบการแนบไฟล์ตัวชี้วัด: AI เปลี่ยนระบบเข้าสู่โหมดสร้างข้อสอบจากเนื้อหาโดยตรง", icon="🚀")

            # ✍️ ขั้นตอนถัดไป: กระบวนการคลอดข้อสอบ (ตามเงื่อนไขโหมดการทำงาน)
            if should_generate:
                with st.spinner("✍️ AI กำลังวิเคราะห์และอัญเชิญข้อสอบตามโครงสร้าง..."):
                    
                    if uploaded_indicator:
                        # Prompt คุมเข้มแบบอิงตัวชี้วัด
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
                    else:
                        # Prompt คลีนแบบสกัดเพียวจากเนื้อหาบทเรียนโดยตรง
                        prompt = f"""จากเนื้อหาบทเรียนที่กำหนดให้ จงสร้างชุดข้อสอบและใบงานประเมินผลการเรียนรู้โดยอิงจากรายละเอียดในเอกสารโดยตรง

                        เงื่อนไขโครงสร้างข้อสอบ:
                        1. สร้างข้อสอบปรนัยจำนวน {num_questions} ข้อ (ตัวเลือก ก, ข, ค, ง)
                        2. 定กำหนดระดับความยากระดับที่ {difficulty_level}/5 ซึ่งมีลักษณะคือ: {difficulty_desc[difficulty_level]}
                        
                        ข้อบังคับสำคัญที่สุด:
                        1. ห้ามใช้เครื่องหมายดอกจัน (**) หรือสัญลักษณ์ Markdown ใดๆ ในการตกแต่งข้อความเด็ดขาด ให้ใช้การขึ้นบรรทัดใหม่ธรรมดาเท่านั้น
                        2. คุณต้องแบ่ง 'ส่วนข้อสอบ' และ 'ส่วนเฉลย' ออกจากกัน โดยพิมพ์คำว่า ---SPLIT--- คั่นกลางระหว่างสองส่วนนี้เท่านั้น

                        เนื้อหาบทเรียนอ้างอิง:
                        {raw_text[:7000]}
                        """
                    
                    try:
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt
                        )
                        result_text = response.text
                    except errors.APIError:
                        st.error("⚠️ เซิร์ฟเวอร์ระบบ AI ของ Google กำลังหนาแน่นในขั้นตอนการ Gen ข้อสอบ กรุณารอสักครู่แล้วลองกดใหม่อีกครั้งครับ")
                        st.stop()

                    if "---SPLIT---" in result_text:
                        questions, answers = result_text.split("---SPLIT---")
                    else:
                        questions = result_text
                        answers = "AI ไม่ได้แบ่งหน้าเฉลยตามคำสั่ง โปรดลองกดใหม่อีกครั้ง"

                    st.success("🎉 ดำเนินการสร้างข้อสอบสำเร็จ!")
                    
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
                    header_title = f"ชุดข้อสอบอิงตัวชี้วัด (ระดับความยาก: {difficulty_level}/5)" if uploaded_indicator else f"ชุดข้อสอบและใบงานจากเนื้อหาบทเรียน (ระดับความยาก: {difficulty_level}/5)"
                    pdf.cell(0, 15, text=header_title, align="C", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("THSarabun", size=16)
                    pdf.multi_cell(0, 8, text=questions.strip())
                    
                    pdf.add_page()
                    pdf.set_font("THSarabun", size=20)
                    pdf.cell(0, 15, text="เฉลยข้อสอบอย่างละเอียด (สำหรับผู้สอน)", align="C", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("THSarabun", size=16)
                    pdf.multi_cell(0, 8, text=answers.strip())
                    
                    pdf_filename = "Smart_exam_generator_pro.pdf"
                    pdf.output(pdf_filename)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    with open(pdf_filename, "rb") as pdf_file:
                        st.download_button(
                            label="📥 บันทึกเป็นไฟล์ PDF (จัดหน้าพร้อมพิมพ์)",
                            data=pdf_file,
                            file_name=pdf_filename,
                            mime="application/pdf"
                        )
            else:
                # กรณีผลประเมินระบุว่า MISMATCH
                st.error(f"❌ ไม่สามารถสร้างข้อสอบได้: เนื่องจากไฟล์ 'ตัวชี้วัด' และ 'เนื้อหาเอกสารบทเรียน' ที่ส่งขึ้นมาไม่มีความสอดคล้องกันอย่างรุนแรง (ผลวิเคราะห์จาก AI: {val_result}) กรุณาตรวจสอบหรือถอดไฟล์ตัวชี้วัดออกเพื่ออกข้อสอบจากเนื้อหาโดยตรงครับ")
        
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดทั่วไปในระบบ: {e}")
