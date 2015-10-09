# -*- coding: utf-8 -*-

'''Reads a wall of the specified user using VKontakte API.'''

from __future__ import unicode_literals

import json
import datetime
import logging
import re
import urllib

from google.appengine.api import memcache

import vkfeed.utils
from vkfeed import constants
from vkfeed.core import Error

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


_TEXT_URL_RE = re.compile(r'(^|\s|>)(https?://[^"]+?)(\.?(?:<|\s|$))')
'''Matches a URL in a plain text.'''

_DOMAIN_ONLY_TEXT_URL_RE = re.compile(r'(^|\s|>)((?:[a-z0-9](?:[-a-z0-9]*[a-z0-9])?\.)+[a-z0-9](?:[-a-z0-9]*[a-z0-9])/[^"]+?)(\.?(?:<|\s|$))')
'''Matches a URL without protocol specification in a plain text.'''

_NEW_LINE_RE = re.compile(r'<br(?:\s*/)?>', re.IGNORECASE)
'''Matches a user link in a post text.'''

_USER_LINK_RE = re.compile(r'\[((?:id|club)\d+)\|([^\]]+)\]')
'''Matches a user link in a post text.'''

_GROUP_ALIAS_RE = re.compile(r'^(?:event|public)(\d+)$')
'''Matches group ID aliases.'''

_HASH_TAG_RE = re.compile(ur'#[a-zA-Zа-яА-Я0-9\-_]+')
'''Matches a hash tag.'''


class ConnectionError(Error):
    '''Raised when we fail to get a data from the server.'''

    def __init__(self, *args, **kwargs):
        Error.__init__(self, *args, **kwargs)

class ServerError(Error):
    '''Raised when the server reports an error.'''

    def __init__(self, code, *args, **kwargs):
        Error.__init__(self, *args, **kwargs)
        self.code = code


def read(profile_name, min_timestamp, max_posts_num, foreign_posts, show_photo, hash_tag_title, text_title, big_photos):
    '''Reads a wall of the specified user.'''

    users = {}
    wall_posts = []
    user = _get_user(profile_name)

    def get_wall(prediction):
        LOG.info('Predicted to %s.', prediction)

        _get_wall(user, foreign_posts, len(wall_posts), prediction - len(wall_posts), users, wall_posts)

        if len(wall_posts) < max_posts_num and len(wall_posts) == prediction and wall_posts[-1]['date'] > min_timestamp:
            LOG.warning('Got invalid prediction %s.', prediction)
            get_wall(min(max(prediction, 5) * 2, max_posts_num))


    wall_request_fingerprint = '{0}|{1}|{2}'.format(user['id'], int(foreign_posts), max_posts_num)
    last_post_num = memcache.get(wall_request_fingerprint, 'post_stat')

    if last_post_num is None:
        LOG.info('There is no statistics on previous number of posts.')
        get_wall(10 if max_posts_num > 10 else max_posts_num)
    else:
        LOG.info('Previously returned number of posts: %s.', last_post_num)
        get_wall(min(max_posts_num, last_post_num + 2))
    wall_posts = wall_posts[:max_posts_num]

    img_style = 'style="border-style: none; display: block;"'

    posts = []
    for post in wall_posts:
        if post['date'] < min_timestamp:
            continue

        supported = []
        unsupported = []

        title = _get_post_title(users, post, text_title, hash_tag_title)

        if 'attachment' in post and post['text'] == post['attachment'][post['attachment']['type']].get('title'):
            post['text'] = ''

        photo_count = reduce(
            lambda count, attachment:
                count + ( attachment['type'] in ( 'photo', 'posted_photo' ) ),
            post.get('attachments', []), 0)

        for attachment in post.get('attachments', []):
            # Notice: attachment object is not always stored in
            # attachment[attachment["type"]] - sometimes it's stored under a
            # different key, so we can't obtain it here for all attachment types.

            if attachment['type'] == 'app':
                supported.append(
                    '<a href="{vk_url}app{info[app_id]}"><img {img_style} src="{info[src]}" /></a>'.format(
                        vk_url = constants.VK_URL, info = attachment[attachment['type']], img_style = img_style))
            elif attachment['type'] == 'graffiti':
                supported.append(
                    '<a href="{vk_url}graffiti{info[gid]}"><img {img_style} src="{info[src]}" /></a>'.format(
                        vk_url = constants.VK_URL, info = attachment[attachment['type']], img_style = img_style))
            elif attachment['type'] == 'link':
                info = attachment[attachment['type']]
                info['description'] = _parse_text(info['description']) or info['title']

                html = '<b>Ссылка: <a href="{info[url]}">{info[title]}</a></b><p>'.format(info = info)

                if info.get('image_src') and info['description']:
                    html += (
                        '<table cellpadding="0" cellspacing="0"><tr valign="top">'
                            '<td><a href="{info[url]}"><img {img_style} src="{info[image_src]}" /></a></td>'
                            '<td style="padding-left: 10px;">{info[description]}</td>'
                        '</tr></table>'.format(info = info, img_style = img_style))
                elif info.get('image_src'):
                    html += '<a href="{info[url]}"><img {img_style} src="{info[image_src]}" /></a>'.format(
                        info = info, img_style = img_style)
                elif info['description']:
                    html += info['description']

                html += '</p>'

                supported.append(html)
            elif attachment['type'] in ('photo', 'posted_photo'):
                info = attachment[attachment['type']]
                photo_id = info.get('pid', info.get('id', 0))
                photo_src = info['src_big'] if photo_count == 1 or big_photos else info['src']

                # Photo may have id = 0 and owner_id = 0 if it for example
                # generated by an application.
                if photo_id == 0 or info['owner_id'] == 0:
                    supported.append(
                        '<a href="{vk_url}wall{profile_id}_{post_id}"><img {img_style} src="{photo_src}" /></a>'.format(
                            vk_url = constants.VK_URL, profile_id = user['id'], post_id = post['id'],
                            img_style = img_style, photo_src = photo_src))
                else:
                    supported.append(
                        '<a href="{vk_url}wall{profile_id}_{post_id}?z=photo{info[owner_id]}_{photo_id}%2Fwall{profile_id}_{post_id}">'
                        '<img {img_style} src="{photo_src}" /></a>'.format(
                            vk_url = constants.VK_URL, profile_id = user['id'], photo_id = photo_id,
                            info = info, post_id = post['id'], img_style = img_style, photo_src = photo_src))
            elif attachment['type'] == 'video':
                info = attachment[attachment['type']]
                supported.append(
                    '<a href="{vk_url}wall{profile_id}_{post_id}?z=video{info[owner_id]}_{info[vid]}">'
                        '<img {img_style} src="{info[image]}" />'
                        '<b>{info[title]} ({duration})</b>'
                    '</a>'.format(
                        vk_url = constants.VK_URL, profile_id = user['id'], post_id = post['id'], info = info,
                        img_style = img_style, duration = _get_duration(info['duration'])))

            elif attachment['type'] == 'audio':
                info = attachment[attachment['type']]
                unsupported.append('<b>Аудиозапись: <a href="{vk_url}search?{query}">{title}</a></b>'.format(
                    vk_url = constants.VK_URL, query = urllib.urlencode({
                        'c[q]': (info['performer'] + ' - ' + info['title']).encode('utf-8'),
                        'c[section]': 'audio'
                    }), title = '{} - {} ({})'.format(info['performer'], info['title'], _get_duration(info['duration']))))
            elif attachment['type'] == 'doc':
                unsupported.append('<b>Документ: {}</b>'.format(attachment[attachment['type']]['title']))
            elif attachment['type'] == 'note':
                unsupported.append('<b>Заметка: {}</b>'.format(attachment[attachment['type']]['title']))
            elif attachment['type'] == 'page':
                unsupported.append('<b>Страница: {}</b>'.format(attachment[attachment['type']]['title']))
            elif attachment['type'] == 'poll':
                unsupported.append('<b>Опрос: {}</b>'.format(attachment[attachment['type']]['question']))

        text = ''

        if supported:
            text += '<p>' + '</p><p>'.join(supported) + '</p>'

        text += _parse_text(post['text'])

        if unsupported:
            text += '<p>' + '</p><p>'.join(unsupported) + '</p>'

        if 'copy_owner_id' in post and 'copy_post_id' in post:
            text = '<p><b><a href="{profile_url}">{user_name}</a></b> пишет:</p>'.format(
                profile_url = _get_profile_url(post['copy_owner_id']), user_name = users[post['copy_owner_id']]['name']) + text

            if 'copy_text' in post:
                text = '<p>{}</p><div style="margin-left: 1em;">{}</div>'.format(post['copy_text'], text)

        if 'reply_owner_id' in post and 'reply_post_id' in post:
            text += (
                '<p><i>'
                    'В ответ на <a href="{vk_url}wall{post[reply_owner_id]}_{post[reply_post_id]}">запись</a> '
                    'пользователя <b><a href="{profile_url}">{user_name}</a></b>.'
                '</i></p>'.format(vk_url = constants.VK_URL, post = post,
                    profile_url = _get_profile_url(post['reply_owner_id']), user_name = users[post['reply_owner_id']]['name']))

        if show_photo:
            text = (
                '<table cellpadding="0" cellspacing="0"><tr valign="top">'
                    '<td><a href="{url}"><img {img_style} src="{photo}" /></a></td>'
                    '<td style="padding-left: 10px;">{text}</td>'
                '</tr></table>'.format(
                    url = _get_profile_url(post['from_id']), img_style = img_style,
                    photo = users[post['from_id']]['photo'], text = text))

        date = datetime.datetime.fromtimestamp(post['date'])

        posts.append({
            'title': title,
            'url':   '{0}wall{1}_{2}'.format(constants.VK_URL, user['id'], post['id']),
            'text':  text,
            'date':  date,
        })

    if last_post_num != len(posts):
        memcache.set(wall_request_fingerprint, len(posts), namespace = 'post_stat')

    return {
        'url':        constants.VK_URL + profile_name,
        'user_name':  user['name'],
        'user_photo': user['photo'],
        'posts':      posts,
    }


def _api(method, **kwargs):
    '''Calls the specified VKontakte API method.'''

    url = '{0}method/{1}?language=0&'.format(constants.API_URL, method) + urllib.urlencode(kwargs)

    try:
        data = vkfeed.utils.fetch_url(url, content_type = 'application/json')

        try:
            data = json.loads(data)
        except Exception as e:
            raise Error('Failed to parse JSON data: {0}.', e)
    except Exception as e:
        raise ConnectionError('API call {0} failed: {1}', url, e)

    if 'error' in data or 'response' not in data:
        error = data.get('error', {}).get('error_msg', '').strip()

        if not error:
            error = 'Ошибка вызова API.'
        elif error == 'Access denied: group is blocked':
            error = (
                'Страница временно заблокирована и проверяется администраторами, '
                'так как некоторые пользователи считают, что она не соответствует правилам сайта.')
        elif error == 'Access denied: this wall available only for community members':
            error = 'Это частное сообщество. Доступ только по приглашениям администраторов.'
        elif error == 'User was deleted or banned':
            error = 'Пользователь удален или забанен.'
        elif not error.endswith('.'):
            error += '.'

        raise ServerError(data.get('error', {}).get('error_code'), error)

    return data['response']


def _get_duration(seconds):
    '''Returns audio/video duration string.'''

    hours = seconds / 60 / 60
    minutes = seconds / 60 % 60
    seconds = seconds % 60

    if hours:
        return '{:02d}:{:02d}:{:02d}'.format(hours, minutes, seconds)
    else:
        return '{:02d}:{:02d}'.format(minutes, seconds)


def _get_post_title(users, post, text_title, hash_tag_title):
    '''Formats title for a post.'''

    title = users[post['from_id']]['name']

    if text_title:
        text = post['text'].lstrip('.?!')
        text = _NEW_LINE_RE.sub(' ', text).strip()

        if text:
            title = _USER_LINK_RE.sub(r'\2', text)
            limit_pos = len(title)

            pos = title.find('.')
            if pos != -1:
                limit_pos = min(limit_pos, pos)
                if title[limit_pos : limit_pos + 3] == '...':
                    limit_pos += 3

            pos = title.find('?')
            if pos != -1:
                limit_pos = min(limit_pos, pos + 1)

            pos = title.find('!')
            if pos != -1:
                limit_pos = min(limit_pos, pos + 1)

            title = title[:limit_pos]
    elif hash_tag_title:
        hash_tags = _HASH_TAG_RE.findall(post['text'])
        if hash_tags:
            title = ', '.join(
                tag[1:].lower() if id else tag[1:].title()
                for id, tag in enumerate(hash_tags))

    return title


def _get_profile_url(profile_id):
    '''Returns URL to profile with the specified ID.'''

    return constants.VK_URL + ( 'club' if profile_id < 0 else 'id' ) + str(abs(profile_id))


def _get_user(profile_name):
    '''Returns user info by profile name.'''

    user = memcache.get(profile_name, 'users')
    if user is not None:
        LOG.info('Got the profile info from memcache.')

        if not user:
            raise ServerError(113, 'Пользователя не существует.')

        return user

    try:
        profiles = _api('users.get', uids = profile_name, fields = 'photo_big,photo_medium,photo')
        if not profiles:
            raise ServerError(-1, 'Пользователь заблокирован.')
        profile = profiles[0]

        user = {
            'id':   profile['uid'],
            'name': profile['first_name'] + ' ' + profile['last_name'],
        }
    except ServerError as e:
        # Invalid user ID
        if e.code == 113:
            try:
                # VKontakte API doesn't understand group ID aliases
                match = _GROUP_ALIAS_RE.match(profile_name)
                if match is not None:
                    profile_name = 'club' + match.group(1)

                profiles = _api('groups.getById', gid = profile_name, fields = 'photo_big,photo_medium,photo')
                if not profiles:
                    raise ServerError(-1, 'Сообщество заблокировано.')
                profile = profiles[0]

                user = {
                    'id':    -profile['gid'],
                    'name':  profile['name'],
                }
            except ServerError as e:
                # Invalid group ID
                if e.code in (100, 125):
                    memcache.set(profile_name, {}, namespace = 'users', time = constants.HOUR_SECONDS)
                    raise ServerError(113, 'Пользователя не существует.')
                else:
                    raise e
        else:
            raise e

    if 'photo_big' in profile:
        user['photo'] = profile['photo_big']
    elif 'photo_medium' in profile:
        user['photo'] = profile['photo_medium']
    else:
        user['photo'] = profile['photo']

    memcache.set(profile_name, user, namespace = 'users', time = constants.DAY_SECONDS)

    return user


def _get_wall(user, foreign_posts, offset, max_posts_num, users, posts):
    '''Returns wall posts of the specified user.'''

    reply = _api(
        'wall.get', owner_id = user['id'], offset = offset, count = max_posts_num,
        filter = 'all' if foreign_posts else 'owner', extended = 1)

    posts.extend(reply['wall'][1:])

    for profile in reply.get('profiles', []):
        users[profile['uid']] = {
            'name':  profile['first_name'] + ' ' + profile['last_name'],
            'photo': profile['photo'],
        }

    for profile in reply.get('groups', []):
        users[-profile['gid']] = {
            'name':  profile['name'],
            'photo': profile['photo'],
        }


def _parse_text(text):
    '''Parses a post text.'''

    text = _TEXT_URL_RE.sub(r'\1<a href="\2">\2</a>\3', text)
    text = _DOMAIN_ONLY_TEXT_URL_RE.sub(r'\1<a href="http://\2">\2</a>\3', text)
    text = _USER_LINK_RE.sub(r'<b><a href="{}\1">\2</a></b>'.format(constants.VK_URL), text)

    return text

