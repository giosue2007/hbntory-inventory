# HBntory - Communication Decisions

Each decision follows the same format: context, decision, benefit,
trade-off. We chose options that fit the requirements and my
capacity, not the most complex ones.

## D1 - Backoffice: Server-Side Rendering

- **Options:** REST + HTML/CSS/JS, or Server-Side Rendering (SSR).
- **Decision:** **SSR** with FastAPI + Jinja2 templates.
- **Benefit:** simple to build and debug. Forms post directly to the
  server, no separate frontend code, no JSON API needed for admin
  pages, and the pages work without JavaScript.
- **Trade-off:** less interactive. Every action reloads the page, and
  the Backoffice cannot reuse the same frontend code as the Client Web
  Interface.

## D2 - Client Web Interface: REST

- **Options:** REST or WebSockets.
- **Decision:** **REST** (JSON over HTTP, called with `fetch`).
- **Benefit:** easy to build, test (curl, browser) and document. It
  fits the main actions: list products, search, ask one question and
  get one answer.
- **Trade-off:** no real-time updates. If stock changes in the
  Backoffice, the user only sees it after reloading or after a new
  request. WebSockets could be added later for live stock updates or
  streamed AI answers (optional feature).

## D3 - AI Query Service <-> MCP tools: MCP over Streamable HTTP

- **Options:** MCP over stdio (server started as a subprocess) or MCP
  over HTTP (server runs as its own service).
- **Decision:** **Streamable HTTP**. The MCP Server runs as a separate
  service (e.g. `http://localhost:8001/mcp`); the AI Query Service
  connects with ADK's `McpToolset` and a `tool_filter` limited to the
  three read-only tools.
- **Benefit:** the MCP Server is independent: it can be started,
  tested (MCP Inspector, FastMCP client) and restarted without the
  agent, and other clients can reuse it.
- **Trade-off:** one more process to run and configure (URL, port).
  The AI Query Service fails if the MCP Server is not running, so we
  need a clear error message and a startup order in the README.

## Summary

| Part | Choice | Main benefit | Main limitation |
|------|--------|--------------|-----------------|
| Backoffice | SSR | Simple, fast to build | Less interactive |
| Client Web Interface | REST | Simple, easy to test | No live updates |
| AI <-> MCP | Streamable HTTP | Independent, testable server | Extra service to run |
