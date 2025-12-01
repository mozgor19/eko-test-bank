import mammoth
from bs4 import BeautifulSoup
import re

def parse_docx(file_path, chapter_name):
    try:
        with open(file_path, "rb") as docx_file:
            result = mammoth.convert_to_html(docx_file)
            html = result.value
    except Exception as e:
        return []

    soup = BeautifulSoup(html, "html.parser")
    questions = []
    
    current_q = None
    question_active = False 
    buffer_html = ""        
    global_last_image = ""  
    options = {}
    answer = None
    ref = None
    q_id = None
    
    # Metadata değişkenleri
    meta_top = None
    meta_msc = None

    q_start_pattern = re.compile(r'^(\d+)\.\s+(.*)') 
    opt_pattern = re.compile(r'^\s*([a-d])[\.\)]\s+(.*)', re.IGNORECASE)
    ans_pattern = re.compile(r'(?:ANS|Answer):\s+([A-D])', re.IGNORECASE)
    ref_pattern = re.compile(r'REF:\s+(.*)')
    
    # Metadata Regexleri
    top_pattern = re.compile(r'TOP:\s*(.*)')
    msc_pattern = re.compile(r'MSC:\s*(.*)')

    figure_keywords = ["refer to figure", "refer to table"]

    elements = soup.find_all(['p', 'table']) 
    
    for elem in elements:
        text = elem.get_text().strip()
        raw_html = str(elem) 

        # --- METADATA YAKALAMA (TOP/MSC) ---
        # Bunları buffer_html'e eklemeyip değişkene alacağız
        match_top = top_pattern.search(text)
        if match_top:
            meta_top = match_top.group(1)
            continue # HTML'e ekleme
        
        match_msc = msc_pattern.search(text)
        if match_msc:
            meta_msc = match_msc.group(1)
            continue # HTML'e ekleme

        if "<img" in raw_html or "<table" in raw_html:
            global_last_image = raw_html

        match_q = q_start_pattern.match(text)
        if match_q:
            if current_q and len(options) >= 2 and answer:
                questions.append({
                    'id': q_id, 'chapter': chapter_name, 
                    'body_html': buffer_html, 'options': options, 
                    'answer': answer.lower(), 'ref': ref,
                    'top': meta_top, 'msc': meta_msc # Metadata ekle
                })
            
            question_active = True
            current_q = True
            q_num = match_q.group(1)
            q_text_content = match_q.group(2) 
            q_id = f"{chapter_name} - Q{q_num}"
            
            # Metadata sıfırla (yeni soru için)
            meta_top = None
            meta_msc = None
            
            q_text_html = f"<p><b>{q_text_content}</b></p>"
            
            if "<img" in raw_html:
                buffer_html = raw_html 
            else:
                q_text_lower = q_text_content.lower()
                needs_image = any(kw in q_text_lower for kw in figure_keywords)
                if needs_image and global_last_image:
                    buffer_html = global_last_image + q_text_html
                else:
                    buffer_html = q_text_html

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
            if question_active: 
                if raw_html != global_last_image:
                    buffer_html += raw_html

    if current_q and len(options) >= 2 and answer:
        questions.append({
            'id': q_id, 'chapter': chapter_name, 'body_html': buffer_html,
            'options': options, 'answer': answer.lower(), 'ref': ref,
            'top': meta_top, 'msc': meta_msc
        })

    return questions
