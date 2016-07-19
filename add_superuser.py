#!/bin/env python

import sqlite3
import pyotp
import qrcode

username = str(raw_input("Username: "))
secret = pyotp.random_base32()

try:
    conn = sqlite3.connect('auth.db')
    c = conn.cursor()
    c.execute('INSERT into users (username, is_admin, secret) values (?, 1, ?);', (username, secret))
    conn.commit()
except sqlite3.IntegrityError, e:
    print("User {} already exists".format(username))
    exit(1)

print("Added user: {}".format(username))
totp = pyotp.TOTP(secret)
img = qrcode.make(totp.provisioning_uri("Unlab:{}".format(username)))
img.show()
with open("{}.png".format(username), "wb") as f:
    img.save(f, format="png")
exit(0)
