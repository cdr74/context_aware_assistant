# context_aware_assistan



## Installation

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

You need a Open API key to run this. Provide the key and url in a ".env" file
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
    --file FILE           Path to source code file (used for unit tests only)
    --style {unit,api,ui}
                            Type of test to generate
    --db DB               Chroma collection name
    --top_k TOP_K         Number of context chunks to retrieve
    --model MODEL         OpenAI model to use (default: gpt-4o)
    --output OUTPUT       Optional file path to save generated test
```

Example_
> python code/generate_with_context.py --file example/src/calculator.py --style unit --db code_docs --output ./out/gen_test.py


This is the centerpiece of the framework and needs more refinement. 


## Check your cost

https://platform.openai.com/settings/organization/usage