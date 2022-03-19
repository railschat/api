import quart
import json
import ulid

from ..permissions import Permissions
from ..database import channels as channels_db, users, members, guilds
from ..data_bodys import error_bodys
from ...gateway import dispatch_event

app = quart.current_app
channels = quart.Blueprint('channels-v3', __name__)


@channels.post('/<int:guild_id>/channels')
async def create_channel(guild_id: int):
    auth = quart.request.headers.get('Authorization')
    ver = await users.find_one({'session_ids': [auth]})
    let = False

    for session_id in ver['session_ids']:
        if session_id == auth:
            let = True

    if let is False:
        return quart.Response(error_bodys['no_auth'], 401)

    member = await members.find_one({'_id': ver['_id']})

    if member == None:
        return quart.Response(error_bodys['not_in_guild'], 403)

    if member['roles'] == []:
        v = await guilds.find_one(member['guild_id'])
        p = Permissions(v['default_permissions'])
    else:
        p = Permissions(member['roles'][0])

    if p.manage_channels is False:
        return quart.Response(error_bodys['no_perms'], 403)

    d: dict = await quart.request.get_json()

    if d.get('type') not in (1, 2):
        return quart.Response(error_bodys['invalid_data'], 400)

    inside_of = d.get('inside_of', 0)

    if inside_of != 0 and d.get('type') == 1:
        return quart.Response(error_bodys['invalid_data'], 400)

    try:
        data = {
            '_id': ulid.new().str,
            'name': d['name'].lower(),
            'description': d.get('description', ''),
            'guild_id': guild_id,
            'type': d['type'],
            'inside_of': inside_of,
            'banner_url': str(d.get('banner_url', ''))
        }
    except KeyError:
        return quart.Response(error_bodys['invalid_data'], 400)

    _d = data.copy()

    await channels_db.insert_one(data)

    await dispatch_event('channel_create', _d)


@channels.get('/channels/<int:channel_id>')
async def edit_channel(channel_id: int):
    auth = quart.request.headers.get('Authorization')
    ver = await users.find_one({'session_ids': [auth]})
    let = False

    for session_id in ver['session_ids']:
        if session_id == auth:
            let = True

    as_member = await members.find_one({'_id': ver['_id']})

    if as_member == None:
        let = False

    if let is False:
        return quart.Response(error_bodys['no_auth'], 401)

    d: dict = await quart.request.get_json()

    if as_member['roles'] == []:
        v = await ...
    else:
        v = as_member['roles'][0]

    p = Permissions(v)

    if p.manage_channels is False:
        return quart.Response(error_bodys['no_auth'], 401)

    data = {}

    for key, value in d.items():
        if key not in ('name', 'inside_of', 'type'):
            return quart.Response(error_bodys['invalid_data'], 400)

        data[key] = value

    if data == {} or data.get('inside_of') != 0 and data.get('type') == 1:
        return quart.Response(error_bodys['invalid_data'], 400)

    await channels_db.update_one({'_id': channel_id}, data)

    return quart.Response(json.dumps({'success': True}))


@channels.delete('/channels/<int:channel_id>')
async def delete_channel(channel_id: int):
    auth = quart.request.headers.get('Authorization')
    ver = await users.find_one({'session_ids': [auth]})
    let = False

    for session_id in ver['session_ids']:
        if session_id == auth:
            let = True

    if await members.find_one({'_id': ver['_id']}) == None:
        let = False

    member_obj = await members.find_one({'_id': ver['_id']})

    let = False

    for permission in member_obj['permissions']:
        if permission == 'manage_channels':
            let = True

    if let is False:
        return quart.Response(error_bodys['no_auth'], 401)

    await channels_db.delete_one({'_id': channel_id})

    return quart.Response(json.dumps({'code': 404}), status=404)
