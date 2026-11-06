from app.rag.vectorstore import get_embeddings

print("Testing Nemotron Embeddings...")

try:
    embeddings = get_embeddings()

    # Test query embedding
    query = "How can I reset my company password?"

    print("\nTesting query embedding...")

    vector = embeddings.embed_query(query)

    print("Query embedding successful!")
    print("Dimensions:", len(vector))

    # Test document embedding
    documents = [
        "Employees must use company VPN.",
        "MFA is required for company accounts."
    ]

    print("\nTesting document embeddings...")

    vectors = embeddings.embed_documents(documents)

    print("Document embeddings successful!")
    print("Number of vectors:", len(vectors))

    for i, vector in enumerate(vectors):
        print(f"Document {i + 1} dimensions: {len(vector)}")

    print("\nALL EMBEDDING TESTS PASSED!")

except Exception as e:
    print("\nEMBEDDING TEST FAILED!")
    print("Error:", repr(e))