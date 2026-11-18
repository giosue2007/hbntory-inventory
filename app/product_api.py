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
        raise ProductAPIError(f"Product API unreachable: {error}") from error
    if response.status_code == 200:
        return True
    if response.status_code == 404:
        return False
    raise ProductAPIError(
        f"Product API returned status {response.status_code}")
