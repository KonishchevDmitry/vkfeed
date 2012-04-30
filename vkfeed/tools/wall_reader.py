# -*- coding: utf-8 -*-
# TODO FIXME

'''Parses a vk.com wall page.'''

import cgi
import datetime
import logging
import re
import urllib

from vkfeed import constants
from vkfeed.core import Error
from vkfeed.tools.html_parser import HTMLPageParser

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

def read(profile_id, data):
    posts = []
    
#    {"response":{"wall":[2,{"text":"","attachment":{"type":"photo","photo":{"pid":280265387,"aid":-7,"owner_id":122138358,"src":"http:\/\/cs10471.userapi.com\/u122138358\/-7\/m_f59f9a42.jpg","src_big":"http:\/\/cs10471.userapi.com\/u122138358\/-7\/x_a7d5ade4.jpg","src_small":"http:\/\/cs10471.userapi.com\/u122138358\/-7\/s_2a475314.jpg","src_xbig":"http:\/\/cs10471.userapi.com\/u122138358\/-7\/y_57a318c0.jpg","src_xxbig":"http:\/\/cs10471.userapi.com\/u122138358\/-7\/z_a5a296f4.jpg","width":1280,"height":960,"text":"Apple'овский The Company Store в Купертино для гика - все равно что Милан для любой девушки. =)","created":1331307382,"access_key":"c32560806f80d76533"}},"attachments":[{"type":"photo","photo":{"pid":280265387,"aid":-7,"owner_id":122138358,"src":"http:\/\/cs10471.userapi.com\/u122138358\/-7\/m_f59f9a42.jpg","src_big":"http:\/\/cs10471.userapi.com\/u122138358\/-7\/x_a7d5ade4.jpg","src_small":"http:\/\/cs10471.userapi.com\/u122138358\/-7\/s_2a475314.jpg","src_xbig":"http:\/\/cs10471.userapi.com\/u122138358\/-7\/y_57a318c0.jpg","src_xxbig":"http:\/\/cs10471.userapi.com\/u122138358\/-7\/z_a5a296f4.jpg","width":1280,"height":960,"text":"Apple'овский The Company Store в Купертино для гика - все равно что Милан для любой девушки. =)","created":1331307382,"access_key":"c32560806f80d76533"}}],"comments":{"count":0},"likes":{"count":2},"reposts":{"count":0}},{"id":4,"from_id":122138358,"to_id":122138358,"date":1315865997,"text":"Написал для себя небольшой \"велосипед\", который отдает сообщения с публичных стен в формате RSS. Пользуйтесь, если кому надо.","attachment":{"type":"link","link":{"url":"http:\/\/vkontakte-feed.appspot.com\/","title":"ВКонтакте RSS","description":""}},"attachments":[{"type":"link","link":{"url":"http:\/\/vkontakte-feed.appspot.com\/","title":"ВКонтакте RSS","description":""}}],"comments":{"count":0},"likes":{"count":4},"reposts":{"count":1}}],"profiles":[{"uid":122138358,"first_name":"Дмитрий","last_name":"Конищев","photo":"http:\/\/cs10188.userapi.com\/u122138358\/e_24a65600.jpg","photo_medium_rec":"http:\/\/cs10188.userapi.com\/u122138358\/d_7ae3d52b.jpg","sex":2,"online":0}],"groups":[]}}'''
    for post in data['response']['wall'][1:]:
        #if post['from_id'] != profile_id:
        #    LOG.debug('Ignore post %s from user %s.', post['id'], post['from_id'])
        #    continue

        description = []
        unsupported = []

        for attachment in post.get('attachments', []):
            if attachment['type'] == 'app':
                description.append(
                    '<a href="{vk_url}app{app_id}>'
                    '<img style="border-style: none; display: block;" src="{photo_src}" /></a>'.format(
                        vk_url = constants.VK_URL, app_id = attachment['app']['app_id'],
                        photo_src = attachment['app']['src']))
            elif attachment['type'] == 'graffiti':
                description.append(
                    '<a href="{vk_url}graffiti{id}>'
                    '<img style="border-style: none; display: block;" src="{photo_src}" /></a>'.format(
                        vk_url = constants.VK_URL, id = post['graffiti']['gid'],
                        photo_src = post['graffiti']['src']))
            elif attachment['type'] == 'link':
                html = u'Ссылка: <b><a href="{url}">{title}</a></b>'.format(
                    url = attachment['link']['url'], title = attachment['link']['title'])

                if attachment['link'].get('image_src') and attachment['link']['description']:
                    html += u'<table><tr><td><img src="{image_src}" /></td><td>{description}</td></tr></table>'.format(
                        image_src = attachment['link']['image_src'], description = attachment['link']['description'])
                elif attachment['link'].get('image_src'):
                    html += '<img src="{image_src}" style="display: block;" />'.format(
                        image_src = attachment['link']['image_src'])
                elif attachment['link']['description']:
                    html += attachment['link']['description']

                description.append(html)
            elif attachment['type'] in ('photo', 'posted_photo'):
                description.append(
                    '<a href="{vk_url}id{profile_id}?z=photo{photo_owner}_{photo_id}%2Fwall{profile_id}_{post_id}">'
                    '<img style="border-style: none; display: block;" src="{photo_src}" /></a>'.format(
                        vk_url = constants.VK_URL, profile_id = profile_id, post_id = post['id'],
                        photo_owner = attachment['photo']['owner_id'], photo_id = attachment['photo']['pid'],
                        photo_src = attachment['photo']['src']))

            elif attachment['type'] == 'audio':
                unsupported.append(u'Аудиозапись: <b><a href="{vk_url}search?{query}">{title}</a></b>'.format(
                    vk_url = constants.VK_URL, query = urllib.urlencode({ 'c[q]': attachment['audio']['title'], 'c[section]': 'audio' }),
                    title = '{0} - {1} ({2})'.format(attachment['audio']['title'], attachment['audio']['title'], attachment['audio']['duration'])))
            elif attachment['type'] == 'doc':
                unsupported.append(u'Документ: <b>{0}</b>'.format(attachment['doc']['title']))
            elif attachment['type'] == 'note':
                unsupported.append(u'Заметка: <b>{0}</b>'.format(attachment['note']['title']))
            elif attachment['type'] == 'page':
                unsupported.append(u'Страница: <b>{0}</b>'.format(attachment['page']['title']))
            elif attachment['type'] == 'poll':
                unsupported.append(u'Опрос: <b>{0}</b>'.format(attachment['poll']['question']))
            elif attachment['type'] == 'video':
                unsupported.append(u'Видео: <b><a href="{vk_url}video{owner_id}_{video_id}">{title}</a></b>'.format(
                    vk_url = constants.VK_URL, owner_id = attachment['video']['owner_id'], video_id = attachment['video']['vid'], title = attachment['video']['title']))

        description.append(post['text'])
        description = '<br />'.join(description) + '<p>' + '<br />'.join(unsupported)

        posts.append({
            'title': 'TODO',
            'url': '{0}wall{1}_{2}'.format(constants.VK_URL, post['from_id'], post['id']),
            'text': description,
            'date': datetime.datetime.fromtimestamp(post['date']), # TODO: tz
        })

    return posts
