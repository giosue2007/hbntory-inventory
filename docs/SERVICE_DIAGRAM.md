# HBntory - Service Diagram

`````mermaid
flowchart LR
    staff([Staff]) --> BO[Backoffice<br/>SSR pages]
    user([User]) --> CWI[Client Web Interface<br/>HTML/CSS/JS]

    BO --> INV[Inventory API<br/>FastAPI]
    CWI -- REST --> INV
    CWI -- "REST POST /ask" --> AI[AI Query Service<br/>ADK + Ollama]

    AI -- "MCP (Streamable HTTP)" --> MCP[MCP Server<br/>FastMCP]
    MCP -- REST --> INV

    INV --> DB[(SQLite<br/>stock, movements, users)]
    INV -- REST --> PAPI[External Product API]
````

Text version:

    Staff --> Backoffice (SSR) ----------------\
                                                 > Inventory API --> SQLite
    User  --> Client Web Interface --REST------/        |
                     |                                   \--> Product API (external)
                     \--REST /ask--> AI Query Service
                                          |
                                          \--MCP--> MCP Server --REST--> Inventory API
