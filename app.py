import streamlit as st
import fitz  # PyMuPDF
import requests
import base64

# جدول الأدوية + رقم القسمة
dividers = {
    "Acyclovir": 5,
    "Amikacin": 5,
    "Vancomycin": 5,
    "Piperacillin": 50,
    "Ampicillin": 20,
    "Gentamicin": 2,
    "Cefotaxime": 40,
    "Ceftriaxone": 40,
    "Cefapime": 40,
    "Cefuroxime": 30,
    "Ceftazidime": 40,
    "Azithromycin": 2,
    "Furosemide": 2,
    "Cloxacillin": 25,
    "omeprazole": 0.8,
    "Cefazolin": 20,
    "Amphotericin B": 0.1,
    "Amphotericin B Liposomal": 0.1,
    "Meropenem": 20,
    "Methylprednisolone": 10,
    "Clindamycin": 18,
    "Levetiracetam": 10,
    "Sulfamethoxazole": 0.64,
}

# جدول التكرار
frequency_repeat = {
    "q12h": 2, "every 12 hour": 2,
    "q8h": 3, "every 8 hour": 3,
    "q6h": 4, "every 6 hour": 4,
    "q4h": 6, "every 4 hour": 6,
}

# دالة لتحويل روابط Google Drive
def fix_drive_url(url: str) -> str:
    if "drive.google.com" in url and "/d/" in url:
        try:
            file_id = url.split("/d/")[1].split("/")[0]
            return f"https://drive.google.com/uc?export=download&id={file_id}"
        except:
            return url
    return url

def process_pdf(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    new_doc = fitz.open()
    found_page = False

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text").lower()

        # تحقق: هل الصفحة فيها دواء؟
        matched_drug = None
        divisor = None
        for drug, div in dividers.items():
            if drug.lower() in text:
                matched_drug = drug
                divisor = div
                break
        if not matched_drug:
            continue

        found_page = True

        # تكرار الصفحة
        repeat_times = 1
        for freq, times in frequency_repeat.items():
            if freq in text:
                repeat_times = times
                break

        for _ in range(repeat_times):
            new_page_count = new_doc.page_count
            new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            new_page = new_doc[new_page_count]

            # ابحث عن "MG"
            words = new_page.get_text("words")
            for idx, w in enumerate(words):
                if w[4].upper() == "MG":
                    prev_word = words[idx - 1][4]
                    if prev_word.replace(".", "", 1).isdigit():
                        dose = float(prev_word)
                        result = dose / divisor
                        x0, y0, x1, y1, *_ = words[idx - 1]
                        new_page.insert_text(
                            (x0, y1 + 25),
                            f"{dose} mg ÷ {divisor} = {round(result, 2)} ml",
                            fontsize=11,
                            color=(0, 0, 1),
                        )
                        break

    if not found_page:
        return pdf_bytes

    output_bytes = new_doc.write()
    new_doc.close()
    doc.close()
    return output_bytes

# ---------------- Streamlit واجهة ----------------
st.title("📄 أداة تعديل ملفات PDF للأدوية")

pdf_url = st.text_input("ضع رابط ملف PDF هنا (واضغط Enter)")

def show_pdf(output_pdf):
    b64_pdf = base64.b64encode(output_pdf).decode("utf-8")
    pdf_display = f"""
    <iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="800px"></iframe>
    <br><br>
    <a href="data:application/pdf;base64,{b64_pdf}" download="output.pdf"
       style="font-size:18px; padding:8px 12px; background:#4CAF50; color:white; text-decoration:none; border-radius:5px;">
       📥 تحميل الملف (في حال لم يُعرض بالأعلى)
    </a>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)

if pdf_url:
    try:
        fixed_url = fix_drive_url(pdf_url)
        response = requests.get(fixed_url)
        response.raise_for_status()
        output_pdf = process_pdf(response.content)
        st.success("✅ الملف جاهز")
        show_pdf(output_pdf)
    except Exception as e:
        st.error(f"❌ خطأ: {e}")
