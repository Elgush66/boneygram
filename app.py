from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from datetime import datetime
from zoneinfo import ZoneInfo
from flask_mail import Mail, Message
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import mm
from reportlab.lib.styles import getSampleStyleSheet
import os


def generate_receipt(t):
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.pagesizes import mm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib import colors

    file_path = f"receipt_{t.id}.pdf"

    doc = SimpleDocTemplate(
        file_path,
        pagesize=(80*mm, 160*mm),
        rightMargin=10,
        leftMargin=10,
        topMargin=10,
        bottomMargin=10
    )

    styles = getSampleStyleSheet()

    # 🔥 CUSTOM STYLES
    title_style = ParagraphStyle(
        'title',
        parent=styles['Normal'],
        fontSize=14,
        alignment=TA_CENTER,
        spaceAfter=6,
        leading=16
    )

    center_small = ParagraphStyle(
        'center_small',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.grey
    )

    normal = ParagraphStyle(
        'normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4
    )

    bold = ParagraphStyle(
        'bold',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=4
    )

    elements = []

    # =====================
    # HEADER
    # =====================
    elements.append(Paragraph("<b>BoneyGram</b>", title_style))
    elements.append(Paragraph("Receipt", center_small))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("_________________________", center_small))
    elements.append(Spacer(1, 6))

    # =====================
    # SENDER
    # =====================
    elements.append(Paragraph("<b>Sender:</b>", bold))
    elements.append(Paragraph(f"{t.nom}", normal))
    elements.append(Paragraph(f"{t.telephone}", normal))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph("_________________________", center_small))
    elements.append(Spacer(1, 6))

    # =====================
    # RECEIVER
    # =====================
    elements.append(Paragraph("<b>Receiver:</b>", bold))
    elements.append(Paragraph(f"{t.receiver_name}", normal))
    elements.append(Paragraph(f"{t.receiver_phone}", normal))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph("_________________________", center_small))
    elements.append(Spacer(1, 6))

    # =====================
    # AMOUNTS
    # =====================
    elements.append(Paragraph(f"<b>Sent:</b> {t.montant_usd} USD", normal))
    elements.append(Paragraph(f"<b>Received:</b> {round(t.montant_kes)} KES", normal))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph("_________________________", center_small))
    elements.append(Spacer(1, 6))

    # =====================
    # DATE
    # =====================
    date_str = t.date.astimezone(ZoneInfo("Africa/Nairobi")).strftime("%d %b %Y - %H:%M")
    elements.append(Paragraph(date_str, center_small))

    elements.append(Spacer(1, 8))

    # =====================
    # FOOTER
    # =====================
    elements.append(Paragraph("Merci pour votre confiance", center_small))

    doc.build(elements)

    return file_path

app = Flask(__name__)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
app.secret_key = "super_secret_key_123"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

mail = Mail(app)



uri = os.environ.get("DATABASE_URL")

if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()

# DATABASE
class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    nom = db.Column(db.String(100))
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(100))

    montant_usd = db.Column(db.Float)
    montant_kes = db.Column(db.Float)

    receiver_phone = db.Column(db.String(20))
    receiver_name = db.Column(db.String(100))

    statut = db.Column(db.String(20), default="En attente")
    from zoneinfo import ZoneInfo

    date = db.Column(
        db.DateTime,
    default=lambda: datetime.now(ZoneInfo("Africa/Nairobi"))
    )
    # NEW FIELDS 🔥
    fee = db.Column(db.Float)
    vodacom_fee = db.Column(db.Float)
    profit = db.Column(db.Float)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100))
    telephone = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(100))
    password = db.Column(db.String(100))
    user_id = db.Column(db.Integer)    


# HOME
@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        nom = request.form["nom"]
        telephone = request.form["telephone"]
        email = request.form.get("email")

        montant = float(request.form["montant"])
        receiver_phone = request.form["receiver_phone"]
        receiver_name = request.form["receiver_name"]

        # SETTINGS 🔥
        real_rate = 129
        your_rate = 125
        fee_percent = 0.05

        # CALCULATIONS
        fee = montant * fee_percent
        net = montant - fee
        montant_kes = net * your_rate

        if montant_kes < 0:
            montant_kes = 0

        # COST (Vodacom)
        vodacom_fee = montant * 0.035

        # PROFIT
        rate_profit = montant * (real_rate - your_rate) / real_rate
        profit = fee - vodacom_fee + rate_profit

        # =====================
        # SAVE TRANSACTION 🔥 (FIXED)
        # =====================
        transaction = Transaction(
            nom=nom,
            telephone=telephone,
            email=email,
            montant_usd=montant,
            montant_kes=montant_kes,
            receiver_phone=receiver_phone,
            receiver_name=receiver_name,

            # 🔥 IMPORTANT
            statut="En attente",
            user_id=session.get("user_id"),

            fee=fee,
            vodacom_fee=vodacom_fee,
            profit=profit
        )

        db.session.add(transaction)
        db.session.commit()

        # =====================
        # SEND EMAIL 🔥 (UPDATED STYLE)
        # =====================
        subject = "Nouvelle demande - BoneyGram"

        msg = Message(
            subject=subject,
            sender=("BoneyGram", "elgush66@gmail.com"),
            recipients=[
                'gustaveshumbusho17@gmail.com',
                'Kambulubonheur510@gmail.com'
            ]
        )

        msg.html = f"""
        <div style="font-family:Arial;background:#f4f6f9;padding:20px;">
            <div style="max-width:500px;margin:auto;background:white;padding:20px;border-radius:12px;box-shadow:0 5px 20px rgba(0,0,0,0.1);">

                <h2 style="text-align:center;color:#00c853;">
                    Nouvelle demande de transfert
                </h2>

                <hr>

                <p><b>Expéditeur</b></p>
                <p>Nom: {nom}</p>
                <p>Téléphone: {telephone}</p>

                <hr>

                <p><b>Destinataire</b></p>
                <p>Nom: {receiver_name}</p>
                <p>Numéro: {receiver_phone}</p>

                <hr>

                <p><b>Détails</b></p>
                <p>Montant: <b>{montant} USD</b></p>
                <p>Reçoit: <b>{round(montant_kes)} KES</b></p>

                <hr>

                <p style="text-align:center;font-size:12px;color:#777;">
                    BoneyGram
                </p>

            </div>
        </div>
        """

        mail.send(msg)

        # =====================
        # SUCCESS PAGE 🔥
        # =====================
        return render_template(
            "success.html",
            montant=montant,
            receiver_name=receiver_name,
            receiver_phone=receiver_phone
        )

    return render_template("index.html")

        
# ADMIN DASHBOARD
@app.route("/admin")
def admin():
    transactions = Transaction.query.order_by(Transaction.id.desc()).all()

    total_usd = 0
    total_kes = 0
    total_profit = 0

    for t in transactions:
        if t.statut == "Validé":
            total_usd += t.montant_usd
            total_kes += t.montant_kes
            total_profit += t.profit

    return render_template(
        "admin.html",
        transactions=transactions,
        total_usd=round(total_usd, 2),
        total_kes=round(total_kes, 2),
        total_profit=round(total_profit, 2)
    )

    


# APPROVE
@app.route("/approve/<int:id>")
def approve(id):
    t = Transaction.query.get(id)

    if t.statut == "En attente":
        t.statut = "Validé"
        db.session.commit()

        # =====================
        # GENERATE PDF RECEIPT 🔥
        # =====================
        pdf_path = generate_receipt(t)

        now = datetime.now(ZoneInfo("Africa/Nairobi"))
        date = now.strftime("%d %b %Y - %H:%M")
        # =====================
        # RECEIPT HTML
        # =====================
        receipt_html = f"""
        <div style="font-family:monospace;background:#f4f4f4;padding:20px;">
            <div style="max-width:320px;margin:auto;background:white;padding:15px;border-radius:10px;border:1px dashed #ccc;">
                <h3 style="text-align:center;">BoneyGram</h3>
                <p style="text-align:center;font-size:12px;">Receipt</p>

                <hr>

                <p><b>Sender:</b> {t.nom}</p>
                <p>{t.telephone}</p>

                <hr>

                <p><b>Receiver:</b> {t.receiver_name}</p>
                <p>{t.receiver_phone}</p>

                <hr>

                <p><b>Sent:</b> {t.montant_usd} USD</p>
                <p><b>Received:</b> {round(t.montant_kes)} KES</p>

                <hr>

                <p style="font-size:12px;">{date}</p>

                <p style="text-align:center;font-size:12px;">
                    Merci pour votre confiance
                </p>
            </div>
        </div>
        """

        # =====================
        # EMAIL TO USER 📩
        # =====================
    if t.email:
        msg_user = Message(
            subject=f"BoneyGram: Envoi confirmé à {t.receiver_name}",
            sender="BoneyGram <elgush66@gmail.com>",  # ✅ branded sender
            recipients=[t.email],
            reply_to="gustave@guzones.com"  # ✅ replies go to your domain
            )

            # 🔥 TEXT VERSION (VERY IMPORTANT FOR ANTI-SPAM)
        msg_user.body = f"""
            Confirmation de transfert

            Montant envoyé: {round(t.montant_kes)} KES
            Destinataire: {t.receiver_name}

            Merci d’avoir choisi BoneyGram.
            """

            # 🔥 CLEAN HTML (less spammy)
        msg_user.html = f"""
            <div style="font-family:Arial;padding:20px;background:#f4f6f9;">
            <div style="max-width:500px;margin:auto;background:white;padding:20px;border-radius:10px;">

            <h2 style="color:#00c853;margin-bottom:10px;">
                Confirmation de transfert
            </h2>

            <p style="font-size:15px;">
                <b>{round(t.montant_kes)} KES</b> ont été envoyés à 
                <b>{t.receiver_name}</b>.
            </p>

            <p style="color:#555;font-size:14px;">
                Merci d’avoir utilisé BoneyGram.
            </p>

            <hr style="margin:20px 0;">

            {receipt_html}

            </div>
            </div>
            """

            # 📎 ATTACH PDF
    with open(pdf_path, "rb") as f:
        msg_user.attach(
            "recu_boneygram.pdf",
            "application/pdf",
            f.read()
            )

    mail.send(msg_user)

        # =====================
        # EMAIL TO ADMINS 📩
        # =====================
    msg_admin = Message(
            subject="Transaction envoyée - BoneyGram",
            sender=("BoneyGram", "elgush66@gmail.com"),
            recipients=[
                'gustaveshumbusho17@gmail.com',
                'Kambulubonheur510@gmail.com',
                'gustave@guzones.com'
            ]
        )

    msg_admin.html = f"""
        <div style="font-family:Arial;padding:20px;">
            <h3>
            Vous avez envoyé {round(t.montant_kes)} KES à {t.receiver_name}
            </h3>

            {receipt_html}
        </div>
        """

        # attach PDF
    with open(pdf_path, "rb") as f:
            msg_admin.attach(
                "recu_boneygram.pdf",
                "application/pdf",
                f.read()
            )

    mail.send(msg_admin)

    return redirect("/admin")


# REJECT
@app.route("/reject/<int:id>")
def reject(id):
    t = Transaction.query.get(id)
    if t.statut == "En attente":
        t.statut = "Rejeté"
        db.session.commit()
    return redirect("/admin")

from collections import defaultdict
from datetime import datetime, timedelta

@app.route("/transactions")
def transactions():
    if "user_id" not in session:
        return redirect("/login")

    # 🔥 GET USER TRANSACTIONS
    user_transactions = Transaction.query.filter_by(
        user_id=session.get("user_id")
    ).order_by(Transaction.date.desc()).all()

    # 🔥 GROUP BY DATE
    grouped = defaultdict(list)

    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)

    for t in user_transactions:
        tx_date = t.date.date()

        if tx_date == today:
            key = "Aujourd’hui"
        elif tx_date == yesterday:
            key = "Hier"
        else:
            key = t.date.strftime("%d %b %Y")

        grouped[key].append(t)

    return render_template("transactions.html", grouped=grouped)   



@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        telephone = request.form["telephone"]
        password = request.form["password"]

        # CHECK USER IN DATABASE
        user = User.query.filter_by(
            telephone=telephone,
            password=password
        ).first()

        if user:
            # ✅ SAVE USER IN SESSION
            session.permanent = True
            session["user_id"] = user.id
            session["nom"] = user.nom
            session["telephone"] = user.telephone
            session["email"] = user.email

            return redirect("/")  # go to home

        else:
            # 🔥 RETURN LOGIN PAGE WITH ERROR (NO UGLY PAGE)
            return render_template(
                "login.html",
                error="Numéro ou mot de passe incorrect"
            )

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")  

@app.route("/profil")
def profil():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("profil.html")  

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        nom = request.form["nom"]
        telephone = request.form["telephone"]
        email = request.form.get("email")
        password = request.form["password"]

        # CHECK IF USER EXISTS
        existing_user = User.query.filter_by(telephone=telephone).first()

        if existing_user:
            return "Ce numéro est déjà utilisé"

        # CREATE USER
        new_user = User(
            nom=nom,
            telephone=telephone,
            email=email,
            password=password
        )

        db.session.add(new_user)
        db.session.commit()

        # AUTO LOGIN AFTER REGISTER 🔥
        session["user_id"] = new_user.id
        session["nom"] = new_user.nom
        session["telephone"] = new_user.telephone
        session["email"] = new_user.email

        return redirect("/")

    return render_template("register.html") 

from flask import send_file

@app.route("/receipt/<int:id>")
def download_receipt(id):
    t = Transaction.query.get_or_404(id)

    if t.statut != "Validé":
        return "Transaction non validée", 403

    pdf_path = generate_receipt(t)

    return send_file(pdf_path, as_attachment=True) 

@app.route("/transactions_data")
def transactions_data():
    transactions = Transaction.query.order_by(Transaction.date.desc()).all()
    return render_template("partials/_transactions.html", transactions=transactions)              



if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))