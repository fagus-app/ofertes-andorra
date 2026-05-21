# Ofertes Andorra — App de Ofertes de Supermercats

Web app per mostrar les ofertes setmanals dels supermercats i botigues locals.

## Instal·lació i execució

### Requisits
- Python 3.9 o superior

### Passos

1. **Instal·la Flask** (si no el tens):
   ```
   pip install flask
   ```

2. **Executa l'app**:
   ```
   python app.py
   ```

3. **Obre el navegador** a:
   ```
   http://localhost:5000
   ```

## Estructura del projecte

```
tilbud/
├── app.py               ← Servidor principal (Flask)
└── templates/
    ├── base.html        ← Plantilla base (nav, styles, footer)
    ├── index.html       ← Pàgina principal
    └── store.html       ← Pàgina de botiga individual
```

## Com afegir botigues i ofertes

Obre `app.py` i edita les llistes `STORES` i `OFFERS` a la part superior.

### Exemple de botiga:
```python
{
    "id": 7,
    "name": "La Meva Botiga",
    "category": "Supermercat",
    "logo": "🛍️",
    "color": "#2D6A4F",
    "accent": "#52B788",
    "description": "Descripció de la botiga.",
    "location": "Carrer de..., Andorra la Vella",
    "phone": "+376 800 007",
}
```

### Exemple d'oferta:
```python
{
    "id": 24,
    "store_id": 7,          ← ha de coincidir amb l'id de la botiga
    "name": "Nom del producte",
    "emoji": "🥕",
    "original_price": 3.50,
    "offer_price": 1.99,
    "unit": "el kg",
    "valid_until": "30/05",
    "category": "Verdura",
    "featured": False,      ← True per mostrar a la secció destacada
}
```

## Pròxims passos (per créixer)

- Afegir base de dades (SQLite o PostgreSQL) per gestionar les dades
- Panel d'administració perquè cada botiga pugi les seves ofertes
- Sistema de pagament (Stripe) per les subscripcions mensuals
- Notificacions push quan hi ha ofertes noves
