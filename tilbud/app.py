from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, flash)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, uuid, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, date, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = 'ofertes-ad-secret-2024'

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, 'database.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED    = {'png','jpg','jpeg','gif','webp','pdf'}

SMTP_USER       = 'ofertes.ad@gmail.com'
SMTP_PASSWORD   = ''
SMTP_SERVER     = 'smtp.gmail.com'
SMTP_PORT       = 587
ADMIN_EMAIL     = 'ofertes.ad@gmail.com'
SUPERADMIN_USER = 'admin'
SUPERADMIN_PASS = 'ofertesad2024'
STRIPE_PAYMENT_LINK = 'https://buy.stripe.com/your_link_here'
TRIAL_DAYS      = 15
WARNING_DAYS    = 7
BRANCH_PRICE    = 12.0  # euros per extra branch per month

# Pricing tiers
SUPERMARKET_TYPES = {'Supermercat'}
PRICE_INTRO = {
    'Supermercat': 49.0,
    'default':     25.0,
}
PRICE_NORMAL = {
    'Supermercat': 99.0,
    'default':     49.0,
}
INTRO_MONTHS = {
    'Supermercat': 3,
    'default':     1,
}

def get_pricing(category):
    is_premium = (category == 'Supermercat')
    intro  = PRICE_INTRO['Supermercat']  if is_premium else PRICE_INTRO['default']
    normal = PRICE_NORMAL['Supermercat'] if is_premium else PRICE_NORMAL['default']
    months = INTRO_MONTHS['Supermercat'] if is_premium else INTRO_MONTHS['default']
    return intro, normal, months

def get_trial_price(category):
    p = PRICE_TRIAL.get(category, PRICE_TRIAL['default'])
    return p[0], p[1]

def get_normal_price(category):
    return PRICE_NORMAL.get(category, PRICE_NORMAL['default'])

PARROQUIES = [
    'Andorra la Vella','Escaldes-Engordany','Encamp','Sant Julià de Lòria',
    'La Massana','Ordino','Canillo'
]

# Main categories with their subtypes/tags
BUSINESS_CATEGORIES = {
    'Alimentació': [
        'Supermercat',
        'Carnisseria',
        'Verduleria i Fruita',
        'Peixateria',
        'Formatgeria i Gourmet',
        'Granel i Productes Naturals',
        'Vineria',
    ],
    'Restauració': [
        'Restaurant',
        'Bar',
        'Cafeteria',
        'Fleca i Cafeteria',
        'Gelateria',
        'Xocolateria',
    ],
    'Salut i Farmàcia': [
        'Farmàcia',
        'Botiga de Suplements',
    ],
    'Botigues': [
        'Moda i Roba',
        'Calçat',
        'Botiga de Esports',
        'Electrodomèstics i Tecnologia',
        'Joieria i Rellotgeria',
        'Perfumeria i Cosmètica',
        'Llibreria i Papereria',
        'Altres Botigues',
    ],
    'Altres': [
        'Altres',
    ],
}

# Flat list of all subtypes
BUSINESS_TYPES = [sub for subs in BUSINESS_CATEGORIES.values() for sub in subs]

BUSINESS_EMOJIS = {
    'Supermercat':'🏪','Carnisseria':'🥩','Verduleria i Fruita':'🥬',
    'Peixateria':'🐟','Formatgeria i Gourmet':'🧀','Granel i Productes Naturals':'🌿',
    'Vineria':'🍷','Restaurant':'🍽️','Bar':'🍺','Cafeteria':'☕',
    'Fleca i Cafeteria':'🥐','Gelateria':'🍦','Xocolateria':'🍫',
    'Farmàcia':'💊','Botiga de Suplements':'💪',
    'Botiga de Esports':'⚽','Electrodomèstics':'📺',
    'Moda i Roba':'👗','Calçat':'👟','Esports':'⚽',
    'Electrodomèstics i Tecnologia':'📺','Joieria i Rellotgeria':'💍',
    'Perfumeria i Cosmètica':'💄','Llibreria i Papereria':'📚',
    'Altres Botigues':'🛍️','Altres':'🏬'
}

ACCENT_COLORS = {
    'Supermercat':'#52B788','Carnisseria':'#E74C3C','Verduleria i Fruita':'#52B788',
    'Peixateria':'#5DADE2','Formatgeria i Gourmet':'#F0D870','Granel i Productes Naturals':'#52B788',
    'Vineria':'#AF7AC5','Restaurant':'#E74C3C','Bar':'#AF7AC5','Cafeteria':'#F0B27A',
    'Fleca i Cafeteria':'#D4A574','Gelateria':'#5DADE2','Xocolateria':'#D4A574',
    'Farmàcia':'#AF7AC5','Botiga de Suplements':'#52B788',
    'Botiga de Esports':'#52B788','Electrodomèstics':'#5DADE2',
    'Moda i Roba':'#AF7AC5','Calçat':'#E74C3C','Esports':'#52B788',
    'Electrodomèstics i Tecnologia':'#5DADE2','Joieria i Rellotgeria':'#F0D870',
    'Perfumeria i Cosmètica':'#E74C3C','Llibreria i Papereria':'#F0B27A',
    'Altres Botigues':'#888880','Altres':'#888880'
}

os.makedirs(os.path.join(UPLOAD_DIR,'folletos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR,'ofertes'),  exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR,'logos'),    exist_ok=True)

# ── DB ────────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS businesses (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT NOT NULL,
            category            TEXT NOT NULL,
            parroquia           TEXT NOT NULL DEFAULT 'Andorra la Vella',
            logo_emoji          TEXT DEFAULT '🏪',
            logo_image          TEXT DEFAULT '',
            color               TEXT DEFAULT '#2D6A4F',
            accent              TEXT DEFAULT '#52B788',
            description         TEXT DEFAULT '',
            location            TEXT DEFAULT '',
            maps_url            TEXT DEFAULT '',
            phone               TEXT DEFAULT '',
            email               TEXT DEFAULT '',
            hours_mon           TEXT DEFAULT '',
            hours_tue           TEXT DEFAULT '',
            hours_wed           TEXT DEFAULT '',
            hours_thu           TEXT DEFAULT '',
            hours_fri           TEXT DEFAULT '',
            hours_sat           TEXT DEFAULT '',
            hours_sun           TEXT DEFAULT '',
            username            TEXT UNIQUE NOT NULL,
            password            TEXT NOT NULL,
            active              INTEGER DEFAULT 1,
            subscription_status TEXT DEFAULT 'trial',
            subscription_start  TEXT DEFAULT (date('now')),
            subscription_end    TEXT DEFAULT (date('now','+'||15||' days')),
            warning_sent        INTEGER DEFAULT 0,
            created             TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS folletos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            title       TEXT NOT NULL,
            filename    TEXT NOT NULL,
            filetype    TEXT NOT NULL,
            valid_from  TEXT NOT NULL,
            valid_until TEXT NOT NULL,
            views       INTEGER DEFAULT 0,
            created     TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        );

        CREATE TABLE IF NOT EXISTS ofertes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id    INTEGER NOT NULL,
            name           TEXT NOT NULL,
            emoji          TEXT DEFAULT '🛒',
            description    TEXT DEFAULT '',
            original_price REAL NOT NULL,
            offer_price    REAL NOT NULL,
            unit           TEXT DEFAULT '',
            category       TEXT DEFAULT '',
            image          TEXT DEFAULT '',
            valid_from     TEXT NOT NULL,
            valid_until    TEXT NOT NULL,
            featured       INTEGER DEFAULT 0,
            views          INTEGER DEFAULT 0,
            created        TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        );

        CREATE TABLE IF NOT EXISTS page_views (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            viewed_at   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS custom_tags (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            tag      TEXT NOT NULL UNIQUE,
            created  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS business_tags (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            tag         TEXT NOT NULL,
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        );

        CREATE TABLE IF NOT EXISTS branches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id INTEGER NOT NULL,
            name        TEXT NOT NULL DEFAULT 'Sucursal',
            location    TEXT DEFAULT '',
            maps_url    TEXT DEFAULT '',
            phone       TEXT DEFAULT '',
            hours_mon   TEXT DEFAULT '',
            hours_tue   TEXT DEFAULT '',
            hours_wed   TEXT DEFAULT '',
            hours_thu   TEXT DEFAULT '',
            hours_fri   TEXT DEFAULT '',
            hours_sat   TEXT DEFAULT '',
            hours_sun   TEXT DEFAULT '',
            created     TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        );
        """)
        for col, defn in [
            ("warning_sent", "INTEGER DEFAULT 0"),
            ("parroquia", "TEXT NOT NULL DEFAULT 'Andorra la Vella'"),
            ("email", "TEXT DEFAULT ''"),
            ("maps_url", "TEXT DEFAULT ''"),
            ("logo_image", "TEXT DEFAULT ''"),
            ("hours_mon", "TEXT DEFAULT ''"),
            ("hours_tue", "TEXT DEFAULT ''"),
            ("hours_wed", "TEXT DEFAULT ''"),
            ("hours_thu", "TEXT DEFAULT ''"),
            ("hours_fri", "TEXT DEFAULT ''"),
            ("hours_sat", "TEXT DEFAULT ''"),
            ("hours_sun", "TEXT DEFAULT ''"),
        ]:
            try: db.execute(f"ALTER TABLE businesses ADD COLUMN {col} {defn}")
            except Exception: pass
        for col in ["views"]:
            try: db.execute(f"ALTER TABLE ofertes ADD COLUMN {col} INTEGER DEFAULT 0")
            except Exception: pass
            try: db.execute(f"ALTER TABLE folletos ADD COLUMN {col} INTEGER DEFAULT 0")
            except Exception: pass
        try: db.execute("CREATE TABLE IF NOT EXISTS custom_tags (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL, tag TEXT NOT NULL UNIQUE, created TEXT DEFAULT (datetime('now')))")
        except Exception: pass
        try: db.execute("CREATE TABLE IF NOT EXISTS business_tags (id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL, tag TEXT NOT NULL, FOREIGN KEY (business_id) REFERENCES businesses(id))")
        except Exception: pass
        try: db.execute("CREATE TABLE IF NOT EXISTS branches (id INTEGER PRIMARY KEY AUTOINCREMENT, business_id INTEGER NOT NULL, name TEXT NOT NULL DEFAULT 'Sucursal', location TEXT DEFAULT '', maps_url TEXT DEFAULT '', phone TEXT DEFAULT '', hours_mon TEXT DEFAULT '', hours_tue TEXT DEFAULT '', hours_wed TEXT DEFAULT '', hours_thu TEXT DEFAULT '', hours_fri TEXT DEFAULT '', hours_sat TEXT DEFAULT '', hours_sun TEXT DEFAULT '', created TEXT DEFAULT (datetime('now')), FOREIGN KEY (business_id) REFERENCES businesses(id))")
        except Exception: pass
        if not db.execute("SELECT 1 FROM businesses LIMIT 1").fetchone():
            seed_demo(db)

def seed_demo(db):
    today = date.today().isoformat()
    def d(n): return (date.today() + timedelta(days=n)).isoformat()
    businesses = [
        ('Mercat Central','Supermercat','Andorra la Vella','🏪','#2D6A4F','#52B788',
         'El supermercat del centre amb les millors ofertes de productes frescos.',
         'Av. Meritxell 42, Andorra la Vella','https://maps.google.com','+376 800 001','mercat@example.com',
         '9:00-21:00','9:00-21:00','9:00-21:00','9:00-21:00','9:00-21:00','9:00-20:00','Tancat',
         'mercat','mercat123'),
        ('Borda Fresh','Verduleria i Fruita','Encamp','🥬','#6B4226','#D4A574',
         'Productes de temporada directes dels agricultors de les valls.',
         'Carrer Major 8, Encamp','https://maps.google.com','+376 800 002','borda@example.com',
         '8:00-20:00','8:00-20:00','8:00-20:00','8:00-20:00','8:00-20:00','9:00-14:00','Tancat',
         'borda','borda123'),
        ('Gourmet Pirineu','Formatgeria i Gourmet','Escaldes-Engordany','🧀','#1B4F72','#5DADE2',
         'Selecció de productes artesanals i importacions exclusives.',
         'Plaça Coprínceps 3, Escaldes','https://maps.google.com','+376 800 003','gourmet@example.com',
         '10:00-20:00','10:00-20:00','10:00-20:00','10:00-20:00','10:00-20:00','10:00-18:00','Tancat',
         'gourmet','gourmet123'),
        ('Bar El Mirador','Bar','Sant Julià de Lòria','🍺','#4A235A','#AF7AC5',
         'El bar de tota la vida amb tapes i menú del dia.',
         'Carrer de la Sardana 5, Sant Julià','https://maps.google.com','+376 800 004','mirador@example.com',
         '7:00-23:00','7:00-23:00','7:00-23:00','7:00-23:00','7:00-00:00','8:00-00:00','9:00-22:00',
         'mirador','mirador123'),
        ('Carnisseria Ros','Carnisseria','Ordino','🥩','#922B21','#E74C3C',
         'Carn de qualitat superior. Vedella, xai i porc de producció local.',
         'Carrer de la Unió 22, Ordino','https://maps.google.com','+376 800 005','carnros@example.com',
         '8:00-13:30','8:00-13:30','8:00-13:30','8:00-13:30','8:00-13:30','8:00-13:00','Tancat',
         'carnros','carnros123'),
        ('Fleca Andorrana','Fleca i Cafeteria','Sant Julià de Lòria','🥐','#784212','#F0B27A',
         'Pa artesanal de forn de llenya. Pastissos i dolços tradicionals.',
         'Av. del Fener 5, Sant Julià','https://maps.google.com','+376 800 006','fleca@example.com',
         '7:00-20:00','7:00-20:00','7:00-20:00','7:00-20:00','7:00-20:00','7:00-14:00','Tancat',
         'fleca','fleca123'),
        ("Restaurant Ca l'Isidre",'Restaurant','La Massana','🍽️','#1A5276','#5DADE2',
         'Cuina tradicional andorrana amb productes de proximitat.',
         'Carrer Major 15, La Massana','https://maps.google.com','+376 800 007','isidre@example.com',
         'Tancat','13:00-22:00','13:00-22:00','13:00-22:00','13:00-22:00','12:00-22:00','12:00-21:00',
         'isidre','isidre123'),
    ]
    for b in businesses:
        db.execute("""INSERT INTO businesses
            (name,category,parroquia,logo_emoji,color,accent,description,location,maps_url,phone,email,
             hours_mon,hours_tue,hours_wed,hours_thu,hours_fri,hours_sat,hours_sun,
             username,password,subscription_end)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (*b[:19], generate_password_hash(b[19]), d(15)))

    biz = {r['username']:r['id'] for r in db.execute("SELECT id,username FROM businesses").fetchall()}
    ofertes = [
        (biz['mercat'],"Oli d'Oliva Verge Extra 1L",'🫒',8.90,5.99,"l'ampolla",'Alimentació',today,d(5),1),
        (biz['mercat'],'Arròs de gra llarg 1kg','🌾',3.50,1.99,'el paquet','Alimentació',today,d(5),0),
        (biz['mercat'],'Llet sencera 6x1L','🥛',7.20,4.99,'el pack','Lactis',today,d(5),0),
        (biz['mercat'],'Cervesa artesana 6 pack','🍺',9.90,6.49,'el pack','Begudes',today,d(5),1),
        (biz['borda'],'Maduixes de temporada 500g','🍓',4.50,2.49,'la bossa','Fruita',today,d(3),1),
        (biz['borda'],'Tomàquets de penjar 1kg','🍅',3.80,1.99,'el kg','Verdura',today,d(3),0),
        (biz['gourmet'],'Formatge Manchego curat 300g','🧀',11.90,7.99,'la peça','Formatgeria',today,d(7),1),
        (biz['gourmet'],'Vi negre Priorat 75cl','🍷',18.00,11.99,"l'ampolla",'Vins',today,d(7),1),
        (biz['mirador'],'Menú del dia (2 plats + postres)','🍽️',14.00,9.90,'per persona','Menús',today,d(6),1),
        (biz['mirador'],'Tapa de patates braves','🥔',3.50,2.00,'la tapa','Tapes',today,d(6),0),
        (biz['carnros'],'Pit de pollastre 1kg','🍗',9.90,6.49,'el kg','Aviram',today,d(4),1),
        (biz['fleca'],'Pa de pagès 800g','🍞',3.50,2.20,'la peça','Pa',today,d(2),1),
        (biz['fleca'],'Croissant mantequilla x6','🥐',5.40,3.50,'el pack','Pastisseria',today,d(2),0),
        (biz['isidre'],'Menú degustació 5 plats','🍽️',45.00,29.90,'per persona','Menús',today,d(7),1),
    ]
    for o in ofertes:
        db.execute("""INSERT INTO ofertes
            (business_id,name,emoji,original_price,offer_price,unit,category,valid_from,valid_until,featured)
            VALUES (?,?,?,?,?,?,?,?,?,?)""", o)

    # Sample folletos for demo
    db.execute("""INSERT INTO folletos (business_id,title,filename,filetype,valid_from,valid_until)
        VALUES (?,?,?,?,?,?)""",(
        biz['mercat'], "Ofertes setmana del 26 de maig al 1 de juny",
        "sample_folleto.jpg", "image", today, d(7)))
    db.execute("""INSERT INTO folletos (business_id,title,filename,filetype,valid_from,valid_until)
        VALUES (?,?,?,?,?,?)""",(
        biz['borda'], "Fruites i verdures de temporada",
        "sample_folleto2.jpg", "image", today, d(5)))

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────
def allowed_file(f): return '.' in f and f.rsplit('.',1)[1].lower() in ALLOWED
def save_file(file, sub):
    ext = file.filename.rsplit('.',1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_DIR, sub, fname))
    return fname
def today_str(): return date.today().isoformat()
def can_publish(b): return b['active'] and b['subscription_end'] >= today_str()
def days_left(b): return (datetime.strptime(b['subscription_end'],'%Y-%m-%d').date()-date.today()).days

def send_email(to, subject, html):
    pwd = os.environ.get('EMAIL_PASSWORD', SMTP_PASSWORD)
    if not pwd: print(f"[EMAIL] {to}: {subject}"); return False
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject; msg['From'] = SMTP_USER; msg['To'] = to
        msg.attach(MIMEText(html,'html'))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
            s.starttls(); s.login(SMTP_USER, pwd); s.sendmail(SMTP_USER, to, msg.as_string())
        return True
    except Exception as e: print(f"[EMAIL ERR] {e}"); return False

def check_subscriptions():
    try:
        db = get_db(); today = today_str()
        warn_date = (date.today()+timedelta(days=WARNING_DAYS)).isoformat()
        for b in db.execute("SELECT * FROM businesses WHERE active=1 AND warning_sent=0 AND subscription_end<=?", (warn_date,)).fetchall():
            dl = days_left(b)
            send_email(b['email'] or ADMIN_EMAIL,
                f"⚠️ La teva subscripció a Ofertes.ad venç en {dl} dies",
                f"""<div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:32px;background:#0F0F0F;color:#F0EDE8">
                <h2 style="color:#E8C547">Ofertes.ad</h2>
                <p>Hola <strong>{b['name']}</strong>,</p>
                <p>La teva subscripció venç el <strong>{b['subscription_end']}</strong> ({dl} dies restants).</p>
                <p>Per renovar: <a href="mailto:{ADMIN_EMAIL}" style="color:#E8C547">{ADMIN_EMAIL}</a></p>
                </div>""")
            db.execute("UPDATE businesses SET warning_sent=1 WHERE id=?", (b['id'],))
        db.commit()
    except Exception as e:
        print(f"[SUBSCRIPTIONS] {e}")

def login_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if 'business_id' not in session: return redirect(url_for('login'))
        return f(*a,**kw)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a,**kw):
        if not session.get('is_admin'): return redirect(url_for('admin_login'))
        return f(*a,**kw)
    return dec

def get_biz_tags(business_id):
    rows = get_db().execute("SELECT tag FROM business_tags WHERE business_id=?", (business_id,)).fetchall()
    return [r['tag'] for r in rows]

def set_biz_tags(db, business_id, tags):
    db.execute("DELETE FROM business_tags WHERE business_id=?", (business_id,))
    for tag in tags:
        if tag.strip():
            db.execute("INSERT INTO business_tags (business_id, tag) VALUES (?,?)", (business_id, tag.strip()))

def get_biz(): return get_db().execute("SELECT * FROM businesses WHERE id=?",(session['business_id'],)).fetchone()

# ── Public ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    check_subscriptions()
    db = get_db(); today = today_str()
    businesses = db.execute("SELECT * FROM businesses WHERE active=1 AND subscription_end>=? ORDER BY name",(today,)).fetchall()
    featured = db.execute("""SELECT o.*,b.name as bname,b.logo_emoji as blogo,b.id as bid
        FROM ofertes o JOIN businesses b ON o.business_id=b.id
        WHERE o.featured=1 AND o.valid_from<=? AND o.valid_until>=?
        AND b.active=1 AND b.subscription_end>=? ORDER BY o.created DESC LIMIT 12""",(today,today,today)).fetchall()
    stats = {
        'businesses': db.execute("SELECT COUNT(*) FROM businesses WHERE active=1").fetchone()[0],
        'ofertes': db.execute("SELECT COUNT(*) FROM ofertes WHERE valid_until>=?",(today,)).fetchone()[0],
        'catalogues': db.execute("SELECT COUNT(*) FROM folletos WHERE valid_until>=?",(today,)).fetchone()[0],
    }
    # Get businesses with active folletos
    folleto_biz = db.execute("""SELECT DISTINCT b.*, f.filename as folleto_file, f.filetype as folleto_type, f.title as folleto_title
        FROM businesses b JOIN folletos f ON b.id=f.business_id
        WHERE b.active=1 AND b.subscription_end>=?
        AND f.valid_from<=? AND f.valid_until>=?
        ORDER BY f.created DESC""", (today,today,today)).fetchall()
    return render_template('index.html', businesses=businesses, featured=featured,
                           parroquies=PARROQUIES, stats=stats,
                           business_categories=BUSINESS_CATEGORIES, business_types=BUSINESS_TYPES,
                           folleto_biz=folleto_biz)

@app.route('/parroquia/<parroquia>')
def parroquia(parroquia):
    db = get_db(); today = today_str()
    businesses = db.execute("SELECT * FROM businesses WHERE active=1 AND subscription_end>=? AND parroquia=? ORDER BY name",(today,parroquia)).fetchall()
    return render_template('parroquia.html', businesses=businesses, parroquia=parroquia, parroquies=PARROQUIES)

@app.route('/negoci/<int:bid>')
def business(bid):
    db = get_db(); today = today_str()
    b = db.execute("SELECT * FROM businesses WHERE id=? AND active=1",(bid,)).fetchone()
    if not b: return redirect(url_for('index'))
    # track view
    db.execute("INSERT INTO page_views (business_id) VALUES (?)",(bid,)); db.commit()
    sub_ok = b['subscription_end'] >= today
    ofertes = folletos = []
    if sub_ok:
        ofertes = db.execute("SELECT * FROM ofertes WHERE business_id=? AND valid_from<=? AND valid_until>=? ORDER BY featured DESC,created DESC",(bid,today,today)).fetchall()
        folletos = db.execute("SELECT * FROM folletos WHERE business_id=? AND valid_from<=? AND valid_until>=? ORDER BY created DESC",(bid,today,today)).fetchall()
        # track offer views
        for o in ofertes: db.execute("UPDATE ofertes SET views=views+1 WHERE id=?",(o['id'],))
        for f in folletos: db.execute("UPDATE folletos SET views=views+1 WHERE id=?",(f['id'],))
        db.commit()
    categories = sorted(set(o['category'] for o in ofertes if o['category']))
    all_biz = db.execute("SELECT * FROM businesses WHERE active=1 AND subscription_end>=? ORDER BY name",(today,)).fetchall()
    return render_template('business.html', b=b, ofertes=ofertes, folletos=folletos,
                           categories=categories, all_businesses=all_biz, sub_active=sub_ok)

@app.route('/sobre-nosaltres')
def sobre():
    db = get_db(); today = today_str()
    stats = {
        'businesses': db.execute("SELECT COUNT(*) FROM businesses WHERE active=1").fetchone()[0],
        'ofertes': db.execute("SELECT COUNT(*) FROM ofertes WHERE valid_until>=?",(today,)).fetchone()[0],
        'parroquies': len(PARROQUIES),
    }
    return render_template('sobre.html', business_types=BUSINESS_TYPES, business_categories=BUSINESS_CATEGORIES, stats=stats)

@app.route('/api/search')
def api_search():
    q = request.args.get('q','').lower().strip()
    if not q: return jsonify([])
    today = today_str()
    rows = get_db().execute("""SELECT o.*,b.name as bname,b.logo_emoji as blogo,b.id as bid
        FROM ofertes o JOIN businesses b ON o.business_id=b.id
        WHERE (LOWER(o.name) LIKE ? OR LOWER(o.category) LIKE ?)
        AND o.valid_from<=? AND o.valid_until>=? AND b.active=1 AND b.subscription_end>=?
        LIMIT 12""",(f'%{q}%',f'%{q}%',today,today,today)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/ofertes')
def api_ofertes():
    today    = today_str()
    bid      = request.args.get('business_id', type=int)
    cat      = request.args.get('cat', '')
    par      = request.args.get('parroquia', '')
    biz_type = request.args.get('biz_type', '')
    main_cat = request.args.get('main_cat', '')

    sql = """SELECT DISTINCT o.*,b.name as bname,b.logo_emoji as blogo,b.id as bid,b.parroquia as bparroquia,b.category as bcategory
             FROM ofertes o JOIN businesses b ON o.business_id=b.id
             WHERE o.valid_from<=? AND o.valid_until>=? AND b.active=1 AND b.subscription_end>=?"""
    p = [today, today, today]
    if bid: sql += " AND o.business_id=?"; p.append(bid)
    if cat: sql += " AND o.category=?";    p.append(cat)
    if par: sql += " AND b.parroquia=?";   p.append(par)
    if biz_type:
        biz_ids = [r[0] for r in get_db().execute(
            "SELECT id FROM businesses WHERE category=? UNION SELECT business_id FROM business_tags WHERE tag=?",
            (biz_type, biz_type)).fetchall()]
        if not biz_ids: return jsonify([])
        ph = ','.join('?'*len(biz_ids))
        sql += f" AND b.id IN ({ph})"; p.extend(biz_ids)
    elif main_cat:
        subtypes = BUSINESS_CATEGORIES.get(main_cat, [])
        if not subtypes: return jsonify([])
        ph2 = ','.join('?'*len(subtypes))
        biz_ids = [r[0] for r in get_db().execute(
            f"SELECT id FROM businesses WHERE category IN ({ph2}) UNION SELECT business_id FROM business_tags WHERE tag IN ({ph2})",
            subtypes + subtypes).fetchall()]
        if not biz_ids: return jsonify([])
        ph = ','.join('?'*len(biz_ids))
        sql += f" AND b.id IN ({ph})"; p.extend(biz_ids)
    sql += " ORDER BY o.featured DESC, o.created DESC"
    rows = get_db().execute(sql, p).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d['is_new']    = r['created']     >= (date.today()-timedelta(days=3)).isoformat()
        d['is_today']  = r['valid_from']  <= today <= r['valid_until']
        d['is_ending'] = r['valid_until'] <= (date.today()+timedelta(days=2)).isoformat()
        d['is_week']   = r['valid_until'] <= (date.today()+timedelta(days=7)).isoformat()
        result.append(d)
    return jsonify(result)


@app.route('/api/businesses')
def api_businesses():
    today = today_str()
    par      = request.args.get('parroquia','')
    biz_type = request.args.get('biz_type','')
    main_cat = request.args.get('main_cat','')
    db = get_db()
    base = "SELECT DISTINCT b.* FROM businesses b LEFT JOIN business_tags bt ON b.id=bt.business_id WHERE b.active=1 AND b.subscription_end>=?"
    p = [today]
    if biz_type:
        sql = base + " AND (b.category=? OR bt.tag=?)"
        p += [biz_type, biz_type]
    elif main_cat:
        subtypes = BUSINESS_CATEGORIES.get(main_cat, [])
        if not subtypes: return jsonify([])
        ph = ','.join('?'*len(subtypes))
        sql = base + f" AND (b.category IN ({ph}) OR bt.tag IN ({ph}))"
        p += subtypes + subtypes
    else:
        sql = "SELECT * FROM businesses WHERE active=1 AND subscription_end>=?"
    if par:
        if 'DISTINCT' in sql: sql += " AND b.parroquia=?"
        else: sql += " AND parroquia=?"
        p.append(par)
    if 'DISTINCT' in sql: sql += " ORDER BY b.name"
    else: sql += " ORDER BY name"
    return jsonify([dict(r) for r in db.execute(sql, p).fetchall()])

# ── Auth ──────────────────────────────────────────────────────────────────────
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        b = get_db().execute("SELECT * FROM businesses WHERE username=? AND active=1",(request.form['username'].strip(),)).fetchone()
        if b and check_password_hash(b['password'],request.form['password']):
            session['business_id'] = b['id']; session['business_name'] = b['name']
            return redirect(url_for('panel'))
        flash('Usuari o contrasenya incorrectes')
    return render_template('login.html')

@app.route('/logout')
def logout(): session.clear(); return redirect(url_for('index'))

@app.route('/registre', methods=['GET','POST'])
def registre():
    if request.method == 'POST':
        f = request.form; username = f['username'].strip().lower()
        db = get_db()
        if db.execute("SELECT 1 FROM businesses WHERE username=?",(username,)).fetchone():
            flash("Aquest nom d'usuari ja existeix"); return render_template('registre.html', business_types=BUSINESS_TYPES, business_categories=BUSINESS_CATEGORIES, parroquies=PARROQUIES, form=f)
        if f['password'] != f['password2']:
            flash("Les contrasenyes no coincideixen"); return render_template('registre.html', business_types=BUSINESS_TYPES, business_categories=BUSINESS_CATEGORIES, parroquies=PARROQUIES, form=f)
        logo_image = ''
        if 'logo' in request.files and request.files['logo'].filename:
            lf = request.files['logo']
            if allowed_file(lf.filename): logo_image = save_file(lf,'logos')
        cat = f['category']
        db.execute("""INSERT INTO businesses
            (name,category,parroquia,logo_emoji,logo_image,color,accent,description,
             location,maps_url,phone,email,
             hours_mon,hours_tue,hours_wed,hours_thu,hours_fri,hours_sat,hours_sun,
             username,password,subscription_end)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            f['name'], cat, f['parroquia'],
            BUSINESS_EMOJIS.get(cat,'🏬'), logo_image,
            '#1C1C1C', ACCENT_COLORS.get(cat,'#52B788'),
            f.get('description',''), f.get('location',''), f.get('maps_url',''),
            f.get('phone',''), f.get('email',''),
            f.get('h_mon',''), f.get('h_tue',''), f.get('h_wed',''),
            f.get('h_thu',''), f.get('h_fri',''), f.get('h_sat',''), f.get('h_sun',''),
            username, generate_password_hash(f['password']),
            (date.today()+timedelta(days=TRIAL_DAYS)).isoformat()
        ))
        db.commit()
        b = db.execute("SELECT * FROM businesses WHERE username=?",(username,)).fetchone()
        session['business_id'] = b['id']; session['business_name'] = b['name']
        # welcome email
        send_email(f.get('email',''), f"Benvingut/da a Ofertes.ad, {f['name']}!",
            f"""<div style="font-family:sans-serif;max-width:520px;margin:0 auto;padding:32px;background:#0F0F0F;color:#F0EDE8">
            <h2 style="color:#E8C547">Benvingut/da a Ofertes.ad!</h2>
            <p>Hola <strong>{f['name']}</strong>, el teu compte ha estat creat correctament.</p>
            <p>Tens <strong>{TRIAL_DAYS} dies de prova gratuïts</strong> per publicar les teves ofertes i folletos.</p>
            <p>Accedeix al teu panel: <a href="https://ofertes-ad.onrender.com/panel" style="color:#E8C547">ofertes-ad.onrender.com/panel</a></p>
            <p style="font-size:12px;color:#888">Ofertes.ad · ofertes.ad@gmail.com</p></div>""")
        # Notify admin of new registration
        admin_html = (
            "<div style='font-family:sans-serif;max-width:520px;margin:0 auto;padding:32px;background:#0F0F0F;color:#F0EDE8'>"
            "<h2 style='color:#E8C547'>Nou comercio registrat a Ofertes.ad</h2>"
            f"<p><strong>Nom:</strong> {f['name']}</p>"
            f"<p><strong>Categoria:</strong> {cat}</p>"
            f"<p><strong>Parroquia:</strong> {f['parroquia']}</p>"
            f"<p><strong>Email:</strong> {f.get('email','no informat')}</p>"
            f"<p><strong>Telefon:</strong> {f.get('phone','no informat')}</p>"
            f"<p><strong>Usuari:</strong> {username}</p>"
            f"<p><strong>Subscripcio fins:</strong> {(date.today()+timedelta(days=TRIAL_DAYS)).isoformat()}</p>"
            "<hr style='border-color:#333;margin:20px 0'>"
            "<p><a href='https://ofertes-ad.onrender.com/admin' style='color:#E8C547'>Accedir al panel admin</a></p>"
            "<p style='font-size:12px;color:#888'>Ofertes.ad</p>"
            "</div>"
        )
        send_email(ADMIN_EMAIL, f"Nou comercio: {f['name']} ({cat})", admin_html)
        flash(f'Benvingut/da! Tens {TRIAL_DAYS} dies de prova gratuits.')
        return redirect(url_for('panel'))
    return render_template('registre.html', business_types=BUSINESS_TYPES, business_categories=BUSINESS_CATEGORIES, parroquies=PARROQUIES, form={})

# ── Panel ─────────────────────────────────────────────────────────────────────
@app.route('/panel')
@login_required
def panel():
    b = get_biz(); today = today_str(); db = get_db()
    ofertes  = db.execute("SELECT * FROM ofertes WHERE business_id=? AND valid_from<=? AND valid_until>=? ORDER BY featured DESC,created DESC",(b['id'],today,today)).fetchall()
    folletos = db.execute("SELECT * FROM folletos WHERE business_id=? AND valid_from<=? AND valid_until>=? ORDER BY created DESC",(b['id'],today,today)).fetchall()
    # stats
    total_views   = db.execute("SELECT COUNT(*) FROM page_views WHERE business_id=?",(b['id'],)).fetchone()[0]
    views_7d      = db.execute("SELECT COUNT(*) FROM page_views WHERE business_id=? AND viewed_at>=datetime('now','-7 days')",(b['id'],)).fetchone()[0]
    total_o_views = db.execute("SELECT COALESCE(SUM(views),0) FROM ofertes WHERE business_id=?",(b['id'],)).fetchone()[0]
    branches = db.execute("SELECT * FROM branches WHERE business_id=? ORDER BY created",(b['id'],)).fetchall()
    branch_count = len(branches)
    trial_price, normal_price, trial_months = get_pricing(b['category'])
    monthly_total = normal_price + (branch_count * BRANCH_PRICE)
    dl = days_left(b); can_pub = can_publish(b)
    return render_template('panel.html', b=b, ofertes=ofertes, folletos=folletos,
                           days_left=dl, can_pub=can_pub,
                           total_views=total_views, views_7d=views_7d, total_o_views=total_o_views,
                           branches=branches, branch_count=branch_count, monthly_total=monthly_total,
                           trial_price=trial_price, normal_price=normal_price)

@app.route('/panel/perfil', methods=['GET','POST'])
@login_required
def editar_perfil():
    b = get_biz()
    if request.method == 'POST':
        f = request.form; db = get_db()
        logo_image = b['logo_image']
        if 'logo' in request.files and request.files['logo'].filename:
            lf = request.files['logo']
            if allowed_file(lf.filename): logo_image = save_file(lf,'logos')
        cat = f.get('category', b['category'])
        db.execute("""UPDATE businesses SET name=?,category=?,parroquia=?,logo_emoji=?,logo_image=?,
            description=?,location=?,maps_url=?,phone=?,email=?,
            hours_mon=?,hours_tue=?,hours_wed=?,hours_thu=?,hours_fri=?,hours_sat=?,hours_sun=?
            WHERE id=?""", (
            f['name'], cat, f['parroquia'], BUSINESS_EMOJIS.get(cat,b['logo_emoji']), logo_image,
            f.get('description',''), f.get('location',''), f.get('maps_url',''),
            f.get('phone',''), f.get('email',''),
            f.get('h_mon',''), f.get('h_tue',''), f.get('h_wed',''),
            f.get('h_thu',''), f.get('h_fri',''), f.get('h_sat',''), f.get('h_sun',''), b['id']
        ))
        db.commit(); session['business_name'] = f['name']
        flash('Perfil actualitzat!'); return redirect(url_for('panel'))
    return render_template('perfil.html', b=b, business_types=BUSINESS_TYPES, parroquies=PARROQUIES)

@app.route('/panel/oferta/nova', methods=['GET','POST'])
@login_required
def nova_oferta():
    b = get_biz()
    if not can_publish(b): flash('La teva subscripció ha vençut.'); return redirect(url_for('panel'))
    if request.method == 'POST':
        f = request.form; image = ''
        if 'image' in request.files and request.files['image'].filename:
            img = request.files['image']
            if allowed_file(img.filename): image = save_file(img,'ofertes')
        db = get_db()
        db.execute("""INSERT INTO ofertes (business_id,name,emoji,description,original_price,offer_price,unit,category,image,valid_from,valid_until,featured)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
            b['id'],f['name'],f.get('emoji','🛒'),f.get('description',''),
            float(f['original_price']),float(f['offer_price']),
            f.get('unit',''),f.get('category',''),image,
            f['valid_from'],f['valid_until'],1 if f.get('featured') else 0))
        db.commit(); flash('Oferta publicada!'); return redirect(url_for('panel'))
    return render_template('form_oferta.html', oferta=None)

@app.route('/panel/oferta/editar/<int:oid>', methods=['GET','POST'])
@login_required
def editar_oferta(oid):
    b = get_biz()
    if not can_publish(b): flash('La teva subscripció ha vençut.'); return redirect(url_for('panel'))
    db = get_db(); o = db.execute("SELECT * FROM ofertes WHERE id=? AND business_id=?",(oid,b['id'])).fetchone()
    if not o: return redirect(url_for('panel'))
    if request.method == 'POST':
        f = request.form; image = o['image']
        if 'image' in request.files and request.files['image'].filename:
            img = request.files['image']
            if allowed_file(img.filename): image = save_file(img,'ofertes')
        db.execute("""UPDATE ofertes SET name=?,emoji=?,description=?,original_price=?,offer_price=?,
            unit=?,category=?,image=?,valid_from=?,valid_until=?,featured=? WHERE id=? AND business_id=?""", (
            f['name'],f.get('emoji','🛒'),f.get('description',''),
            float(f['original_price']),float(f['offer_price']),
            f.get('unit',''),f.get('category',''),image,
            f['valid_from'],f['valid_until'],1 if f.get('featured') else 0,oid,b['id']))
        db.commit(); flash('Oferta actualitzada!'); return redirect(url_for('panel'))
    return render_template('form_oferta.html', oferta=o)

@app.route('/panel/oferta/eliminar/<int:oid>', methods=['POST'])
@login_required
def eliminar_oferta(oid):
    db = get_db(); db.execute("DELETE FROM ofertes WHERE id=? AND business_id=?",(oid,session['business_id'])); db.commit()
    flash('Oferta eliminada.'); return redirect(url_for('panel'))

@app.route('/panel/folleto/nou', methods=['GET','POST'])
@login_required
def nou_folleto():
    b = get_biz()
    if not can_publish(b): flash('La teva subscripció ha vençut.'); return redirect(url_for('panel'))
    if request.method == 'POST':
        f = request.form
        if 'file' not in request.files or not request.files['file'].filename:
            flash('Cal seleccionar un arxiu'); return redirect(request.url)
        fil = request.files['file']
        if not allowed_file(fil.filename): flash('Format no permès.'); return redirect(request.url)
        ext = fil.filename.rsplit('.',1)[1].lower()
        filename = save_file(fil,'folletos')
        db = get_db()
        db.execute("INSERT INTO folletos (business_id,title,filename,filetype,valid_from,valid_until) VALUES (?,?,?,?,?,?)",
            (b['id'],f['title'],filename,'pdf' if ext=='pdf' else 'image',f['valid_from'],f['valid_until']))
        db.commit(); flash('Folleto publicat!'); return redirect(url_for('panel'))
    return render_template('form_folleto.html', folleto=None)

@app.route('/panel/folleto/editar/<int:fid>', methods=['GET','POST'])
@login_required
def editar_folleto(fid):
    b = get_biz()
    if not can_publish(b): flash('La teva subscripció ha vençut.'); return redirect(url_for('panel'))
    db = get_db(); fl = db.execute("SELECT * FROM folletos WHERE id=? AND business_id=?",(fid,b['id'])).fetchone()
    if not fl: return redirect(url_for('panel'))
    if request.method == 'POST':
        frm = request.form; filename = fl['filename']; filetype = fl['filetype']
        if 'file' in request.files and request.files['file'].filename:
            fil = request.files['file']
            if allowed_file(fil.filename):
                try: os.remove(os.path.join(UPLOAD_DIR,'folletos',filename))
                except: pass
                ext = fil.filename.rsplit('.',1)[1].lower()
                filetype = 'pdf' if ext=='pdf' else 'image'
                filename = save_file(fil,'folletos')
        db.execute("UPDATE folletos SET title=?,filename=?,filetype=?,valid_from=?,valid_until=? WHERE id=? AND business_id=?",
            (frm['title'],filename,filetype,frm['valid_from'],frm['valid_until'],fid,b['id']))
        db.commit(); flash('Folleto actualitzat!'); return redirect(url_for('panel'))
    return render_template('form_folleto.html', folleto=fl)

@app.route('/panel/folleto/eliminar/<int:fid>', methods=['POST'])
@login_required
def eliminar_folleto(fid):
    db = get_db(); row = db.execute("SELECT * FROM folletos WHERE id=? AND business_id=?",(fid,session['business_id'])).fetchone()
    if row:
        try: os.remove(os.path.join(UPLOAD_DIR,'folletos',row['filename']))
        except: pass
        db.execute("DELETE FROM folletos WHERE id=?",(fid,)); db.commit()
    flash('Folleto eliminat.'); return redirect(url_for('panel'))


@app.route('/api/tags/<category>')
def api_tags(category):
    from app import BUSINESS_CATEGORIES
    predefined = BUSINESS_CATEGORIES.get(category, [])
    custom = [r['tag'] for r in get_db().execute(
        "SELECT tag FROM custom_tags WHERE category=? ORDER BY tag", (category,)).fetchall()]
    # merge, remove duplicates
    all_tags = predefined + [t for t in custom if t not in predefined]
    return jsonify(all_tags)

@app.route('/api/tags/add', methods=['POST'])
def api_add_tag():
    data = request.get_json()
    category = data.get('category','').strip()
    tag = data.get('tag','').strip()
    if not category or not tag or len(tag) > 50:
        return jsonify({'ok': False})
    try:
        db = get_db()
        db.execute("INSERT OR IGNORE INTO custom_tags (category, tag) VALUES (?,?)", (category, tag))
        db.commit()
    except Exception as e:
        print(f'[TAG ADD ERROR] {e}')
    return jsonify({'ok': True, 'tag': tag})

@app.route('/cataleg')
def cataleg():
    db = get_db(); today = today_str()
    # Get latest folleto per business
    folletos = db.execute("""SELECT f.*, b.name as bname, b.logo_emoji as blogo, b.logo_image as blogo_img,
               b.id as bid, b.accent as baccent, b.parroquia as bparroquia
        FROM folletos f JOIN businesses b ON f.business_id=b.id
        WHERE b.active=1 AND b.subscription_end>=?
        AND f.valid_from<=? AND f.valid_until>=?
        ORDER BY f.created DESC""", (today,today,today)).fetchall()
    parroquies_with = sorted(set(f['bparroquia'] for f in folletos))
    return render_template('cataleg.html', folletos=folletos,
                           parroquies=PARROQUIES,
                           parroquies_with=parroquies_with)

@app.route('/cataleg/<int:fid>')
def cataleg_detail(fid):
    db = get_db(); today = today_str()
    f = db.execute("""SELECT f.*, b.name as bname, b.logo_emoji as blogo, b.logo_image as blogo_img,
               b.id as bid, b.accent as baccent
        FROM folletos f JOIN businesses b ON f.business_id=b.id
        WHERE f.id=? AND b.active=1 AND b.subscription_end>=?
        AND f.valid_from<=? AND f.valid_until>=?""", (fid,today,today,today)).fetchone()
    if not f: return redirect(url_for('cataleg'))
    # Get other folletos from same business
    others = db.execute("""SELECT * FROM folletos WHERE business_id=? AND id!=?
        AND valid_from<=? AND valid_until>=? ORDER BY created DESC LIMIT 4""", (f['bid'],fid,today,today)).fetchall()
    return render_template('cataleg_detail.html', f=f, others=others)

# ── Branches ──────────────────────────────────────────────────────────────────
@app.route('/panel/sucursal/nova', methods=['GET','POST'])
@login_required
def nova_sucursal():
    b = get_biz()
    if not can_publish(b): flash('La teva subscripció ha vençut.'); return redirect(url_for('panel'))
    if request.method == 'POST':
        f = request.form
        db = get_db()
        db.execute("""INSERT INTO branches (business_id,name,location,maps_url,phone,
            hours_mon,hours_tue,hours_wed,hours_thu,hours_fri,hours_sat,hours_sun)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
            b['id'], f.get('name','Sucursal'), f.get('location',''), f.get('maps_url',''),
            f.get('phone',''), f.get('h_mon',''), f.get('h_tue',''), f.get('h_wed',''),
            f.get('h_thu',''), f.get('h_fri',''), f.get('h_sat',''), f.get('h_sun','')))
        db.commit()
        flash(f"Sucursal afegida! (+{BRANCH_PRICE:.0f}€/mes a la teva subscripció)")
        return redirect(url_for('panel'))
    return render_template('form_sucursal.html', sucursal=None)

@app.route('/panel/sucursal/editar/<int:sid>', methods=['GET','POST'])
@login_required
def editar_sucursal(sid):
    b = get_biz()
    db = get_db()
    s = db.execute("SELECT * FROM branches WHERE id=? AND business_id=?",(sid,b['id'])).fetchone()
    if not s: return redirect(url_for('panel'))
    if request.method == 'POST':
        f = request.form
        db.execute("""UPDATE branches SET name=?,location=?,maps_url=?,phone=?,
            hours_mon=?,hours_tue=?,hours_wed=?,hours_thu=?,hours_fri=?,hours_sat=?,hours_sun=?
            WHERE id=? AND business_id=?""", (
            f.get('name','Sucursal'), f.get('location',''), f.get('maps_url',''), f.get('phone',''),
            f.get('h_mon',''), f.get('h_tue',''), f.get('h_wed',''),
            f.get('h_thu',''), f.get('h_fri',''), f.get('h_sat',''), f.get('h_sun',''),
            sid, b['id']))
        db.commit()
        flash('Sucursal actualitzada!')
        return redirect(url_for('panel'))
    return render_template('form_sucursal.html', sucursal=s)

@app.route('/panel/sucursal/eliminar/<int:sid>', methods=['POST'])
@login_required
def eliminar_sucursal(sid):
    db = get_db()
    db.execute("DELETE FROM branches WHERE id=? AND business_id=?",(sid,session['business_id']))
    db.commit()
    flash('Sucursal eliminada.')
    return redirect(url_for('panel'))

# ── Superadmin ────────────────────────────────────────────────────────────────
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['username']==SUPERADMIN_USER and request.form['password']==SUPERADMIN_PASS:
            session['is_admin']=True; return redirect(url_for('admin_panel'))
        flash('Credencials incorrectes')
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout(): session.pop('is_admin',None); return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin_panel():
    today = today_str(); db = get_db()
    businesses = db.execute("""SELECT b.*,
        (SELECT COUNT(*) FROM ofertes WHERE business_id=b.id AND valid_until>=?) as oferta_count,
        (SELECT COUNT(*) FROM folletos WHERE business_id=b.id AND valid_until>=?) as folleto_count,
        (SELECT COUNT(*) FROM page_views WHERE business_id=b.id) as total_views
        FROM businesses b ORDER BY b.created DESC""",(today,today)).fetchall()
    stats = {
        'total': len(businesses),
        'active': sum(1 for b in businesses if b['active'] and b['subscription_end']>=today),
        'expired': sum(1 for b in businesses if b['subscription_end']<today),
    }
    return render_template('admin_panel.html', businesses=businesses, today=today, stats=stats)

@app.route('/admin/toggle/<int:bid>', methods=['POST'])
@admin_required
def admin_toggle(bid):
    db = get_db(); b = db.execute("SELECT active FROM businesses WHERE id=?",(bid,)).fetchone()
    db.execute("UPDATE businesses SET active=? WHERE id=?",(0 if b['active'] else 1,bid)); db.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/renovar/<int:bid>', methods=['POST'])
@admin_required
def admin_renovar(bid):
    db = get_db(); new_end = (date.today()+timedelta(days=30)).isoformat()
    db.execute("UPDATE businesses SET subscription_end=?,subscription_status='active',warning_sent=0 WHERE id=?",(new_end,bid))
    db.commit(); flash(f'Subscripció renovada fins {new_end}.'); return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
