from flask import Flask, request, redirect, render_template, session, flash, abort
from flask_assets import Environment, Bundle
from datetime import timedelta
import hashlib
import uuid
import re

from models import User, Channel, Message


app = Flask(__name__)
app.secret_key = uuid.uuid4().hex
app.permanent_session_lifetime = timedelta(days=30)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 2678400

# CSSの圧縮と結合
assets = Environment(app)
css_bundle = Bundle('css/*.css', filters='cssmin', output='gen/bundled.css')
assets.register('css_all', css_bundle)
css_bundle.build()



# サインアップページの表示
@app.route('/signup', methods=['GET'])
def signup_view():
    return render_template('auth/signup.html')


# サインアップ処理
@app.route('/signup', methods=['POST'])
def signup_process():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    passwordConfirmation = request.form.get('password-confirmation')

    pattern = "^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"

    if name == '' or email =='' or password == '' or passwordConfirmation == '':
        flash('空のフォームがあるようです')
    elif password != passwordConfirmation:
        flash('二つのパスワードの値が違っています')
    elif re.match(pattern, email) is None:
        flash('正しいメールアドレスの形式ではありません')
    else:
        uid = uuid.uuid4()
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        registered_user = User.find_by_email(email)

        if registered_user != None:
            flash('既に登録されているようです')
        else:
            User.create(uid, name, email, password)
            UserId = str(uid)
            session['uid'] = UserId
            return redirect('/channels')
    return redirect('/signup')


# ログインページの表示
@app.route('/login', methods=['GET'])
def login_view():
    return render_template('auth/login.html')


# ログイン処理
@app.route('/login', methods=['POST'])
def login_process():
    email = request.form.get('email')
    password = request.form.get('password')

    if email =='' or password == '':
        flash('空のフォームがあるようです')
    else:
        user = User.find_by_email(email)
        if user is None:
            flash('このユーザーは存在しません')
        else:
            hashPassword = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if hashPassword != user["password"]:
                flash('パスワードが間違っています！')
            else:
                session['uid'] = user["uid"]
                return redirect('/channels')
    return redirect('/login')


# ログアウト
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# チャンネル一覧ページの表示
@app.route('/channels', methods=['GET'])
def channels_view():
    uid = session.get("uid")
    if uid is None:
        return redirect('/login')
    else:
        channels = Channel.get_all()
        channels.reverse()
    return render_template('channels.html', channels=channels, uid=uid)


# チャンネルの作成
@app.route('/channels', methods=['POST'])
def create_channel():
    uid = session.get('uid')
    if uid is None:
        return redirect('/login')

    channel_name = request.form.get('channelTitle')
    channel = Channel.find_by_name(channel_name)
    if channel == None:
        channel_description = request.form.get('channelDescription')
        Channel.create(uid, channel_name, channel_description)
        return redirect('/channels')
    else:
        error = '既に同じ名前のチャンネルが存在しています'
        return render_template('error/error.html', error_message=error)


# チャンネルの更新
@app.route('/channels/update/<cid>', methods=['POST'])
def update_channel(cid):
    uid = session.get("uid")
    if uid is None:
        return redirect('/login')

    channel_name = request.form.get('channelTitle')
    channel_description = request.form.get('channelDescription')

    Channel.update(uid, channel_name, channel_description, cid)
    return redirect(f'/channels/{cid}/messages')



# チャンネルの削除
@app.route('/channels/delete/<cid>', methods=['POST'])
def delete_channel(cid):
    uid = session.get("uid")
    if uid is None:
        return redirect('/login')
    else:
        channel = Channel.find_by_CID(cid)
        if channel["uid"] != uid:
            flash('チャンネルは作成者のみ削除可能です')
        else:
            Channel.delete(cid)
        return redirect ('/channels')



# チャンネル詳細ページの表示（各チャンネル内で、そのチャンネルに属している全メッセージを表示させる）
@app.route('/channels/<cid>/messages', methods=['GET'])
def detail(cid):
    uid = session.get("uid")
    if uid is None:
        return redirect('/login')

    channel = Channel.find_by_CID(cid)
    messages = Message.get_all(cid)

    return render_template('messages.html', messages=messages, channel=channel, uid=uid)


# メッセージの投稿
@app.route('/channels/<cid>/messages', methods=['POST'])
def create_message(cid):
    uid = session.get("uid")
    if uid is None:
        return redirect('/login')

    message = request.form.get('message')

    if message:
        Message.create(uid, cid, message)

    return redirect('/channels/{cid}/messages'.format(cid = cid))


# メッセージの削除
@app.route('/channels/<cid>/messages/<message_id>', methods=['POST'])
def delete_message(cid, message_id):
    uid = session.get("uid")
    if uid is None:
        return redirect('/login')


    if message_id:
        Message.delete(message_id)

    return redirect('/channels/{cid}/messages'.format(cid = cid))


@app.errorhandler(404)
def page_not_found(error):
    return render_template('error/404.html'),404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error/500.html'),500

if __name__ == '__main__':
        app.run(host="0.0.0.0", debug=False)
