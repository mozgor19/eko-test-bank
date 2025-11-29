import streamlit as st
import mammoth
from bs4 import BeautifulSoup
import re
import random
import os
import base64  # PDF görüntülemek için gerekli

# -----------------------------------------------------------------------------
# 1. DOCX -> HTML -> SORU AYRIŞTIRMA (Önceki Mantık Aynen Korundu)
# -----------------------------------------------------------------------------
def parse_docx_with_images(file_obj, chapter_name):
    """
    DOCX dosyasını HTML'e çevirir (resimler gömülü gelir) ve soruları ayıklar.
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
    current_q = None
    question_active = False 
    
    buffer_html = ""        
    preamble_html = ""      
    options = {}
    answer = None
    ref = None
    q_id = None

    # Regexler
    q_start_pattern = re.compile(r'^(\d+)\.\s+(.*)') 
    opt_pattern = re.compile(r'^\s*([a-d])[\.\)]\s+(.*)', re.IGNORECASE)
    ans_pattern = re.compile(r'(?:ANS|Answer):\s+([A-D])', re.IGNORECASE)
    ref_pattern = re.compile(r'REF:\s+(.*)')

    elements = soup.find_all(['p', 'table']) 
    
    for elem in elements:
        text = elem.get_text().strip()
        raw_html = str(elem) 

        # --- SENARYO 1: YENİ SORU BAŞLANGICI ---
        match_q = q_start_pattern.match(text)
        if match_q:
            if current_q and len(options) >= 2 and answer:
                questions.append({
                    'id': q_id, 'chapter': chapter_name, 'body_html': buffer_html, 
                    'options': options, 'answer': answer.lower(), 'ref': ref
                })

            question_active = True
            current_q = True # current_q flagini set et
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

        # --- SENARYO 4: İÇERİK (RESİM VS) ---
        if "REF:" not in text and "ANS:" not in text:
            if question_active: buffer_html += raw_html
            else: preamble_html += raw_html

    # Son soruyu ekle
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
    """
    PDF dosyasını binary okuyup base64 ile iframe içine gömer.
    Bu yöntem cloud servislerinde (Streamlit Cloud, Netlify vb.) sorunsuz çalışır.
    """
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode('utf-8')
    
    # PDF'i gömülü gösteren HTML (Genişlik ve Yükseklik ayarlı)
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf"></iframe>'
    st.markdown(pdf_display, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 3. UYGULAMA ARAYÜZÜ
# -----------------------------------------------------------------------------

st.set_page_config(page_title="ekoTestBank Pro", layout="wide")

# Çalışma dizinini sabitle
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SLIDES_DIR = os.path.join(BASE_DIR, "slides") # Slayt klasörü

# CSS Stilleri (Resim boyutları vs.)
st.markdown("""
<style>
    img { max-width: 100%; max-height: 350px; width: auto; display: block; margin-bottom: 10px; border-radius: 5px; border: 1px solid #ddd; cursor: pointer; }
    .stMarkdown p { font-size: 16px; }
    iframe { border: 1px solid #eee; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("🎓 ekoTestBank")

# Session State
if 'all_questions' not in st.session_state:
    st.session_state.all_questions = []
if 'current_quiz' not in st.session_state:
    st.session_state.current_quiz = []

# --- SIDEBAR NAVİGASYON ---
with st.sidebar:
    st.header("📌 Menü")
    # Sayfa Seçimi: Quiz mi Slayt mı?
    page_selection = st.radio("Git:", ["📝 Quiz Çöz", "📊 Ders Slaytları"])
    st.markdown("---")

# -----------------------------------------------------------------------------
# SAYFA 1: QUIZ ÇÖZME
# -----------------------------------------------------------------------------
if page_selection == "📝 Quiz Çöz":
    with st.sidebar:
        st.subheader("⚙️ Quiz Ayarları")
        
        # 1. Klasör Tarama Butonu
        if st.button("📂 Soru Dosyalarını Tara (.docx)"):
            # Sadece root klasördeki docx'leri al
            local_files = [f for f in os.listdir(BASE_DIR) if f.endswith('.docx')]
            if local_files:
                all_loaded = []
                progress_bar = st.progress(0)
                
                for idx, file_name in enumerate(local_files):
                    ch_name = file_name.split('.')[0]
                    file_path = os.path.join(BASE_DIR, file_name)
                    with open(file_path, "rb") as f:
                        qs = parse_docx_with_images(f, ch_name)
                        all_loaded.extend(qs)
                    progress_bar.progress((idx + 1) / len(local_files))
                
                st.session_state.all_questions = all_loaded
                st.success(f"İşlem tamam! {len(all_loaded)} soru yüklendi.")
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

        # 3. Quiz Oluşturma Seçenekleri
        if st.session_state.all_questions:
            st.markdown("---")
            mode = st.radio("Çalışma Modu", ["Chapter Bazlı", "Karma Test"])
            all_qs = st.session_state.all_questions
            
            new_quiz = []
            
            if mode == "Chapter Bazlı":
                chapters = sorted(list(set(q['chapter'] for q in all_qs)))
                sel_chap = st.selectbox("Chapter Seç:", chapters)
                # Butona gerek yok, seçim yapınca quiz güncellensin
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
                        st.session_state.user_answers = {} # Cevapları sıfırla
                        st.rerun()

            # Chapter modunda otomatik güncelleme mantığı
            if mode == "Chapter Bazlı" and new_quiz:
                 # Eğer yeni seçilen quiz eskisiyle aynı değilse güncelle
                 current_ids = [q['id'] for q in st.session_state.current_quiz]
                 new_ids = [q['id'] for q in new_quiz]
                 if current_ids != new_ids:
                     st.session_state.current_quiz = new_quiz
                     st.session_state.user_answers = {}

    # --- ANA EKRAN (QUIZ) ---
    if not st.session_state.current_quiz:
        st.info("👈 Başlamak için sol menüden soru dosyalarını yükleyin.")
    else:
        st.subheader(f"📝 Soru Çözümü ({len(st.session_state.current_quiz)} Soru)")
        
        for i, q in enumerate(st.session_state.current_quiz):
            with st.expander(f"Soru {i+1} - {q['id']}", expanded=True):
                # Soru Metni ve Resimler
                st.markdown(q['body_html'], unsafe_allow_html=True)
                
                # Şıklar
                opts = list(q['options'].keys())
                fmt_opts = [f"{k}) {v}" for k, v in q['options'].items()]
                
                key = f"ans_{i}_{q['id']}"
                # Cevabı session_state'den hatırla (eğer varsa)
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
# SAYFA 2: DERS SLAYTLARI
# -----------------------------------------------------------------------------
elif page_selection == "📊 Ders Slaytları":
    st.subheader("📊 Ders Materyalleri ve Slaytlar")
    
    # Slides klasörü var mı kontrol et
    if not os.path.exists(SLIDES_DIR):
        os.makedirs(SLIDES_DIR) # Yoksa oluştur
        st.warning(f"⚠️ '{SLIDES_DIR}' klasörü oluşturuldu. Lütfen içine PDF dosyalarınızı atın.")
    
    # PDF Dosyalarını Listele
    pdf_files = [f for f in os.listdir(SLIDES_DIR) if f.lower().endswith('.pdf')]
    pdf_files.sort() # Sıralı gelsin
    
    if not pdf_files:
        st.info(f"📂 'slides' klasöründe henüz PDF dosyası yok. Dosyaları yükledikten sonra sayfayı yenileyin.")
    else:
        # Dosya isimlerini temizle (Örn: "Chapter03_Sunum.pdf" -> "Chapter03")
        # Kullanıcıya gösterilecek isimler ve gerçek dosya adları için sözlük
        slide_map = {}
        display_names = []
        
        for f in pdf_files:
            # İsmi '_' karakterine göre böl ve ilk kısmı al
            clean_name = f.split('_')[0] 
            # Eğer '_' yoksa dosya adını olduğu gibi al (uzantısız)
            if clean_name == f:
                clean_name = os.path.splitext(f)[0]
            
            # Aynı chapter ismi varsa karışmasın diye orijinal ismi de parantezde tutabiliriz
            # Ama talep "sadece başını al" olduğu için:
            display_name = f"{clean_name} ({f})" # Kullanıcı tam adı da görsün karışıklık olmasın
            slide_map[display_name] = f
            display_names.append(display_name)
            
        # Kenar Çubuğunda Seçim
        with st.sidebar:
            st.markdown("### 📑 Slayt Seç")
            selected_display_name = st.radio("Mevcut Slaytlar:", display_names)
        
        # Seçilen PDF'i Göster
        if selected_display_name:
            filename = slide_map[selected_display_name]
            full_path = os.path.join(SLIDES_DIR, filename)
            
            st.write(f"**Görüntülenen:** `{filename}`")
            display_pdf(full_path)
