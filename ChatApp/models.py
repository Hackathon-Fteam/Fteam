from flask import abort
import pymysql
from util.DB import DB

#初期起動時にコネクションプールを作成し接続を確率
db_pool = DB.init_db_pool()

#ユーザークラス
class User:
    @classmethod
    def create(cls, uid, name, email, password, is_admin=0):
        #ユーザー作成
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "INSERT INTO users (uid, user_name, email, password, is_admin) VALUES (%s, %s, %s, %s, %s)"
                cur.execute(sql, (uid, name, email, password, is_admin))
                conn.commit()
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)

    @classmethod
    def find_by_email(cls, email):
        #メールアドレスでユーザー検索
        conn = db_pool.get_conn()
        try:
                with conn.cursor(pymysql.cursors.DictCursor) as cur:
                    sql = "SELECT * FROM users WHERE email=%s"
                    cur.execute(sql, (email,))
                    user = cur.fetchone()
                return user
        except pymysql.Error as e:
            print(f'エラーが発生しています：{e}')
            abort(500)
        finally:
            db_pool.release(conn)
    
    @classmethod
    def is_admin(cls, email):
        # 管理者判定
        user = cls.find_by_email(email)
        if user:
            return user['is_admin'] == 1
        return False
    
    @classmethod
    def get_usr_group(cls, user_id):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql ="SELECT group_chat_id FROM group_members WHERE user_id = %s"
                cur.execute(sql, (user_id,))
                result = cur.fetchone()
                return result[0] if result else None
        finally:
            db_pool.release(conn)


    @classmethod
    def get_all(cls):
        conn = db_pool.get_conn()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                cur.execute("SELECT uid, user_name FROM users")
                return cur.fetchall()
        finally:
            db_pool.release(conn)

#ユーザー関連のデータ操作をまとめたクラス
class UserModel:
    @staticmethod
    def get_user_by_id(user_id):
        #指定したユーザーの情報を取得する
        sql = "SELECT uid, user_name, email, is_admin FROM users WHERE uid = %s"
        conn = db_pool.get_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, (user_id,))
            user = cursor.fetchone()
        conn.close()
        return user

    @staticmethod
    def get_admin():
        #管理者ユーザーの取得('is_admin'カラムで判定)
        sql = "SELECT uid, user_name FROM users WHERE is_admin = TRUE"
        conn = db_pool.get_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql)
            admin = cursor.fetchone()
        conn.close()
        return admin
    
    @staticmethod
    def get_all_users():
        #一般ユーザーのリストを取得（管理者を除く）
        sql = "SELECT uid, user_name FROM users WHERE is_admin = FALSE"
        conn = db_pool.get_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql)
            users = cursor.fetchall()
        conn.close()
        return users
    
#個人チャットクラス
class Private_chats:
    @staticmethod
    def create_chat(user1_id, user2_id):
        sql = "INSERT INTO private_chats (user1_id, user2_id) VALUES (%s, %s)"
        conn = db_pool.get_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, (user1_id, user2_id))
            chat_id = cursor.lastrowid
        conn.commit()
        conn.close
        return chat_id
    
    @staticmethod
    def get_or_create_chat(user1_id, user2_id):
        chat_id = Private_chats.get_chat_id(user1_id, user2_id)
        if chat_id is None:
            chat_id = Private_chats.create_chat(user1_id, user2_id)
        return chat_id
        
    @staticmethod
    def get_chat_id(user1_id, user2_id):
        #チャットIDを取得する。存在しない場合はNoneを返す
        sql = "SELECT id FROM private_chats WHERE (user1_id = %s AND user2_id = %s) OR (user1_id = %s AND user2_id = %s)"
        conn = db_pool.get_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, (user1_id, user2_id, user2_id, user1_id))
            chat = cursor.fetchone()
            return chat['id'] if chat else None

        

#個別チャットメッセージ
class Private_chat_message:    
    @staticmethod
    def insert_message(private_chats_id, user_id, content):
        #メッセージを送信する
        print(f"[DB] insert_message: chat_id={private_chats_id}, user_id={user_id}, content={content}")
        sql = "INSERT INTO private_messages (private_chats_id, user_id, content) VALUES (%s, %s, %s)"
        conn = db_pool.get_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, (private_chats_id, user_id, content))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_message(chat_id):
        #指定したチャットIDのメッセージを取得する
        sql = """
        SELECT pm.id, pm.user_id, pm.content, pm.created_at, u.user_name FROM private_messages pm JOIN users u 
        ON pm.user_id = u.uid WHERE pm.private_chats_id = %s ORDER BY pm.created_at ASC
        """
        conn = db_pool.get_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql, (chat_id,))
            messages = cursor.fetchall()
        conn.close()
        return messages

#グループクラス
class Group:            
    @classmethod
    def find_by_user_id(cls, user_id):
        conn = db_pool.get_conn()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                sql = """
                SELECT group_chats.id, group_chats.name
                FROM group_members
                JOIN group_chats ON group_members.group_chats_id = group_chats.id
                WHERE group_members.user_id = %s 
                LIMIT 1
                """
                cur.execute(sql, (user_id,))
                group = cur.fetchone()
                return group
        except pymysql.Error as e:
            print(f'エラーが発生しています: {e}')
            abort(500)
        finally:
            db_pool.release(conn)

    @classmethod
    def find_by_id(cls, group_chats_id):
        conn = db_pool.get_conn()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                sql = "SELECT id, name FROM group_chats WHERE id = %s"
                cur.execute(sql, (group_chats_id,))
                group = cur.fetchone()
                return group
        except pymysql.Error as e:
            print(f'エラーが発生しています: {e}')
            abort(500)
        finally:
            db_pool.release(conn)
            
    @classmethod
    def update(cls, group_chats_id, name, description):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "UPDATE group_chats SET name=%s, description=%s WHERE id=%s"
                cur.execute(sql, (name, description, group_chats_id))
                conn.commit()
        finally:
            db_pool.release(conn)
            
    @classmethod
    def get_all(cls):
        conn = db_pool.get_conn()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                sql = "SELECT id, name FROM group_chats;"
                cur.execute(sql)
                groups = cur.fetchall()
                return groups
        except pymysql.Error as e:
            print(f'エラーが発生しています : {e}')
            abort(500)
        finally:
            db_pool.release(conn)

    @classmethod
    def is_admin(cls, uid):
        return uid == "admin123"

    @classmethod
    def get_member_ids(cls, group_chats_id):
        conn = db_pool.get_conn()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                sql = ("SELECT user_id FROM group_members WHERE group_chats_id = %s")
                cur.execute(sql, (group_chats_id,))
                result = cur.fetchall()
                return [row['user_id'] for row in result]
        finally:
            db_pool.release(conn)

    @classmethod
    def update_members(cls, group_chats_id, user_ids):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql_delete = "DELETE FROM group_members WHERE group_chats_id = %s"
                cur.execute(sql_delete, (group_chats_id,))
                sql_insert = "INSERT INTO group_members (group_chats_id, user_id, created_at) VALUES (%s, %s, NOW())"
                for user_id in user_ids:
                    cur.execute(sql_insert, (group_chats_id, user_id))
            conn.commit()
        finally:
            db_pool.release(conn)

    @classmethod
    def create_group(cls, name, creator_id):
        #グループチャットの作成（管理者のみ）
        if not cls.is_admin(creator_id):
            return {"error": "権限がありません"}
        
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "INSERT INTO group_chats (name, is_open, created_at) VALUES (%s, FALSE, NOW())"
                cur.execute(sql, (name,))
                conn.commit()
                return {"success": "グループチャット作成されました"}
        finally:
            db_pool.release(conn)

    @classmethod
    def delete_group(cls, group_id, deleter_id):
        #グループチャットの削除（管理者のみ）
        if not cls.is_admin(deleter_id):
            return {"error": "権限がありません"}
        
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "DELETE FROM group_chats WHERE id = %s"
                cur.execute(sql, (group_id,))

                conn.commit()
                return {"success": "グループチャットが削除されました"}
        finally:
            db_pool.release(conn)

#グループメッセージクラス
class GroupMessage:
    @classmethod
    def create(cls, current_user_id, group_chats_id, content):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO group_messages (user_id, group_chats_id, content, created_at)
                    VALUES (%s, %s, %s, NOW())
                """
                cur.execute(sql, (current_user_id, group_chats_id, content))
                conn.commit()
        except pymysql.Error as e:
            print(f'エラーが発生しています: {e}')
            abort(500)
        finally:
            db_pool.release(conn)

@classmethod
def get_all(cls, group_chats_id):
    conn = db_pool.get_conn()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            sql = """
                SELECT group_messages.user_id AS uid,
                        users.user_name,
                        group_messages.content
                FROM group_messages
                JOIN users ON group_messages.user_id = users.uid
                WHERE group_messages.group_chats_id = %s
                ORDER BY group_messages.created_at ASC
            """
            cur.execute(sql, (group_chats_id,))
            messages = cur.fetchall()
            return messages
    except pymysql.Error as e:
        print(f'エラーが発生しています: {e}')
        abort(500)
    finally:
        db_pool.release(conn)

#オープンチャットクラス
class OpenChat:
    @classmethod
    def create(cls, name, description, creator_id, is_open=True):
        #オープンチャットの作成
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "INSERT INTO open_chats (name, description, is_open, creator_id) VALUES (%s, %s, %s, %s)"
                cur.execute(sql, (name, description, is_open, creator_id))
                conn.commit()
        except pymysql.Error as e:
            print(f'エラーが発生しました: {e}')
            abort(500)
        finally:
            db_pool.release(conn)

    @classmethod
    def get(cls, chat_id):
        conn = db_pool.get_conn()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                sql = "SELECT * FROM open_chats WHERE id = %s"
                cur.execute(sql, (chat_id,))
                return cur.fetchone()
        except pymysql.Error as e:
            print(f'エラーが発生しました: {e}')
            abort(500)
        finally:
            db_pool.release(conn)

    @classmethod
    def delete(cls, chat_id, user_id):
        #オープンチャットの削除
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                #チャットルームの情報取得
                sql = "SELECT create_id FROM group_chats WHERE id = %s"
                cur.execute(sql, (chat_id,))
                chat = cur.fetchone()

                #チャットルームが存在しない場合
                if not chat:
                    return False
                
                #管理者または作成者のみが削除可能
                if chat['creator_id'] == user_id or User.is_admin(user_id):
                    sql = "DELETE FROM open_chats WHERE id = %s"
                    cur.execute(sql, (chat_id,))
                    conn.commit()
                    return True
                else:
                    return False
        except pymysql.Error as e:
            print(f'エラーが発生しました: {e}')
            abort(500)
        finally:
            db_pool.release(conn)
            
    @classmethod
    def get_all(cls):
        conn = db_pool.get_conn()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                sql = "SELECT * FROM open_chats;"
                cur.execute(sql)
                opc_room = cur.fetchall()
                return opc_room
        except pymysql.Error as e:
            print(f'エラーが発生しています : {e}')
            abort(500)
        finally:
            db_pool.release(conn)
            
    @classmethod
    def find_by_id(cls, chat_id):
        conn = db_pool.get_conn()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                sql = "SELECT * FROM open_chats WHERE id=%s;"
                cur.execute(sql, (chat_id,))
                opc_room = cur.fetchone()
                return opc_room
        except pymysql.Error as e:
            print(f'エラーが発生しています : {e}')
            abort(500)
        finally:
            db_pool.release(conn)

    @classmethod
    def update(cls, chat_id, name, description):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = "UPDATE open_chats SET name=%s, description=%s WHERE id=%s"
                cur.execute(sql, (name, description, chat_id))
                conn.commit()
        finally:
            db_pool.release(conn)
    

    @staticmethod
    def get_all_openchats():
        sql = "SELECT * FROM open_chats;"
        conn = db_pool.get_conn()
        with conn.cursor() as cursor:
            cursor.execute(sql)
            open_chats = cursor.fetchall()
        conn.close()
        return open_chats

#オープンチャットメッセージクラス
class OpenChatMessage:
    @classmethod
    def create(cls, user_id, open_chat_id, content):
        conn = db_pool.get_conn()
        try:
            with conn.cursor() as cur:
                sql = """
                    INSERT INTO open_chat_messages (user_id, open_chat_id, content, created_at)
                    VALUES (%s, %s, %s, NOW())
                """
                cur.execute(sql, (user_id, open_chat_id, content))
                conn.commit()
        except pymysql.Error as e:
            print(f"エラー(create) : {e}")
            abort(500)
        finally:
            db_pool.release(conn)

    @classmethod
    def get_all(cls, open_chat_id):
        conn = db_pool.get_conn()
        try:
            with conn.cursor(pymysql.cursors.DictCursor) as cur:
                sql = """
                    SELECT users.user_name, open_chat_messages.user_id, open_chat_messages.content
                    FROM open_chat_messages
                    JOIN users ON open_chat_messages.user_id = users.uid
                    WHERE open_chat_messages.open_chat_id = %s
                    ORDER BY open_chat_messages.created_at ASC
                """
                cur.execute(sql, (open_chat_id,))
                return cur.fetchall()
        except pymysql.Error as e:
            print(f"エラー（get_all）: {e}")
            abort(500)
        finally:
            db_pool.release(conn)    