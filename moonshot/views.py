from datetime import datetime, timedelta
import jwt
import requests
from requests_oauthlib import OAuth1

from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

from moonshot._compat import (
    parse_qsl,
    urlencode,
)
from .users import USERS

request_token_url = 'https://api.twitter.com/oauth/request_token'
access_token_url = 'https://api.twitter.com/oauth/access_token'
authenticate_url = 'https://api.twitter.com/oauth/authenticate'


# Helper Functions
def create_jwt_token(user, token_secret):
    payload = dict(
        iat=datetime.now(),
        exp=datetime.now() + timedelta(days=7),
        user=dict(
            id=user['id'],
            email=user['email'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            twitter=user['twitter']))
    token = jwt.encode(payload, token_secret)
    return token


class MySite:
    def __init__(self, request):
        self.request = request
        self.settings = request.registry.settings

    # Routes
    @view_config(route_name='profile', renderer='json', permission='view')
    def profile(self):
        twitter_name = self.request.authenticated_userid
        user = USERS.get(twitter_name)
        return dict(user=user)


    @view_config(route_name='auth_twitter', renderer='json')
    def twitter(self):
        request = self.request

        if request.params.get('oauth_token') and request.params.get(
                'oauth_verifier'):
            auth = OAuth1(self.settings['TWITTER_CONSUMER_KEY'],
                          client_secret=self.settings[
                              'TWITTER_CONSUMER_SECRET'],
                          resource_owner_key=request.params.get(
                              'oauth_token'),
                          verifier=request.params.get('oauth_verifier'))
            r = requests.post(access_token_url, auth=auth)
            profile = dict(parse_qsl(r.text))

            twitter = profile['screen_name']
            user = USERS.get(twitter)
            token_secret = self.settings['TOKEN_SECRET']
            token = create_jwt_token(user, token_secret)
            return dict(token=token)
        else:
            oauth = OAuth1(self.settings[
                               'TWITTER_CONSUMER_KEY'],
                           client_secret=self.settings[
                               'TWITTER_CONSUMER_SECRET'],
                           callback_uri=self.settings[
                               'TWITTER_CALLBACK_URL'])
            r = requests.post(request_token_url, auth=oauth)
            oauth_token = dict(parse_qsl(r.text))
            qs = urlencode(dict(oauth_token=oauth_token['oauth_token']))
            url = authenticate_url + '?' + qs
            return HTTPFound(location=url)


@view_config(route_name='ok', renderer='json', permission='view')
def ok_view(request):
    return dict(ok='OK')

