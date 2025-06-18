#!/bin/python3
import argparse
import logging
import os
import smtplib
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from pathlib import Path

parser = argparse.ArgumentParser(
    prog="sn-mail.py",
    description="Download and mail the most recent Security Now episode, if not already sent",
    usage="%(prog)s [OPTIONS] USERNAME PASSWORD RECIPIENT [RECIPIENT ...]",
)
parser.add_argument("username", metavar="USERNAME", help="sender email username")
parser.add_argument("password", metavar="PASSWORD", help="sender email password")
parser.add_argument(
    "recipients", metavar="RECIPIENT", help="recipient email address", nargs="+"
)
parser.add_argument(
    "-e",
    "--episode",
    type=int,
    metavar="NUMBER",
    default=None,
    help="instead of checking, just send the specified episode",
)
parser.add_argument(
    "-b", "--body", default="", help="email body (default: empty string)"
)
parser.add_argument(
    "-d",
    "--dir",
    default=None,
    help="dir to store lastfile and downloaded content (default: script location)",
)
parser.add_argument(
    "-l",
    "--lastfile",
    metavar="FILE",
    default="last.txt",
    help="file to store the last-sent episode number (default: %(default)s)",
)
parser.add_argument(
    "-s",
    "--server",
    default="smtp.gmail.com",
    help="SMTP server name (default: %(default)s)",
)
parser.add_argument(
    "-p",
    "--port",
    type=int,
    default=587,
    help="SMTP server port (default %(default)s)",
)
args = parser.parse_args()

# Logging setup
levelName = os.getenv("LOG_LEVEL", "INFO").upper()
level = getattr(logging, levelName, logging.INFO)
logging.basicConfig(level=level, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Determine dir for lastFile and media
if args.dir:
    dir = Path(args.dir)
else:
    dir = Path(__file__).resolve().parent

# If a number was specified, use that
if args.episode:
    number = args.episode
    lastFile = None
# Otherwise, check last sent against newest episode
else:
    # Get number of last-sent episode
    lastFile = dir / args.lastfile
    logger.debug(f"Checking {lastFile} for last sent ep. #...")

    try:
        with open(lastFile, "r") as file:
            old = int(file.read())
    except FileNotFoundError:
        logger.warning(f"{lastFile} not found. Creating it...")
        try:
            with open(lastFile, "w") as file:
                file.write("\n")
        except FileNotFoundError:
            logger.error(f"Could not create {lastFile}")
        else:
            logger.info(f"Successfully created {lastFile}")
        finally:
            logger.info("Pretending last ep. = 0")
            old = 0
    except ValueError:
        logger.warning("Non-int lastfile value")
        logger.info("Pretending last ep. = 0")
        old = 0
    else:
        logger.info(f"Last sent ep. {old}")

    # Get most recent ep. #
    logger.debug("Retrieving podcast feed...")

    feedURL = "https://feeds.twit.tv/podcasts/sn.xml"

    with urllib.request.urlopen(feedURL) as u:
        XMLFeed = u.read()

    latest = int(
        ET.fromstring(XMLFeed)
        .find("./channel/item")
        .find(
            "podcast:episode",
            namespaces={"podcast": "https://podcastindex.org/namespace/1.0"},
        )
        .text
    )

    logger.debug("Retrieved")
    logger.info(msg=f"Most recent ep. {latest}")
    if old != latest:
        number = latest
    else:
        # Do nothing
        number = None
        logger.info("No new episode")


if number:
    logger.debug(f"Will send episode {number}")

    # Hopefully he never changes the filenames,
    # but neither of them are reliably in the XML as far as I can tell

    # the feed is often updated a few hours before the files become available
    # so I try-excepted the requests to catch the 404s

    # Download the low-quality mp3;
    # the normal mp3 is too large for Gmail
    logger.debug("Downloading audio...")
    audio = f"sn-{number}-lq.mp3"
    audioURL = f"https://media.grc.com/sn/{audio}"
    audioFile = str(dir / audio)
    try:
        urllib.request.urlretrieve(audioURL, audioFile)
    except urllib.error.HTTPError as e:
        logger.critical(f"Audio download failed: {e.code} {e.reason}")
        sys.exit()
    else:
        logger.debug("Downloaded")

    # Download the show notes
    logger.debug("Downloading show notes...")
    pdf = f"sn-{number}-notes.pdf"
    pdfURL = f"https://www.grc.com/sn/{pdf}"
    pdfFile = str(dir / pdf)
    try:
        urllib.request.urlretrieve(pdfURL, pdfFile)
    except urllib.error.HTTPError as e:
        logger.critical(f"Notes download failed: {e.code} {e.reason}")
        sys.exit()
    else:
        logger.debug("Downloaded")

    # Attach both files to an email and send
    logger.debug("Sending email...")

    msg = MIMEMultipart()
    msg["From"] = args.username
    msg["To"] = ", ".join(args.recipients)
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = f"Security Now #{number}"

    msg.attach(MIMEText(args.body))
    for f in [audioFile, pdfFile]:
        with open(f, "rb") as fil:
            part = MIMEApplication(fil.read(), Name=os.path.basename(f))
        part["Content-Disposition"] = 'attachment; filename="%s"' % os.path.basename(f)
        msg.attach(part)

    session = smtplib.SMTP(args.server, args.port)
    session.ehlo()
    session.starttls()
    session.ehlo()
    session.login(args.username, args.password)
    session.sendmail(args.username, args.recipients, msg.as_string())
    session.quit()

    logger.debug("Sent")

    if lastFile:
        # Update the lastfile unless episode specified
        logger.debug(f"Updating {lastFile}")
        try:
            with open(lastFile, "w") as file:
                file.write(str(number) + "\n")
        except FileNotFoundError:
            logger.error(f"Could not create {lastFile}")
        else:
            logger.debug("Updated")
        finally:
            logger.info(f"Sent ep. {number}")
