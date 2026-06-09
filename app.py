from flask_mail import Mail, Message
from flask import Flask, render_template, request, send_from_directory, session
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
import hashlib
import qrcode
import os
import json

application = Flask(__name__)
application.secret_key = 'pld2026rahasia'

application.config['MAIL_SERVER'] = 'smtp.gmail.com'
application.config['MAIL_PORT'] = 465
application.config['MAIL_USE_TLS'] = False
application.config['MAIL_USE_SSL'] = True
application.config['MAIL_USERNAME'] = 'aestetoqnoyla@gmail.com'
application.config['MAIL_PASSWORD'] = 'xnqbscmhqvbsmrtk'
application.config['MAIL_DEFAULT_SENDER'] = 'aestetoqnoyla@gmail.com'
application.config['MAIL_TIMEOUT'] = 30

mail = Mail(application)

def buat_sertifikat(nama):
    # 1. Buat sertifikat PNG dengan nama
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

    # 2. Buat PDF
    img = Image.open(path_png)
    lebar, tinggi = img.size
    os.makedirs("pdf", exist_ok=True)
    path_pdf = f"pdf/Sertifikat_PLD_2026_{nama_file}.pdf"

    c = canvas.Canvas(path_pdf, pagesize=(lebar, tinggi))
    c.drawImage(path_png, 0, 0, width=lebar, height=tinggi)
    c.save()

    # 3. Hitung hash
    with open(path_pdf, "rb") as f:
        isi_pdf = f.read()
    hash_pdf = hashlib.sha256(isi_pdf).hexdigest()

    # 4. Buat QR
    os.makedirs("static/qr", exist_ok=True)
    path_qr = f"static/qr/qr_{nama_file}.png"
    qr = qrcode.make(hash_pdf)
    qr.save(path_qr)

    return path_png, path_pdf, hash_pdf, path_qr

def kirim_email(nama, email, path_pdf, hash_pdf, path_qr):
    msg = Message(
        subject='Sertifikat Program Leadership Development 2026',
        sender=application.config['MAIL_USERNAME'],
        recipients=[email]
    )
    msg.html = f"""
    <p>Halo <b>{nama}</b>,</p>
    <p>Terimakasih, telah berpartisipasi dalam Program Leadership Development Malang 2026.</p>
    <p>Berikut terlampir sertifikat anda dalam format PDF.</p>
    <p><b>Hash SHA-256 PDF:</b></p>
    <p style="background:#f4f4f4; padding:10px; font-family:monospace;">{hash_pdf}</p>
    <p><b>QR Code Hash:</b></p>
    <img src="cid:qr_image" width="200" height="200"/>
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

@application.route('/', methods=['GET', 'POST'])
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

        # Simpan hasil ke session untuk dipakai saat kirim email
        session['hasil'] = hasil
        return render_template('response.html', hasil=hasil)

    return render_template('form.html')

@application.route('/kirim', methods=['POST'])
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

@application.route('/pdf/<filename>')
def download_pdf(filename):
    return send_from_directory('pdf', filename, as_attachment=True)

if __name__ == '__main__':
    application.run(debug=True)