
import asyncio, os, inspect, logging, functools

from urllib import parse
from aiohttp import web

def get(path):
    #定义装饰器 @get('/path')
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__='GET'
        wrapper.__route__=path
        return wrapper
    return decorator

def post(path):
    #定义装饰器 @post('/path')
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__='POST'
        wrapper.__route__=path
        return wrapper
    return decorator


###################################################
def has_request_arg(fn):
    params=inspect.signature(fn).parameters
    found=False
    for name,param in params.items():
        if name == 'request':
            found=True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be thr last named parameter infunction: %s%s' % (fn.__name__,str(sig)))
    return found

def has_var_kw_arg(fn):

    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_named_kw_args(fn):

    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def get_named_key_args(fn):

    args=[];
    params=inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)


def get_required_kw_args(fn):

    args = [];
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

class RequestHandler(object):
    ' 封装处理函数 '
    def __init__(self,app,fn):
        self._app=app
        self._func=fn
        self._has_request_arg=has_request_arg(fn)
        self._has_var_kw_arg=has_var_kw_arg(fn)
        self._has_named_kw_args=has_named_kw_args(fn)
        self._named_kw_args=get_named_key_args(fn)
        self._required_kw_args=get_required_kw_args(fn)

    async def __call__(self,request):
        '分析request'
        kw=None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('missing content_type.')
                ct=request.content_type.lower()
                if ct.startswith('application/json'):
                    params=await request.json()
                    if not isinstance(params,dict):
                        return web.HTTPBadRequest('JSON body must be object.')
                    kw=params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    params=await request.post()
                    kw=dict(**params)
                else:
                    return web.HTTPBadRequest('unsupported content-type: %s'% request.content_type)








