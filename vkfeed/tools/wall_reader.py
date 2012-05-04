# -*- coding: utf-8 -*-
# TODO FIXME

'''Parses a vk.com wall page.'''

import json
import datetime
import logging
import re
import urllib

import vkfeed.util
from vkfeed import constants
from vkfeed.core import Error
from vkfeed.tools.html_parser import HTMLPageParser

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

_USER_LINK_RE = re.compile(r'\[(id\d+)\|([^\]]+)\]')
'''Matches a user link in post text.'''


# TODO
class ConnectionError(Error):
    '''Raised when we fail to get a data from the server.'''

    def __init__(self, *args, **kwargs):
        Error.__init__(self, *args, **kwargs)

class ServerError(Error):
    '''Raised when the server reports an error.'''

    def __init__(self, *args, **kwargs):
        Error.__init__(self, *args, **kwargs)


# TODO
def api(method, **kwargs):
    url = '{0}method/{1}?language=0&'.format(constants.API_URL, method) + urllib.urlencode(kwargs)

    try:
        data = vkfeed.util.fetch_url(url, content_type = 'application/json')
    except Exception as e:
        raise ConnectionError('Failed to fetch %s: %s.', url, e)

    try:
        data = json.loads(data)
    except Exception as e:
        raise ConnectionError('Failed to parse JSON data: %s.', e)

    if 'error' in data:
        raise ServerError(data['error']['error_msg'])

    return data['response']

# TODO FIXME: 2.7


def read(profile_name):
    #user = [{u'first_name': u'\u0414\u043c\u0438\u0442\u0440\u0438\u0439', u'last_name': u'\u0428\u0438\u043f\u0438\u043b\u043e\u0432', u'uid': 1266630, u'photo_big': u'http://cs302104.userapi.com/u1266630/a_72f4d335.jpg'}][0]
    user = api('users.get', uids = profile_name, fields = 'photo_big')[0]
    #wall = json.loads(open("../music_video.json").read())['response']['wall'][1:]
    LOG.error(api('wall.get', owner_id = user['uid'], extended = 1)) # TODO [0]
    wall = api('wall.get', owner_id = user['uid'], extended = 1)['wall'][1:]

# TODO
# User was deleted or banned

# TODO
#       u'reply_owner_id': 2126980,
#                u'reply_post_id': 1818,
#                "profiles":[{"uid":122138358,"first_name":"Дмитрий","last_name":"Конищев","photo":"http:\/\/cs10188.userapi.com\/u122138358\/e_24a65600.jpg","photo_medium_rec":"http:\/\/cs10188.userapi.com\/u122138358\/d_7ae3d52b.jpg","sex":2,"online":1}],"groups":[]}}
#В ответ на запись Насти
#http://vk.com/wall2126980_1818

    posts = []
    for post in wall:
#        if post['from_id'] != user['uid']:
#            LOG.debug('Ignore post %s from user %s.', post['id'], post['from_id'])
#            continue

        supported = []
        unsupported = []

        for attachment in post.get('attachments', []):
            info = attachment[attachment['type']]

            if attachment['type'] == 'app':
                supported.append(
                    '<a href="{vk_url}app{id}">'
                    '<img style="border-style: none; display: block;" src="{photo_src}" /></a>'.format(
                        vk_url = constants.VK_URL, id = info['app_id'], photo_src = info['src']))
            elif attachment['type'] == 'graffiti':
                supported.append(
                    '<a href="{vk_url}graffiti{id}">'
                    '<img style="border-style: none; display: block;" src="{photo_src}" /></a>'.format(
                        vk_url = constants.VK_URL, id = info['gid'], photo_src = info['src']))
            elif attachment['type'] == 'link':
                html = u'Ссылка: <b><a href="{url}">{title}</a></b><p>'.format(
                    url = info['url'], title = info['title'])

                if info.get('image_src') and info.get('description'):
                    html += u'<table><tr><td><img src="{image_src}" /></td><td>{description}</td></tr></table>'.format(
                        image_src = info['image_src'], description = info['description'])
                elif info.get('image_src'):
                    html += '<img src="{image_src}" style="display: block;" />'.format(image_src = info['image_src'])
                elif info.get('description'):
                    html += info['description']

                html += '</p>'

                supported.append(html)
            elif attachment['type'] in ('photo', 'posted_photo'):
                supported.append(
                    '<a href="{vk_url}id{profile_id}?z=photo{photo_owner}_{photo_id}%2Fwall{profile_id}_{post_id}">'
                    '<img style="border-style: none; display: block;" src="{photo_src}" /></a>'.format(
                        vk_url = constants.VK_URL, profile_id = user['uid'], post_id = post['id'],
                        photo_owner = info['owner_id'], photo_id = info['pid'], photo_src = info['src']))

            elif attachment['type'] == 'audio':
                unsupported.append(u'<b>Аудиозапись: <a href="{vk_url}search?{query}">{title}</a></b>'.format(
                    vk_url = constants.VK_URL, query = urllib.urlencode({ 'c[q]': info['title'], 'c[section]': 'audio' }),
                    title = u'{0} - {1} ({2})'.format(info['performer'], info['title'], info['duration'])))
            elif attachment['type'] == 'doc':
                unsupported.append(u'<b>Документ: {0}</b>'.format(info['title']))
            elif attachment['type'] == 'note':
                unsupported.append(u'<b>Заметка: {0}</b>'.format(info['title']))
            elif attachment['type'] == 'page':
                unsupported.append(u'<b>Страница: {0}</b>'.format(info['title']))
            elif attachment['type'] == 'poll':
                unsupported.append(u'<b>Опрос: {0}</b>'.format(info['question']))
            elif attachment['type'] == 'video':
                unsupported.append(u'<b>Видео: <a href="{vk_url}video{owner_id}_{video_id}">{title}</a></b>'.format(
                    vk_url = constants.VK_URL, owner_id = attachment['video']['owner_id'], video_id = attachment['video']['vid'], title = attachment['video']['title']))

        description = u"".join(supported)
        description += _USER_LINK_RE.sub(r'<a href="{0}\1">\2</a>'.format(constants.VK_URL), post['text'])
        if unsupported:
            description += u'<br />' + u'<br />'.join(unsupported)

        posts.append({
            'title': user['first_name'] + ' ' + user['last_name'],
            'url': '{0}wall{1}_{2}'.format(constants.VK_URL, post['from_id'], post['id']),
            'text': description,
            'date': datetime.datetime.fromtimestamp(post['date']), # TODO: tz
        })

    return {
        'url': constants.VK_URL + profile_name,
        'user_name': user['first_name'] + ' ' + user['last_name'],
        'user_photo': user['photo_big'],
        'posts': posts,
    }

