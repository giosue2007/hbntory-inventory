#!/usr/bin/env python3
"""
HBntory Product MCP server: a bridge between AI agents and the external
Product API.

It exposes two read-only MCP tools:
    list_products(category=None)   -> every product, or one category
    get_product_details(product_id) -> one product

Every tool returns the same clear structure: "ok" tells if it worked,
the data is in "products" / "product", and a failure is described in
"error" with a stable code and a message (never a Python traceback).

Run it (Streamable HTTP on http://127.0.0.1:8001/mcp):
    python3 -m mcp_server.product_server
or over stdio (used by scripts/test_mcp_tools.py):
    python3 -m mcp_server.product_server --stdio
"""
import logging
import os
import re
import sys
from typing import Literal, Optional

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

load_dotenv()
logging.getLogger("httpx").setLevel(logging.WARNING)

PRODUCT_API_URL = os.getenv("PRODUCT_API_URL", "http://localhost:9000")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
TIMEOUT = 5
# A product id is short and simple: it is put inside a URL.
PRODUCT_ID = re.compile(r"^[A-Za-z0-9_-]{1,50}$")

ErrorCode = Literal["INVALID_INPUT", "PRODUCT_NOT_FOUND",
                    "PRODUCT_API_UNAVAILABLE", "PRODUCT_API_ERROR"]


class ToolError(Exception):
    """
    A failure that is sent back to the agent as a clear error object.
    """

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class Error(BaseModel):
    """
    Why a tool call failed.
    """
    code: ErrorCode = Field(description="Stable error code")
    message: str = Field(description="Explanation for a human or an agent")


class Product(BaseModel):
    """
    One product as given by the Product API.
    """
    id: str
    name: str
    category: Optional[str] = None
    price: Optional[float] = None


class ProductList(BaseModel):
    """
    Result of list_products.
    """
    ok: bool
    count: int = 0
    products: list[Product] = []
    error: Optional[Error] = None


class ProductDetails(BaseModel):
    """
    Result of get_product_details.
    """
    ok: bool
    product: Optional[Product] = None
    error: Optional[Error] = None


def call_product_api(path):
    """
    GET {PRODUCT_API_URL}{path} and return the decoded JSON.
    Return None for a 404. Raise ToolError for every other problem.
    """
    url = PRODUCT_API_URL.rstrip("/") + path
    try:
        response = httpx.get(url, timeout=TIMEOUT)
    except httpx.TimeoutException:
        raise ToolError("PRODUCT_API_UNAVAILABLE",
                        f"The Product API did not answer within {TIMEOUT} "
                        "seconds.")
    except httpx.HTTPError:
        raise ToolError("PRODUCT_API_UNAVAILABLE",
                        f"The Product API cannot be reached at "
                        f"{PRODUCT_API_URL}.")
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise ToolError("PRODUCT_API_ERROR",
                        f"The Product API answered with status "
                        f"{response.status_code}.")
    try:
        return response.json()
    except ValueError:
        raise ToolError("PRODUCT_API_ERROR",
                        "The Product API sent an answer that is not JSON.")


def to_product(data):
    """
    Keep only the fields we expose, so the output shape never changes.
    """
    try:
        return Product(id=str(data["id"]), name=data["name"],
                       category=data.get("category"),
                       price=data.get("price"))
    except (KeyError, TypeError, ValueError):
        raise ToolError("PRODUCT_API_ERROR",
                        "The Product API sent a product without id or name.")


mcp = FastMCP("HBntory Product MCP", port=MCP_PORT, log_level="WARNING")
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)


@mcp.tool(annotations=READ_ONLY)
def list_products(category: Optional[str] = None) -> ProductList:
    """
    List the products available in the catalog.

    Args:
        category: optional category name (e.g. "Audio"); case does not
            matter. Leave empty to get every product.
    """
    try:
        data = call_product_api("/products")
        if not isinstance(data, list):
            raise ToolError("PRODUCT_API_ERROR",
                            "The Product API did not send a list.")
        products = [to_product(item) for item in data]
    except ToolError as error:
        return ProductList(ok=False, error=Error(code=error.code,
                                                 message=error.message))
    if category and category.strip():
        wanted = category.strip().lower()
        products = [p for p in products
                    if (p.category or "").lower() == wanted]
    return ProductList(ok=True, count=len(products), products=products)


@mcp.tool(annotations=READ_ONLY)
def get_product_details(product_id: str) -> ProductDetails:
    """
    Get the details of one product (name, category, price).

    Args:
        product_id: the product id, e.g. "6".
    """
    product_id = (product_id or "").strip()
    try:
        if not PRODUCT_ID.match(product_id):
            raise ToolError("INVALID_INPUT",
                            "product_id must be 1 to 50 letters, digits, "
                            "'-' or '_'.")
        data = call_product_api(f"/products/{product_id}")
        if data is None:
            raise ToolError("PRODUCT_NOT_FOUND",
                            f"No product with id {product_id} in the "
                            "catalog.")
        product = to_product(data)
    except ToolError as error:
        return ProductDetails(ok=False, error=Error(code=error.code,
                                                    message=error.message))
    return ProductDetails(ok=True, product=product)


if __name__ == "__main__":
    mcp.run("stdio" if "--stdio" in sys.argv else "streamable-http")
