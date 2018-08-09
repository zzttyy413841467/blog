import logging;logging.basicConfig(level=logging.INFO)
import asyncio,os,json,time
from datetime import datetime
from aiohttp import web

def index(request):
    return web.Response(body=b'<h1>Awesome</h1',content_type="text/html")


async def init():
    app=web.Application()
    app.add_routes([web.get('/',index)])
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

