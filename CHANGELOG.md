# Changelog

## 0.1.1 - 2024-03-14

### Added

- `launch.py` script to make starting Concierge simpler.
- Collaborator Guide to clarify our internal policy on handling branches and versioning.

## 0.1.0 2024-03-06

Initial Data Concierge MVP release for public testing.

### Features

- `install.py` helper to ensure correct configuration
- Ability to ingest PDF documents and web pages into a Milvus vector database
- Ability to retrieve documents from the database that match the user's prompt
- Ability to answer the user's prompt using the retrieved documents as the context and Ollama to generate the response
- Streamlit powered Web UI
- CLI scripts also available


