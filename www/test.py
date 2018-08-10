import orm
import asyncio
from models import User,Blog,Comment

async def test(loop):
    await orm.create_pool(user='www',password='www',db='awesome',loop=loop)
    u=User(name='Test5',email='test5@email.com',passwd='12564687',image='about:blank')
    await u.save()

async def find(loop):
    await orm.create_pool(user='www',password='www',db='awesome',loop=loop)
    rs = await User.findAll()
    for i in rs:
        print('查找测试： %s' % i)

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.wait([test(loop),find(loop)]))
loop.close()
if loop.is_closed():
    exit(0)