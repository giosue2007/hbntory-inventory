#!/usr/bin/env python3
"""
Client for the external Product API.
Only used to check that a product id exists: details are never stored.
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PRODUCT_API_URL = os.getenv("PRODUCT_API_URL", "http://localhost:9000")


class ProductAPIError(Exception):
    """
    Raised when the Product API cannot be reached.
    """


def product_exists(product_id):
    """
    Return True if GET {PRODUCT_API_URL}/products/{id} answers 200,
    False if it answers 404. Raise ProductAPIError otherwise.
    """
    url = f"{PRODUCT_API_URL.rstrip('/')}/products/{product_id}"
    try:
        response = httpx.get(url, timeout=5)
    except httpx.HTTPError as error:
        raise ProductAPIError(f"API Produits injoignable : {error}") from error
    if response.status_code == 200:
        return True
    if response.status_code == 404:
        return False
    raise ProductAPIError(
        f"L'API Produits a répondu {response.status_code}.")


def get_product(product_id):
    """
    Return the product details from the Product API as a dict,
    or None if it answers 404. Nothing is stored locally.
    """
    url = f"{PRODUCT_API_URL.rstrip('/')}/products/{product_id}"
    try:
        response = httpx.get(url, timeout=5)
    except httpx.HTTPError as error:
        raise ProductAPIError(f"API Produits injoignable : {error}") from error
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise ProductAPIError(
            f"L'API Produits a répondu {response.status_code}.")
    return response.json()
