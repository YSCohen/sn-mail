#!/bin/python3
import argparse
import logging
import os
import urllib.request
from pathlib import Path

import feedparser

import mailer

parser = argparse.ArgumentParser(
    prog="sn-mail.py",
    description="Download and mail the most recent Security Now episode, if not already sent",
    usage="%(prog)s [OPTIONS] USERNAME PASSWORD RECIPIENTS [RECIPIENTS ...]",
)
parser.add_argument("username", metavar="USERNAME", help="sender email username")
parser.add_argument("password", metavar="PASSWORD", help="sender email password")
parser.add_argument(
    "recipients", metavar="RECIPIENT", help="recipient email address", nargs="+"
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
level_name = os.getenv("LOG_LEVEL", "INFO").upper()
level = getattr(logging, level_name, logging.INFO)
logging.basicConfig(level=level, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

if args.dir:
    dir = Path(args.dir)
else:
    dir = Path(__file__).resolve().parent

# get number of last-sent episode
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

# get most recent ep. #
logger.debug("Retrieving podcast feed...")
latest = int(
    feedparser.parse("https://feeds.twit.tv/podcasts/sn.xml")["entries"][0][
        "podcast_episode"
    ]
)
logger.debug("Retrieved")
logger.info(f"Most recent ep. {latest}")


if old != latest:
    logger.debug("There is a new episode...")

    # Hopefully he never changes the filenames,
    # but neither of them are reliably in the XML as far as I can tell

    # the feed is often updated a few hours before the files become available
    # so I try-excepted the requests to catch the 404s

    # Download the low-quality mp3;
    # the normal mp3 is too large for Gmail
    logger.debug("Downloading audio...")
    audio = f"sn-{latest}-lq.mp3"
    audioLink = f"https://media.grc.com/sn/{audio}"
    audioFile = str(dir / audio)
    try:
        urllib.request.urlretrieve(audioLink, audioFile)
    except urllib.error.HTTPError as e:
        logger.warning(f"Audio download failed: {e.code} {e.reason}")
    else:
        logger.debug("Downloaded")

    # Download the show notes
    logger.debug("Downloading show notes...")
    pdf = f"sn-{latest}-notes.pdf"
    pdfLink = f"https://www.grc.com/sn/{pdf}"
    pdfFile = str(dir / pdf)
    try:
        urllib.request.urlretrieve(pdfLink, pdfFile)
    except urllib.error.HTTPError as e:
        logger.warning(f"Notes download failed: {e.code} {e.reason}")
    else:
        logger.debug("Downloaded")

    # Attach both files to an empty email and send
    logger.debug("Sending email...")
    mailer.send(
        args.username,
        args.password,
        args.server,
        args.port,
        args.recipients,
        f"Security Now #{latest}",
        args.body,
        [audioFile, pdfFile],
    )
    logger.debug("Sent")

    # Update the lastfile
    logger.debug(f"Updating {lastFile}")
    try:
        with open(lastFile, "w") as file:
            file.write(str(latest) + "\n")
    except FileNotFoundError:
        logger.error(f"Could not create {lastFile}")
    else:
        logger.debug("Updated")
    finally:
        logger.info(f"Sent ep. {latest}")
else:
    # nothing has changed
    logger.info("No new episode")
