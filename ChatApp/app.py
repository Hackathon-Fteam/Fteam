from flask import Flask, request, redirect, render_template, session, flash, abort, url_for
from datetime import timedelta
import hashlib, uuid, re, os
from models import User, Group, GroupMessage, OpenChat, OpenChatMessage, UserModel, Private_chats, Private_chat_message
# from util.assets import bundle_css_files
 
# 定数定義
EMAIL_PATTERN = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
SESSION_DAYS = 30

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', uuid.uuid4().hex)
app.permanent_session_lifetime = timedelta(days=SESSION_DAYS)

# 静的ファイルをキャッシュする設定。開発中はコメントアウト
#app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 2678400
#bundle_css_files(app)


# ルートページのリダイレクト処理
@app.route('/', methods=['GET'])
def index():
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))
    if uid == 'admin123':
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('user_dashboard'))


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

    if name == '' or email =='' or password == '' or passwordConfirmation == '':
        flash('未入力の項目があります')
    elif password != passwordConfirmation:
        flash('パスワードが一致しません')
    elif re.match(EMAIL_PATTERN, email) is None:
        flash('メールアドレスの形式が正しくありません')
    else:
        uid = uuid.uuid4()
        password = hashlib.sha256(password.encode('utf-8')).hexdigest()
        registered_user = User.find_by_email(email)

        if registered_user != None:
            flash('すでに登録されているようです')
        else:
            User.create(uid, name, email, password)
            UserId = str(uid)
            session['uid'] = UserId
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('signup_process'))


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
        flash('未入力の項目があります')
    else:
        user = User.find_by_email(email)
        if user is None:
            flash('このユーザーは存在しません')
        else:
            hashPassword = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if hashPassword != user["password"]:
                flash('パスワードが間違っています')
            else:
                #正しくログインできたのでセッションに保存
                session['user_id'] = user["uid"]
                session['is_admin'] = user["is_admin"]
                #管理者の判定
                if user['is_admin'] == 1:
                    return redirect(url_for('admin_dashboard'))
                #一般ユーザー
                else:
                    return redirect(url_for('user_dashboard'))
    return redirect(url_for('login_view'))

# ログアウト
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_view'))


#管理者用ダッシュボード
@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        flash('権限がありません')
        return redirect(url_for('login_view'))
    return render_template('admin/dashboard.html')

# #管理者：グループチャット一覧へ
# @app.route('/admin/group/list', methods=['GET'])
# def group_list_view():
#     return render_template('admin/group_list.html')

#管理者：オープンチャット一覧へ
@app.route('/admin/open/list', methods=['GET'])
def open_list_view():
    return render_template('admin/open_list.html')

#管理者判定
def is_admin():
    user_id = session.get("user_id")
    if not user_id:
        return False
    user = User.get_user_by_id(user_id)
    return user["is_admin"]

#管理者：個人チャット一覧へ
@app.route('/admin/private/list', methods=['GET'])
def private_list_view():
    if not session.get('is_admin'):
        return redirect(url_for("login_view"))
    users = UserModel.get_all_users()

    if not users:
        users = []
    return render_template('admin/private_list.html', users=users)

#個人チャット画面
@app.route("/private_chat/<user_id>", methods=['GET'])
def private_chat(user_id):
    current_user_id = session.get("user_id")
    if not current_user_id:
        return redirect(url_for("login_view"))

    admin = Private_chats.get_admin()
    if not admin:
        return "管理者が存在しません"
    
    #ログインユーザーが管理者かどうか
    if is_admin():
        #管理者がユーザーのチャットを閲覧
        chat_id = Private_chat_message.get_chat_id(admin["uid"], user_id)
    else:
        #一般ユーザーは管理者とのチャットのみ可能
        if user_id != admin["uid"]:
            return "アクセス権限がありません"
        chat_id = Private_chat_message.get_chat_id(user_id, admin["uid"])
    
    if not chat_id:
        return "チャットが存在しません"
    
    #メッセージ取得
    messages = Private_chat_message.get_message(chat_id)
    return render_template("chat/private_chat.html", messages=messages, chat_id=chat_id, user_id=user_id)

#管理者メニューまとめ(グループチャット作成)
@app.route('/admin_menu/group/create', methods=['GET'])
def create_group_view():
    return render_template('admin/create_group.html')

#管理者メニューまとめ(グループチャット削除)
@app.route('/admin_menu/group/delete', methods=['GET'])
def delete_group_view():
    return render_template('admin/delete_group.html')

#メニューまとめ(オープンチャット作成)
@app.route('/menu/open/create', methods=['GET'])
def create_open_view():
    return render_template('menu/create_open.html')

#オープンチャット作成処理
app.route('/open_chat/create', methods=['POST'])
def create_open_chat():
    uesr_id = session.get('uid')
    is_admin = session.get('is_admin')
    name = request.form.get('name')
    description = request.form.get('description')

    if not uesr_id:
        flash('ログインしてください')
        return redirect(url_for('login_view'))

    if not name:
        flash('チャットルーム名を入力してください')
        return redirect(url_for('login_view'))
    
    if not description:
        flash('チャットルームの説明を入力してください')
        return redirect(url_for('login_view'))
    
    try:
        OpenChat.create(name, description, uesr_id)
        flash('オープンチャットを作成しました。')
    except Exception as e:
        flash(f'エラーが発生しました： {str(e)}')
    #遷移先を判定
    if is_admin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))


#まとめ(オープンチャット削除)
@app.route('/menu/open/delete', methods=['GET'])
def delete_open_view():
    return render_template('menu/delete_open.html')
        
#オープンチャットの削除
@app.route('/open_chat/delete/<int:chat_id>', methods=['POST'])        
def delete_open_chat(chat_id):
    user_id = session.get('uid')
    is_admin = session.get('is_admin')

    if not user_id:
        flash('ログインしてください')
        return redirect(url_for('login_view'))

    try:
        success = OpenChat.delete(chat_id, user_id)
        if success:
            flash('チャットが削除されました')
        else:
            flash('削除権限がありません')
    except Exception as e:
        flash(f'エラーが発生しました： {str(e)}')

    #遷移先を判定
    if is_admin:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('user_dashboard'))



#一般ユーザー用ダッシュボード
@app.route('/user_dashboard')
def user_dashboard():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_view"))
    return render_template('user/dashboard.html')

#ユーザー：個人チャットへ
@app.route('/user/private/chat', methods=['GET'])
def enter_private_chat():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_view"))
    
    admin = Private_chats.get_admin()
    if not admin:
        return "管理者が存在しません"
    
    #チャットID取得
    chat_id = Private_chat_message.get_chat_id(admin["uid"], user_id)

    #チャットが存在しない場合
    if not chat_id:
        return "チャットが存在しません"
    
    #メッセージ取得
    messages = Private_chat_message.get_message(chat_id)
    return render_template("chat/private_chat.html", messages=messages, chat_id=chat_id, user_id=admin["uid"])

#メッセージ送信
@app.route("/send_message", methods=["POST"])
def send_message():
    user_id = session("user_id")
    chat_id = request.form("chat_id")
    content = request.form("content")
    target_user_id = request.form.get("user_id")

    if not user_id or not content:
        return "無効なリクエストです"
    
    Private_chat_message.insert_message(chat_id, user_id, content)

    if is_admin():
        return redirect(url_for("private_chat", user_id=target_user_id))
    else:
        return redirect(url_for("enter_private_chat"))

#ユーザー：グループチャットへ
@app.route('/user/group/chat', methods=['GET'])
def enter_group_chat():
    if 'uid' not in session:
        return redirect(url_for('login_view'))
    
    user_id = session['uid']
    group_chat_id = User.get_group(user_id)

    if group_chat_id:
        return redirect(url_for('group_chat_view', group_chat_id=group_chat_id))
    else:
        flash('あなたはまだグループに招待されていません。')
        return redirect(url_for('user_dashboard'))

# #ユーザーメニューまとめ(オープンチャット作成)
# @app.route('/user_menu/open/create', methods=['GET'])
# def user_create_open_view():
#     return render_template('user/create_open.html')

# #ユーザーメニューまとめ(オープンチャット削除)
# @app.route('/user_menu/open/delete', methods=['GET'])
# def user_delete_opem_view():
#     return render_template('user/delete_open.html')

# #ユーザーメニューまとめ(オープンチャット作成)
# @app.route('/user_menu/open/create', methods=['GET','POST'])
# def user_create_open_view():
#     uid = session.get('uid')
#     if uid is None:
#         return redirect(url_for('login_view'))
    
#     if request.method =='POST':
#         name = request.form.get('name')
#         opc_room = Opc.find_by_name(name)
#         if opc_room == None:
#             description = request.form.get('open_description')
#             Opc.create(uid, name, description, is_open=False)
#             flash("オープンチャットを作成しました")
#             return redirect(url_for('user_dashboard'))
#         else:
#             flash("既に同じ名前のチャンネルが存在しています")
#             return redirect(url_for('/user_menu/open/create'))
    
#     return render_template('user/create_open.html')

# #ユーザーメニューまとめ(オープンチャット削除ルーム)
# @app.route('/user_menu/open/delete', methods=['GET'])
# def user_delete_open_view():
#     uid = session.get('uid')
#     if uid is None:
#         return redirect(url_for('login_view'))
    
#     return render_template('user/delete_open.html')

# #オープンチャット削除ボタン
# @app.route('/user_menu/open/delete/<int:room_id>', methods=['POST'])
# def delete_button(room_id):
#     uid = session.get('uid')
#     if uid is None:
#         return redirect(url_for('login_view'))
    
#     room = Opc.find_by_room_id(room_id)
    
#     if room['create_id'] != uid:
#         flash('チャンネルは制作者のみ削除可能です')
#     else:
#         Opc.delete(room_id)
#     return redirect(url_for('/user_menu/open/delete'))

#グループチャット(リダイレクト)
@app.route('/group_view', methods=['GET'])
def group_chat_redirect():
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))
    
    group = Group.find_by_user_id(uid)
    if group is None:
        flash("グループに所属していません")    
        return redirect(url_for('user_dashboard'))

    return redirect(url_for('group_view',group_chat_id=group['id']))

#管理者用グループチャット
@app.route('/admin/group_list', methods=['GET'])
def admin_group_list():
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))
    
    if not Group.is_admin(uid):
        return redirect(url_for('login_view'))

    groups = Group.get_all()
    return render_template('admin/group_list.html', groups=groups)

#グループチャット(管理者、一般ユーザ共通)
@app.route('/group_view/<int:group_chat_id>/messages', methods=['GET','POST'])
def group_view(group_chat_id):
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))

    group = Group.find_by_id(group_chat_id)
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            GroupMessage.create(uid, group_chat_id, message)
        return redirect(url_for('group_view', group_chat_id=group_chat_id))

    messages = GroupMessage.get_all(group_chat_id)
    return render_template('user/group_chat.html', group=group, messages=messages)

#管理者用グループチャット右上編集ボタン→管理者用チャンネル編集
@app.route('/admin/create_group/<int:group_chat_id>', methods=['GET','POST'])
def create_group(group_chat_id):
    uid = session.get('uid')
    if uid is None or not Group.is_admin(uid):
        flash("管理者専用ページです")
        return redirect(url_for('login_view'))
    
    group = Group.find_by_id(group_chat_id)
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        if name:
            Group.update(group_chat_id, name, description)
            flash("グループ情報を更新しました")
            return redirect(url_for('create_group', group_chat_id=group_chat_id))
    
    return render_template('admin/create_group.html', group=group)

#管理者用メンバー登録、削除
@app.route('/admin/member_edit/<int:group_chat_id>', methods=['GET', 'POST'])
def member_edit(group_chat_id):
    uid = session.get('uid')
    if uid is None or not User.is_admin(uid):
        flash("管理者専用ページです")
        return redirect(url_for('login_view'))

    if request.method == 'POST':
        selected_user_ids = request.form.getlist('user_ids')
        Group.update_members(group_chat_id, selected_user_ids)
        flash("メンバーを更新しました")
        return redirect(url_for('member_edit', group_chat_id=group_chat_id))

    all_users = User.get_all()
    current_member_ids = Group.get_member_ids(group_chat_id)
    return render_template('admin/member_edit.html',
                           users=all_users,
                           member_ids=current_member_ids,
                           group_chat_id=group_chat_id)

#管理者用オープンチャット一覧
@app.route('/admin/open_list', methods=['GET'])
def admin_open_list():
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))
    
    if not Group.is_admin(uid):
        return redirect(url_for('login_view'))

    open_room = OpenChat.get_all()
    return render_template('admin/open_list.html', open_room = open_room)

#オープンチャット(管理者、一般ユーザ共通)
@app.route('/open_view/<int:id>/messages', methods=['GET','POST'])
def open_view(chat_id):
    uid = session.get('uid')
    if uid is None:
        return redirect(url_for('login_view'))

    opens = OpenChat.find_by_id(chat_id)
    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            OpenChatMessage.create(uid, chat_id, message)
        return redirect(url_for('open_view', chat_id=chat_id))

    messages = OpenChatMessage.get_all(chat_id)
    return render_template('user/open_chat.html', opens=opens, messages=messages)

#管理者用オープンチャット右上編集ボタン→管理者用チャンネル編集
@app.route('/admin/create_open/<int:id>', methods=['GET','POST'])
def create_open(chat_id):
    uid = session.get('uid')
    if uid is None or not Group.is_admin(uid):
        flash("管理者専用ページです")
        return redirect(url_for('login_view'))
    
    open = OpenChat.find_by_id(chat_id)
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        if name:
            OpenChat.update(chat_id, name, description)
            flash("グループ情報を更新しました")
            return redirect(url_for('create_open', chat_id=chat_id))
    
    return render_template('admin/create_open.html', open=open)

@app.errorhandler(404)
def page_not_found(error):
    return render_template('error/404.html'),404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template('error/500.html'),500

if __name__ == '__main__': 
    app.run(host="0.0.0.0", debug=True)