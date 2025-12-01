import streamlit as st
import mammoth
from bs4 import BeautifulSoup
import re
import random
import os
from streamlit_pdf_viewer import pdf_viewer

# -----------------------------------------------------------------------------
# 1. DOCX -> HTML -> SORU AYRIŞTIRMA (GELİŞTİRİLMİŞ YAPIŞKAN FİGÜR MANTIĞI)
# -----------------------------------------------------------------------------
def parse_docx_with_images(file_obj, chapter_name):
    """
    DOCX dosyasını HTML'e çevirir. 
    Resimler bir soru bloğu boyunca (yeni resim gelene kadar) 
    ilgili sorulara 'yapışkan' olarak eklenir.
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
    preamble_html = ""      # İki soru arasındaki içerik (Resimler buraya düşer)
    
    # Yapışkan Resim Mantığı İçin:
    sticky_image_html = ""  # Son görülen resmi hafızada tutar
    
    options = {}
    answer = None
    ref = None
    q_id = None

    # Regexler
    q_start_pattern = re.compile(r'^(\d+)\.\s+(.*)') 
    opt_pattern = re.compile(r'^\s*([a-d])[\.\)]\s+(.*)', re.IGNORECASE)
    ans_pattern = re.compile(r'(?:ANS|Answer):\s+([A-D])', re.IGNORECASE)
    ref_pattern = re.compile(r'REF:\s+(.*)')
    
    # Soru metninde bu kelimeler varsa eski resmi tekrar yapıştıracağız
    figure_keywords = ["refer to", "figure", "table", "graph", "chart", "diagram", "shown in", "following", "aşağıdaki", "göre"]

    elements = soup.find_all(['p', 'table']) 
    
    for elem in elements:
        text = elem.get_text().strip()
        raw_html = str(elem) 

        # --- SENARYO 1: YENİ SORU BAŞLANGICI ---
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
            q_text_content = match_q.group(2) # Sadece metin kısmı
            q_id = f"{chapter_name} - Q{q_num}"
            
            # 1. Preamble (ara boşluk) içinde resim var mı kontrol et
            # Eğer yeni bir resim geldiyse, sticky_image'ı güncelle
            if "<img" in preamble_html or "<table" in preamble_html:
                sticky_image_html = preamble_html
            
            # 2. Soru metnini hazırla
            q_text_html = f"<p><b>{q_text_content}</b></p>"
            
            # 3. Resim Ekleme Mantığı (KRİTİK BÖLÜM)
            # Eğer preamble doluysa (yani hemen bu sorunun üstünde resim varsa) onu kullan.
            if preamble_html.strip():
                buffer_html = preamble_html + q_text_html
            else:
                # Preamble boşsa (yani üstte resim yoksa), soru metnine bak.
                # "Refer to figure" diyor mu? Ve elimizde eski bir resim (sticky) var mı?
                q_text_lower = q_text_content.lower()
                needs_image = any(kw in q_text_lower for kw in figure_keywords)
                
                if needs_image and sticky_image_html:
                    # Evet, eski resmi bu soruya da yapıştır!
                    buffer_html = sticky_image_html + q_text_html
                else:
                    # Hayır, düz metin devam et
                    buffer_html = q_text_html

            preamble_html = "" # Kullandık, temizle
            options = {}
            answer = None
            ref = None
            continue

        # --- SENARYO 2: CEVAP SATIRI ---
        match_ans = ans_pattern.search(text)
        if match_ans:
            answer = match_ans.group(1)
            question_active = False 
            match_ref = ref_pattern.search(text)
            if match_ref: ref = match_ref.group(1)
            continue
        
        # --- SENARYO 3: ŞIKLAR ---
        if question_active: 
            match_opt = opt_pattern.match(text)
            if match_opt:
                options[match_opt.group(1).lower()] = match_opt.group(2)
                continue

        # --- SENARYO 4: İÇERİK (RESİM, TABLO, METİN) ---
        if "REF:" not in text and "ANS:" not in text:
            if question_active: 
                # Soru hala aktif, cevap gelmedi -> Sorunun parçası
                buffer_html += raw_html
            else: 
                # Cevap geldi, yeni soru başlamadı -> Bu bir PREAMBLE (Resim/Tablo)
                preamble_html += raw_html

    # Döngü bitti, son soruyu ekle
    if current_q and len(options) >= 2 and answer:
        questions.append({
            'id': q_id, 'chapter': chapter_name, 'body_html': preamble_html + buffer_html,
            'options': options, 'answer': answer.lower(), 'ref': ref
        })

    return questions

# -----------------------------------------------------------------------------
# 2. PDF GÖSTERME FONKSİYONU
# -----------------------------------------------------------------------------
def display_pdf(file_path):
    # Eğer cloud ortamında dosya yolu sorunu olursa diye try-except
    try:
        pdf_viewer(file_path, height=800)
    except Exception as e:
        st.error(f"PDF görüntülenemedi: {e}")

# -----------------------------------------------------------------------------
# 3. UYGULAMA ARAYÜZÜ
# -----------------------------------------------------------------------------

st.set_page_config(page_title="ekoTestBank Pro", layout="wide")

# Çalışma dizinini sabitle
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SLIDES_DIR = os.path.join(BASE_DIR, "slides") 

# CSS Stilleri
st.markdown("""
<style>
    /* Resimlerin stili */
    img { max-width: 100%; max-height: 350px; width: auto; display: block; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; cursor: pointer; }
    /* Soru metni */
    .stMarkdown p { font-size: 16px; }
    /* PDF Viewer çerçevesi */
    iframe { border: 1px solid #eee; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 ekoTestBank")

# Session State
if 'all_questions' not in st.session_state:
    st.session_state.all_questions = []
if 'current_quiz' not in st.session_state:
    st.session_state.current_quiz = []

# --- SIDEBAR ---
with st.sidebar:
    st.header("📌 Menü")
    page_selection = st.radio("Git:", ["📝 Quiz Çöz", "📊 Ders Slaytları"])
    st.markdown("---")

# -----------------------------------------------------------------------------
# SAYFA 1: QUIZ ÇÖZME
# -----------------------------------------------------------------------------
if page_selection == "📝 Quiz Çöz":
    with st.sidebar:
        st.subheader("⚙️ Quiz Ayarları")
        
        # 1. Klasör Tarama
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

        # 2. Manuel Yükleme
        uploaded_files = st.file_uploader("Veya manuel yükle", type=['docx'], accept_multiple_files=True)
        if uploaded_files:
            all_loaded = []
            for up_file in uploaded_files:
                ch_name = up_file.name.split('.')[0]
                qs = parse_docx_with_images(up_file, ch_name)
                all_loaded.extend(qs)
            st.session_state.all_questions = all_loaded
            st.success(f"{len(all_loaded)} soru yüklendi.")

        # 3. Quiz Oluşturma
        if st.session_state.all_questions:
            st.markdown("---")
            mode = st.radio("Çalışma Modu", ["Chapter Bazlı", "Karma Test"])
            all_qs = st.session_state.all_questions
            new_quiz = []
            
            if mode == "Chapter Bazlı":
                chapters = sorted(list(set(q['chapter'] for q in all_qs)))
                sel_chap = st.selectbox("Chapter Seç:", chapters)
                new_quiz = [q for q in all_qs if q['chapter'] == sel_chap]
                
            else: # Karma
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

    # --- ANA EKRAN ---
    if not st.session_state.current_quiz:
        st.info("👈 Başlamak için sol menüden soru dosyalarını yükleyin.")
    else:
        st.subheader(f"📝 Soru Çözümü ({len(st.session_state.current_quiz)} Soru)")
        
        for i, q in enumerate(st.session_state.current_quiz):
            with st.expander(f"Soru {i+1} - {q['id']}", expanded=True):
                # HTML Render
                st.markdown(q['body_html'], unsafe_allow_html=True)
                
                # Şıklar
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

# -----------------------------------------------------------------------------
# SAYFA 2: SLAYTLAR
# -----------------------------------------------------------------------------
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
