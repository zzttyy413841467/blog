import re,time,json,logging,hashlib,base64,asyncio
from webframe import get,post
from models import User,Comment,Blog,next_id
import time,json,hashlib
from apis import APIError,APIValueError,APIPermissionError,Page,APIResourceNotFoundError
from aiohttp import web
from config import configs
import markdown2
COOKIE_NAME='ztysession'
_COOKIE_KEY=configs.session.secret

def check_admin(request):
    if not request.__user__.admin or request.__user__ is None:
        raise APIPermissionError()

def get_page_index(page_str):
    p=1
    try:
        p=int(page_str)
    except ValueError as e:
        pass
    if p<1:
        p=1
    return p

@get('/')
async def index(request,*,page='1'):
    page_index=get_page_index(page)
    num=await Blog.findNumber('count(id)')
    page=Page(num)
    if num==0:
        blogs=[]
    else:
        blogs=await Blog.findAll(orderBy='created_at desc',limit=(page.offset,page.limit))
    return {'__template__':'blogs.html',
            'page':page,
            'blogs':blogs,
            'user':request.__user__}

@get('/api/users')
async def api_get_users(request,*,page='1'):
    page_index=get_page_index(page)
    num=await User.findNumber('count(id)')
    p=Page(num,page_index)
    if num==0:
        return dict(page=p,users=())
    users=await User.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
    for u in users:
        u.password='*******'
    return dict(page=p,users=users)

def user2cookie(user,max_age):
    expires=str(int(time.time()+max_age))
    s='%s-%s-%s-%s'%(user.id,user.passwd,expires,_COOKIE_KEY)
    L=[user.id,expires,hashlib.sha1(s.encode('utf-8')).hexdigest()]
    return '-'.join(L)

def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)


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
            return None
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
    return {'__template__':'signin.html'}

_reEmail = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
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
    user=users[0]
    sha1=hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest():
        raise APIValueError('passwd','Invalid password')
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
    if not passwd or not _reSha1.match(passwd):
        raise APIValueError('passwd')
    users=await User.findAll('email=?',[email])
    if len(users)>0:
        raise APIError('register failed',email,'email is already in use')
    uid=next_id()
    sha1Passwd='%s:%s' % (uid,passwd)
    user=User(id=uid,name=name.strip(),email=email,passwd=hashlib.sha1(sha1Passwd.encode('utf-8')).hexdigest(),image='about:blank')
    await user.save()
    r=web.Response()
    r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
    user.passwd='******'
    r.content_type='application/json'
    r.body=json.dumps(user,ensure_ascii=False).encode('utf-8')
    return r

@get('/signout')
def signout(request):
    referer=request.headers.get('Referer')
    r=web.HTTPFound(referer or '/')
    r.set_cookie(COOKIE_NAME,'-deleted-',max_age=0,httponly=True)
    logging.info('user: %s signed out!'% request.__user__.name)
    return r

@get('/manage/blogs/create')
def manage_create_blog(request):
    if not request.__user__.admin:
        raise APIPermissionError()
    return {'__template__':'manage_blog_edit.html','id':'','action':'/api/blogs','user': request.__user__}

@post('/api/blogs')
async def api_create_blog(request,*,name,summary,content):
    check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name','name cannot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary','summary cannot be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty')
    blog=Blog(
        user_id=request.__user__.id,
        user_name=request.__user__.name,
        user_image=request.__user__.image,
        name=name.strip(),
        summary=summary.strip(),
        content=content.strip()
    )
    await blog.save()
    return blog

@get('/blog/{id}')
async def get_blog(id,request):
    blog=await Blog.find(id)
    comments=await Comment.findAll('blog_id=?',[id],orderBy='created_at desc')
    for c in comments:
        c.html_content=text2html(c.content)
    blog.html_content=markdown2.markdown(blog.content)
    return {'__template__':'blog.html','blog':blog,'comments':comments,'user': request.__user__}

@get('/manage/blogs')
def manage_blogs(request,*,page='1'):
    return {'__template__':'manage_blogs.html','page_index':get_page_index(page),'user': request.__user__}

@get('/api/blogs')
async def api_blogs(*,page='1'):
    page_index=get_page_index(page)
    num=await Blog.findNumber('count(id)')
    p=Page(num,page_index)
    if num==0:
        return dict(page=p,blogs=())
    blogs=await Blog.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
    return dict(page=p,blogs=blogs)

@get('/api/blogs/{id}')
async def api_get_blog(*,id):
    blog=await Blog.find(id)
    return 'redirect:/manage/blogs'

@get('/manage/')
def manage():
    return 'redirect:/manage/comments'

@get('/manage/comments')
def manage_comments(request,*,page='1'):
    return{
        '__template__':'manage_comments.html',
        'page_index':get_page_index(page),
        'user':request.__user__
    }


@get('/manage/users')
def manage_users(request,*,page='1'):
    return{
        '__template__':'manage_users.html',
        'page_index':get_page_index(page),
        'user':request.__user__
    }

@get('/api/comments')
async def api_comments(*,page='1'):
    page_index=get_page_index(page)
    num=await Comment.findNumber('count(id)')
    p=Page(num,page_index)
    if num==0:
        return dict(page=p,comments=())
    comments=await Comment.findAll(orderBy='created_at desc',limit=(p.offset,p.limit))
    return dict(page=p,comments=comments)

@post('/api/blogs/{id}/comments')
async def api_create_comment(id,request, *, content):
    user=request.__user__
    if user is None:
        raise APIPermissionError('please sign in first')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty')
    blog=await Blog.find(id)
    if blog is None:
        raise APIResourceNotFoundError('blog')
    comment=Comment(blog_id=blog.id,user_id=user.id,user_name=user.name,user_image=user.image,content=content.strip())
    await comment.save()
    return comment


@get('/manage/blogs/edit')
def manage_edit_blog(request,*,id):
    return{
        '__template__':'manage_blog_edit.html',
        'id':id,
        'action':'/api/blogs/%s' % id,
        'user':request.__user__
    }

@post('/api/comments/{id}/delete')
async def api_delete_comments(id,request):
    check_admin(request)
    c=await Comment.find(id)
    if c is None:
        raise APIResourceNotFoundError('Comment')
    await c.remove()
    return dict(id=id)

@post('/api/blogs/{id}')
async def api_update_blog(id,request,*,name,summary,content):
    check_admin(request)
    blog=await Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name','name cannot be empty')
    if not summary or not summary.strip():
        raise APIValueError('summary','summary cannot be empty')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty')
    blog.name=name.strip()
    blog.summary=summary.strip()
    blog.content=content.strip()
    await blog.update()
    return blog

@post('/api/blogs/{id}/delete')
async def api_delete_blogs(request,*,id):
    check_admin(request)
    blog=await Blog.find(id)
    await blog.remove()
    return dict(id=id)




