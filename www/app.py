import logging;logging.basicConfig(level=logging.INFO)
import asyncio,os,json,time
from datetime import datetime
from aiohttp import web

from jinja2 import Environment,FileSystemLoader
import orm
from webframe import add_routes,add_static
from config import configs
######################################################################

######################################################################
async def logger_factory(app,handler):
    async def logger(request):
        logging.info('request: %s %s '% (request.method,request.path))
        return (await handler(request))
    return logger
async def response_factory(app,handler):
    async def respones(request):
        logging.info('response handler')
        r=await handler(request)
        if isinstance(r,web.StreamResponse):
            return r
        if isinstance(r,bytes):
            resp=web.Response(body=r)
            resp.content_type='application/octet-stream'
            return resp
        if isinstance(r,str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp=web.Response(body=r.encode('utf-8'))
            resp.content_type='text/html;charset=utf-8'
            return resp
        if isinstance(r,dict):
            #r['__user__']=request.__user__
            template=r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r,ensure_ascii=False,default=lambda o:o.__dict__).encode('utf-8'))
                resp.content_type='application/json;charset=utf-8'
                return resp
            else:
                resp=web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type='text/html;charset=utf-8'
                return resp
        if isinstance(r,int) and r>=100 and r<600:
            return web.Response(r)
        if isinstance(r,tuple) and len(r)==2:
            t,m=r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t,str(m))
        resp=web.Response(body=str(r).encode('utf-8'))
        resp.content_type='text/plain;charset=utf-8'
        return resp
    return respones

async def auth_factory(app,handler):
    async def auth(request):
        logging.info('check user: %s %s' % (request.method,request.path))
        request.__user__=None
        cookie_str=request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user=await cookie2user(cookie_str)
            if user:
                logging.info('set current user:%s' % user.email)
                request.__user__=user
        if request.path.startswith('/manage/') and (request.__user__ is None or not  request.__user__.admin):
            return web.HTTPFound('/signin')
        return (await handler(request))
    return auth

def init_jinja2(app,**kw):
    logging.info('init jinja2')
    options=dict(
        autoescape=kw.get('autoescape',True),
        block_start_string=kw.get('block_start_string','{%'),
        block_end_string=kw.get('block_end_string','%}'),
        variable_start_string=kw.get('variable_start_string','{{'),
        variable_end_string=kw.get('variable_end_string', '}}'),
        auto_reload=kw.get('auto_reload',True)
    )
    path=kw.get('path',None)
    if path is None:
        path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')
    logging.info('set jinja2 template path: %s' % path)
    env=Environment(loader=FileSystemLoader(path),**options)
    filters=kw.get('filters',None)
    if filters is not None:
        for name,f in filters.items():
            env.filters[name]=f
    app['__templating__'] = env

def datetime_filter(t):
    delta=int(time.time()-t)
    if delta<60:
        return u'1 minute ago'
    if delta<3600:
        return u'%s minutes ago' % (delta//60)
    if delta<86400:
        return u'%s hours ago' % (delta//3600)
    if delta<604800:
        return u'%s day ago' % (delta//86400)
    dt=datetime.fromtimestamp(t)
    return u'%s-%s-%s' % (dt.year,dt.month,dt.day)

async def init():
    await orm.create_pool(loop=loop,**configs.db)
    app=web.Application(middlewares=[logger_factory,response_factory])
    init_jinja2(app,filters=dict(datetime=datetime_filter))
    add_routes(app,'handlers')
    #add_routes(app, index)
    add_static(app)
    app_runner=web.AppRunner(app)
    #srv = await event_loop.create_server(app_runner.app.make_handler(), '127.0.0.1', 9000)
    await app_runner.setup()
    site = web.TCPSite(app_runner,'127.0.0.1',9000)
    await site.start()
    logging.info('server started at http://127.0.0.1:9000...')
    #return srv

loop=asyncio.get_event_loop()
loop.run_until_complete(init())
loop.run_forever()

