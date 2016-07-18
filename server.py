import jinja2
import sqlite3
import pyotp
import qrcode
from klein import Klein

from zope.interface import Interface, Attribute, implements
from twisted.python.components import registerAdapter

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.web.static import File
from twisted.web.server import Session

from twisted.enterprise import adbapi
dbpool = adbapi.ConnectionPool('sqlite3', 'auth.db')

webapp = Klein()
webapp.templates = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))

class IUser(Interface):
    username = Attribute("Unique user identifier")
    is_admin = Attribute("Boolean describes permisisons")

class User:
    implements(IUser)
    def __init__(self, session):
        self.username = None
        self.is_admin = False

registerAdapter(User, Session, IUser)

@inlineCallbacks
def check_passwd(username, passwd):
    row = yield dbpool.runQuery("SELECT secret, is_admin FROM users WHERE username = ?;", (username,))
    row = row[0] if row else None
    if not row:
        returnValue((None, False))
    secret = row[0]
    is_admin = row[1]
    totp = pyotp.TOTP(secret)
    if totp.verify(passwd):
        returnValue((username, is_admin))
    returnValue((None, False))

@webapp.route('/static/', branch=True)
def static(request):
    return File("./static")

@webapp.route('/', methods=['GET', 'POST'])
@inlineCallbacks
def home(request):
    messages=None
    if request.method == 'POST':
        uid = request.args.get('username', None)[0] if request.args.get('username', None) else None
        passwd = request.args.get('password', None)[0] if request.args.get('password', None) else None
        print uid, passwd
        if uid and passwd:
            uid, is_admin = yield check_passwd(uid, passwd)
            if uid is not None:
                session = request.getSession()
                user = IUser(session)
                user.username = uid
                user.is_admin = is_admin
                # Unlock Here
                page = webapp.templates.get_template('success.html')
                returnValue(page.render(user=user))
        messages="Invalid Entry"
    page = webapp.templates.get_template('index.html')
    returnValue(page.render(messages=messages))

@webapp.route('/adduser', methods=['GET', 'POST'])
@inlineCallbacks
def adduser(request):
    """ Method to insert new username, generate secret"""
    messages = None
    session = request.getSession()
    user = IUser(session)
    if not user.is_admin:
        request.setResponseCode(403)
        returnValue('Permission Denied')
    if request.method == 'POST':
        username = request.args.get("username", None)[0]
        if username is not None:
            # Generate Secret
            secret = pyotp.random_base32()
            # Insert user into db
            try:
                yield dbpool.runOperation('INSERT into users (username, secret) values (?, ?);', (username, secret))
                # generate QRCODE
                totp = pyotp.TOTP(secret)
                img = qrcode.make(totp.provisioning_uri("Unlab:{}".format(username)))
                page = webapp.templates.get_template('show_qrcode.html')
                returnValue(page.render(username=username, img=make_datauri(img)))
            except sqlite3.IntegrityError, e:
                messages = "User {} already exists".format(username)
        else:
            messages = "Failed to create user"
    # Display new user form
    page = webapp.templates.get_template('new_user_form.html')
    returnValue(page.render(messages=messages))

def make_datauri(img):
    from StringIO import StringIO
    from base64 import b64encode
    fp = StringIO()
    img.save(fp, format="png")
    return("data:image/png;base64,{}".format(b64encode(fp.getvalue())))

resource = webapp.resource
