from decimal import Decimal
import boto3
import tweepy
import json
import smtplib
from email.message import EmailMessage
from os import environ
from datetime import date


username = 'Sprachgefuhl'
table_name = 'twitter_Sprachgefuhl'

api_key = "I3EvQ2erc4WuR"
api_key_secret = "T1mpT31723F4D94Ll1"
access_token = "58144PEAs0VnxwwncOKWT"
access_token_secret = "OYNOhnlmJrsgepwcHuiuPH"

from_mail = 'dailyuminder@gmail.com'
to_mail = 'asf@a.com'
smtp_mail = 'dailyuminder@gmail.com'
smtp_mail_password = 'ouhnswqcd' 

dynamodb = boto3.resource('dynamodb')
client = boto3.client('dynamodb')
table = dynamodb.Table(table_name)


# ******************************************************
# ******** DO NOT CHANGE CODE BELOW THIS LINE ********** 
# ******************************************************


def lambda_handler(event, context):
    print('inside lambda handler')
    compare= comparetweepy()
    return {
        'statusCode': 200,
        'body': compare
    }

def authentication_dance():
    CONSUMER_KEY = api_key
    CONSUMER_SECRET = api_key_secret
    ACCESS_TOKEN = access_token
    ACCESS_SECRET = access_token_secret
    return CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_SECRET


def get_api(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_SECRET):
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_SECRET)
    api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True, compression=True)
    return api

def fetch_pastfollowers():
    response = table.scan()
    response_items = response['Items']
    pflist = []
    with table.batch_writer() as batch:
        for i in response['Items']:
            pflist.append(i['user_id'])
            batch.delete_item(
                Key={
                'sn': i['sn'],  'user_id': i['user_id']
            }
        )
    print(pflist)
    return response_items, pflist

def comparetweepy():
    CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_SECRET = authentication_dance()
    api = get_api(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_SECRET)

    response_items, pflist = fetch_pastfollowers()
    unfollowers, total_follower, followers_list, flw = compare_followers(api, pflist)
    mail_user(unfollowers, api, total_follower)
    write_data(followers_list)
    print(f'The total number of current followers: {total_follower}. Previous followers{len(pflist)}')

def compare_followers(api, pflist):
    total_follower = 0
    followers_list = []
    flw = []
    
    for status in tweepy.Cursor( api.followers_ids, screen_name=username).pages():
        for data in status:
            total_follower = total_follower + 1
            print('total_follower: ', str(total_follower), 'data: ', str(data))
            pfdict = {}
            pfdict['sn'] = str(total_follower)
            pfdict['user_id'] = str(data)
            followers_list.append(pfdict)
            flw.append(str(data))
            
    print('our followers are: ', followers_list)
    
    unfollowers = [x for x in pflist if x not in flw]
    print('unfollowers are: ', unfollowers)
    return unfollowers, total_follower, followers_list, flw

def write_data(followers_list):
    print('Inserting new follwer list into DB:', followers_list)
    with table.batch_writer() as batch:
        for user in followers_list:
            batch.put_item(Item=user)


def mail_user(a, api, total_follower):
    print('outside mail_user if loop: ',a)
    if a:
        print('inside mail_user method')
        header = """
        <html>
        <body>
             <TABLE CELLPADDING=10 CELLSPACING=20>
        <tr>
            <th style="text-align:centre">Handle</th>
            <th style="text-align:centre">Name</th>
            <th style="text-align:centre">Avatar</th>
        </tr>
            """
        total = []
        mailer = ""
        for data in a:
            try:
                user_data = api.get_user(data)
                unfollower_name = user_data.screen_name
                fullname = user_data.name
                total.append(fullname)            
                pics = user_data.profile_image_url
                profilelink = f'https://twitter.com/{user_data.screen_name}'
                result = """<tr><td style="text-align:left">""" + unfollower_name + """<td style="text-align:left"><a href="""+'"' + profilelink + '">'+ fullname + """</a></td><td style="text-align:left"><img src=""" + '"' + pics + '"></td></tr>'
                f_count = '</br> You now have <b> ' + str(total_follower) + '</b> followers'
                mailer = mailer + result #+ f_count
            except:
                pass
            
        if len(total) == 1:
            subject = total[0] + " Unfollowed "+username
        elif len(total) ==2:
            subject = total[0] +' and ' + total[1] + ' Unfollowed '+username
        else:
            subject = total[0] +" and " + str(len(total)-1) + " Others Unfollowed "+username
        mailer = mailer + '</table> <p></html>'
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_mail
        msg['To'] = to_mail
        msg.set_content('Hi man. \n Today, 20 Novemeber 2020, 1 person unfollowed your account jrick on Twitter. \n Thank you.')
        msg.add_alternative(header + mailer, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(smtp_mail, smtp_mail_password)
            smtp.send_message(msg)
        print('Done mailing the user')
    '''else:
        msg = EmailMessage()
        today = date.today()
        d1 = today.strftime("%m/%d/%Y")
        msg['Subject'] = 'No One Unfollowed '+ username +' on ' + str(d1)
        msg['From'] = from_mail
        msg['To'] = to_mail
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(smtp_mail, smtp_mail_password)
            smtp.send_message(msg)'''
