# HBntory - Architecture

> Status: initial design (Task 0). This document describes what we plan
> to build. It contains no implementation code.

## 1. Overview

HBntory is an inventory management platform. Staff manage stock levels
in a **Backoffice**, users browse products and stock in a **Client Web
Interface**, and an **AI Query Service** answers natural-language
questions ("Is the blue mug in stock?") by calling **MCP tools**.

Product information (name, description, price, category, image) comes
from an **external Product API**. HBntory does not copy the whole
catalog: it only stores what belongs to the inventory (stock levels,
stock movements, users).

## 2. Services

| # | Service | Responsibility | Main technology |
|---|---------|----------------|-----------------|
| 1 | **Inventory API** | Single source of truth for stock. Reads products from the external Product API, stores stock data locally, exposes a REST API (products + stock). | Python, FastAPI, SQLite |
| 2 | **Backoffice** | Pages for staff: list products with their stock, update quantities, record stock movements. Rendered on the server. | FastAPI + Jinja2 templates (SSR) |
| 3 | **Client Web Interface** | Public pages: browse/search products, see availability, ask a question to the AI. Calls the Inventory API and the AI Query Service over REST. | HTML/CSS/JS + `fetch` |
| 4 | **MCP Server** | Exposes product and stock information as MCP tools. It does not access the database directly: it calls the Inventory API. | Python, FastMCP (Streamable HTTP) |
| 5 | **AI Query Service** | Receives a question, lets an agent call the MCP tools, returns a short answer built from tool results. | Python, Google ADK + LiteLLM + Ollama |
| - | **Product API** (external) | Provides the product catalog. Not developed by us, read-only for us. | Third-party REST API |

Each service has **one** responsibility. Only the Inventory API talks to
the database and to the external Product API.

## 3. Communication

| From | To | Protocol | Purpose |
|------|----|----------|---------|
| Backoffice | Inventory API | Internal Python calls (same app) or REST | Read products, update stock |
| Client Web Interface (browser) | Inventory API | REST (JSON over HTTP) | List / search products and stock |
| Client Web Interface (browser) | AI Query Service | REST (`POST /ask`) | Send a question, receive the answer |
| AI Query Service | MCP Server | MCP over Streamable HTTP | Call `search_products`, `get_product_details`, `get_stock` |
| MCP Server | Inventory API | REST | Get product + stock data |
| Inventory API | Product API | REST (HTTPS) | Get catalog data |

The AI never reads the database and never calls the Product API
directly: it only goes through MCP tools, which go through the
Inventory API. This keeps one path to the data and one place to
validate it.

## 4. Data

### Stored locally (SQLite, owned by the Inventory API)

| Table | Content |
|-------|---------|
| `stock` | `product_id` (id from the Product API), `quantity`, `low_stock_threshold`, `updated_at` |
| `stock_movements` | `id`, `product_id`, `change` (+/-), `reason` (restock, sale, correction), `created_at`, `user_id` |
| `users` | `id`, `username`, `password_hash`, `role` (admin / staff) |

### Coming from the external Product API

`id`, `name`, `description`, `price`, `category`, `image_url`.

Product data is **not** duplicated in our database. The Inventory API
joins it with local stock when it answers. A short in-memory cache may
be added later to reduce calls to the Product API.

## 5. How the AI agent accesses products and stock

1. The user types a question in the Client Web Interface.
2. The browser sends `POST /ask {"question": "..."}` to the AI Query
   Service.
3. The agent (ADK) is connected to the MCP Server with a `tool_filter`
   that only allows three read-only tools:
   - `search_products(query)` - find matching products;
   - `get_product_details(product_id)` - product info + stock;
   - `get_stock(product_id)` - current quantity and low-stock flag.
4. Each tool calls the Inventory API, which combines Product API data
   with local stock.
5. The agent writes a short answer using only the tool results and
   returns it to the browser.

The AI has **read-only** access: no MCP tool can change stock (least
privilege). Stock changes are only possible in the Backoffice.

## 6. Diagram

See [SERVICE_DIAGRAM.md](SERVICE_DIAGRAM.md).

## 7. Related documents

- [DECISIONS.md](DECISIONS.md) - communication strategy decisions.
- [MVP.md](MVP.md) - what we build first and what we leave for later.

## 8. Solo project note

This is a solo project. The five services above are logical responsibilities.
To save time, services 1, 2 and 3 run in one FastAPI application.
The MCP Server and the AI Query Service run as two separate processes.
