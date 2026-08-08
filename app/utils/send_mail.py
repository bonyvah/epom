import resend
from app.config import settings

resend.api_key = settings.resend_api_key

def send_mail(sender: str, receiver:str, subject:str, body:str) -> None:
    resend.Emails.send(
        {
            "from": sender,
            "to": receiver,
            "subject": subject,
            "html": body,
        }
    )
