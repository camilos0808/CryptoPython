import tweepy as tw
import support_keys as keys
import json
from _TwiBOT.accounts.accounts import accounts_dict as accounts

auth = tw.OAuthHandler(keys.consumer_key, keys.consumer_key_secret)
auth.set_access_token(keys.access_Token, keys.access_Token_Secret)
api = tw.API(auth, wait_on_rate_limit=True)


class MyStreamListener(tw.StreamListener):
    ACC = accounts

    def on_status(self, status):
        if status.user.id.__str__() in accounts.values() \
                and status.in_reply_to_user_id is None \
                and 'RT' not in status.text:
            print('%s TWEETED:' % status.user.screen_name)
            print(status.text)


mst = MyStreamListener()
my_stream = tw.Stream(auth=api.auth, listener=mst)
my_stream.filter(follow=accounts.values(), is_async=True)

# a = api.user_timeline(screen_name=list(accounts.keys())[1])
