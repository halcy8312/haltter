from flask import Flask, request, render_template, redirect, url_for, session, flash
import sqlite3
from datetime import datetime
import hashlib
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'default-secret-key')

# データベース接続の関数
def get_db_connection():
    conn = sqlite3.connect('tweets.db')
    conn.row_factory = sqlite3.Row
    return conn

# データベースとテーブルのセットアップ
def setup_database():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tweets
                     (id INTEGER PRIMARY KEY, username TEXT, content TEXT, posted_at TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, created_at TEXT)''')
        conn.commit()

# パスワードをハッシュ化
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# アプリケーション起動時にデータベースセットアップを実行
setup_database()

@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT username, content, posted_at FROM tweets ORDER BY posted_at DESC').fetchall()
    conn.close()
    return render_template('index.html', posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)

        with get_db_connection() as conn:
            try:
                conn.execute('INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)',
                             (username, hashed_password, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                flash('ユーザー登録が完了しました。ログインしてください。')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash('エラー: ユーザー名が既に存在します。')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

        if user and hash_password(password) == user['password']:
            session['username'] = username
            flash('ログイン成功!')
            return redirect(url_for('index'))
        else:
            flash('ログイン失敗: ユーザー名またはパスワードが間違っています。')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('ログアウトしました。')
    return redirect(url_for('index'))

@app.route('/post', methods=['GET', 'POST'])
def post():
    if 'username' not in session:
        flash('ログインが必要です。')
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form['content']
        with get_db_connection() as conn:
            conn.execute('INSERT INTO tweets (username, content, posted_at) VALUES (?, ?, ?)',
                         (session['username'], content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
        flash('投稿が完了しました!')
        return redirect(url_for('index'))
    return render_template('post.html')

if __name__ == '__main__':
    app.run(debug=True)
