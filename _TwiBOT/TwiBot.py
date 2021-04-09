import tweepy as tw
import support_keys as keys
import json
from _TwiBOT.accounts.accounts import accounts_dict as accounts

auth = tw.OAuthHandler(keys.consumer_key, keys.consumer_key_secret)
auth.set_access_token(keys.access_Token, keys.access_Token_Secret)
api = tw.API(auth, wait_on_rate_limit=True)


class MyStreamListener(tw.StreamListener):
    def on_status(self, status):
        if status.text.startswith('RT'):
            print(status.text)
        else:
            print('Just RT')


mst = MyStreamListener()
my_stream = tw.Stream(auth=api.auth, listener=mst)
my_stream.filter(follow=[accounts['@RookieXBT']], is_async=True)
