# sn-mail
Checks if there's a new Security Now episode, and emails you the audio and show notes it if it hasn't already. Keeps track of last sent episode number in a text file. I'd recommend a `cron` job or something similar to run it periodically.

Yes, I know there's already a mailing list, but he doesn't attach the files, so I found this convenient.


```
usage: sn-mail.py [OPTIONS] USERNAME PASSWORD RECIPIENT [RECIPIENT ...]

Download and mail the most recent Security Now episode, if not already sent

positional arguments:
  USERNAME              sender email username
  PASSWORD              sender email password
  RECIPIENT             recipient email address

options:
  -h, --help            show this help message and exit
  -e, --episode NUMBER  instead of checking, just send the specified episode
  -b, --body BODY       email body (default: empty string)
  -d, --dir DIR         dir to store lastfile and downloaded content (default: script location)
  -l, --lastfile FILE   file to store the last-sent episode number (default: last.txt)
  -s, --server SERVER   SMTP server name (default: smtp.gmail.com)
  -p, --port PORT       SMTP server port (default 587)
```
