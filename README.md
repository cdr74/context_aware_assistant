# 🛠 AI-Powered Test Code Assistant

A command-line toolset for software developers (Java & Python focus) that:
1. Lets you **define project context** (source code folders, documentation, etc.) in a local vector database.
2. Lets you **inspect the context** and ask questions about your codebase.
3. Provides an **iterative, persistent prompt interface** to generate or update tests:
   - Unit tests (positive + negative cases)
   - API tests (based on API documentation)
   - UI tests (Playwright)
4. Supports **refinement loops** so you can tweak or correct generated tests without starting over.

---

## 📂 Architecture Overview

The toolset is built as **three main scripts**, each with a clear responsibility, using **ChromaDB** as the local vector store and **OpenAI GPT models** for generation.


      ┌────────────────────────────────────────────────────┐
      │  1. Context Ingestion (generate_with_context.py)   │
      │  - Reads source/docs                               │
      │  - Generates embeddings                            │
      │  - Stores in ChromaDB                              │
      └────────────────────────────────────────────────────┘
                      │
                      ▼
      ┌────────────────────────────────────────────────────┐
      │  2. Context Query                                  │
      │  - Ask questions about project                     │
      │  - Retrieves top-k chunks from ChromaDB            │
      │  - Uses GPT to answer                              │
      └────────────────────────────────────────────────────┘
                      │
                      ▼
      ┌────────────────────────────────────────────────────┐
      │  3. Test Generation (generate_tests.py)            │
      │  - Retrieves relevant context                      │
      │  - Applies prompt template (unit/api/ui)           │
      │  - Uses persistent chat history for refinement     │
      │  - Saves output optionally to file                 │
      └────────────────────────────────────────────────────┘



## Installation

Perform the following steps
- python3 -m venv venv
- source venv/bin/activate
- pip install --upgrade pip
- pip install -r requirements.txt
- touch .env

You need a Open API key to run this, please add to the .env the following keys
```
    OPENAI_API_KEY=sk-...
    OPENAI_API_BASE=https://api.openai.com/v1
```


## Usage


### Create Chroma DB

To start the process, create a vector db based on source code, tests and documents. 
The collection can be updated by running the cscript again. 

```
usage: create_vector_db.py [-h] [--src SRC] [--test TEST] [--doc DOC] [--db DB]

Create a Chroma vector DB from source/test/doc directories.

options:
  -h, --help   show this help message and exit
  --src SRC    Directory with source code files (.py/.java)
  --test TEST  Directory with test code files (.py/.java)
  --doc DOC    Directory with markdown docs (.md)
  --db DB      Name of the Chroma collection (default: code_docs)
```

Example:
> python ./code/create_vector_db.py --src ./example/src --test ./example/test --doc ./example/doc --db code_docs


### Inspect Chroma DB Helper

In order to understand what is in the chrome db, use the following helper scripts, first list all collections:
> python ./code/list_collections.py

Then inspect the collection

```
usage: query_vector_db.py [-h] [--db DB] --query QUERY [--top_k TOP_K] [--tag {source,test,doc}]

Query a Chroma vector DB collection.

options:
  -h, --help            show this help message and exit
  --db DB               Collection name to query (default: code_docs)
  --query QUERY         Search query text
  --top_k TOP_K         Number of results to return (default: 3)
  --tag {source,test,doc}
                        Optional filter by document type
```

Example:
> python code/query_vector_db.py --db code_docs  --query "what operations are supported" --tag source


### Generate code / test with context

This is the core of the tool, allowing to generate different test types with the context in a chroma db.

```
usage: generate_with_context.py [-h] [--file FILE] [--style {unit,api,ui}] [--db DB] [--top_k TOP_K]
                                [--model MODEL] [--output OUTPUT]

Generate test code using OpenAI + Chroma vector DB as context.

options:
  -h, --help            show this help message and exit
  --file FILE           Path to source code file (required for unit tests)
  --style {unit,api,ui} Type of test to generate:
                          - unit → Generates positive & negative unit tests (requires --file)
                          - api  → Prompts for what to test, retrieves API docs, and writes API tests
                          - ui   → Prompts for user flow, retrieves UI context, and writes Playwright tests
  --db DB               Chroma collection name (default: code_docs)
  --top_k TOP_K         Number of context chunks to retrieve (default: 4)
  --model MODEL         OpenAI model to use (default: gpt-4o)
  --output OUTPUT       Optional file path to save generated test
```

Example:
> python code/generate_with_context.py --file example/src/calculator.py --style unit --db code_docs --output ./out/test_calculator.py
> python code/generate_with_context.py --style api --db code_docs --output ./out/test_api.py
> python code/generate_with_context.py --style ui --db code_docs --output ./out/test_ui.py



## Check your cost

https://platform.openai.com/settings/organization/usage