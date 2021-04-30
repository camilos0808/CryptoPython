import requests

def telegram_bot_sendtext(bot_message):
    bot_token = '1255391215:AAGBWEosmnyPeh-iO-_sydOjZWYEZC_q2mo'
    #bot_chatID = '1228473341'
    bot_chatID ='-374660432'
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message

    response = requests.get(send_text)
    print(bot_message)
    return response.json()
