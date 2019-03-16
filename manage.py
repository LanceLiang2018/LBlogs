import base64
import hashlib
# import json
import os

import requests
from flask import *
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client

from database import DataBase

secret_id = 'AKIDcq7HVrj0nlAWUYvPoslyMKKI2GNJ478z'
secret_key = '70xZrtGAwmf6WdXGhcch3gRt7hV4SJGx'
region = 'ap-chengdu'
config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
# 2. 获取客户端对象
client = CosS3Client(config)

bucket = 'chatroom-1254016670'

app = Flask(__name__)

db = DataBase()


def delete_dir(_dir):
    for name in os.listdir(_dir):
        file = _dir + "/" + name
        if not os.path.isfile(file) and os.path.isdir(file):
            delete_dir(file)  # It's another directory - recurse in to it...
        else:
            os.remove(file)  # It's a file - remove it...
    os.rmdir(_dir)


@app.route('/', methods=["GET", "POST"])
def index():
    """
        res = '###### manage.py:\n'
        with open('manage.py', 'r', encoding='utf8') as f:
            res = res + f.read()
        res = res + "###### database.py\n"
        with open('database.py', 'r', encoding='utf8') as f:
            res = res + f.read()
        res = res + '\n\n##### End of files.\n'
        return res
    """
    return \
        "<title>Chat 2 Server</title>" \
        "<h1>It is a server for Chat 2! <br>@LanceLiang2018</h1><br>" \
        "<a href=\"http://github.com/LanceLiang2018/ChatRoom2/\">About (Server)</a><br>" \
        "<a href=\"http://github.com/LanceLiang2018/Chat2-Android/\">About (Client)</a>"


@app.route('/v1/api/clear_all', methods=["POST", "GET"])
def v3_clear_all():
    try:
        db.db_init()
    except Exception as e:
        return db.make_result(1, message=str(e))
    return db.make_result(0)


@app.route('/update', methods=["GET"])
def update():
    return redirect("https://%s.cos.ap-chengdu.myqcloud.com/release.apk" % bucket)


@app.route('/license', methods=["GET"])
def license_help():
    return redirect("https://static-1254016670.cos.ap-chengdu.myqcloud.com/license.html")


@app.route('/v1/api', methods=["POST"])
def main_api():
    form = request.form
    print("DEBUG Form:", form)
    # 一定需要action
    if 'action' not in form:
        return db.make_result(1, error="No action selected")
    action = form['action']

    # print("Action...")

    # 这三个api不需要auth
    if action == 'clear_all':
        # 访问/v3/api/clear_all
        pass

    if action == "get_version":
        ver = requests.get("https://raw.githubusercontent.com/LanceLiang2018/Chat2-Android/master/ver").text
        return db.make_result(0, version=ver)

    if action == 'get_user':
        if 'username' not in form:
            return db.make_result(1, error=form)
        username = get_if_in('username', form, default='Lance')
        return db.user_get_info(username=username)

    if action == 'get_room':
        if 'gid' not in form:
            return db.make_result(1, error=form)
        gid = int(get_if_in('gid', form, default='0'))
        return db.room_get_info(gid=gid, auth='')

    if action == 'login':
        if 'username' not in form \
                or 'password' not in form:
            return db.make_result(1, error=form)
        username = get_if_in('username', form)
        password = get_if_in('password', form)
        return db.create_auth(username=username, password=password)

    if action == 'signup':
        if 'username' not in form \
                or 'password' not in form:
            return db.make_result(1, error=form)
        username = get_if_in('username', form)
        password = get_if_in('password', form)
        user_type = get_if_in('user_type', form, default='normal')
        email = get_if_in('email', form, default='')
        return db.create_user(username=username, password=password, email=email, user_type=user_type)

    # 需要auth
    if 'auth' not in form:
        return db.make_result(1, error="No auth")
    auth = form['auth']

    # print("Auth...")

    if action == 'beat':
        if db.check_auth(auth) is False:
            return db.make_result(2)
        return db.make_result(0)

    if action == 'create_room':
        name = get_if_in('name', form, default='New group')
        room_type = get_if_in('room_type', form, default='public')
        if db.check_auth(auth) is False:
            return db.make_result(2)
        gid = db.create_room(auth=auth, name=name, room_type=room_type)
        return db.room_get_info(auth=auth, gid=gid)

    if action == 'get_room_all':
        # print("Your request:", form)
        return db.room_get_all(auth=auth)

    if action == 'join_in':
        if 'gid' not in form:
            return db.make_result(1, error=form)
        gid = int(get_if_in('gid', form, default="0"))
        return db.room_join_in(auth=auth, gid=gid)

    if action == 'set_room':
        if 'gid' not in form:
            return db.make_result(1, error=form)
        gid = int(get_if_in('gid', form, default=None))
        name = get_if_in('name', form, default=None)
        head = get_if_in('head', form, default=None)
        return db.room_set_info(auth=auth, gid=gid, name=name, head=head)

    # New Action
    if action == 'pre_upload':
        return db.make_result(0, pre_upload={'pre_url': 'https://%s.cos.ap-chengdu.myqcloud.com/' % bucket})

    if action == 'upload':
        if 'data' not in form:
            return db.make_result(1, error=form)
        filename = get_if_in('filename', form, default='filename')
        data = get_if_in('data', form, default=None)
        data = base64.b64decode(data)
        username = db.auth2username(auth)
        # md5 = hashlib.md5(data).hexdigest()
        # filename_md5 = "%s" % md5
        response = client.put_object(
            Bucket=bucket,
            Body=data,
            # Key=filename_md5,
            Key="%s/%s" % (username, filename),
            StorageClass='STANDARD',
            EnableMD5=False
            # 我自己算吧......
        #     不算了
        )
        print(response)
        # url = 'https://%s.cos.ap-chengdu.myqcloud.com/%s' % (bucket, filename_md5)
        url = 'https://%s.cos.ap-chengdu.myqcloud.com/%s/%s' % (bucket, username, filename)
        result = {
            'filename': filename, 'etag': response['ETag'][1:-1],
            "url": url
        }
        db.file_upload(auth, filename, url)
        res = db.make_result(0, upload_result=result)
        return res

    if action == 'get_files':
        limit = int(get_if_in('limit', form, default='30'))
        offset = int(get_if_in('limit', form, default='0'))
        return db.file_get(auth=auth, limit=limit, offset=offset)

    if action == 'get_messages':
        if db.check_auth(auth) is False:
            return db.make_result(2)
        gid = int(get_if_in('gid', form, default='0'))
        limit = int(get_if_in('limit', form, default='30'))
        since = int(get_if_in('since', form, default='0'))
        req = get_if_in('request', form, default='all')
        # print("req: ", req)

        if req == 'all' and gid == 0:
            print("req: all")
            gids = db.room_get_gids(auth=auth, req='all')
            messages = []
            for g in gids:
                result = json.loads(db.get_new_message(auth=auth, gid=g, limit=limit, since=since))
                if result['code'] != 0:
                    return jsonify(result)
                messages.extend(result['data']['message'])
            return db.make_result(0, message=messages)
        elif req == 'private':
            print("req: private")
            gids = db.room_get_gids(auth=auth, req='private')
            messages = []
            for g in gids:
                result = json.loads(db.get_new_message(auth=auth, gid=g, limit=limit, since=since))
                if result['code'] != 0:
                    return jsonify(result)
                messages.extend(result['data']['message'])
            print('private:', messages)
            return db.make_result(0, message=messages)
        elif gid != 0:
            print("req: single room...")
            return db.get_new_message(auth=auth, gid=gid, limit=limit, since=since)
        return db.make_result(1)

    if action == 'send_message':
        if 'gid' not in form \
                or 'text' not in form:
            return db.make_result(1, error=form)
        gid = int(get_if_in('gid', form, default='0'))
        text = get_if_in('text', form, default='text')
        message_type = get_if_in('message_type', form, default='text')
        return db.send_message(auth=auth, gid=gid, text=text, message_type=message_type)

    if action == 'make_friends':
        if 'friend' not in form:
            return db.make_result(1, error=form)
        friend = get_if_in('friend', form, default='Lance')
        return db.make_friends(auth=auth, friend=friend)

    if action == "set_user":
        head = get_if_in('head', form, default=None)
        motto = get_if_in('motto', form, default=None)
        email = get_if_in("email", form, default=None)
        return db.user_set_info(auth=auth, head=head, motto=motto, email=email)

    return db.make_result(1, error='Not support method')


if __name__ == '__main__':
    app.run("0.0.0.0", port=int(os.environ.get('PORT', '5000')), debug=False)

