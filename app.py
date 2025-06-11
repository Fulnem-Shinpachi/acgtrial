from flask import Flask, render_template, session
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
import os, json
from flask import send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret-key'

UPLOAD_FOLDER = 'uploads'
USERS_FILE = 'users.json'

ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4',
    'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'
}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ===================== Utility Functions =====================

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ===================== Routes =====================
@app.route('/admin')
def admin_page():
    # 🛑 Only YOU (admin) can see this page
    if 'username' not in session or session['username'] != 'admin':
        return "Access denied", 403

    # ✅ All files by all users
    all_files = []
    for user, files in user_upload_data.items():
        for file in files:
            all_files.append({
                "username": user,
                "filename": file
            })

    return render_template('admin.html', all_files=all_files)

@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        users = load_users()

        if username in users:
            return render_template('signup.html', error='Username already exists.')

        users[username] = generate_password_hash(password)
        save_users(users)
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        users = load_users()

        if username in users and check_password_hash(users[username], password):
            session['user'] = username
            return redirect(url_for('dashboard'))

        return render_template('login.html', error='Invalid credentials')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session['user']
    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    os.makedirs(user_folder, exist_ok=True)

    metadata_path = os.path.join(user_folder, 'metadata.json')
    metadata = {}

    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

    files = []
    for f in os.listdir(user_folder):
        if f == 'metadata.json':
            continue
        upload_time = metadata.get(f, {}).get('upload_time', '1970-01-01 00:00:00')
        files.append({'filename': f, 'upload_time': upload_time})

    # Sort files by upload time (newest first)
    files.sort(key=lambda x: datetime.strptime(x['upload_time'], '%Y-%m-%d %H:%M:%S'), reverse=True)

    return render_template('dashboard.html', username=username, files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user' not in session:
        return redirect(url_for('login'))

    username = session['user']
    if 'file' not in request.files:
        return redirect(url_for('dashboard'))

    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('dashboard'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
        os.makedirs(user_folder, exist_ok=True)

        filepath = os.path.join(user_folder, filename)
        file.save(filepath)

        # Save metadata
        metadata_file = os.path.join(user_folder, 'metadata.json')
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {}

        metadata[filename] = {
            'upload_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)

    return redirect(url_for('dashboard'))


@app.route('/uploads/<username>/<filename>')
def uploaded_file(username, filename):
    if 'user' not in session or session['user'] != username:
        return redirect(url_for('login'))
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], username), filename)

@app.route('/uploads/<filename>')
def download_file(filename):
    return send_from_directory('uploads', filename, as_attachment=True)

@app.route('/delete/<username>/<filename>', methods=['POST'])
def delete_file(username, filename):
    if 'user' not in session or session['user'] != username:
        return redirect(url_for('login'))

    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
    file_path = os.path.join(user_folder, filename)
    metadata_file = os.path.join(user_folder, 'metadata.json')

    # Delete the file
    if os.path.exists(file_path):
        os.remove(file_path)

    # Remove metadata entry if exists
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)

        if filename in metadata:
            del metadata[filename]
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f)

    return redirect(url_for('dashboard'))


# ===================== Run App =====================

if __name__ == '__main__':
    app.run(debug=True)
