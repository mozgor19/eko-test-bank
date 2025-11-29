import streamlit as st
import mammoth
from bs4 import BeautifulSoup
import re
import random
import os

# -----------------------------------------------------------------------------
# 1. DOCX -> HTML -> SORU AYRIŞTIRMA
# -----------------------------------------------------------------------------
def parse_docx_with_images(file_obj, chapter_name):
    """
    DOCX dosyasını HTML'e çevirir (resimler gömülü gelir) ve soruları ayıklar.
    """
    # 1. Mammoth ile DOCX'i HTML'e çevir
    result = mammoth.convert_to_html(file_obj)
    html = result.value
    
    # 2. HTML'i BeautifulSoup ile parçala
    soup = BeautifulSoup(html, "html.parser")
    
    questions = []
    current_q = None
    
    # Tüm paragrafları ve elementleri sırayla gez
    # Genellikle sorular <p> etiketi içindedir
    elements = soup.find_all(['p', 'table']) 
    
    # Akış kontrolü için tampon değişkenler
    buffer_html = "" # Sorunun gövdesi (resimler dahil)
    options = {}
    answer = None
    ref = None
    q_id = None
    
    # Regex desenleri
    q_start_pattern = re.compile(r'^(\d+)\.\s+(.*)') # "1. Soru metni"
    opt_pattern = re.compile(r'^\s*([a-d])\.\s+(.*)', re.IGNORECASE) # "a. Şık metni"
    ans_pattern = re.compile(r'ANS:\s+([A-D])', re.IGNORECASE) # "ANS: C"
    ref_pattern = re.compile(r'REF:\s+(.*)')

    for elem in elements:
        text = elem.get_text().strip()
        raw_html = str(elem) # Resimler bu html içinde (<img src="data:...">)

        # A) YENİ BİR SORU BAŞLANGICI MI? (Örn: "1. Aşağıdakilerden...")
        match_q = q_start_pattern.match(text)
        if match_q:
            # Önceki soruyu kaydet (Eğer varsa ve tamamsa)
            if current_q and len(options) >= 2 and answer:
                questions.append({
                    'id': q_id,
                    'chapter': chapter_name,
                    'body_html': buffer_html, # Soru metni + Resimler HTML olarak
                    'options': options,
                    'answer': answer.lower(),
                    'ref': ref
                })
            
            # Yeni soru başlat
            current_q = True
            q_num = match_q.group(1)
            q_text_content = match_q.group(2)
            q_id = f"{chapter_name} - Q{q_num}"
            
            # Soru metnini HTML olarak başlat (Sayıyı temizleyerek)
            # Sadece metni değil, elem içindeki HTML'i alıyoruz (belki bold/italik vardır)
            # Ancak "1." kısmını temizlemek için basitçe metni alıyoruz şimdilik,
            # Resim varsa genellikle soru metninden sonraki paragraflarda gelir.
            buffer_html = f"<p><b>{q_text_content}</b></p>" 
            
            # Değişkenleri sıfırla
            options = {}
            answer = None
            ref = None
            continue

        # Eğer şu an bir soru okumuyorsak geç
        if not current_q:
            continue

        # B) CEVAP SATIRI MI? (ANS: C)
        match_ans = ans_pattern.search(text)
        if match_ans:
            answer = match_ans.group(1)
            # Aynı satırda REF var mı?
            match_ref = ref_pattern.search(text)
            if match_ref:
                ref = match_ref.group(1)
            continue

        # C) ŞIK MI? (a. Şık metni)
        match_opt = opt_pattern.match(text)
        if match_opt:
            opt_char = match_opt.group(1).lower()
            opt_text = match_opt.group(2)
            options[opt_char] = opt_text
            continue

        # D) SORUNUN DEVAMI VEYA RESİM OLABİLİR
        # Eğer yukarıdakilerden hiçbiri değilse, sorunun parçasıdır (Resim, tablo veya devam metni)
        # Sadece REF satırı değilse ekle
        if "REF:" not in text and "ANS:" not in text:
            buffer_html += raw_html

    # Döngü bittiğinde son soruyu ekle
    if current_q and len(options) >= 2 and answer:
        questions.append({
            'id': q_id,
            'chapter': chapter_name,
            'body_html': buffer_html,
            'options': options,
            'answer': answer.lower(),
            'ref': ref
        })

    return questions

# -----------------------------------------------------------------------------
# 2. UYGULAMA ARAYÜZÜ
# -----------------------------------------------------------------------------

st.set_page_config(page_title="ekoTestBank (Resimli)", layout="wide")
st.title("🎓 ekoTestBank")
st.markdown("---")

# Session State
if 'all_questions' not in st.session_state:
    st.session_state.all_questions = []
if 'current_quiz' not in st.session_state:
    st.session_state.current_quiz = []

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Ayarlar")
    
    # 1. Klasör Tarama Butonu
    if st.button("📂 Klasördeki .docx Dosyalarını Tara"):
        local_files = [f for f in os.listdir('.') if f.endswith('.docx')]
        if local_files:
            all_loaded = []
            progress_bar = st.progress(0)
            
            for idx, file_name in enumerate(local_files):
                ch_name = file_name.split('.')[0]
                with open(file_name, "rb") as f:
                    qs = parse_docx_with_images(f, ch_name)
                    all_loaded.extend(qs)
                progress_bar.progress((idx + 1) / len(local_files))
                
            st.session_state.all_questions = all_loaded
            st.success(f"İşlem tamam! {len(all_loaded)} soru yüklendi.")
        else:
            st.warning("Klasörde .docx dosyası yok.")

    # 2. Manuel Yükleme
    uploaded_files = st.file_uploader("Veya .docx yükle", type=['docx'], accept_multiple_files=True)
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
        mode = st.radio("Mod Seç", ["Chapter Bazlı", "Karma Test"])
        all_qs = st.session_state.all_questions
        
        # Seçilen soruları geçici tut
        new_quiz = []
        
        if mode == "Chapter Bazlı":
            chapters = sorted(list(set(q['chapter'] for q in all_qs)))
            sel_chap = st.selectbox("Chapter:", chapters)
            new_quiz = [q for q in all_qs if q['chapter'] == sel_chap]
            
        else: # Karma
            chapters = sorted(list(set(q['chapter'] for q in all_qs)))
            target_chaps = st.multiselect("Chapterlar:", chapters)
            count = st.number_input("Soru Sayısı:", 10, 100, 20)
            if st.button("Testi Oluştur"):
                pool = [q for q in all_qs if q['chapter'] in target_chaps]
                if pool:
                    new_quiz = random.sample(pool, min(count, len(pool)))
                    st.session_state.current_quiz = new_quiz
                    st.rerun()

        # Chapter modunda otomatik güncelle
        if mode == "Chapter Bazlı" and new_quiz:
             if st.session_state.current_quiz != new_quiz:
                 st.session_state.current_quiz = new_quiz

# --- ANA EKRAN ---
if not st.session_state.current_quiz:
    st.info("👈 Soldan dosya yükleyip test oluşturun.")
else:
    st.subheader(f"📝 Quiz Başladı ({len(st.session_state.current_quiz)} Soru)")
    
    for i, q in enumerate(st.session_state.current_quiz):
        with st.expander(f"Soru {i+1} - {q['id']}", expanded=True):
            # 1. Soruyu ve Resimleri Göster (HTML render edilir)
            # unsafe_allow_html=True sayesinde <img> etiketleri çalışır
            st.markdown(q['body_html'], unsafe_allow_html=True)
            
            # 2. Şıklar (Streamlit Radio)
            opts = list(q['options'].keys())
            fmt_opts = [f"{k}) {v}" for k, v in q['options'].items()]
            
            key = f"ans_{i}_{q['id']}"
            user_choice = st.radio("Cevap:", fmt_opts, key=key, index=None)
            
            # 3. Kontrol
            if user_choice:
                sel = user_choice.split(')')[0]
                corr = q['answer']
                
                if sel == corr:
                    st.success("✅ Doğru")
                else:
                    st.error(f"❌ Yanlış. Cevap: {corr.upper()}")
                
                if q.get('ref'):
                    st.caption(f"Ref: {q['ref']}")

