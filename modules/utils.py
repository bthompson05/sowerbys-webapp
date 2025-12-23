import os

def read_graphql(filename: str) -> str:
    with open(os.path.join(os.getcwd(), "graphql", f"{filename}.gql")) as f:
        return f.read()