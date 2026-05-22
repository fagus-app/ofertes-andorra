from flask import (Flask, render_template, request, jsonify,
                   redirect, url_for, session, flash, send_from_directory)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os, uuid
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)
app.secret_key = 'ofertes-ad-secret-2024'

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(BASE_DIR, 'database.db')
UPLOAD_DIR = os.path.join(BASE_DIR, 'static', 'uploads')
ALLOWED    = {'png','jpg','jpeg','gif','webp','pdf'}

os.makedirs(os.path.join(UPLOAD_DIR, 'folletos'), exist_ok=True)
os.makedirs(os.path.join(UPLOAD_DIR, 'ofertes'),  exist_ok=True)

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
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            category  TEXT NOT NULL,
            logo      TEXT DEFAULT '🏪',
            color     TEXT DEFAULT '#2D6A4F',
            accent    TEXT DEFAULT '#52B788',
            description TEXT DEFAULT '',
            location  TEXT DEFAULT '',
            phone     TEXT DEFAULT '',
            username  TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL,
            active    INTEGER DEFAULT 1,
            created   TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS folletos (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id  INTEGER NOT NULL,
            title        TEXT NOT NULL,
            filename     TEXT NOT NULL,
            filetype     TEXT NOT NULL,
            valid_from   TEXT NOT NULL,
            valid_until  TEXT NOT NULL,
            created      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        );

        CREATE TABLE IF NOT EXISTS ofertes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id  INTEGER NOT NULL,
            name         TEXT NOT NULL,
            emoji        TEXT DEFAULT '🛒',
            description  TEXT DEFAULT '',
            original_price REAL NOT NULL,
            offer_price  REAL NOT NULL,
            unit         TEXT DEFAULT '',
            category     TEXT DEFAULT '',
            image        TEXT DEFAULT '',
            valid_from   TEXT NOT NULL,
            valid_until  TEXT NOT NULL,
            featured     INTEGER DEFAULT 0,
            created      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (business_id) REFERENCES businesses(id)
        );
        """)
        # Seed demo data if empty
        if not db.execute("SELECT 1 FROM businesses LIMIT 1").fetchone():
            seed_demo(db)

def seed_demo(db):
    businesses = [
        (1,'Mercat Central','Supermercat','🏪','#2D6A4F','#52B788',
         'El supermercat del centre amb les millors ofertes de productes frescos.',
         'Av. Meritxell 42, Andorra la Vella','+376 800 001','mercat','mercat123'),
        (2,'Borda Fresh','Fruites i Verdures','🥬','#6B4226','#D4A574',
         'Productes de temporada directes dels agricultors de les valls.',
         'Carrer Major 8, Encamp','+376 800 002','borda','borda123'),
        (3,'Gourmet Pirineu','Productes Gourmet','🧀','#1B4F72','#5DADE2',
         'Selecció de productes artesanals i importacions exclusives.',
         'Plaça Coprínceps 3, Escaldes','+376 800 003','gourmet','gourmet123'),
        (4,'Super Baixada','Supermercat','🛒','#6C3483','#AF7AC5',
         'Preus baixos cada dia. La cadena de confiança de les famílies.',
         'Baixada del Molí 15, Andorra la Vella','+376 800 004','baixada','baixada123'),
        (5,'Carnisseria Ros','Carnisseria','🥩','#922B21','#E74C3C',
         'Carn de qualitat superior. Vedella, xai i porc de producció local.',
         'Carrer de la Unió 22, Ordino','+376 800 005','carnros','carnros123'),
        (6,'Fleca Andorrana','Fleca i Pastisseria','🥖','#784212','#F0B27A',
         'Pa artesanal de forn de llenya. Pastissos i dolços tradicionals.',
         'Av. del Fener 5, Sant Julià','+376 800 006','fleca','fleca123'),
    ]
    for b in businesses:
        db.execute("""INSERT INTO businesses
            (id,name,category,logo,color,accent,description,location,phone,username,password)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (*b[:10], generate_password_hash(b[10])))

    today = date.today().isoformat()
    from datetime import timedelta
    def d(n): return (date.today() + timedelta(days=n)).isoformat()

    ofertes = [
        (1,1,"Oli d'Oliva Verge Extra 1L",'🫒','',8.90,5.99,"l'ampolla",'Alimentació','',today,d(5),1),
        (2,1,'Arròs de gra llarg 1kg','🌾','',3.50,1.99,'el paquet','Alimentació','',today,d(5),0),
        (3,1,'Llet sencera 6x1L','🥛','',7.20,4.99,'el pack','Lactis','',today,d(5),0),
        (4,1,'Cervesa artesana 6 pack','🍺','',9.90,6.49,'el pack','Begudes','',today,d(5),1),
        (5,2,'Maduixes de temporada 500g','🍓','',4.50,2.49,'la bossa','Fruita','',today,d(3),1),
        (6,2,'Tomàquets de penjar 1kg','🍅','',3.80,1.99,'el kg','Verdura','',today,d(3),0),
        (7,2,'Préssecs de la vall 1kg','🍑','',4.20,2.79,'el kg','Fruita','',today,d(3),0),
        (8,2,'Enciam de fulla de roure','🥬','',1.80,0.99,'la peça','Verdura','',today,d(3),1),
        (9,3,'Formatge Manchego curat 300g','🧀','',11.90,7.99,'la peça','Formatgeria','',today,d(7),1),
        (10,3,'Vi negre Priorat 75cl','🍷','',18.00,11.99,"l'ampolla",'Vins','',today,d(7),1),
        (11,4,'Pasta italiana 500g','🍝','',2.20,0.99,'el paquet','Alimentació','',today,d(6),0),
        (12,4,'Iogurt natural 8 unitats','🥛','',3.60,1.99,'el pack','Lactis','',today,d(6),1),
        (13,4,'Tonyina en conserva x3','🐟','',4.50,2.79,'el pack','Conserves','',today,d(6),1),
        (14,5,'Pit de pollastre 1kg','🍗','',9.90,6.49,'el kg','Aviram','',today,d(4),1),
        (15,5,'Costelles de xai 500g','🥩','',13.50,8.99,'els 500g','Xai','',today,d(4),0),
        (16,6,'Pa de pagès 800g','🍞','',3.50,2.20,'la peça','Pa','',today,d(2),1),
        (17,6,'Croissant mantequilla x6','🥐','',5.40,3.50,'el pack','Pastisseria','',today,d(2),0),
        (18,6,'Coca de recapte familiar','🫓','',8.00,5.49,'la peça','Especialitats','',today,d(2),1),
    ]
    for o in ofertes:
        db.execute("""INSERT INTO ofertes
            (id,business_id,name,emoji,description,original_price,offer_price,
             unit,category,image,valid_from,valid_until,featured)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", o)

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED

def save_file(file, subfolder):
    ext = file.filename.rsplit('.',1)[1].lower()
    fname = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_DIR, subfolder, fname))
    return fname

def today_str():
    return date.today().isoformat()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'business_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# ── Public routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    today = today_str()
    businesses = db.execute(
        "SELECT * FROM businesses WHERE active=1 ORDER BY name").fetchall()
    featured = db.execute("""
        SELECT o.*, b.name as bname, b.logo as blogo, b.id as bid
        FROM ofertes o JOIN businesses b ON o.business_id=b.id
        WHERE o.featured=1 AND o.valid_from<=? AND o.valid_until>=?
        ORDER BY o.created DESC LIMIT 10""", (today, today)).fetchall()
    return render_template('index.html', businesses=businesses, featured=featured)

@app.route('/negoci/<int:bid>')
def business(bid):
    db = get_db()
    today = today_str()
    b = db.execute("SELECT * FROM businesses WHERE id=? AND active=1", (bid,)).fetchone()
    if not b:
        return redirect(url_for('index'))
    ofertes = db.execute("""
        SELECT * FROM ofertes WHERE business_id=?
        AND valid_from<=? AND valid_until>=?
        ORDER BY featured DESC, created DESC""", (bid, today, today)).fetchall()
    folletos = db.execute("""
        SELECT * FROM folletos WHERE business_id=?
        AND valid_from<=? AND valid_until>=?
        ORDER BY created DESC""", (bid, today, today)).fetchall()
    categories = sorted(set(o['category'] for o in ofertes if o['category']))
    all_businesses = db.execute("SELECT * FROM businesses WHERE active=1 ORDER BY name").fetchall()
    return render_template('business.html', b=b, ofertes=ofertes,
                           folletos=folletos, categories=categories,
                           all_businesses=all_businesses)

@app.route('/api/search')
def api_search():
    q = request.args.get('q','').lower().strip()
    if not q: return jsonify([])
    db  = get_db()
    today = today_str()
    rows = db.execute("""
        SELECT o.*, b.name as bname, b.logo as blogo, b.id as bid
        FROM ofertes o JOIN businesses b ON o.business_id=b.id
        WHERE (LOWER(o.name) LIKE ? OR LOWER(o.category) LIKE ?)
        AND o.valid_from<=? AND o.valid_until>=?
        LIMIT 12""", (f'%{q}%', f'%{q}%', today, today)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/ofertes')
def api_ofertes():
    db  = get_db()
    today = today_str()
    bid = request.args.get('business_id', type=int)
    cat = request.args.get('category','')
    sql = """SELECT o.*, b.name as bname, b.logo as blogo, b.id as bid
             FROM ofertes o JOIN businesses b ON o.business_id=b.id
             WHERE o.valid_from<=? AND o.valid_until>=?"""
    params = [today, today]
    if bid:
        sql += " AND o.business_id=?"; params.append(bid)
    if cat:
        sql += " AND o.category=?"; params.append(cat)
    sql += " ORDER BY o.featured DESC, o.created DESC"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])

# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        b = db.execute("SELECT * FROM businesses WHERE username=? AND active=1",
                       (username,)).fetchone()
        if b and check_password_hash(b['password'], password):
            session['business_id'] = b['id']
            session['business_name'] = b['name']
            return redirect(url_for('panel'))
        flash('Usuari o contrasenya incorrectes')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ── Admin panel ───────────────────────────────────────────────────────────────

@app.route('/panel')
@login_required
def panel():
    db = get_db()
    today = today_str()
    bid = session['business_id']
    ofertes = db.execute("""
        SELECT * FROM ofertes WHERE business_id=?
        AND valid_from<=? AND valid_until>=?
        ORDER BY featured DESC, created DESC""", (bid, today, today)).fetchall()
    folletos = db.execute("""
        SELECT * FROM folletos WHERE business_id=?
        AND valid_from<=? AND valid_until>=?
        ORDER BY created DESC""", (bid, today, today)).fetchall()
    b = db.execute("SELECT * FROM businesses WHERE id=?", (bid,)).fetchone()
    return render_template('panel.html', ofertes=ofertes, folletos=folletos, b=b)

@app.route('/panel/oferta/nova', methods=['GET','POST'])
@login_required
def nova_oferta():
    if request.method == 'POST':
        f = request.form
        image = ''
        if 'image' in request.files and request.files['image'].filename:
            img = request.files['image']
            if allowed_file(img.filename):
                image = save_file(img, 'ofertes')
        db = get_db()
        db.execute("""INSERT INTO ofertes
            (business_id,name,emoji,description,original_price,offer_price,
             unit,category,image,valid_from,valid_until,featured)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", (
            session['business_id'],
            f['name'], f.get('emoji','🛒'), f.get('description',''),
            float(f['original_price']), float(f['offer_price']),
            f.get('unit',''), f.get('category',''), image,
            f['valid_from'], f['valid_until'],
            1 if f.get('featured') else 0
        ))
        db.commit()
        flash('Oferta publicada correctament!')
        return redirect(url_for('panel'))
    return render_template('form_oferta.html')

@app.route('/panel/oferta/eliminar/<int:oid>', methods=['POST'])
@login_required
def eliminar_oferta(oid):
    db = get_db()
    db.execute("DELETE FROM ofertes WHERE id=? AND business_id=?",
               (oid, session['business_id']))
    db.commit()
    flash('Oferta eliminada.')
    return redirect(url_for('panel'))

@app.route('/panel/folleto/nou', methods=['GET','POST'])
@login_required
def nou_folleto():
    if request.method == 'POST':
        f = request.form
        if 'file' not in request.files or not request.files['file'].filename:
            flash('Cal seleccionar un arxiu')
            return redirect(request.url)
        fil = request.files['file']
        if not allowed_file(fil.filename):
            flash('Format no permès. Usa PDF, JPG, PNG o WebP.')
            return redirect(request.url)
        ext      = fil.filename.rsplit('.',1)[1].lower()
        filetype = 'pdf' if ext == 'pdf' else 'image'
        filename = save_file(fil, 'folletos')
        db = get_db()
        db.execute("""INSERT INTO folletos
            (business_id,title,filename,filetype,valid_from,valid_until)
            VALUES (?,?,?,?,?,?)""", (
            session['business_id'], f['title'], filename,
            filetype, f['valid_from'], f['valid_until']
        ))
        db.commit()
        flash('Folleto publicat correctament!')
        return redirect(url_for('panel'))
    return render_template('form_folleto.html')

@app.route('/panel/folleto/eliminar/<int:fid>', methods=['POST'])
@login_required
def eliminar_folleto(fid):
    db = get_db()
    row = db.execute("SELECT * FROM folletos WHERE id=? AND business_id=?",
                     (fid, session['business_id'])).fetchone()
    if row:
        try:
            os.remove(os.path.join(UPLOAD_DIR, 'folletos', row['filename']))
        except: pass
        db.execute("DELETE FROM folletos WHERE id=?", (fid,))
        db.commit()
    flash('Folleto eliminat.')
    return redirect(url_for('panel'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
