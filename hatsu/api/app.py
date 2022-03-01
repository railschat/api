import json
import dotenv
import logging
import hypercorn.asyncio
import hypercorn.config
import quart.flask_patch

from quart import Quart, Response
from .guilds import channels, core as guilds_core
from .users import me, core as users_core
from .gateway import connect
from .rate import rater
from .database import loop

app = Quart(__name__)
dotenv.load_dotenv()
app.config['debug'] = True
logging.basicConfig(level=logging.DEBUG)
rater.init_app(app)

@app.route('/gateway')
async def health_check():
    d = {
        'url': 'wss://gateway.vincentrps.xyz',
    }
    return Response(json.dumps(d), 200)


app.before_serving(connect)

@app.after_request
async def after_request(resp: Response):
    if rater.current_limit:
        resp.headers.add('X-RateLimit-Bucket', rater.current_limit.key)
        retry = resp.headers.pop('Retry-After', '0')
        resp.headers.add('X-RateLimit-Retry-After', retry)
    return resp

bps = {
    channels.channels: '/guilds',
    guilds_core.guilds: '/guilds',
    me.users_me: '/users/@me',
    users_core.users: '/users',
}

for value, suffix in bps.items():
    app.register_blueprint(value, url_prefix=suffix)

cfg = hypercorn.config.Config()
cfg.bind.clear()
cfg.bind.append('0.0.0.0:443')

loop.run_until_complete(hypercorn.asyncio.serve(app, cfg))
loop.run_forever()