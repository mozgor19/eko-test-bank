import streamlit as st
import mammoth
from bs4 import BeautifulSoup
import re
import random
import os
from streamlit_pdf_viewer import pdf_viewer

# -----------------------------------------------------------------------------
# 1. DOCX -> HTML -> SORU AYRIŞTIRMA (GLOBAL HAFIZA MANTIĞI)
# -----------------------------------------------------------------------------
def parse_docx_with_images(file_obj, chapter_name):
    """
    DOCX dosyasını HTML'e çevirir. 
    Resimleri global bir hafızada tutar ve 'Refer to' diyen her soruya
    en son görülen resmi yapıştırır.
    """
    # 1. Mammoth ile DOCX'i HTML'e çevir
    try:
        result = mammoth.convert_to_html(file_obj)
        html = result.value
    except Exception as e:
        st.error(f"Dosya dönüştürme hatası: {e}")
        return []
    
    # 2. HTML'i BeautifulSoup ile parçala
    soup = BeautifulSoup(html, "html.parser")
    
    questions = []
    
    # --- DEĞİŞKENLER ---
    current_q = None
    question_active = False 
    
    buffer_html = ""        # Şu anki sorunun HTML içeriği
    
    # GLOBAL RESİM HAFIZASI (En önemli değişiklik)
    # Belge boyunca gördüğümüz son resmi burada tutacağız.
    global_last_image = ""  
    
    options = {}
    answer = None
    ref = None
    q_id = None

    # Regexler
    q_start_pattern = re.compile(r'^(\d+)\.\s+(.*)') 
    opt_pattern = re.compile(r'^\s*([a-d])[\.\)]\s+(.*)', re.IGNORECASE)
    ans_pattern = re.compile(r'(?:ANS|Answer):\s+([A-D])', re.IGNORECASE)
    ref_pattern = re.compile(r'REF:\s+(.*)')
    
    # Bu kelimeler geçiyorsa hafızadaki resmi çağıracağız
    figure_keywords = ["refer to figure", "refer to table"]

    elements = soup.find_all(['p', 'table']) 
    
    for elem in elements:
        text = elem.get_text().strip()
        raw_html = str(elem) 

        # --- ADIM 1: RESİM GÜNCELLEME ---
        # Bu element bir resim veya tablo içeriyor mu?
        # Soru, cevap veya şık fark etmeksizin gördüğümüz an hafızaya alıyoruz.
        if "<img" in raw_html or "<table" in raw_html:
            # Cevap şıkkı (a. b. c.) içindeki minik resimleri almamak için basit bir kontrol
            # Genellikle figürler <p><img...></p> şeklinde gelir ve kısadır.
            global_last_image = raw_html

        # --- ADIM 2: YENİ SORU BAŞLANGICI ---
        match_q = q_start_pattern.match(text)
        if match_q:
            # Önceki soruyu kaydet
            if current_q and len(options) >= 2 and answer:
                questions.append({
                    'id': q_id, 'chapter': chapter_name, 'body_html': buffer_html, 
                    'options': options, 'answer': answer.lower(), 'ref': ref
                })

            # --- YENİ SORU HAZIRLIĞI ---
            question_active = True
            current_q = True
            q_num = match_q.group(1)
            q_text_content = match_q.group(2) 
            q_id = f"{chapter_name} - Q{q_num}"
            
            # Soru metnini hazırla
            q_text_html = f"<p><b>{q_text_content}</b></p>"
            
            # --- RESİM YAPIŞTIRMA MANTIĞI ---
            # 1. Bu satırın kendisi zaten resim içeriyor mu? (Nadir ama olur)
            if "<img" in raw_html:
                buffer_html = raw_html # Zaten içinde var, direkt al
            else:
                # 2. Soru metni "Refer to Figure" gibi bir şey diyor mu?
                q_text_lower = q_text_content.lower()
                needs_image = any(kw in q_text_lower for kw in figure_keywords)
                
                # Eğer soru resim istiyorsa VE hafızamızda bir resim varsa
                if needs_image and global_last_image:
                    # Resmi sorunun tepesine ekle
                    buffer_html = global_last_image + q_text_html
                else:
                    # İstemiyorsa düz metin
                    buffer_html = q_text_html

            options = {}
            answer = None
            ref = None
            continue

        # --- ADIM 3: CEVAP SATIRI ---
        match_ans = ans_pattern.search(text)
        if match_ans:
            answer = match_ans.group(1)
            question_active = False 
            match_ref = ref_pattern.search(text)
            if match_ref: ref = match_ref.group(1)
            continue
        
        # --- ADIM 4: ŞIKLAR ---
        if question_active: 
            match_opt = opt_pattern.match(text)
            if match_opt:
                options[match_opt.group(1).lower()] = match_opt.group(2)
                continue

        # --- ADIM 5: SORUNUN DEVAMI ---
        if "REF:" not in text and "ANS:" not in text:
            if question_active: 
                # Eğer soru metninin devamıysa (veya şıklardan önce gelen açıklamayla) ekle
                # Ancak son eklediğimiz şey zaten aynı resimse tekrar ekleme (duplicate önleme)
                if raw_html != global_last_image:
                    buffer_html += raw_html

    # Döngü bitti, son soruyu ekle
    if current_q and len(options) >= 2 and answer:
        questions.append({
            'id': q_id, 'chapter': chapter_name, 'body_html': buffer_html,
            'options': options, 'answer': answer.lower(), 'ref': ref
        })

    return questions

# -----------------------------------------------------------------------------
# 2. PDF GÖSTERME (Aynen Kaldı)
# -----------------------------------------------------------------------------
def display_pdf(file_path):
    try:
        pdf_viewer(file_path, height=800)
    except Exception as e:
        st.error(f"PDF görüntülenemedi: {e}")

# -----------------------------------------------------------------------------
# 3. UYGULAMA ARAYÜZÜ (Aynen Kaldı)
# -----------------------------------------------------------------------------

st.set_page_config(page_title="ekoTestBank Pro", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SLIDES_DIR = os.path.join(BASE_DIR, "slides") 

st.markdown("""
<style>
    img { max-width: 100%; max-height: 350px; width: auto; display: block; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; cursor: pointer; }
    .stMarkdown p { font-size: 16px; }
    iframe { border: 1px solid #eee; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 ekoTestBank")

if 'all_questions' not in st.session_state:
    st.session_state.all_questions = []
if 'current_quiz' not in st.session_state:
    st.session_state.current_quiz = []

with st.sidebar:
    st.header("📌 Menü")
    page_selection = st.radio("Git:", ["📝 Quiz Çöz", "📊 Ders Slaytları"])
    st.markdown("---")

if page_selection == "📝 Quiz Çöz":
    with st.sidebar:
        st.subheader("⚙️ Quiz Ayarları")
        
        if st.button("📂 Soru Dosyalarını Tara (.docx)"):
            local_files = [f for f in os.listdir(BASE_DIR) if f.endswith('.docx')]
            if local_files:
                all_loaded = []
                bar = st.progress(0)
                for idx, file_name in enumerate(local_files):
                    ch_name = file_name.split('.')[0]
                    file_path = os.path.join(BASE_DIR, file_name)
                    with open(file_path, "rb") as f:
                        qs = parse_docx_with_images(f, ch_name)
                        all_loaded.extend(qs)
                    bar.progress((idx + 1) / len(local_files))
                
                st.session_state.all_questions = all_loaded
                st.success(f"Tamam! {len(all_loaded)} soru yüklendi.")
            else:
                st.warning("Klasörde .docx dosyası yok.")

        uploaded_files = st.file_uploader("Veya manuel yükle", type=['docx'], accept_multiple_files=True)
        if uploaded_files:
            all_loaded = []
            for up_file in uploaded_files:
                ch_name = up_file.name.split('.')[0]
                qs = parse_docx_with_images(up_file, ch_name)
                all_loaded.extend(qs)
            st.session_state.all_questions = all_loaded
            st.success(f"{len(all_loaded)} soru yüklendi.")

        if st.session_state.all_questions:
            st.markdown("---")
            mode = st.radio("Çalışma Modu", ["Chapter Bazlı", "Karma Test"])
            all_qs = st.session_state.all_questions
            new_quiz = []
            
            if mode == "Chapter Bazlı":
                chapters = sorted(list(set(q['chapter'] for q in all_qs)))
                sel_chap = st.selectbox("Chapter Seç:", chapters)
                new_quiz = [q for q in all_qs if q['chapter'] == sel_chap]
                
            else: 
                chapters = sorted(list(set(q['chapter'] for q in all_qs)))
                target_chaps = st.multiselect("Dahil Et:", chapters)
                count = st.number_input("Soru Sayısı:", 5, 200, 20)
                if st.button("Karma Test Oluştur"):
                    pool = [q for q in all_qs if q['chapter'] in target_chaps]
                    if pool:
                        new_quiz = random.sample(pool, min(count, len(pool)))
                        st.session_state.current_quiz = new_quiz
                        st.session_state.user_answers = {} 
                        st.rerun()

            if mode == "Chapter Bazlı" and new_quiz:
                 current_ids = [q['id'] for q in st.session_state.current_quiz]
                 new_ids = [q['id'] for q in new_quiz]
                 if current_ids != new_ids:
                     st.session_state.current_quiz = new_quiz
                     st.session_state.user_answers = {}

    if not st.session_state.current_quiz:
        st.info("👈 Başlamak için sol menüden soru dosyalarını yükleyin.")
    else:
        st.subheader(f"📝 Soru Çözümü ({len(st.session_state.current_quiz)} Soru)")
        
        for i, q in enumerate(st.session_state.current_quiz):
            with st.expander(f"Soru {i+1} - {q['id']}", expanded=True):
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
                    if q.get('ref'):
                        st.caption(f"Ref: {q['ref']}")

elif page_selection == "📊 Ders Slaytları":
    st.subheader("📊 Ders Materyalleri")
    if not os.path.exists(SLIDES_DIR):
        os.makedirs(SLIDES_DIR)
        st.warning(f"⚠️ '{SLIDES_DIR}' klasörü oluşturuldu. PDF'leri buraya atın.")
    
    pdf_files = [f for f in os.listdir(SLIDES_DIR) if f.lower().endswith('.pdf')]
    pdf_files.sort()
    
    if not pdf_files:
        st.info(f"📂 'slides' klasöründe dosya yok.")
    else:
        slide_map = {}
        display_names = []
        for f in pdf_files:
            clean = os.path.splitext(f)[0].split('_')[0]
            d_name = f"{clean} ({f})"
            slide_map[d_name] = f
            display_names.append(d_name)
            
        with st.sidebar:
            st.markdown("### 📑 Slayt Seç")
            sel_name = st.selectbox("Dosya:", display_names)
        
        if sel_name:
            path = os.path.join(SLIDES_DIR, slide_map[sel_name])
            st.write(f"**Görüntülenen:** `{slide_map[sel_name]}`")
            display_pdf(path)

