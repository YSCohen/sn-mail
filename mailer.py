import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from os.path import basename


def send(
    sender: str,
    password: str,
    server: str,
    port: int,
    rcpts: list[str],
    sub: str,
    content: str,
    attachments=None,
) -> None:
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(rcpts)
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = sub

    msg.attach(MIMEText(content))
    for f in attachments or []:
        with open(f, "rb") as fil:
            part = MIMEApplication(fil.read(), Name=basename(f))
        # After the file is closed
        part["Content-Disposition"] = 'attachment; filename="%s"' % basename(f)
        msg.attach(part)

    session = smtplib.SMTP(server, port)
    session.ehlo()
    session.starttls()
    session.ehlo()
    session.login(sender, password)
    session.sendmail(sender, rcpts, msg.as_string())
    session.quit()
