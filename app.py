from flask import Flask, render_template, request, send_from_directory, session, redirect, url_for
from flask_mail import Mail, Message
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
import hashlib
import qrcode
import os
import json
from functools import wraps

application = Flask(__name__)
application.secret_key = 'pld2026rahasia'
application.config['SESSION_PERMANENT'] = False

# Kredensial admin
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'pld2026'

# Konfigurasi Gmail SMTP
application.config['MAIL_SERVER'] = 'smtp.gmail.com'
application.config['MAIL_PORT'] = 587
application.config['MAIL_USE_TLS'] = True
application.config['MAIL_USE_SSL'] = False
application.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
application.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
application.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')
application.config['MAIL_TIMEOUT'] = 30

mail = Mail(application)

# File penyimpanan hash
HASH_FILE = 'data/hashes.json'

def simpan_hash(nama, hash_pdf):
    os.makedirs('data', exist_ok=True)
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {}
    data[hash_pdf] = nama
    with open(HASH_FILE, 'w') as f:
        json.dump(data, f)

def cek_hash(hash_pdf):
    if not os.path.exists(HASH_FILE):
        return None
    with open(HASH_FILE, 'r') as f:
        data = json.load(f)
    return data.get(hash_pdf)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            session.clear()
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def buat_sertifikat(nama):
    gambar = Image.open("static/sertif.png")
    draw = ImageDraw.Draw(gambar)
    font = ImageFont.truetype("fonts/ITCEDSCR.TTF", 300)
    bbox = draw.textbbox((0, 0), nama, font=font)
    lebar_teks = bbox[2] - bbox[0]
    x = (gambar.width - lebar_teks) / 2
    y = 850
    draw.text((x, y), nama, fill=(212, 175, 55), font=font)

    nama_file = nama.replace(' ', '_')
    path_png = f"static/sertifikat_{nama_file}.png"
    gambar.save(path_png)

    img = Image.open(path_png)
    lebar, tinggi = img.size
    os.makedirs("pdf", exist_ok=True)
    path_pdf = f"pdf/Sertifikat_PLD_2026_{nama_file}.pdf"

    c = canvas.Canvas(path_pdf, pagesize=(lebar, tinggi))
    c.drawImage(path_png, 0, 0, width=lebar, height=tinggi)
    c.save()

    with open(path_pdf, "rb") as f:
        isi_pdf = f.read()
    hash_pdf = hashlib.sha256(isi_pdf).hexdigest()

    os.makedirs("static/qr", exist_ok=True)
    path_qr = f"static/qr/qr_{nama_file}.png"
    qr = qrcode.make(hash_pdf)
    qr.save(path_qr)

    simpan_hash(nama, hash_pdf)

    return path_png, path_pdf, hash_pdf, path_qr

def kirim_email(nama, email, path_pdf, hash_pdf, path_qr):
    verifikasi_url = os.environ.get('APP_URL', 'http://localhost:5000') + '/verifikasi'
    msg = Message(
        subject='Sertifikat Program Leadership Development 2026',
        sender=application.config['MAIL_USERNAME'],
        recipients=[email]
    )
    msg.html = f"""
    <p>Halo <b>{nama}</b>,</p>
    <p>Terimakasih, telah berpartisipasi dalam Program Leadership Development Malang 2026.</p>
    <p>Berikut terlampir sertifikat anda dalam format PDF.</p>
    <p><b>QR Code Hash:</b></p>
    <img src="cid:qr_image" width="180" height="180"/>
    <p style="margin-top:16px;">Untuk memverifikasi keaslian sertifikat Anda, kunjungi link berikut:<br>
    <a href="{verifikasi_url}">{verifikasi_url}</a></p>
    <p>Upload file PDF sertifikat Anda, sistem akan mengecek keasliannya secara otomatis.</p>
    <p>Salam,<br>Panitia Program Leadership Development 2026</p>
    """
    with open(path_pdf, "rb") as f:
        msg.attach(
            f"Sertifikat_PLD_2026_{nama}.pdf",
            "application/pdf",
            f.read()
        )
    with open(path_qr, "rb") as f:
        msg.attach(
            "qr_hash.png",
            "image/png",
            f.read(),
            headers={"Content-ID": "<qr_image>", "Content-Disposition": "inline"}
        )
    mail.send(msg)

@application.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = 'Username atau password salah!'
    return render_template('login.html', error=error)

@application.route('/logout')
def logout():
    session.clear()
    session.modified = True
    return redirect(url_for('login'))

@application.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        nama_list = request.form.getlist('nama[]')
        email_list = request.form.getlist('email[]')

        hasil = []
        for nama, email in zip(nama_list, email_list):
            nama = nama.strip()
            email = email.strip()
            if nama and email:
                try:
                    path_png, path_pdf, hash_pdf, path_qr = buat_sertifikat(nama)
                    hasil.append({
                        'nama': nama,
                        'email': email,
                        'hash': hash_pdf,
                        'png': f"sertifikat_{nama.replace(' ', '_')}.png",
                        'pdf': f"Sertifikat_PLD_2026_{nama.replace(' ', '_')}.pdf",
                        'qr': f"qr/qr_{nama.replace(' ', '_')}.png"
                    })
                except Exception as e:
                    hasil.append({
                        'nama': nama,
                        'email': email,
                        'hash': f'Error: {str(e)}',
                        'png': None,
                        'pdf': None,
                        'qr': None
                    })

        session['hasil'] = hasil
        return render_template('response.html', hasil=hasil)

    return render_template('form.html')

@application.route('/kirim', methods=['POST'])
@login_required
def kirim():
    hasil = session.get('hasil', [])
    laporan = []

    for p in hasil:
        if p['pdf'] and p['qr']:
            try:
                kirim_email(
                    p['nama'],
                    p['email'],
                    f"pdf/{p['pdf']}",
                    p['hash'],
                    f"static/{p['qr']}"
                )
                laporan.append({**p, 'status': 'Terkirim ✅'})
            except Exception as e:
                laporan.append({**p, 'status': f'Gagal ❌ ({str(e)})'})
        else:
            laporan.append({**p, 'status': 'Gagal ❌ (sertifikat tidak dibuat)'})

    return render_template('response.html', hasil=laporan, sudah_kirim=True)

@application.route('/verifikasi', methods=['GET', 'POST'])
def verifikasi():
    hasil = None
    nama_peserta = None
    if request.method == 'POST':
        file = request.files.get('pdf_file')
        if file:
            isi_pdf = file.read()
            hash_pdf = hashlib.sha256(isi_pdf).hexdigest()
            nama_peserta = cek_hash(hash_pdf)
            if nama_peserta:
                hasil = 'asli'
            else:
                hasil = 'palsu'
    return render_template('verifikasi.html', hasil=hasil, nama=nama_peserta)

@application.route('/pdf/<filename>')
def download_pdf(filename):
    return send_from_directory('pdf', filename, as_attachment=True)

if __name__ == '__main__':
    application.run(debug=True)
