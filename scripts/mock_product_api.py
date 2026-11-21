#!/usr/bin/env python3
"""
Local stand-in for the external Product API, for development and demos.

The real Product API is not developed by us. This mock answers the same
two routes with a small catalog of electronics, so the Backoffice can show
product names and check that a product exists:
    GET /products        -> list of all products
    GET /products/{id}   -> one product, or 404 if the id is unknown

Usage (from the project folder):
    uvicorn scripts.mock_product_api:app --port 9000
PRODUCT_API_URL in .env must point to it: http://localhost:9000
"""
from fastapi import FastAPI, HTTPException

app = FastAPI(title="HBntory - Mock Product API")

PRODUCTS = {
    "1": ("Ordinateur portable Pro 14", "Ordinateurs", 1299),
    "2": ("Souris sans fil", "Accessoires", 29),
    "3": ("Clavier mécanique", "Accessoires", 89),
    "4": ("Écran 27 pouces", "Écrans", 249),
    "5": ("Station d'accueil USB-C", "Accessoires", 119),
    "6": ("Smartphone X12", "Téléphones", 799),
    "7": ("Tablette Air 11", "Tablettes", 649),
    "8": ("Casque à réduction de bruit", "Audio", 299),
    "9": ("Enceinte Bluetooth", "Audio", 79),
    "10": ("Montre connectée S3", "Objets connectés", 199),
    "11": ("Webcam 4K", "Accessoires", 129),
    "12": ("SSD externe 1 To", "Stockage", 109),
    "13": ("Chargeur USB-C 65 W", "Accessoires", 39),
    "14": ("Console de jeux", "Jeux", 499),
    "15": ("Routeur Wi-Fi 6", "Réseau", 149),
    "16": ("Écouteurs sans fil", "Audio", 159),
}


def to_dict(product_id):
    """
    Return one product as the JSON object sent to the client.
    """
    name, category, price = PRODUCTS[product_id]
    return {"id": product_id, "name": name, "category": category,
            "price": price}


@app.get("/products")
def list_products():
    """
    Return the whole catalog.
    """
    return [to_dict(product_id) for product_id in PRODUCTS]


@app.get("/products/{product_id}")
def get_product(product_id: str):
    """
    Return one product, or 404 if the id is not in the catalog.
    """
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    return to_dict(product_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=9000)
