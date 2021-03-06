import base64
import hashlib
# import json
import os
from io import BytesIO
import zipfile
import shutil
import time
import threading

from lblogs_config import config

import requests
from flask import *
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client

from database import DataBase

secret_id = 'AKIDcq7HVrj0nlAWUYvPoslyMKKI2GNJ478z'
secret_key = '70xZrtGAwmf6WdXGhcch3gRt7hV4SJGx'
region = 'ap-guangzhou'
config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
# 2. 获取客户端对象
client = CosS3Client(config)

bucket = 'lblogs-1254016670'

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
    with open('about.html', 'r', encoding='utf-8') as f:
        return f.read()


def get_if_in(key: str, form: dict, default=None):
    if key in form:
        return form[key]
    return default


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


def do_upload(filename: str, username: str):
    if username != '':
        key = "%s/%s" % (username, filename)
    else:
        key = "%s" % (filename, )

    with open("tmp/_site/%s" % filename, 'rb') as f:
        response = client.put_object(
            Bucket=bucket,
            Body=f.read(),
            Key=key,
            # Key="%s" % (filename, ),
            StorageClass='STANDARD',
            EnableMD5=False
        )
        print("Upload %s..." % filename, response)


def do_upload_(filename: str, username: str, data: bytes):
    if username != '':
        key = "%s/%s" % (username, filename)
    else:
        key = "%s" % (filename, )

    response = client.put_object(
        Bucket=bucket,
        Body=data,
        Key=key,
        # Key="%s" % (filename, ),
        StorageClass='STANDARD',
        EnableMD5=False
    )
    print("Upload %s..." % filename, response)


def publish_zip(zipdata: bytes, username: str):
    userdir = 'build_%s' % username
    basedir = os.path.abspath('.')

    z = zipfile.ZipFile(BytesIO(zipdata))
    if os.path.exists(userdir):
        shutil.rmtree(userdir)
    os.mkdir(userdir)
    z.extractall(userdir)
    z.close()
    os.chdir(userdir)
    print('Doing Jekyll...')
    result = BytesIO()
    ths = []

    if os.system("jekyll build") == 0:
        # time.sleep(1)
        os.chdir("_site")
        z = zipfile.ZipFile(result, 'w')
        # _site

        for current_path, subfolders, filesname in os.walk('.'):
            # print(current_path, subfolders, filesname)
            #  filesname是一个列表，我们需要里面的每个文件名和当前路径组合
            for file in filesname:
                # 将当前路径与当前路径下的文件名组合，就是当前文件的绝对路径
                filepath = os.path.join(current_path, file)
                filepath = filepath.replace('\\', '/')
                filepath = filepath.split('./')[-1]
                z.write(filepath)
                print("ADD file:", filepath)

                t = threading.Thread(target=do_upload, args=(filepath, username))
                ths.append(t)

        # 关闭资源
        z.close()
    os.chdir(basedir)

    for t in ths:
        t.start()
    for t in ths:
        t.join()

    if username != '':
        key = "%s/%s" % (username, 'raw.zip')
    else:
        key = "%s" % ('raw.zip',)

    response = client.put_object(
        Bucket=bucket,
        Body=result,
        # Key=filename_md5,
        Key=key,
        StorageClass='STANDARD',
        EnableMD5=False
    )
    print("Upload raw.zip...", response)


@app.route('/v1/api', methods=["POST"])
def main_api():
    form = request.form
    print("DEBUG Form:", form)
    # 一定需要action
    if 'action' not in form:
        return db.make_result(1, error="No action selected")
    action = form['action']

    # print("Action...")

    # 不需要auth
    if action == 'clear_all':
        # 访问/v1/api/clear_all
        return redirect('/v1/api/clear_all')

    if action == "get_version":
        ver = requests.get("https://raw.githubusercontent.com/LanceLiang2018/LBlogs/master/version").text
        return db.make_result(0, version=ver)

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
        email = get_if_in('email', form, default='')
        result = db.create_user(username=username, password=password, email=email)
        res = json.loads(result)
        if res['code'] != 0:
            return result

        try:
            # 建立网站。
            template = get_if_in('template', form, 'template1')
            target = ' https://lblogs-1254016670.cos.ap-guangzhou.myqcloud.com/template/%s.zip' % template
            tempbytes = requests.get(target).content
            tempfile = BytesIO(tempbytes)
            zipped = zipfile.ZipFile(tempfile)
            if username == '':
                pre_key = ''
            else:
                pre_key = '%s/' % username
            ths = []
            for file in zipped.namelist():
                if not file.startswith('_site/'):
                    continue
                filepath = file[6:]
                data = zipped.open(file, 'r').read()
                t = threading.Thread(target=do_upload_, args=(filepath, username, data))
                ths.append(t)

            for t in ths:
                t.start()
            for t in ths:
                t.join(20)
            #
            # if username == '':
            #     name = 'Lblogs'
            # else:
            #     name = "%s 的博客" % username
            # yml = config(zipped.open('_config.yml', 'r').read(), name=name)
            # do_upload_('%s_config.yml' % pre_key, username, yml.encode())

            do_upload_('%sraw.zip' % pre_key, username, tempbytes)

            return db.make_result(0)
        except Exception as e:
            return db.make_result(1, error=str(e))

    if action == 'get_user':
        if 'username' not in form:
            return db.make_result(1, error=form)
        username = get_if_in('username', form)
        return db.user_get_info(username)

    # 需要auth
    if 'token' not in form:
        return db.make_result(1, error="No token")
    token = form['token']

    # print("Auth...")

    if action == 'beat':
        if db.check_auth(token) is False:
            return db.make_result(2)
        return db.make_result(0)

    if action == 'upload':
        if 'data' not in form:
            return db.make_result(1, error=form)
        filename = get_if_in('filename', form, default='filename')
        data = get_if_in('data', form, default=None)
        data = base64.b64decode(data)
        username = db.token2username(token)
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
            # 不算了
        )
        print(response)
        # url = 'https://%s.cos.ap-chengdu.myqcloud.com/%s' % (bucket, filename_md5)
        url = 'https://%s.cos.ap-chengdu.myqcloud.com/%s/%s' % (bucket, username, filename)
        result = {
            'filename': filename, 'etag': response['ETag'][1:-1],
            "url": url
        }
        db.file_upload(token, filename, url)
        res = db.make_result(0, upload_result=result)
        return res

    if action == 'publish':
        if 'zipfile' not in request.files:
            return db.make_result(1)
        f = request.files['zipfile']
        username = db.token2username(token)

        try:
            z = zipfile.ZipFile(BytesIO(f.read()))
            # print(z.namelist())
            if os.path.exists('tmp'):
                shutil.rmtree('tmp')
            os.mkdir('tmp')
            z.extractall('tmp/')
            z.close()
            os.chdir('tmp')
            print('Doing Jekyll...')
            result = BytesIO()
            ths = []

            if os.system("jekyll build") == 0:
                # time.sleep(1)
                os.chdir("_site")
                z = zipfile.ZipFile(result, 'w')
                # _site

                for current_path, subfolders, filesname in os.walk('.'):
                    # print(current_path, subfolders, filesname)
                    #  filesname是一个列表，我们需要里面的每个文件名和当前路径组合
                    for file in filesname:
                        # 将当前路径与当前路径下的文件名组合，就是当前文件的绝对路径
                        filepath = os.path.join(current_path, file)
                        filepath = filepath.replace('\\', '/')
                        filepath = filepath.split('./')[-1]
                        z.write(filepath)
                        print("ADD file:", filepath)

                        t = threading.Thread(target=do_upload, args=(filepath, username))
                        ths.append(t)

                        # with open(os.path.join(current_path, file), 'rb') as f:
                        #     response = client.put_object(
                        #         Bucket=bucket,
                        #         Body=f.read(),
                        #         # Key="%s/%s" % (username, filepath),
                        #         Key="%s" % (filepath, ),
                        #         StorageClass='STANDARD',
                        #         EnableMD5=False
                        #     )
                        #     print("Upload %s..." % filepath, response)
                # 关闭资源
                z.close()
            os.chdir('../..')

            for t in ths:
                t.start()
            for t in ths:
                t.join()

            if username != '':
                key = "%s/%s" % (username, 'raw.zip')
            else:
                key = "%s" % ('raw.zip', )

            response = client.put_object(
                Bucket=bucket,
                Body=result,
                # Key=filename_md5,
                Key=key,
                StorageClass='STANDARD',
                EnableMD5=False
            )
            print("Upload raw.zip...", response)

        except Exception as e:
            return db.make_result(1, error=str(e))
        return db.make_result(0)

    if action == 'get_files':
        return db.file_get(token=token)

    if action == "set_user":
        email = get_if_in("email", form, default=None)
        return db.user_set_info(token=token, email=email)

    return db.make_result(1, error='Not support method')


if __name__ == '__main__':
    app.run("0.0.0.0", port=int(os.environ.get('PORT', '5000')), debug=False)

