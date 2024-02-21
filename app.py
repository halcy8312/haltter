from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import hashlib
from dotenv import load_dotenv
import os
from flask_migrate import Migrate


load_dotenv()  # 環境変数を読み込む

app = Flask(__name__)
# 環境変数からデータベースURLを取得、設定されていない場合はデフォルトのSQLiteデータベースを使用
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mydatabase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# セッションの秘密鍵、環境変数から取得、設定されていない場合はデフォルト値を使用
app.secret_key = os.environ.get('SECRET_KEY', 'mysecretkey')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile = db.Column(db.Text, nullable=True)
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    followed = db.relationship(
        'Follow', foreign_keys='Follow.follower_id',
        backref='follower', lazy='dynamic', cascade='all, delete-orphan')
    followers = db.relationship(
        'Follow', foreign_keys='Follow.followed_id',
        backref='followed', lazy='dynamic', cascade='all, delete-orphan')

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(Follow(followed=user))

    def unfollow(self, user):
        Follow.query.filter_by(
            follower_id=self.id,
            followed_id=user.id).delete()

    def is_following(self, user):
        return Follow.query.filter(
            Follow.follower_id == self.id,
            Follow.followed_id == user.id).count() > 0

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

db.create_all()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = hash_password(password)

        user = User(username=username, password=hashed_password)
        db.session.add(user)
        try:
            db.session.commit()
            flash('登録が成功しました。ログインしてください。')
            return redirect(url_for('login'))
        except:
            db.session.rollback()
            flash('ユーザー名は既に存在しています。')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and hash_password(password) == user.password:
            session['username'] = username
            flash('ログイン成功！')
            return redirect(url_for('index'))
        else:
            flash('ログイン失敗。ユーザー名またはパスワードを確認してください。')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('ログアウトしました。')
    return redirect(url_for('index'))

@app.route('/post', methods=['GET', 'POST'])
def post():
    if 'username' not in session:
        flash('投稿するにはログインが必要です。')
        return redirect(url_for('login'))

    if request.method == 'POST':
        content = request.form['content']
        user = User.query.filter_by(username=session['username']).first()
        post = Post(content=content, author=user)
        db.session.add(post)
        db.session.commit()
        flash('投稿が公開されました。')
        return redirect(url_for('index'))
    return render_template('post.html')

@app.route('/account/<username>')
def account(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('account.html', user=user, posts=posts)

@app.route('/follow/<username>', methods=['POST'])
def follow(username):
    if 'username' not in session:
        flash('フォローするにはログインが必要です。')
        return redirect(url_for('login'))
    user_to_follow = User.query.filter_by(username=username).first()
    if user_to_follow is None:
        flash('ユーザーが見つかりません。')
        return redirect(url_for('index'))
    if user_to_follow.username == session['username']:
        flash('自分自身をフォローすることはできません。')
        return redirect(url_for('account', username=username))
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.follow(user_to_follow)
    db.session.commit()
    flash(f'{username}をフォローしました。')
    return redirect(url_for('account', username=username))

@app.route('/unfollow/<username>', methods=['POST'])
def unfollow(username):
    if 'username' not in session:
        flash('アンフォローするにはログインが必要です。')
        return redirect(url_for('login'))
    user_to_unfollow = User.query.filter_by(username=username).first()
    if user_to_unfollow is None:
        flash('ユーザーが見つかりません。')
        return redirect(url_for('index'))
    if user_to_unfollow.username == session['username']:
        flash('自分自身のフォローを解除することはできません。')
        return redirect(url_for('account', username=username))
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.unfollow(user_to_unfollow)
    db.session.commit()
    flash(f'{username}のフォローを解除しました。')
    return redirect(url_for('account', username=username))

if __name__ == '__main__':
    app.run(debug=True)
