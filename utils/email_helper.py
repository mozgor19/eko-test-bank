import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import streamlit as st

def send_reset_code(to_email, code):
    """Kullanıcıya 6 haneli doğrulama kodunu mail atar."""
    
    # Bilgileri çek (Hem .env hem Streamlit Secrets uyumlu)
    sender_email = os.getenv("EMAIL_SENDER") or st.secrets.get("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD") or st.secrets.get("EMAIL_PASSWORD")

    if not sender_email or not sender_password:
        return False, "Mail ayarları (Secrets) yapılmamış."

    subject = "ekoTestBank - Şifre Sıfırlama Kodu"
    body = f"""
    Merhaba,
    
    Şifrenizi sıfırlamak için doğrulama kodunuz:
    
    <h2>{code}</h2>
    
    Bu kodu kimseyle paylaşmayın.
    
    Sevgiler,
    ekoTestBank Ekibi
    """

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        # Gmail SMTP Sunucusu
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, to_email, text)
        server.quit()
        return True, "Kod gönderildi"
    except Exception as e:
        return False, str(e)
