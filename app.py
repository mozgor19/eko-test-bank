import streamlit as st
import mammoth
from bs4 import BeautifulSoup
import re
import random
import os

# -----------------------------------------------------------------------------
# 1. DOCX -> HTML -> AKILLI AYRIŞTIRMA
# -----------------------------------------------------------------------------
def parse_docx_smart(file_path, chapter_name):
    """
    Dosya yolundan okur ve soruları ayrıştırır.
    """
    # Dosyayı binary modda aç
    with open(file_path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        html = result.value
    
    soup = BeautifulSoup(html, "html.parser")
    
    questions = []
    current_q = None        
    question_active = False 
    
    buffer_html = ""        
    preamble_html = ""      
    options = {}
    answer = None
    ref = None
    q_id = None

    q_start_pattern = re.compile(r'^(\d+)\.\s+(.*)') 
    opt_pattern = re.compile(r'^\s*([a-d])[\.\)]\s+(.*)', re.IGNORECASE)
    ans_pattern = re.compile(r'(?:ANS|Answer):\s+([A-D])', re.IGNORECASE)
    ref_pattern = re.compile(r'REF:\s+(.*)')

    elements = soup.find_all(['p', 'table']) 
    
    for elem in elements:
        text = elem.get_text().strip()
        raw_html = str(elem) 

        match_q = q_start_pattern.match(text)
        if match_q:
            if current_q and len(options) >= 2 and answer:
                questions.append({
                    'id': q_id, 'chapter': chapter_name, 'body_html': buffer_html, 
                    'options': options, 'answer': answer.lower(), 'ref': ref
                })

            question_active = True
            q_num = match_q.group(1)
            q_text_content = match_q.group(2)
            q_id = f"{chapter_name} - Q{q_num}"
            q_text_html = f"<p><b>{q_text_content}</b></p>"
            buffer_html = preamble_html + q_text_html
            preamble_html = "" 
            options = {}
            answer = None
            ref = None
            continue

        match_ans = ans_pattern.search(text)
        if match_ans:
            answer = match_ans.group(1)
            question_active = False 
            match_ref = ref_pattern.search(text)
            if match_ref: ref = match_ref.group(1)
            continue
        
        if question_active: 
            match_opt = opt_pattern.match(text)
            if match_opt:
                options[match_opt.group(1).lower()] = match_opt.group(2)
                continue

        if "REF:" not in text and "ANS:" not in text:
            if question_active: buffer_html += raw_html
            else: preamble_html += raw_html

    if len(options) >= 2 and answer:
        questions.append({
            'id': q_id, 'chapter': chapter_name, 'body_html': preamble_html + buffer_html,
            'options': options, 'answer': answer.lower(), 'ref': ref
        })

    return questions

# -----------------------------------------------------------------------------
# 2. AYARLAR VE PATH BULMA
# -----------------------------------------------------------------------------

st.set_page_config(page_title="ekoTestBank Pro", layout="wide")

# App.py'nin olduğu gerçek klasör yolunu bul
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.markdown("""
<style>
    img { max-width: 100%; max-height: 350px; width: auto; display: block; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; }
    .stMarkdown p { font-size: 16px; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 ekoTestBank - Cloud")

if 'all_questions' not in st.session_state:
    st.session_state.all_questions = []
if 'current_quiz' not in st.session_state:
    st.session_state.current_quiz = []

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Dosya Yönetimi")
    
    # DEBUG BİLGİSİ (Sorunu anlamak için)
    with st.expander("🛠️ Hata Ayıklama (Debug)"):
        st.write(f"📂 Çalışma Dizini: `{BASE_DIR}`")
        files_in_dir = os.listdir(BASE_DIR)
        st.write("📄 Buradaki Dosyalar:", files_in_dir)
        
        docx_files = [f for f in files_in_dir if f.endswith('.docx')]
        if not docx_files:
            st.error("❌ Hiç .docx dosyası bulunamadı! Lütfen dosyaları GitHub'a yüklediğinizden emin olun.")
    
    # TARAMA BUTONU
    if st.button("🔄 Dosyaları Tara ve Yükle"):
        # Sadece .docx dosyalarını al
        local_files = [f for f in os.listdir(BASE_DIR) if f.endswith('.docx')]
        
        if local_files:
            all_loaded = []
            bar = st.progress(0)
            status_text = st.empty()
            
            for idx, file_name in enumerate(local_files):
                status_text.text(f"İşleniyor: {file_name}")
                ch_name = file_name.split('.')[0]
                
                # Tam dosya yolunu oluştur
                full_path = os.path.join(BASE_DIR, file_name)
                
                try:
                    qs = parse_docx_smart(full_path, ch_name)
                    all_loaded.extend(qs)
                except Exception as e:
                    st.error(f"Hata ({file_name}): {e}")
                
                bar.progress((idx + 1) / len(local_files))
            
            status_text.text("Tamamlandı!")
            st.session_state.all_questions = all_loaded
            st.success(f"✅ Toplam {len(all_loaded)} soru başarıyla yüklendi.")
        else:
            st.warning("⚠️ Bu klasörde .docx dosyası bulunamadı. Lütfen 'Hata Ayıklama' kutusuna bakın.")

    # QUIZ MODU
    if st.session_state.all_questions:
        st.markdown("---")
        mode = st.radio("Mod Seç", ["Chapter Bazlı", "Karma Test"])
        all_qs = st.session_state.all_questions
        
        if mode == "Chapter Bazlı":
            chapters = sorted(list(set(q['chapter'] for q in all_qs)))
            sel_chap = st.selectbox("Chapter:", chapters)
            if st.button("Bu Chapter'ı Başlat"):
                st.session_state.current_quiz = [q for q in all_qs if q['chapter'] == sel_chap]
                st.session_state.user_answers = {}
                st.rerun()
            
        else:
            chapters = sorted(list(set(q['chapter'] for q in all_qs)))
            target_chaps = st.multiselect("Chapterlar:", chapters)
            count = st.number_input("Soru Sayısı:", 5, 200, 20)
            if st.button("Karma Test Oluştur"):
                pool = [q for q in all_qs if q['chapter'] in target_chaps]
                if pool:
                    st.session_state.current_quiz = random.sample(pool, min(count, len(pool)))
                    st.session_state.user_answers = {}
                    st.rerun()

# --- ANA EKRAN ---
if not st.session_state.current_quiz:
    st.info("👈 Sol menüden 'Dosyaları Tara' butonuna basın.")
else:
    st.subheader(f"📝 Quiz ({len(st.session_state.current_quiz)} Soru)")
    
    for i, q in enumerate(st.session_state.current_quiz):
        with st.expander(f"Soru {i+1} ({q['id']})", expanded=True):
            st.markdown(q['body_html'], unsafe_allow_html=True)
            
            opts = list(q['options'].keys())
            fmt_opts = [f"{k}) {v}" for k, v in q['options'].items()]
            
            key = f"ans_{i}_{q['id']}"
            user_choice = st.radio("Cevap:", fmt_opts, key=key, index=None)
            
            if user_choice:
                sel = user_choice.split(')')[0]
                corr = q['answer']
                if sel == corr:
                    st.success("✅ Doğru")
                else:
                    st.error(f"❌ Yanlış. Cevap: {corr.upper()}")
                if q.get('ref'): st.caption(f"Ref: {q['ref']}")
