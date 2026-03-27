import streamlit as st
import difflib
import re

# พยายาม Import fitz (PyMuPDF) สำหรับ PDF
try:
    import fitz
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

# ==========================================
# ตั้งค่าหน้าเว็บ (Web Page Configuration)
# ==========================================
st.set_page_config(
    page_title="Text, Table & PDF Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ------------------------------------------
# การตั้งค่า Session State (สำหรับปุ่มล้างข้อมูล)
# ------------------------------------------
if "t1" not in st.session_state: st.session_state["t1"] = ""
if "t2" not in st.session_state: st.session_state["t2"] = ""
if "tbl1" not in st.session_state: st.session_state["tbl1"] = ""
if "tbl2" not in st.session_state: st.session_state["tbl2"] = ""

def clear_text_tab():
    st.session_state["t1"] = ""
    st.session_state["t2"] = ""

def clear_table_tab():
    st.session_state["tbl1"] = ""
    st.session_state["tbl2"] = ""

# ==========================================
# Custom CSS
# ==========================================
st.markdown("""
    <style>
    .diff-box {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 20px;
        font-family: 'Helvetica', sans-serif;
        font-size: 16px;
        line-height: 1.6;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        max-height: 400px;
        overflow-y: auto;
        color: #000000; 
    }
    .equal-text { color: #000000; }
    .delete-text { color: #dc3545; text-decoration: line-through; background-color: #f8d7da; padding: 0 4px; border-radius: 4px; font-weight: bold;}
    .insert-text { color: #198754; font-weight: bold; background-color: #d1e7dd; padding: 0 4px; border-radius: 4px;}
    
    .stTabs[data-baseweb="tab-list"] button[data-testid="stMarkdownContainer"] p {
        font-size: 18px;
        font-weight: bold;
    }
    .legend-box {
        background-color: #f8f9fa;
        padding: 10px 15px;
        border-radius: 6px;
        border-left: 4px solid #6c757d;
        margin-bottom: 15px;
        font-size: 15px;
        color: #000000;
    }
    
    div[data-baseweb="textarea"] {
        border: 2px solid #333333 !important;
        border-radius: 6px !important;
        background-color: #ffffff !important;
    }
    div[data-baseweb="textarea"] textarea {
        white-space: pre !important;
        overflow-wrap: normal !important;
        overflow-x: scroll !important;
        font-family: 'Courier New', Courier, monospace !important;
        background-color: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        caret-color: #000000 !important;
    }
    
    /* CSS สำหรับตารางผลลัพธ์ */
    .result-table-container {
        overflow: auto; 
        max-height: 600px; 
        border: 1px solid #cccccc; 
        margin-top: 15px;
        border-radius: 4px;
    }
    .result-table {
        width: 100%; 
        border-collapse: collapse; 
        font-size: 14px; 
        background-color: #ffffff; 
        color: #000000;
        font-family: 'Helvetica', sans-serif;
    }
    .result-table th {
        border: 1px solid #bbbbbb; 
        padding: 10px; 
        text-align: center; 
        background-color: #e9ecef !important; 
        color: #000000 !important;
        position: sticky; 
        top: 0; 
        z-index: 1;
        font-weight: bold;
    }
    .result-table td {
        border: 1px solid #dddddd; 
        padding: 10px; 
        color: #000000;
        vertical-align: top;
    }
    .td-match { background-color: #ffffff; }
    .td-empty { background-color: #f4f4f4; }
    .td-mismatch {
        border: 2px solid #dc3545 !important;
        background-color: #ffe6e6 !important;
    }
    .row-number {
        background-color: #e9ecef !important; 
        font-weight: bold; 
        text-align: center;
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# ส่วนฟังก์ชันแกนหลัก (Core Logic)
# ==========================================

def clean_text(text):
    if not text: return ""
    return re.sub(r'\s+', '', text)

def clean_cell_text(text):
    if not text: return ""
    return re.sub(r' +', '', text)

def parse_table_data(raw_text):
    if not raw_text or not raw_text.strip(): return[]
    lines = raw_text.replace('\r', '').strip('\n').split('\n')
    return [line.split('\t') for line in lines]

def get_excel_col_name(col_index):
    result = ""
    while col_index >= 0:
        result = chr(col_index % 26 + 65) + result
        col_index = col_index // 26 - 1
    return result

def count_digital_highlights(pdf_bytes):
    """ฟังก์ชันนับไฮไลท์ พร้อมเก็บรายละเอียดเลขหน้า"""
    if not PDF_SUPPORT:
        return -1,[], "ไม่พบไลบรารี PyMuPDF กรุณาติดตั้ง pip install pymupdf"
    
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_highlights = 0
        page_details =[] # เก็บข้อมูลหน้าที่มีไฮไลท์
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_hl_count = 0
            
            for annot in page.annots():
                if annot.type[1].lower() == 'highlight':
                    page_hl_count += 1
                    total_highlights += 1
            
            # ถ้าน้านี้มีไฮไลท์ ให้บันทึกไว้ (page_num เริ่มจาก 0 เลยต้อง +1 เพื่อให้เข้าใจง่าย)
            if page_hl_count > 0:
                page_details.append({"page": page_num + 1, "count": page_hl_count})
                
        doc.close()
        return total_highlights, page_details, None
    except Exception as e:
        return -1,[], str(e)

def generate_diff_html(cleaned_original, cleaned_compare):
    matcher = difflib.SequenceMatcher(None, cleaned_original, cleaned_compare)
    html_output =[]
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            html_output.append(f"<span class='equal-text'>{cleaned_original[i1:i2]}</span>")
        elif tag == 'delete':
            html_output.append(f"<span class='delete-text'>{cleaned_original[i1:i2]}</span>")
        elif tag == 'insert':
            html_output.append(f"<span class='insert-text'>{cleaned_compare[j1:j2]}</span>")
        elif tag == 'replace':
            html_output.append(f"<span class='delete-text'>{cleaned_original[i1:i2]}</span> ")
            html_output.append(f"<span class='insert-text'>{cleaned_compare[j1:j2]}</span>")
    return "".join(html_output)

# ==========================================
# สร้างหน้าเว็บ (Web UI)
# ==========================================

st.title("🔍 Text, Table & PDF Analyzer")
st.markdown("โปรแกรมตรวจสอบความเหมือน/แตกต่าง ของข้อความ ตาราง และนับไฮไลท์ในไฟล์ PDF")

legend_html = """
<div class="legend-box">
    <strong>คำอธิบายสัญลักษณ์จุดที่ผิดพลาด:</strong><br>
    🔴 พื้นหลังเซลล์ <span style="background-color: #ffe6e6; border: 1px solid #dc3545; padding: 2px 6px; font-weight: bold; color:#000;">สีแดงอ่อน</span> คือ ช่องคอลัมน์และแถวที่ข้อมูล <b>"ไม่ตรงกัน"</b><br>
    ❌ ข้อความ <span class='delete-text'>สีแดง (ขีดฆ่า)</span> คือ ข้อความในต้นฉบับที่ <b>หายไป หรือ พิมพ์ผิด</b><br>
    ✅ ข้อความ <span class='insert-text'>สีเขียว (ตัวหนา)</span> คือ ข้อความที่ถูก <b>เพิ่มเข้ามาใหม่</b> ในช่องเปรียบเทียบ
</div>
"""

tab1, tab2, tab3 = st.tabs(["📝 ตรวจสอบข้อความ", "📊 ตรวจสอบตาราง", "📁 ตรวจสอบไฮไลท์ PDF"])

# ---------------------------------------------------------
# TAB 1: ตรวจสอบข้อความปกติ
# ---------------------------------------------------------
with tab1:
    st.markdown("### 📝 เปรียบเทียบข้อความปกติ")
    col1, col2 = st.columns(2)
    with col1:
        text1 = st.text_area("1. ข้อความต้นฉบับ:", height=200, key="t1")
    with col2:
        text2 = st.text_area("2. ข้อความที่ต้องการเปรียบเทียบ:", height=200, key="t2")
        
    # สร้างคอลัมน์สำหรับปุ่ม ประมวลผล และ ปุ่มล้างข้อมูล
    btn_col1, btn_col2 = st.columns([4, 1])
    with btn_col1:
        submit_text = st.button("🔍 ตรวจสอบข้อความ", type="primary", use_container_width=True)
    with btn_col2:
        st.button("🗑️ ล้างข้อมูล", on_click=clear_text_tab, use_container_width=True, key="clear_text_btn")
        
    if submit_text:
        cleaned_original = clean_text(text1)
        cleaned_compare = clean_text(text2)
        
        if not cleaned_original or not cleaned_compare:
            st.warning("⚠️ กรุณากรอกข้อความให้ครบทั้งสองช่องครับ")
        else:
            matcher = difflib.SequenceMatcher(None, cleaned_original, cleaned_compare)
            sim_percent = matcher.ratio() * 100
            err_percent = 100 - sim_percent
            st.divider()
            m1, m2 = st.columns(2)
            m1.metric("✅ อัตราความคล้ายคลึงระดับตัวอักษร", f"{sim_percent:.2f}%")
            m2.metric("❌ อัตราการผิดพลาดระดับตัวอักษร", f"{err_percent:.2f}%")
            
            st.markdown(legend_html, unsafe_allow_html=True)
            diff_html = generate_diff_html(cleaned_original, cleaned_compare)
            st.markdown(f"<div class='diff-box'>{diff_html}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 2: ตรวจสอบตาราง
# ---------------------------------------------------------
with tab2:
    st.markdown("### 📊 เปรียบเทียบข้อมูลในตาราง")
    st.info("💡 **คำแนะนำ:** กรุณาวางตารางจาก Excel ลงในกล่องสี่เหลี่ยมด้านล่าง (คลิกแล้วกด Ctrl+V) \n\n*ถึงแม้ในกล่องจะไม่มีเส้นตารางเพื่อป้องกันเซลล์เคลื่อน แต่ **เมื่อกดปุ่มตรวจสอบ ระบบจะวาดเส้นตารางแบบ Excel พร้อมไฮไลท์สีแดงให้ดูง่ายๆ ทันทีครับ***")
    
    col3, col4 = st.columns(2)
    with col3:
        table1 = st.text_area("1. ตารางต้นฉบับ:", height=150, key="tbl1")
    with col4:
        table2 = st.text_area("2. ตารางที่ต้องการเปรียบเทียบ:", height=150, key="tbl2")
        
    # สร้างคอลัมน์สำหรับปุ่ม ประมวลผล และ ปุ่มล้างข้อมูล
    btn_col3, btn_col4 = st.columns([4, 1])
    with btn_col3:
        submit_table = st.button("📊 ตรวจสอบตาราง และสร้างตารางเปรียบเทียบ", type="primary", use_container_width=True)
    with btn_col4:
        st.button("🗑️ ล้างข้อมูล", on_click=clear_table_tab, use_container_width=True, key="clear_table_btn")
        
    if submit_table:
        t1 = parse_table_data(table1)
        t2 = parse_table_data(table2)
        
        if not t1 or not t2:
            st.warning("⚠️ กรุณาวางข้อมูลตารางลงในช่องให้ครบทั้งสองฝั่งครับ")
        else:
            max_r = max(len(t1), len(t2))
            max_c = max(max((len(row) for row in t1), default=0), 
                        max((len(row) for row in t2), default=0))
            
            total_matches = 0
            total_length = 0
            html_table = "<div class='result-table-container'><table class='result-table'>"
            html_table += "<thead><tr><th style='min-width: 50px;'>#</th>"
            for c in range(max_c):
                html_table += f"<th style='min-width: 120px;'>{get_excel_col_name(c)}</th>"
            html_table += "</tr></thead><tbody>"
            
            has_diff = False
            
            for r in range(max_r):
                html_table += "<tr>"
                html_table += f"<td class='row-number'>{r+1}</td>"
                
                for c in range(max_c):
                    val1 = clean_cell_text(t1[r][c]) if r < len(t1) and c < len(t1[r]) else ""
                    val2 = clean_cell_text(t2[r][c]) if r < len(t2) and c < len(t2[r]) else ""
                    
                    if not val1 and not val2:
                        html_table += "<td class='td-empty'></td>"
                        continue
                        
                    matcher = difflib.SequenceMatcher(None, val1, val2)
                    t_len = len(val1) + len(val2)
                    total_length += t_len
                    matches_x2 = matcher.ratio() * t_len 
                    total_matches += matches_x2 / 2
                    
                    if val1 == val2:
                        html_table += f"<td class='td-match'>{val1}</td>"
                    else:
                        has_diff = True
                        cell_diff = generate_diff_html(val1, val2)
                        html_table += f"<td class='td-mismatch'>{cell_diff}</td>"
                        
                html_table += "</tr>"
            html_table += "</tbody></table></div>"
            
            sim_percent = (2 * total_matches / total_length * 100) if total_length > 0 else 0.0
            err_percent = 100 - sim_percent
            
            st.divider()
            m1, m2 = st.columns(2)
            m1.metric("✅ อัตราความคล้ายคลึงระดับตัวอักษร", f"{sim_percent:.2f}%")
            m2.metric("❌ อัตราการผิดพลาดระดับตัวอักษร", f"{err_percent:.2f}%")
            
            st.markdown("### 🔍 ผลลัพธ์การเปรียบเทียบ (จุดสีแดงคือข้อมูลที่ไม่ตรงกัน)")
            st.markdown(legend_html, unsafe_allow_html=True)
            
            if not has_diff and sim_percent == 100.0:
                st.success("✅ ข้อมูลในตารางตรงกันทุกตำแหน่ง")
            else:
                st.markdown(html_table, unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 3: ไฮไลท์ใน PDF
# ---------------------------------------------------------
with tab3:
    st.markdown("### 📁 ตรวจสอบและนับไฮไลท์ดิจิตอลในไฟล์ PDF")
    
    if not PDF_SUPPORT:
        st.error("⚠️ ไม่พบไลบรารี PyMuPDF กรุณาติดตั้งผ่าน Terminal ด้วยคำสั่ง: `pip install pymupdf`")
    else:
        uploaded_file = st.file_uploader("📂 เลือกไฟล์ PDF (ระบบจะนับเฉพาะจุดไฮไลท์แถบสีดิจิตอล):", type=['pdf'])
        
        if uploaded_file is not None:
            if st.button("📑 เริ่มนับไฮไลท์ดิจิตอล", type="primary"):
                with st.spinner("⏳ กำลังวิเคราะห์ไฟล์ PDF..."):
                    pdf_bytes = uploaded_file.read()
                    
                    # คืนค่าตัวแปร details มาด้วยเพื่อแจกแจงเลขหน้า
                    count, details, error_msg = count_digital_highlights(pdf_bytes)
                    
                    if error_msg:
                        st.error(f"❌ เกิดข้อผิดพลาด: {error_msg}")
                    else:
                        st.divider()
                        if count == 0:
                            st.info("ไม่พบไฮไลท์ดิจิตอลในไฟล์นี้")
                        else:
                            st.success(f"📊 พบการไฮไลท์แถบสีดิจิตอลทั้งหมด: **{count}** จุด")
                            
                            # แสดงรายละเอียดเลขหน้า
                            st.markdown("#### 📄 รายละเอียดหน้าที่มีไฮไลท์:")
                            for item in details:
                                st.markdown(f"- **หน้าที่ {item['page']}** : พบ {item['count']} จุด")