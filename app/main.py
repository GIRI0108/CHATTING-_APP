import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import random
import openai
load_dotenv()

from routes.ai_routes import ai_bp
from routes.game_routes import game_bp
from routes.news_routes import news_bp
from routes.weather_routes import weather_bp
from models.game_model import GameState, WatchSession, MusicSession


# Basic config
app = Flask(__name__, static_folder="static", template_folder="templates")
openai.api_key = os.getenv("AI_API_KEY")
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'postgresql://postgres:admin@localhost:5433/app_1')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

from extensions import db
db.init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    contact = db.Column(db.String(120), unique=True, nullable=False)  # phone or email
    name = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contact_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # For 1:1 conversation, store sorted user ids to easily find room
    user_a = db.Column(db.Integer, nullable=False)
    user_b = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text)
    msg_type = db.Column(db.String(20), default='text')  # text, file, system
    file_url = db.Column(db.String(300))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    delivered = db.Column(db.Boolean, default=False)
    read = db.Column(db.Boolean, default=False)

class PrivateRoom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(20), unique=True, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Login loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helpers
def get_or_create_conversation(a, b):
    a_, b_ = (min(a,b), max(a,b))
    conv = Conversation.query.filter_by(user_a=a_, user_b=b_).first()
    if not conv:
        conv = Conversation(user_a=a_, user_b=b_)
        db.session.add(conv)
        db.session.commit()
    return conv

def generate_room_key():
    import secrets, string
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(6))


# Routes: auth pages and simple APIs
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('contacts'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        contact = request.form['contact']
        name = request.form['name']
        pwd = generate_password_hash(request.form['password'])
        if User.query.filter_by(contact=contact).first():
            return "Contact already exists", 400
        user = User(contact=contact, name=name, password=pwd)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('contacts'))
    return render_template('login.html', register=True)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        contact = request.form['contact']
        password = request.form['password']
        user = User.query.filter_by(contact=contact).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            user.last_seen = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('contacts'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html', register=False)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/contacts')
@login_required
def contacts():
    # Return the contact page (frontend loads contact list via socket or API)
    return render_template('contacts.html')

@app.route('/chat/<int:other_id>')
@login_required
def chat_page(other_id):
    other = User.query.get_or_404(other_id)
    return render_template('chat.html', other=other)

@app.route('/private-room')
@login_required
def private_room_page():
    return render_template('private_room.html')

@app.route('/create-room', methods=['POST'])
@login_required
def create_room():
    key = generate_room_key()
    room = PrivateRoom(key=key, creator_id=current_user.id)
    db.session.add(room)
    db.session.commit()
    return jsonify({'room_key': key})

@app.route('/join-room', methods=['POST'])
@login_required
def join_room_key():
    data = request.get_json()
    key = data.get('key')
    room = PrivateRoom.query.filter_by(key=key).first()
    if not room:
        return jsonify({'error': 'Invalid key'}), 404
    return jsonify({'room_key': room.key})


# in main.py (or game_routes.py blueprint)
from flask import render_template, abort
@app.route("/private/module/<module_name>")
@login_required
def private_module(module_name):
    allowed = {"chess", "checkers", "tictactoe", "music", "watch", "news", "weather", "ai"}
    if module_name not in allowed:
        return abort(404)
    return render_template(f"private_modules/{module_name}.html")


# Upload endpoint for file messages
ALLOWED_EXT = {'png','jpg','jpeg','gif','pdf','mp4','mp3','ogg'}
def allowed(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    f = request.files.get('file')
    if not f or not allowed(f.filename):
        return jsonify({'error':'invalid file'}), 400
    filename = secure_filename(f"{uuid.uuid4().hex}_{f.filename}")
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    f.save(path)
    url = url_for('uploaded_file', filename=filename, _external=True)
    return jsonify({'url': url})

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/api/ai/process", methods=["POST"])
def ai_process():
    try:
        data = request.get_json()
        text = data.get("text", "").strip()
        task = data.get("task", "").strip()
        lang = data.get("lang", "English").strip()

        if not text:
            return jsonify({"result": "Please enter some text."}), 400

        if task == "translate":
            prompt = f"Translate the following text into {lang}:\n{text}"
        elif task == "summarize":
            prompt = f"Summarize the following text clearly and concisely:\n{text}"
        elif task == "improve":
            prompt = f"Improve this text for clarity, tone, and grammar:\n{text}"
        elif task == "analyze":
            prompt = f"Analyze the sentiment and intent of this text:\n{text}"
        else:
            prompt = f"Process the following text in a helpful way:\n{text}"

        # 🔥 OpenAI call
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful multilingual AI assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        ai_output = response.choices[0].message.content.strip()
        return jsonify({"result": ai_output})

    except Exception as e:
        print("AI Process Error:", e)
        return jsonify({"result": f"Error: {str(e)}"}), 500

# Simple API to add contact
@app.route('/api/add_contact', methods=['POST'])
@login_required
def add_contact():
    contact_value = request.json.get('contact')
    user = User.query.filter_by(contact=contact_value).first()
    if not user:
        return jsonify({'error':'user not found'}), 404
    # Prevent duplicates
    existing = Contact.query.filter_by(owner_id=current_user.id, contact_user_id=user.id).first()
    if existing:
        return jsonify({'ok':True, 'contact_id':existing.id})
    c = Contact(owner_id=current_user.id, contact_user_id=user.id)
    db.session.add(c)
    db.session.commit()
    return jsonify({'ok':True, 'contact_user': {'id': user.id, 'name': user.name, 'contact': user.contact}})

# Socket.IO events: presence, messaging and WebRTC signalling
# We'll map user.id -> sid(s) (support multiple devices)
connected_users = {}  # user_id -> set of sid

@socketio.on('connect')
def handle_connect():
    if not current_user or not current_user.is_authenticated:
        # Allow connect, but we recommend auth on connect for real app
        return
    sid = request.sid
    uid = current_user.id
    connected_users.setdefault(uid, set()).add(sid)
    current_user.last_seen = datetime.utcnow()
    db.session.commit()
    # broadcast presence
    emit('presence_update', {'user_id': uid, 'status': 'online'}, broadcast=True)
    print(f"User {uid} connected sid={sid}")

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    # find user by sid
    for uid, sids in list(connected_users.items()):
        if sid in sids:
            sids.remove(sid)
            if not sids:
                connected_users.pop(uid)
                # broadcast offline
                emit('presence_update', {'user_id': uid, 'status': 'offline'}, broadcast=True)
            break
    print("Disconnected", sid)

@socketio.on('get_contacts')
def handle_get_contacts():
    owner = current_user.id
    contacts = Contact.query.filter_by(owner_id=owner).all()
    payload = []
    for c in contacts:
        u = User.query.get(c.contact_user_id)
        payload.append({
            'id': u.id, 'name': u.name, 'contact': u.contact,
            'online': u.id in connected_users
        })
    emit('contacts_list', payload)

@socketio.on('start_conversation')
def handle_start_conv(data):
    other_id = int(data.get('other_id'))
    conv = get_or_create_conversation(current_user.id, other_id)
    room = f"conv_{conv.id}"
    join_room(room)
    # send back conversation id
    emit('conversation', {'conv_id': conv.id})

@socketio.on('join_conv')
def handle_join_conv(data):
    conv_id = int(data.get('conv_id'))
    room = f"conv_{conv_id}"
    join_room(room)
    # send last 50 messages
    msgs = Message.query.filter_by(conversation_id=conv_id).order_by(Message.timestamp.asc()).limit(200).all()
    out = []
    for m in msgs:
        out.append({
            'id': m.id,
            'sender_id': m.sender_id,
            'content': m.content,
            'msg_type': m.msg_type,
            'file_url': m.file_url,
            'timestamp': m.timestamp.isoformat(),
            'read': m.read
        })
    emit('history', out)

@socketio.on("game:move")
def handle_game_move(data):
    conv_id = data.get("conv_id")
    game_type = data.get("game")
    state = data.get("state")
    move_by = current_user.id

    gs = GameState.query.filter_by(conv_id=conv_id, game_type=game_type).first()
    if gs:
        gs.state = state
        gs.last_move_by = move_by
        db.session.commit()

    room = f"conv_{conv_id}"
    emit("game:update", data, room=room)

@socketio.on("watch:play")
def watch_play(data):
    conv_id = data["conv_id"]
    ws = WatchSession.query.filter_by(conv_id=conv_id).first()
    ws.is_playing = True
    db.session.commit()
    emit("watch:play", data, room=f"conv_{conv_id}", include_self=False)

@socketio.on("watch:pause")
def watch_pause(data):
    conv_id = data["conv_id"]
    ws = WatchSession.query.filter_by(conv_id=conv_id).first()
    ws.is_playing = False
    db.session.commit()
    emit("watch:pause", data, room=f"conv_{conv_id}", include_self=False)

@socketio.on("watch:seek")
def watch_seek(data):
    conv_id = data["conv_id"]
    timestamp = data["timestamp"]
    ws = WatchSession.query.filter_by(conv_id=conv_id).first()
    ws.timestamp = timestamp
    db.session.commit()
    emit("watch:seek", data, room=f"conv_{conv_id}", include_self=False)

@socketio.on("music:play")
def music_play(data):
    conv_id = data["conv_id"]
    ms = MusicSession.query.filter_by(conv_id=conv_id).first()
    ms.is_playing = True
    db.session.commit()
    emit("music:play", data, room=f"conv_{conv_id}", include_self=False)

@socketio.on("music:pause")
def music_pause(data):
    conv_id = data["conv_id"]
    ms = MusicSession.query.filter_by(conv_id=conv_id).first()
    ms.is_playing = False
    db.session.commit()
    emit("music:pause", data, room=f"conv_{conv_id}", include_self=False)

@socketio.on("music:seek")
def music_seek(data):
    conv_id = data["conv_id"]
    timestamp = data["timestamp"]
    ms = MusicSession.query.filter_by(conv_id=conv_id).first()
    ms.timestamp = timestamp
    db.session.commit()
    emit("music:seek", data, room=f"conv_{conv_id}", include_self=False)


@socketio.on('send_message')
def handle_send_message(data):
    conv_id = int(data.get('conv_id'))
    content = data.get('content')
    msg_type = data.get('msg_type', 'text')
    file_url = data.get('file_url')
    m = Message(conversation_id=conv_id, sender_id=current_user.id, content=content, msg_type=msg_type, file_url=file_url)
    db.session.add(m)
    db.session.commit()
    out = {
        'id': m.id,
        'conversation_id': conv_id,
        'sender_id': m.sender_id,
        'content': m.content,
        'msg_type': m.msg_type,
        'file_url': m.file_url,
        'timestamp': m.timestamp.isoformat()
    }
    room = f"conv_{conv_id}"
    emit('new_message', out, room=room)
    # optionally mark delivered for recipients who are online
    # update delivered flags in DB if someone is connected
    # (left as exercise for maturity)

@socketio.on('typing')
def handle_typing(data):
    conv_id = int(data.get('conv_id'))
    state = data.get('state', True)
    room = f"conv_{conv_id}"
    emit('typing', {'user_id': current_user.id, 'state': state}, room=room, include_self=False)

@socketio.on('private:join')
def handle_private_join(data):
    room_key = data.get('room_key')
    if not room_key:
        return
    join_room(room_key)
    emit('private:joined', {'room_key': room_key, 'user': current_user.name}, room=room_key)
    print(f"{current_user.name} joined private room {room_key}")

@socketio.on('private:message')
def handle_private_message(data):
    room_key = data.get('room_key')
    msg = data.get('message')
    emit('private:message', {'user': current_user.name, 'message': msg}, room=room_key)


# Read receipt
@socketio.on('message_read')
def handle_message_read(data):
    msg_id = int(data.get('msg_id'))
    m = Message.query.get(msg_id)
    if m:
        m.read = True
        db.session.commit()
        room = f"conv_{m.conversation_id}"
        emit('message_read', {'msg_id': msg_id, 'reader_id': current_user.id}, room=room)

# ---- WebRTC signalling for 1:1 calls ----
# We'll send events: 'call:offer', 'call:answer', 'call:ice', 'call:hangup'
@socketio.on('call:request')
def handle_call_request(data):
    # data: {to: user_id, conv_id: ...}
    to = int(data.get('to'))
    from_user = current_user.id
    payload = {'from': from_user, 'conv_id': data.get('conv_id')}
    # send to all sids of target
    sids = connected_users.get(to, set())
    for sid in sids:
        emit('call:incoming', payload, room=sid)

@socketio.on('call:offer')
def handle_call_offer(data):
    # data: {to: user_id, sdp: ..., conv_id: ...}
    to = int(data.get('to'))
    payload = {'from': current_user.id, 'sdp': data.get('sdp'), 'conv_id': data.get('conv_id')}
    for sid in connected_users.get(to, set()):
        emit('call:offer', payload, room=sid)

@socketio.on('call:answer')
def handle_call_answer(data):
    to = int(data.get('to'))
    payload = {'from': current_user.id, 'sdp': data.get('sdp'), 'conv_id': data.get('conv_id')}
    for sid in connected_users.get(to, set()):
        emit('call:answer', payload, room=sid)

@socketio.on('call:ice')
def handle_call_ice(data):
    to = int(data.get('to'))
    payload = {'from': current_user.id, 'candidate': data.get('candidate')}
    for sid in connected_users.get(to, set()):
        emit('call:ice', payload, room=sid)

@socketio.on('call:hangup')
def handle_call_hangup(data):
    to = int(data.get('to'))
    payload = {'from': current_user.id}
    for sid in connected_users.get(to, set()):
        emit('call:hangup', payload, room=sid)

@socketio.on("private:module:start")
def handle_private_module_start(data):
    conv_id = data.get("conv_id")
    module = data.get("module")
    if not conv_id or not module:
        return
    # Optionally create session rows based on module
    room = f"conv_{conv_id}"
    emit("private:module:started", {"module": module, "conv_id": conv_id}, room=room)

@socketio.on("game:start")
def handle_game_start(data):
    conv_id = data.get("conv_id")
    game_type = data.get("game")
    if not conv_id or not game_type:
        return
    # create GameState if not exists
    gs = GameState.query.filter_by(conv_id=conv_id, game_type=game_type).first()
    if not gs:
        gs = GameState(conv_id=conv_id, game_type=game_type, state="{}")
        db.session.add(gs)
        db.session.commit()
    room = f"conv_{conv_id}"
    emit("game:started", {"conv_id": conv_id, "game": game_type}, room=room)


# Initialize DB
with app.app_context():
    db.create_all()

app.register_blueprint(ai_bp, url_prefix="/api/ai")
app.register_blueprint(game_bp, url_prefix="/games")
app.register_blueprint(news_bp, url_prefix="/news")
app.register_blueprint(weather_bp, url_prefix="/weather")

@app.route("/private/module/<module>")
@login_required
def load_private_module(module):
    allowed = {
        "chess": "private_modules/chess.html",
        "tictactoe": "private_modules/tictactoe.html",
        "watch": "private_modules/watch.html",
        "music": "private_modules/music.html",
        "checkers": "private_modules/checkers.html",
        "news": "private_modules/news.html",
        "weather": "private_modules/weather.html",
        "ai": "private_modules/ai.html"
    }

    if module not in allowed:
        return "Module not found", 404

    return render_template(allowed[module])

if __name__ == '__main__':
    # use eventlet for SocketIO support
  socketio.run(app, host="0.0.0.0", port=500, debug=True, use_reloader=False)

