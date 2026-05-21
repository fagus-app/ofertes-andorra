from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# ── Mock data ────────────────────────────────────────────────────────────────

STORES = [
    {
        "id": 1,
        "name": "Mercat Central",
        "category": "Supermercado",
        "logo": "🏪",
        "color": "#2D6A4F",
        "accent": "#52B788",
        "description": "El supermercat del centre amb les millors ofertes de productes frescos.",
        "location": "Av. Meritxell 42, Andorra la Vella",
        "phone": "+376 800 001",
    },
    {
        "id": 2,
        "name": "Borda Fresh",
        "category": "Fruites i Verdures",
        "logo": "🥬",
        "color": "#6B4226",
        "accent": "#D4A574",
        "description": "Productes de temporada directes dels agricultors de les valls.",
        "location": "Carrer Major 8, Encamp",
        "phone": "+376 800 002",
    },
    {
        "id": 3,
        "name": "Gourmet Pirineu",
        "category": "Productes Gourmet",
        "logo": "🧀",
        "color": "#1B4F72",
        "accent": "#5DADE2",
        "description": "Selecció de productes artesanals i importacions exclusives.",
        "location": "Plaça Coprínceps 3, Escaldes",
        "phone": "+376 800 003",
    },
    {
        "id": 4,
        "name": "Super Baixada",
        "category": "Supermercat",
        "logo": "🛒",
        "color": "#6C3483",
        "accent": "#AF7AC5",
        "description": "Preus baixos cada dia. La cadena de confiança de les famílies.",
        "location": "Baixada del Molí 15, Andorra la Vella",
        "phone": "+376 800 004",
    },
    {
        "id": 5,
        "name": "Carnisseria Ros",
        "category": "Carnisseria",
        "logo": "🥩",
        "color": "#922B21",
        "accent": "#E74C3C",
        "description": "Carn de qualitat superior. Vedella, xai i porc de producció local.",
        "location": "Carrer de la Unió 22, Ordino",
        "phone": "+376 800 005",
    },
    {
        "id": 6,
        "name": "Fleca Andorrana",
        "category": "Fleca i Pastisseria",
        "logo": "🥖",
        "color": "#784212",
        "accent": "#F0B27A",
        "description": "Pa artesanal de forn de llenya. Pastissos i dolços tradicionals.",
        "location": "Av. del Fener 5, Sant Julià",
        "phone": "+376 800 006",
    },
]

today = datetime.now()

OFFERS = [
    # Mercat Central
    {"id": 1, "store_id": 1, "name": "Oli d'Oliva Verge Extra 1L", "emoji": "🫒", "original_price": 8.90, "offer_price": 5.99, "unit": "l'ampolla", "valid_until": (today + timedelta(days=5)).strftime("%d/%m"), "category": "Alimentació", "featured": True},
    {"id": 2, "store_id": 1, "name": "Arròs de gra llarg 1kg", "emoji": "🌾", "original_price": 3.50, "offer_price": 1.99, "unit": "el paquet", "valid_until": (today + timedelta(days=5)).strftime("%d/%m"), "category": "Alimentació", "featured": False},
    {"id": 3, "store_id": 1, "name": "Llet sencera 6x1L", "emoji": "🥛", "original_price": 7.20, "offer_price": 4.99, "unit": "el pack", "valid_until": (today + timedelta(days=5)).strftime("%d/%m"), "category": "Lactis", "featured": False},
    {"id": 4, "store_id": 1, "name": "Detergent roba 3L", "emoji": "🧺", "original_price": 12.50, "offer_price": 7.99, "unit": "l'ampolla", "valid_until": (today + timedelta(days=5)).strftime("%d/%m"), "category": "Llar", "featured": False},
    {"id": 5, "store_id": 1, "name": "Cervesa artesana 6 pack", "emoji": "🍺", "original_price": 9.90, "offer_price": 6.49, "unit": "el pack", "valid_until": (today + timedelta(days=5)).strftime("%d/%m"), "category": "Begudes", "featured": True},

    # Borda Fresh
    {"id": 6, "store_id": 2, "name": "Maduixes de temporada 500g", "emoji": "🍓", "original_price": 4.50, "offer_price": 2.49, "unit": "la bossa", "valid_until": (today + timedelta(days=3)).strftime("%d/%m"), "category": "Fruita", "featured": True},
    {"id": 7, "store_id": 2, "name": "Tomàquets de penjar 1kg", "emoji": "🍅", "original_price": 3.80, "offer_price": 1.99, "unit": "el kg", "valid_until": (today + timedelta(days=3)).strftime("%d/%m"), "category": "Verdura", "featured": False},
    {"id": 8, "store_id": 2, "name": "Préssecs de la vall 1kg", "emoji": "🍑", "original_price": 4.20, "offer_price": 2.79, "unit": "el kg", "valid_until": (today + timedelta(days=3)).strftime("%d/%m"), "category": "Fruita", "featured": False},
    {"id": 9, "store_id": 2, "name": "Enciam de fulla de roure", "emoji": "🥬", "original_price": 1.80, "offer_price": 0.99, "unit": "la peça", "valid_until": (today + timedelta(days=3)).strftime("%d/%m"), "category": "Verdura", "featured": True},

    # Gourmet Pirineu
    {"id": 10, "store_id": 3, "name": "Formatge Manchego curat 300g", "emoji": "🧀", "original_price": 11.90, "offer_price": 7.99, "unit": "la peça", "valid_until": (today + timedelta(days=7)).strftime("%d/%m"), "category": "Formatgeria", "featured": True},
    {"id": 11, "store_id": 3, "name": "Foie gras artesanal 125g", "emoji": "🥫", "original_price": 14.50, "offer_price": 9.90, "unit": "la llauna", "valid_until": (today + timedelta(days=7)).strftime("%d/%m"), "category": "Delicatessen", "featured": False},
    {"id": 12, "store_id": 3, "name": "Vi negre Priorat 75cl", "emoji": "🍷", "original_price": 18.00, "offer_price": 11.99, "unit": "l'ampolla", "valid_until": (today + timedelta(days=7)).strftime("%d/%m"), "category": "Vins", "featured": True},
    {"id": 13, "store_id": 3, "name": "Xocolata Belga 72% 200g", "emoji": "🍫", "original_price": 5.90, "offer_price": 3.49, "unit": "la barra", "valid_until": (today + timedelta(days=7)).strftime("%d/%m"), "category": "Dolços", "featured": False},

    # Super Baixada
    {"id": 14, "store_id": 4, "name": "Pasta italiana 500g", "emoji": "🍝", "original_price": 2.20, "offer_price": 0.99, "unit": "el paquet", "valid_until": (today + timedelta(days=6)).strftime("%d/%m"), "category": "Alimentació", "featured": False},
    {"id": 15, "store_id": 4, "name": "Paper higiènic 12 rotlles", "emoji": "🧻", "original_price": 8.90, "offer_price": 5.49, "unit": "el pack", "valid_until": (today + timedelta(days=6)).strftime("%d/%m"), "category": "Llar", "featured": False},
    {"id": 16, "store_id": 4, "name": "Iogurt natural 8 unitats", "emoji": "🥛", "original_price": 3.60, "offer_price": 1.99, "unit": "el pack", "valid_until": (today + timedelta(days=6)).strftime("%d/%m"), "category": "Lactis", "featured": True},
    {"id": 17, "store_id": 4, "name": "Tonyina en conserva x3", "emoji": "🐟", "original_price": 4.50, "offer_price": 2.79, "unit": "el pack", "valid_until": (today + timedelta(days=6)).strftime("%d/%m"), "category": "Conserves", "featured": True},

    # Carnisseria Ros
    {"id": 18, "store_id": 5, "name": "Pit de pollastre 1kg", "emoji": "🍗", "original_price": 9.90, "offer_price": 6.49, "unit": "el kg", "valid_until": (today + timedelta(days=4)).strftime("%d/%m"), "category": "Aviram", "featured": True},
    {"id": 19, "store_id": 5, "name": "Costelles de xai 500g", "emoji": "🥩", "original_price": 13.50, "offer_price": 8.99, "unit": "els 500g", "valid_until": (today + timedelta(days=4)).strftime("%d/%m"), "category": "Xai", "featured": False},
    {"id": 20, "store_id": 5, "name": "Llonganissa artesana 250g", "emoji": "🌭", "original_price": 6.90, "offer_price": 4.49, "unit": "la peça", "valid_until": (today + timedelta(days=4)).strftime("%d/%m"), "category": "Embotits", "featured": False},

    # Fleca Andorrana
    {"id": 21, "store_id": 6, "name": "Pa de pagès 800g", "emoji": "🍞", "original_price": 3.50, "offer_price": 2.20, "unit": "la peça", "valid_until": (today + timedelta(days=2)).strftime("%d/%m"), "category": "Pa", "featured": True},
    {"id": 22, "store_id": 6, "name": "Croissant mantequilla x6", "emoji": "🥐", "original_price": 5.40, "offer_price": 3.50, "unit": "el pack", "valid_until": (today + timedelta(days=2)).strftime("%d/%m"), "category": "Pastisseria", "featured": False},
    {"id": 23, "store_id": 6, "name": "Coca de recapte familiar", "emoji": "🫓", "original_price": 8.00, "offer_price": 5.49, "unit": "la peça", "valid_until": (today + timedelta(days=2)).strftime("%d/%m"), "category": "Especialitats", "featured": True},
]

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    featured = [o for o in OFFERS if o["featured"]]
    # attach store info to each offer
    store_map = {s["id"]: s for s in STORES}
    for o in featured:
        o["store"] = store_map[o["store_id"]]
    return render_template("index.html", stores=STORES, featured=featured)

@app.route("/tienda/<int:store_id>")
def store_detail(store_id):
    store = next((s for s in STORES if s["id"] == store_id), None)
    if not store:
        return "Botiga no trobada", 404
    offers = [o for o in OFFERS if o["store_id"] == store_id]
    categories = sorted(set(o["category"] for o in offers))
    return render_template("store.html", store=store, offers=offers, categories=categories, stores=STORES)

@app.route("/api/offers")
def api_offers():
    store_id = request.args.get("store_id", type=int)
    category = request.args.get("category", "")
    q = request.args.get("q", "").lower()

    result = OFFERS
    if store_id:
        result = [o for o in result if o["store_id"] == store_id]
    if category:
        result = [o for o in result if o["category"] == category]
    if q:
        result = [o for o in result if q in o["name"].lower()]

    store_map = {s["id"]: s for s in STORES}
    for o in result:
        o = dict(o)
        o["store"] = store_map[o["store_id"]]
    return jsonify(result)

@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").lower().strip()
    if not q:
        return jsonify([])
    store_map = {s["id"]: s for s in STORES}
    results = []
    for o in OFFERS:
        if q in o["name"].lower() or q in o["category"].lower():
            item = dict(o)
            item["store"] = store_map[o["store_id"]]
            results.append(item)
    return jsonify(results[:12])

if __name__ == "__main__":
    app.run(debug=True, port=5000)
