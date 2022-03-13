import json
import dotenv
import logging
import os
import hypercorn.asyncio
import hypercorn.config
import quart.flask_patch

from quart import Quart, Response
from .api.v2.guilds import channels, core as guilds_core
from .api.v2.users import me, core as users_core
from .api.gateway import connect
from .api.v2.rate import rater, _reset
from .api.v2.database import loop
from .api.v2.ui import friends

from .api.v3.guilds import channels as channels3, core as guilds_core3
from .api.v3.users import me as me3, core as users_core3
from .api.v3.rate import rater as rater3, _reset as _reset3
from .api.v3.ui import friends as friends3


app = Quart(__name__)
dotenv.load_dotenv()
app.config['debug'] = True
logging.basicConfig(level=logging.DEBUG)
rater.init_app(app)
rater3.init_app(app)


@app.route('/gateway')
async def health_check():
    d = {
        'url': 'wss://gateway.vincentrps.xyz',
    }
    return Response(json.dumps(d), 200)

@app.errorhandler(404)
async def not_found(*_):
    return json.dumps({'message': '404: Not Found', 'code': 0})

@app.errorhandler(500)
async def internal(*_):
    return json.dumps({'message': '500: Internal Server Error', 'code': 0})

@app.errorhandler(429)
async def ratelimited(*_):
    return json.dumps({'message': '429: Too Many Requests', 'retry_after': rater.current_limit.reset_at})

@app.after_request
async def set_ratelimit(resp: Response):
    if rater.current_limit:
        resp.headers.add('X-RateLimit-Limit', rater.current_limit.limit)
        resp.headers.add('X-RateLimit-Remaining', rater.current_limit.remaining)
        resp.headers.add('X-RateLimit-Breached', str(rater.current_limit.breached))
        resp.headers.add('X-RateLimit-Bucket', rater._key_func())
        resp.headers.add('X-RateLimit-Reset-After', rater.current_limit.reset_at)
    resp.headers['Content-Type'] = 'application/json'
    return resp

bps = {

    # v2

    channels.channels: '/v2/guilds',
    guilds_core.guilds: '/v2/guilds',
    me.users_me: '/v2/users/@me',
    users_core.users: '/v2/users',
    friends.ui: '/v2/ui/friends',

    # v3

    channels3.channels:'/v3/guilds',
    guilds_core3.guilds: '/v3/guilds',
    me3.users_me: '/v3/users/@me',
    users_core3.users: '/v3/users',
    friends3.ui: '/v3/ui/friends'
}

for value, suffix in bps.items():
    app.register_blueprint(value, url_prefix=suffix)

cfg = hypercorn.config.Config()
cfg.bind.clear()
cfg.bind.append(f'0.0.0.0:{os.getenv("PORT")}')

loop.create_task(connect())
loop.create_task(_reset())
loop.create_task(_reset3())
loop.run_until_complete(hypercorn.asyncio.serve(app, cfg))
loop.run_forever()
