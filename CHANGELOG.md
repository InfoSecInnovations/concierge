# Changelog

## 0.5.0 - TBD

- RBAC is here! Concierge can optionally be configured to use Keycloak to handle user accounts and permissions.
- The installer script has been replaced by an executable file available for Windows, Linux and MacOS. This executable serves up a web UI to enable you to configure Concierge locally or remotely. This should make it a lot easier to get Concierge up and running, we felt that the text based installer was no longer practical and it was running into issues with different OSes and Python versions.
- Still a work in progress but some automated tests are now present. This will help us catch bugs more easily in the various permutations of Concierge that are possible.

## 0.4.0 - 2024-09-05

### Changes

- OpenSearch backend now uses multiple indices to store document metadata, this avoids unnecessary duplication of said metadata and allows us to more easily reference specific documents in the collection.
- Documents are inserted into OpenSearch database instead of uploads directory.
- Some of the CLI scripts have been renamed to be more consistent and better fit the new database schema.
- Volumes are managed by Docker instead of mounting directories from the host OS. This allows us to resolve some issues with permissions that may have been preventing Linux users from using the app.
- Chat UI uses new chatbot interface provided by Shiny for Python.

### Added

- Install script makes necessary changes if previously installed version is incompatible with the one being installed. As we approach 1.0 we will refine this system to minimize data loss when upgrading, while still in Alpha phase we make no such promises!

## 0.3.0 - 2024-07-03

### Changes

- Vector Database backend now uses OpenSearch instead of Milvus. This will give us many more options with managing metadata from the ingested documents as well as strong RBAC features.
- install scripts should be a little more intuitive to use now.
- Loader page has been merged into Collection Management.
- The production version of Concierge now runs entirely in Docker, this should limit the number of issues relating to Python configurations.
- The user no longer needs to download the repository from GitHub to install Concierge, it is now done via the PyPI package manager.
- Default port set to 15130

### Added

- `delete_index` command
- `documents` command
- `list_indices` command
- `delete_document` command
- Ability to view documents in collection
- Ability to delete documents from collection
- Ability to set web app port in environment variables

## 0.2.0 - 2024-05-15

### Changes

- Web GUI ported from Streamlit to Shiny for Python: we have found Shiny to be much more robust, especially with handling long tasks such as ingesting documents.
- `launch.py` and `install.py` improved to (hopefully) work on more Operating Systems.

### Added

- Theme selector for Web GUI

## 0.1.3 - 2024-03-14

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


