import streamlit as st
import difflib
import re
import json # นำเข้าไลบรารีสำหรับจัดการ JSON

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
    page_title="โปรแกรมสำหรับวัดผลคะแนนการ POC",
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
if "json1" not in st.session_state: st.session_state["json1"] = ""
if "json2" not in st.session_state: st.session_state["json2"] = ""

def clear_text_tab():
    st.session_state["t1"] = ""
    st.session_state["t2"] = ""

def clear_table_tab():
    st.session_state["tbl1"] = ""
    st.session_state["tbl2"] = ""

def clear_json_tab():
    st.session_state["json1"] = ""
    st.session_state["json2"] = ""

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
    .warning-text { color: #fd7e14; font-weight: bold; background-color: #ffe69c; padding: 0 4px; border-radius: 4px;}
    
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
        text-align: left; 
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
    .td-extra {
        border: 2px solid #198754 !important;
        background-color: #d1e7dd !important;
    }
    .td-warning {
        border: 2px solid #fd7e14 !important;
        background-color: #fff3cd !important;
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
    return[line.split('\t') for line in lines]

def get_excel_col_name(col_index):
    result = ""
    while col_index >= 0:
        result = chr(col_index % 26 + 65) + result
        col_index = col_index // 26 - 1
    return result

# ---------------------------------------------------------
# ฟังก์ชัน PDF อัปเดตใหม่: เพิ่มความแม่นยำด้วยการอ่านบริบท
# ---------------------------------------------------------
def count_digital_highlights(pdf_bytes):
    if not PDF_SUPPORT:
        return -1,[], {}, "ไม่พบไลบรารี PyMuPDF กรุณาติดตั้ง pip install pymupdf"
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        total_highlights = 0
        page_details =[]
        
        # คีย์เวิร์ดสำหรับจัดหมวดหมู่ (ใช้ตรวจจับจากประโยครอบๆ ไฮไลต์)
        categories = {
            "(๑) คุณสมบัติผู้ยื่นข้อเสนอ":["คุณสมบัติของผู้ยื่นข้อเสนอ", "ผลงานที่เกี่ยวข้องกัน", "ผลงาน", "ประสบการณ์", "ผู้ยื่นข้อเสนอจะต้องมี"],
            "(๒) ค่าจ้างและการจ่ายเงิน/การส่งมอบ":["งวดงานและการจ่ายเงิน", "งวดที่", "ส่งมอบพัสดุ", "ส่งมอบ"],
            "(๓) วงเงินงบประมาณ":["วงเงินงบประมาณ", "งบประมาณโครงการ"],
            "(๔) การรับประกันความชำรุดบกพร่อง":["เงื่อนไขการรับประกัน", "รับประกันคุณภาพ", "รับประกันประสิทธิภาพ", "รับประกันฮาร์ดแวร์", "รับประกันซอฟต์แวร์"],
            "(๕) อัตราค่าปรับ":["อัตราค่าปรับ", "ค่าปรับ", "ปรับเป็นรายวัน"]
        }
        
        # เตรียม Dictionary เก็บผลลัพธ์แยกตามหัวข้อ
        categorized_results = {cat: [] for cat in categories.keys()}
        categorized_results["(๖) ข้อมูลอื่นๆ ที่ถูกไฮไลต์"] =[]

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_hl_count = 0
            
            for annot in page.annots():
                if annot.type[1].lower() == 'highlight':
                    page_hl_count += 1
                    total_highlights += 1
                    
                    # 1. ดึงข้อความ "เฉพาะส่วนที่ปาดไฮไลต์" ตรงๆ
                    quads = annot.vertices
                    rect = annot.rect
                    hl_text = ""
                    if quads:
                        for i in range(0, len(quads), 4):
                            quad = fitz.Quad(quads[i:i+4])
                            hl_text += page.get_textbox(quad.rect) + " "
                    
                    hl_text = re.sub(r'\s+', ' ', hl_text).strip()
                    if not hl_text:
                        hl_text = "[ไม่สามารถสกัดข้อความได้]"
                        
                    # 2. ดึงข้อความ "บริบทรอบๆ (Context)" เพื่อหาหมวดหมู่ที่แม่นยำ
                    # ขยายพื้นที่ค้นหาขึ้น-ลง เพื่ออ่านหัวข้อหรือประโยครอบๆ 
                    context_rect = fitz.Rect(0, max(0, rect.y0 - 150), page.rect.width, min(page.rect.height, rect.y1 + 150))
                    context_text = page.get_textbox(context_rect)
                    context_text = re.sub(r'\s+', ' ', context_text).strip()
                        
                    # 3. นำบริบท (Context) มาเปรียบเทียบหาหมวดหมู่
                    matched_category = "(๖) ข้อมูลอื่นๆ ที่ถูกไฮไลต์"
                    for cat, keywords in categories.items():
                        if any(kw in context_text for kw in keywords):
                            matched_category = cat
                            break # เจอหมวดหมู่แล้วให้หยุดค้นหา
                            
                    # 4. บันทึกข้อมูล (เก็บเฉพาะคำที่ถูกไฮไลต์จริงๆ เพื่อนำไปแสดงผล)
                    categorized_results[matched_category].append({
                        "page": page_num + 1,
                        "text": hl_text
                    })

            if page_hl_count > 0:
                page_details.append({"page": page_num + 1, "count": page_hl_count})
                
        doc.close()
        return total_highlights, page_details, categorized_results, None
    except Exception as e:
        return -1,[], {}, str(e)

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

def extract_json_schema(obj, prefix=""):
    schema = {}
    if isinstance(obj, dict):
        if prefix != "": schema[prefix] = ("dict", obj)
        for k, v in obj.items():
            new_key = f"{prefix}.{k}" if prefix else str(k)
            schema.update(extract_json_schema(v, new_key))
    elif isinstance(obj, list):
        if prefix != "": schema[prefix] = ("list", obj)
        if len(obj) > 0:
            new_key = f"{prefix}[0]" if prefix else "[0]"
            schema.update(extract_json_schema(obj[0], new_key))
    else:
        if prefix != "": schema[prefix] = (type(obj).__name__, obj)
    return schema

# ==========================================
# สร้างหน้าเว็บ (Web UI)
# ==========================================

st.title("🔍 Text, Table, PDF & JSON Analyzer")
st.markdown("โปรแกรมตรวจสอบความเหมือน/แตกต่าง ของข้อความ, ตาราง, ไฟล์ PDF และโครงสร้าง JSON")

# สร้าง 4 Tabs
tab1, tab2, tab3, tab4 = st.tabs(["⚙️ 2.1.1 ตรวจสอบ JSON Schema", "📝 2.2.2 ตรวจสอบข้อความ", "📊 2.2.3 ตรวจสอบตาราง", "📁 2.3.1 ตรวจสอบไฮไลท์ PDF"])

# ---------------------------------------------------------
# TAB 2: ตรวจสอบข้อความปกติ
# ---------------------------------------------------------
with tab2:
    st.markdown("### 📝 เปรียบเทียบข้อความปกติ")
    col1, col2 = st.columns(2)
    with col1:
        text1 = st.text_area("1. ข้อความต้นฉบับ:", height=200, key="t1")
    with col2:
        text2 = st.text_area("2. ข้อความที่ต้องการเปรียบเทียบ:", height=200, key="t2")
        
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
            
            st.markdown("""
            <div class="legend-box">
                <span class='delete-text'>สีแดง (ขีดฆ่า)</span> = หายไป/พิมพ์ผิด | 
                <span class='insert-text'>สีเขียว (ตัวหนา)</span> = เพิ่มเข้ามาใหม่
            </div>
            """, unsafe_allow_html=True)
            diff_html = generate_diff_html(cleaned_original, cleaned_compare)
            st.markdown(f"<div class='diff-box'>{diff_html}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 3: ตรวจสอบตาราง
# ---------------------------------------------------------
with tab3:
    st.markdown("### 📊 เปรียบเทียบข้อมูลในตาราง")
    col3, col4 = st.columns(2)
    with col3:
        table1 = st.text_area("1. ตารางต้นฉบับ:", height=150, key="tbl1")
    with col4:
        table2 = st.text_area("2. ตารางที่ต้องการเปรียบเทียบ:", height=150, key="tbl2")
        
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
            max_c = max(max((len(row) for row in t1), default=0), max((len(row) for row in t2), default=0))
            total_matches, total_length = 0, 0
            has_diff = False
            
            html_table = "<div class='result-table-container'><table class='result-table'>"
            html_table += "<thead><tr><th style='width: 50px; text-align: center;'>#</th>"
            for c in range(max_c): html_table += f"<th style='min-width: 120px; text-align: center;'>{get_excel_col_name(c)}</th>"
            html_table += "</tr></thead><tbody>"
            
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
                    total_matches += (matcher.ratio() * t_len) / 2
                    
                    if val1 == val2:
                        html_table += f"<td class='td-match'>{val1}</td>"
                    else:
                        has_diff = True
                        cell_diff = generate_diff_html(val1, val2)
                        html_table += f"<td class='td-mismatch'>{cell_diff}</td>"
                html_table += "</tr>"
            html_table += "</tbody></table></div>"
            
            sim_percent = (2 * total_matches / total_length * 100) if total_length > 0 else 0.0
            st.divider()
            st.metric("✅ อัตราความคล้ายคลึงระดับตัวอักษร", f"{sim_percent:.2f}%")
            
            if not has_diff and sim_percent == 100.0:
                st.success("✅ ข้อมูลในตารางตรงกันทุกตำแหน่ง")
            else:
                st.markdown(html_table, unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 4: ไฮไลท์ใน PDF (อัปเดตแยกหัวข้อแม่นยำ)
# ---------------------------------------------------------
with tab4:
    st.markdown("### 📁 ตรวจสอบและดึงข้อมูลไฮไลต์ในไฟล์ PDF ตามหัวข้อ TOR")
    st.info("💡 ระบบจะอ่านบริบทรอบๆ ข้อความที่ถูกไฮไลต์ เพื่อจับคู่หัวข้ออย่างแม่นยำ (แต่จะดึงแสดงผลเฉพาะข้อความเป๊ะๆ ที่โดนปาดสีเหลืองเท่านั้น)")
    
    if not PDF_SUPPORT:
        st.error("⚠️ ไม่พบไลบรารี PyMuPDF กรุณาติดตั้งผ่าน Terminal ด้วยคำสั่ง: `pip install pymupdf`")
    else:
        uploaded_file = st.file_uploader("📂 เลือกไฟล์ PDF:", type=['pdf'])
        if uploaded_file is not None:
            if st.button("📑 เริ่มวิเคราะห์และแยกหมวดหมู่ไฮไลต์", type="primary"):
                with st.spinner("⏳ กำลังสกัดข้อความจากไฮไลต์..."):
                    pdf_bytes = uploaded_file.read()
                    count, details, cat_results, error_msg = count_digital_highlights(pdf_bytes)
                    
                    if error_msg: 
                        st.error(f"❌ เกิดข้อผิดพลาด: {error_msg}")
                    else:
                        st.divider()
                        if count == 0: 
                            st.info("ไม่พบไฮไลต์ดิจิตอลในไฟล์นี้")
                        else:
                            st.success(f"📊 พบการไฮไลต์ทั้งหมด: **{count}** จุด")

                            st.markdown("#### 📑 สรุปข้อความที่ถูกไฮไลต์ (แยกตามหมวดหมู่):")
                            
                            # แสดงผลวนลูปตามหมวดหมู่แบบ Expand/Collapse
                            for cat_name, items in cat_results.items():
                                # ให้ Expander เปิดอัตโนมัติถ้ามีข้อมูล
                                with st.expander(f"📌 {cat_name} (พบ {len(items)} จุด)", expanded=(len(items) > 0)):
                                    if len(items) == 0:
                                        st.write("*- ไม่พบข้อความไฮไลต์ที่ตรงกับหัวข้อนี้ -*")
                                    else:
                                        for idx, item in enumerate(items, 1):
                                            st.markdown(f"**{idx}. หน้า {item['page']}:** <span style='background-color: yellow; color: black; padding: 2px 6px; border-radius: 4px;'>{item['text']}</span>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 1: ตรวจสอบ JSON Schema
# ---------------------------------------------------------
with tab1:
    st.markdown("### ⚙️ เปรียบเทียบโครงสร้าง JSON Schema")
    st.info("💡 **ระบบจะทำการเทียบ Data Type และเช็คว่ามี Key ครบถ้วนตรงกันหรือไม่ (โดยมีระบบยืดหยุ่นอัตโนมัติหาก Key เก็บไฟล์/Base64 แต่ถูกปล่อยว่างต่างดีไซน์กัน เช่น `null` กับ `\"\"`)**")
    
    col5, col6 = st.columns(2)
    with col5:
        json_input1 = st.text_area("1. JSON ต้นฉบับ (Base Object):", height=250, key="json1", help="วางข้อมูล JSON ที่ถูกต้องที่นี่")
    with col6:
        json_input2 = st.text_area("2. JSON ที่ต้องการตรวจสอบ (Compare Object):", height=250, key="json2", help="วางข้อมูล JSON ที่ถูกต้องที่นี่")
        
    btn_col5, btn_col6 = st.columns([4, 1])
    with btn_col5:
        submit_json = st.button("⚙️ ตรวจสอบ JSON Schema", type="primary", use_container_width=True)
    with btn_col6:
        st.button("🗑️ ล้างข้อมูล", on_click=clear_json_tab, use_container_width=True, key="clear_json_btn")

    if submit_json:
        if not json_input1 or not json_input2:
            st.warning("⚠️ กรุณาวางข้อมูล JSON ให้ครบทั้งสองช่องครับ")
        else:
            try:
                data1 = json.loads(json_input1)
                data2 = json.loads(json_input2)
                
                schema1 = extract_json_schema(data1)
                schema2 = extract_json_schema(data2)
                
                all_keys = sorted(list(set(schema1.keys()).union(set(schema2.keys()))))
                
                # --- Helper Functions สำหรับตรวจสอบความยืดหยุ่น (Flexible Match) ---
                SCHEMA_KEYWORDS = ["string", "number", "integer", "boolean", "object", "array", "null", "any"]

                def is_schema_list_val(v):
                    return isinstance(v, list) and len(v) > 0 and all(isinstance(x, str) and x.lower() in SCHEMA_KEYWORDS for x in v)

                keys_to_remove = set()
                for k in all_keys:
                    if k in ["$schema", "title"] or k.endswith(".$schema"):
                        keys_to_remove.add(k)
                        continue
                        
                    parts = k.split('.')
                    if any(p == "required" or p.startswith("required[") for p in parts):
                        keys_to_remove.add(k)
                        continue
                        
                    t1, _ = schema1.get(k, (None, None))
                    t2, _ = schema2.get(k, (None, None))
                    if t1 == "dict" or t2 == "dict":
                        keys_to_remove.add(k)
                        continue
                        
                    if k.endswith("[0]"):
                        parent_k = k[:-3]
                        if parent_k:
                            v1_parent = schema1.get(parent_k, (None, None))[1]
                            v2_parent = schema2.get(parent_k, (None, None))[1]
                            if is_schema_list_val(v1_parent) or is_schema_list_val(v2_parent):
                                keys_to_remove.add(k)
                                continue
                
                all_keys =[k for k in all_keys if k not in keys_to_remove]
                
                base_total_keys = len([k for k in schema1.keys() if k not in keys_to_remove])
                
                key_exist_count = 0  
                type_match_count = 0 
                extra_keys_count = 0 

                def is_empty_val(v):
                    return v in[None, "", [], {}]

                def is_file_b64_key(k, v):
                    k_lower = str(k).lower()
                    file_kws =['file', 'base64', 'image', 'img', 'pic', 'photo', 'pdf', 'doc', 'attachment', 'avatar', 'sign', 'data', 'url']
                    if any(kw in k_lower for kw in file_kws): return True
                    if isinstance(v, str):
                        if v.startswith('data:') or v.startswith('http'): return True
                        if len(v) > 80 and ' ' not in v[:80]: return True 
                    return False
                
                def is_special_file_docs(k):
                    k_lower = str(k).lower()
                    return k_lower.endswith('_file') or k_lower.endswith('_docs')

                def is_allowed_file_schema(val):
                    if val is None: return True
                    if isinstance(val, str) and val.lower() in ["null", "string", ""]: return True
                    if isinstance(val, list):
                        lower_list = [str(x).lower() for x in val]
                        if all(x in["string", "null"] for x in lower_list): return True
                    return False
                
                table_rows =[]
                
                for k in all_keys:
                    in_s1 = k in schema1
                    in_s2 = k in schema2
                    
                    t1, v1 = schema1.get(k, (None, None))
                    t2, v2 = schema2.get(k, (None, None))
                    
                    status = ""
                    css_class = ""
                    
                    if in_s1 and in_s2:
                        key_exist_count += 1
                        
                        types_match = (t1 == t2)
                        
                        def is_schema_val(v):
                            if isinstance(v, str) and v.lower() in SCHEMA_KEYWORDS:
                                return True
                            if isinstance(v, list) and len(v) > 0 and all(isinstance(x, str) and x.lower() in SCHEMA_KEYWORDS for x in v):
                                return True
                            return False

                        if is_schema_val(v1) or is_schema_val(v2):
                            def get_schema_set(v):
                                if isinstance(v, str): return {v.lower()}
                                if isinstance(v, list): return {str(x).lower() for x in v}
                                return set()
                                
                            s1 = get_schema_set(v1)
                            s2 = get_schema_set(v2)
                            
                            if is_schema_val(v1) and is_schema_val(v2):
                                if s1 == s2:
                                    types_match = True
                                elif s1 == {"string", "null"} and s2 in[{"string"}, {"null"}]:
                                    types_match = True
                                elif s2 == {"string", "null"} and s1 in [{"string"}, {"null"}]:
                                    types_match = True
                                else:
                                    types_match = False
                            else:
                                types_match = False

                        if types_match:
                            type_match_count += 1
                            status = "✅ สมบูรณ์"
                            css_class = "td-match"
                        else:
                            is_flex = False
                            
                            if is_special_file_docs(k) and is_allowed_file_schema(v1) and is_allowed_file_schema(v2):
                                is_flex = True
                            elif is_empty_val(v1) and is_empty_val(v2):
                                is_flex = True
                            elif is_file_b64_key(k, v1) and is_empty_val(v2):
                                is_flex = True
                            elif is_file_b64_key(k, v2) and is_empty_val(v1):
                                is_flex = True
                                
                            if is_flex:
                                type_match_count += 1
                                status = "✅ สมบูรณ์ (ยืดหยุ่น File/Base64)"
                                css_class = "td-match"
                            else:
                                status = "⚠️ ชนิดข้อมูลผิด"
                                css_class = "td-warning"
                                
                    elif in_s1 and not in_s2:
                        status = "❌ หายไป"
                        css_class = "td-mismatch"
                    elif not in_s1 and in_s2:
                        extra_keys_count += 1
                        status = "➕ เกินมา"
                        css_class = "td-extra"
                    
                    def format_display_type(t, v):
                        if isinstance(v, str) and v.lower() in SCHEMA_KEYWORDS:
                            return v
                        if isinstance(v, list) and len(v) > 0 and all(isinstance(x, str) and x.lower() in SCHEMA_KEYWORDS for x in v):
                            return json.dumps(v)
                        return t
                        
                    display_t1 = format_display_type(t1, v1) if t1 else "-"
                    display_t2 = format_display_type(t2, v2) if t2 else "-"
                    
                    table_rows.append((k, display_t1, display_t2, status, css_class))
                
                key_exist_pct = (key_exist_count / base_total_keys * 100) if base_total_keys > 0 else 0.0
                type_match_pct = (type_match_count / base_total_keys * 100) if base_total_keys > 0 else 0.0

                st.divider()
                st.markdown("### 📊 สรุปคะแนนการประเมิน (อิงจากต้นฉบับเป็นเกณฑ์ 100%)")
                
                score_col1, score_col2 = st.columns(2)
                
                with score_col1:
                    st.markdown(f"""
                    <div style="background-color: #f0f7ff; border-left: 5px solid #0d6efd; padding: 20px; border-radius: 6px; height: 100%;">
                        <h4 style="color: #0d6efd; margin-top: 0; font-size: 20px;">1️⃣ ส่วนที่ 1: ตรวจสอบการมีอยู่ของ Key</h4>
                        <p style="font-size: 15px; margin-bottom: 5px; color: #333;">จำนวน "ชื่อ Key" ฝั่งเปรียบเทียบ ที่มีอยู่ตรงกับต้นฉบับ</p>
                        <h2 style="margin: 0; color: #000;">{key_exist_count} / {base_total_keys} <span style="font-size: 16px; color: #6c757d; font-weight: normal;">คีย์</span></h2>
                        <p style="font-size: 18px; font-weight: bold; color: #0d6efd; margin-top: 10px;">คิดเป็น {key_exist_pct:.2f}%</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with score_col2:
                    st.markdown(f"""
                    <div style="background-color: #f0fff4; border-left: 5px solid #198754; padding: 20px; border-radius: 6px; height: 100%;">
                        <h4 style="color: #198754; margin-top: 0; font-size: 20px;">2️⃣ ส่วนที่ 2: ตรวจสอบประเภทข้อมูล (Type)</h4>
                        <p style="font-size: 15px; margin-bottom: 5px; color: #333;">จำนวน Key ที่ชื่อตรงกัน และ "ประเภทข้อมูล (Data Type)" ตรงกัน (รวมถึงกรณีอนุโลมยืดหยุ่น)</p>
                        <h2 style="margin: 0; color: #000;">{type_match_count} / {base_total_keys} <span style="font-size: 16px; color: #6c757d; font-weight: normal;">คีย์</span></h2>
                        <p style="font-size: 18px; font-weight: bold; color: #198754; margin-top: 10px;">คิดเป็น {type_match_pct:.2f}%</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                if extra_keys_count > 0:
                    st.warning(f"⚠️ **ข้อสังเกต:** พบข้อมูล Key ที่ **เกินเข้ามา** ในช่องเปรียบเทียบจำนวน **{extra_keys_count} คีย์** (ระบบจะไม่นำส่วนนี้ไปหักคะแนน เพราะอิงจากต้นฉบับ แต่จะแสดงเป็นสีเขียวในตารางด้านล่างครับ)")

                st.markdown("<br>### 🔍 ตารางแจกแจงรายละเอียดการตรวจสอบ", unsafe_allow_html=True)
                st.markdown("""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6; margin-bottom: 20px; color: #000;">
                    <p style="margin-top:0; font-weight:bold; font-size: 16px;">💡 วิธีอ่านสีของผลลัพธ์ในตาราง:</p>
                    <div style="display: flex; flex-direction: column; gap: 10px; font-size: 15px;">
                        <div style="display: flex; align-items: center;">
                            <div style="width: 120px; text-align: center; background-color: #ffffff; border: 1px solid #ccc; padding: 5px; border-radius: 4px; margin-right: 15px; font-weight: bold;">⬜ สีขาว</div>
                            <div><b>สมบูรณ์:</b> มีชื่อ Key ครบ และประเภทข้อมูลตรงกัน 100% <br><span style="color:#0d6efd; font-size:14px;">*(รวมถึง <b>"สมบูรณ์แบบยืดหยุ่น"</b> กรณีเก็บไฟล์/Base64 แต่แสดงค่าว่างต่าง Design กัน เช่น <code>null</code> กับ <code>""</code> เป็นต้น)*</span></div>
                        </div>
                        <div style="display: flex; align-items: center;">
                            <div style="width: 120px; text-align: center; background-color: #ffe6e6; border: 2px solid #dc3545; color: #dc3545; padding: 5px; border-radius: 4px; margin-right: 15px; font-weight: bold;">❌ สีแดง</div>
                            <div><b>ข้อมูลขาดหาย:</b> ต้นฉบับมี Key นี้ แต่ฝั่งเปรียบเทียบกลับไม่มี (หายไป)</div>
                        </div>
                        <div style="display: flex; align-items: center;">
                            <div style="width: 120px; text-align: center; background-color: #d1e7dd; border: 2px solid #198754; color: #198754; padding: 5px; border-radius: 4px; margin-right: 15px; font-weight: bold;">➕ สีเขียว</div>
                            <div><b>ข้อมูลเกินมา:</b> ต้นฉบับไม่มี แต่ฝั่งเปรียบเทียบดันมี Key นี้แทรกเข้ามา</div>
                        </div>
                        <div style="display: flex; align-items: center;">
                            <div style="width: 120px; text-align: center; background-color: #fff3cd; border: 2px solid #fd7e14; color: #fd7e14; padding: 5px; border-radius: 4px; margin-right: 15px; font-weight: bold;">⚠️ สีส้ม</div>
                            <div><b>ชนิดข้อมูลผิด:</b> มี Key ตรงกัน แต่รูปแบบผิด (เช่น ต้นฉบับเป็น Text แต่เปรียบเทียบเป็น Number)</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                html_json = "<div class='result-table-container'><table class='result-table'>"
                html_json += "<thead><tr>"
                html_json += "<th style='width: 50px; text-align: center;'>#</th>"
                html_json += "<th>ชื่อ Key (ลำดับชั้นใน JSON)</th>"
                html_json += "<th>ประเภทข้อมูล (ต้นฉบับ)</th>"
                html_json += "<th>ประเภทข้อมูล (ช่องเปรียบเทียบ)</th>"
                html_json += "<th>สถานะ</th>"
                html_json += "</tr></thead><tbody>"
                
                for index, row in enumerate(table_rows, 1):
                    k, type1, type2, status, css_class = row
                        
                    html_json += f"<tr class='{css_class}'>"
                    html_json += f"<td style='text-align: center; font-weight: bold; background-color: #f8f9fa;'>{index}</td>"
                    html_json += f"<td><b>{k}</b></td>"
                    html_json += f"<td>{type1}</td>"
                    html_json += f"<td>{type2}</td>"
                    html_json += f"<td>{status}</td>"
                    html_json += "</tr>"
                    
                html_json += "</tbody></table></div>"
                
                if type_match_count == base_total_keys and base_total_keys > 0 and extra_keys_count == 0:
                    st.success("✅ โครงสร้าง JSON Schema ทั้งสองฝั่งเหมือนกันเป๊ะ 100% ไม่มีผิดเพี้ยนหรือเกินมาเลย!")
                
                st.markdown(html_json, unsafe_allow_html=True)

            except json.JSONDecodeError as e:
                st.error(f"❌ โครงสร้าง JSON ไม่ถูกต้อง: กรุณาตรวจสอบวงเล็บ ปีกกา หรือเครื่องหมายคำพูด (\"\") ให้ถูกต้อง\n\nรายละเอียด Error: {str(e)}")
            except Exception as e:
                st.error(f"❌ เกิดข้อผิดพลาดที่ไม่คาดคิด: {str(e)}")
