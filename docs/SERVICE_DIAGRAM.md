# HBntory - Service Diagram

`````mermaid
flowchart LR
    staff([Staff]) --> BO[Backoffice<br/>SSR pages]
    user([User]) --> CWI[Client Web Interface<br/>HTML/CSS/JS]

    BO --> INV[Inventory API<br/>FastAPI]
    CWI -- REST --> INV
    CWI -- "REST POST /ask" --> AI[AI Query Service<br/>ADK + Ollama]

