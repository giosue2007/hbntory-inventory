# HBntory - Minimum Viable Product

Goal: a complete path from data to user, working end to end, before
any extra feature. Integration first, polish later.

Solo project: one developer. To keep the MVP realistic, the Inventory API, the Backoffice and the Client Web Interface run in the same FastAPI application (3 processes in total: web app, MCP Server, AI Query Service).

## Phase 1 - Implement first (MVP)

1. **Inventory API**
   - Read products from the external Product API (list + one product).
   - SQLite tables `stock` and `stock_movements`.
   - REST endpoints: `GET /products`, `GET /products/{id}`,
     `GET /stock/{product_id}`, `POST /stock/{product_id}/movements`.
   - Clear errors when the Product API is unavailable or an id does
     not exist.
2. **Backoffice (SSR)**
   - Simple login for staff.
   - Page listing products with their stock.
   - Form to add a stock movement (restock / sale / correction).
3. **Client Web Interface (REST)**
   - Product list with search and availability (in stock / low / out).
   - Product detail page.
   - A "Ask a question" box that calls the AI Query Service.
4. **MCP Server**
   - Read-only tools: `search_products`, `get_product_details`,
     `get_stock`, all calling the Inventory API.
   - Tested with a FastMCP client before connecting the agent.
5. **AI Query Service**
   - `POST /ask` endpoint.
   - ADK agent connected to the MCP Server (`tool_filter` on the three
     tools), local model through Ollama.
   - Answers built only from tool results; says clearly when a product
     is not found.
6. **Documentation**
   - README with setup, startup order of the services and example
     requests.

## Phase 2 - Leave for later

- Roles beyond admin/staff and user management pages.
- Stock movement history page with filters.
- Caching of Product API responses.
- Docker Compose to start every service with one command.
- Automated tests beyond basic checks of each endpoint and tool.

## Optional - only if time allows

- WebSockets for live stock updates in the Client Web Interface.
- Streaming of the AI answer token by token.
- Low-stock alerts (email or notification).
- Dashboard with charts (stock per category, movements per day).
- Multi-language interface.

## Integration checkpoints

1. Inventory API returns products with their stock.
2. Backoffice changes stock and the change is visible through the API.
3. Client Web Interface shows the same data.
4. MCP Server tools return the same data (tested without the agent).
5. AI Query Service answers "Is <product> in stock?" correctly.

Each checkpoint must work before moving to the next one.
