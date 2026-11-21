# HBntory - Product MCP server

## Role

`mcp_server/product_server.py` is an MCP server that acts as a bridge
between AI agents and the external Product API. The agent never calls
the Product API itself: it calls MCP tools, and the server calls
`GET {PRODUCT_API_URL}/products` and `GET {PRODUCT_API_URL}/products/{id}`.

    AI agent --MCP (Streamable HTTP)--> Product MCP server --REST--> Product API

For now the server only covers product data, as asked in task 4. Stock
tools (through the Inventory API, see ARCHITECTURE.md) can be added
later without changing these two tools.

Both tools are **read-only** (`readOnlyHint`): no tool can change data.

## Run it

    pip install -r requirements.txt
    uvicorn scripts.mock_product_api:app --port 9000   # or the real API
    python3 -m mcp_server.product_server

The server listens on `http://127.0.0.1:8001/mcp` (Streamable HTTP).
`PRODUCT_API_URL` (default `http://localhost:9000`) and `MCP_PORT`
(default `8001`) come from `.env`. With `--stdio` it talks over
stdin/stdout instead (used by the test script).

## Tool definitions

| Tool | Input | Output |
|------|-------|--------|
| `list_products` | `category` (string, optional, case-insensitive) | `ProductList`: `ok`, `count`, `products[]`, `error` |
| `get_product_details` | `product_id` (string, required) | `ProductDetails`: `ok`, `product`, `error` |

A product always has the same shape:

    {"id": "6", "name": "Smartphone X12", "category": "Téléphones", "price": 799.0}

The inputs and outputs are typed (type hints and Pydantic models), so
the server publishes a JSON schema for both: the agent knows exactly
what to send and what it will get back. Fields the Product API may add
later are dropped, so the output shape never changes.

## Error handling

A tool never crashes and never returns a Python traceback. It returns
`"ok": false` and an `error` object with a stable `code` and a clear
`message`:

| Code | When | Example message |
|------|------|-----------------|
| `INVALID_INPUT` | `product_id` empty, too long, or with characters other than letters, digits, `-`, `_` (it is put in a URL) | `product_id must be 1 to 50 letters, digits, '-' or '_'.` |
| `PRODUCT_NOT_FOUND` | the Product API answers 404 | `No product with id 999 in the catalog.` |
| `PRODUCT_API_UNAVAILABLE` | connection refused, DNS error, or no answer within 5 seconds | `The Product API cannot be reached at http://localhost:9000.` |
| `PRODUCT_API_ERROR` | any other status (500...), an answer that is not JSON, or a product without id/name | `The Product API answered with status 500.` |

Returning errors as data (instead of raising) lets the agent tell the
user "this product does not exist" or "the catalog is unavailable,
try again later" instead of failing.

## Manual tests

Steps (the mock Product API must run on port 9000):

    python3 scripts/test_mcp_tools.py

The script starts the server like a real MCP client, lists the tools
and calls them in 6 cases. Result:

    Tools: list_products, get_product_details
    --- 1: list_products({})                      -> ok, count 16
    --- 2: list_products({"category": "audio"})   -> ok, count 3 (Audio only)
    --- 3: get_product_details({"product_id": "6"})
        {"ok": true, "product": {"id": "6", "name": "Smartphone X12",
         "category": "Téléphones", "price": 799.0}, "error": null}
    --- 4: get_product_details({"product_id": "999"})
        {"ok": false, "error": {"code": "PRODUCT_NOT_FOUND",
         "message": "No product with id 999 in the catalog."}}
    --- 5: get_product_details({"product_id": "../admin"})
        {"ok": false, "error": {"code": "INVALID_INPUT", ...}}
    --- 6 (API down): get_product_details({"product_id": "6"})
        {"ok": false, "error": {"code": "PRODUCT_API_UNAVAILABLE",
         "message": "The Product API cannot be reached at http://127.0.0.1:9."}}
    6 / 6 checks passed

The tools can also be tried by hand with the MCP Inspector
(`npx @modelcontextprotocol/inspector`, transport "Streamable HTTP",
URL `http://127.0.0.1:8001/mcp`).
