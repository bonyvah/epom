import resend
import asyncio
from app.config import settings

resend.api_key = settings.resend_api_key


async def send_mail(sender: str, receiver: str, subject: str, body: str) -> None:
    await asyncio.to_thread(
        resend.Emails.send,
        {
            "from": sender,
            "to": receiver,
            "subject": subject,
            "html": body,
        },
    )
