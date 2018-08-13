import re,time,json,logging,hashlib,base64,asyncio
from webframe import get,post
from models import User,Comment,Blog,next_id
import time,json,hashlib
from apis import APIError,APIValueError
from aiohttp import web
from config import configs

COOKIE_NAME='ztysession'
_COOKIE_KEY=configs.session.secret


@get('/')
async def index(request):
    summary = '与其感慨路难行，不如马上出发'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
    ]
    return {'__template__':'blogs.html',
            'blogs':blogs}

@get('/api/users')
async def api_get_users():
    users=await User.findAll(orderBy='created_at desc')
    for u in users:
        u.password='*******'
    return dict(users=users)

def user2cookie(user,max_age):
    expires=str(int(time.time()+max_age))
    s='%s-%s-%s-%s'%(user.id,user.passwd,expires,_COOKIE_KEY)
    L=[user.id,expires,hashlib.sha1(s.encode('utf-8').hexdigest())]
    return '-'.join(L)

async def cookie2user(cookie_str):
    if not cookie_str:
        return None
    try:
        L=cookie_str.split('-')
        if len(L)!=3:
            return None
        uid,expires,sha1=L
        if int(expires)<time.time():
            return None
        user=await User.find(uid)
        if user is None:
            s='%s-%s-%s-%s'% (uid,user.passwd,expires,_COOKIE_KEY)
        if sha1 !=hashlib.sha1(s.encode('utf-8')).hexdigest():
            logging.info('invalid sha1')
            return None
        user.passwd='******'
        return user
    except Exception as e:
        logging.exception(e)
        return None

@get('/register')
def register():
    return {'__template__':'register.html'}

@get('/signin')
def signin():
    return {'__tempalte__':'signin.html'}

_reEmail = re.compile(r'^[0-9a-z\.\-\_]+\@[0-9a-z\-\_]+(\.[0-9a-z\-\_]+){1,4}$')
_reSha1 = re.compile(r'^[0-9a-f]{40}$') # SHA1不够安全，后续需升级

@post('/api/authenticate')
async def authenticate(*,email,passwd):
    if not email:
        raise APIValueError('email','Invalid email.')
    if not passwd:
        raise APIValueError('passwd','Invalid password')
    users=await User.findAll('email=?',[email])
    if len(users)==0:
        raise APIValueError('email','email is not existed')
    user=user[0]
    sha1=hashlib.sh1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd','invalid password')
    r=web.Response()
    r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
    user.passwd='******'
    r.content_type='application/json'
    r.body=json.dumps(user,ensure_ascii=False).encode('utf-8')
    return r

@post('/api/users')
async def api_register_user(*,email,name,passwd):
    if not email or not _reEmail.match(email):
        raise APIValueError('email')
    if not name or not name.strip():
        raise APIValueError('name')
    if not passwd or _reSha1.match(passwd):
        raise APIValueError('passwd')
    users=await User.findAll('email=?',[email])
    if len(users)>0:
        raise APIError('register failed',email,'email is already in use')
    uid=next_id()
    sha1Passwd='%s:%s' % (uid,passwd)
    user=User(id=uid,email=email,passwd=hashlib.sha1(sha1Passwd.encode('utf-8')).hexdigest(),name=name.strip(),image='about:blank')
    await user.save()
    r=web.Response()
    r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
    user.passwd='******'
    r.content_type='application/json'
    r.body=json.dumps(user,ensure_ascii=False).encode('utf-8')
    return r






