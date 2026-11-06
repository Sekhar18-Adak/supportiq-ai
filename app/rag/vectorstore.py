import time
import logging

from openai import OpenAI, APIError, RateLimitError
from langchain_core.embeddings import Embeddings

from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore

from app.core.config import get_settings


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

logger = logging.getLogger(__name__)

settings = get_settings()

_embeddings = None
_vectorstore = None


# NVIDIA Nemotron 3.5 Embed 8B
EMBEDDING_DIMENSIONS = {
    "openai/text-embedding-3-small": 1536,
}


BATCH_SIZE = 2
MAX_RETRIES = 3


# --------------------------------------------------
# EMBEDDING DIMENSION
# --------------------------------------------------

def get_embedding_dimension(
    model_name: str | None = None
) -> int:

    name = (
        model_name or settings.embedding_model or ""
    ).strip().lower()

    if not name:
        raise RuntimeError(
            "Embedding model is not configured"
        )

    if name in EMBEDDING_DIMENSIONS:
        return EMBEDDING_DIMENSIONS[name]

    raise ValueError(
        f"Unsupported embedding model: {name}. "
        "Add its dimension to EMBEDDING_DIMENSIONS."
    )


# --------------------------------------------------
# OPENROUTER EMBEDDINGS
# --------------------------------------------------

class OpenRouterEmbeddings(Embeddings):

    def __init__(self):

        self.model = settings.embedding_model

        self.client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            timeout=60.0,
            max_retries=0,
        )

        self.dimension = get_embedding_dimension(
            self.model
        )

    # ----------------------------------------------
    # API REQUEST WITH RETRY
    # ----------------------------------------------

    def _create_embedding(
        self,
        texts: list[str],
        input_type: str
    ):

        for attempt in range(MAX_RETRIES):

            try:

                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                    extra_body={
                        "input_type": input_type
                    }
                )

                # Maintain original input ordering
                data = sorted(
                    response.data,
                    key=lambda item: item.index
                )

                vectors = [
                    item.embedding
                    for item in data
                ]

                # Validate response
                if len(vectors) != len(texts):
                    raise RuntimeError(
                        "Embedding count mismatch. "
                        f"Expected {len(texts)}, "
                        f"received {len(vectors)}"
                    )

                for vector in vectors:

                    if len(vector) != self.dimension:
                        raise ValueError(
                            f"Embedding dimension mismatch. "
                            f"Expected {self.dimension}, "
                            f"received {len(vector)}"
                        )

                return vectors

            except RateLimitError:

                if attempt == MAX_RETRIES - 1:
                    raise

                wait_time = 2 ** attempt

                logger.warning(
                    "OpenRouter rate limit. Retrying in %s seconds.",
                    wait_time
                )

                time.sleep(wait_time)

            except APIError as error:

                # Retry temporary server errors
                if (
                    error.status_code not in (500, 502, 503, 504)
                    or attempt == MAX_RETRIES - 1
                ):
                    raise

                wait_time = 2 ** attempt

                logger.warning(
                    "OpenRouter server error (%s). "
                    "Retrying in %s seconds.",
                    error.status_code,
                    wait_time
                )

                time.sleep(wait_time)

        raise RuntimeError(
            "Embedding generation failed after retries"
        )

    # ----------------------------------------------
    # DOCUMENT EMBEDDINGS
    # ----------------------------------------------

    def embed_documents(
        self,
        texts: list[str]
    ) -> list[list[float]]:

        if not texts:
            return []

        all_embeddings = []

        total_batches = (
            len(texts) + BATCH_SIZE - 1
        ) // BATCH_SIZE

        logger.info(
            "Generating embeddings for %s documents in %s batches.",
            len(texts),
            total_batches
        )

        for i in range(0, len(texts), BATCH_SIZE):

            batch = texts[i:i + BATCH_SIZE]

            logger.info(
                "Processing embedding batch %s/%s",
                (i // BATCH_SIZE) + 1,
                total_batches
            )

            vectors = self._create_embedding(
                texts=batch,
                input_type="passage"
            )

            all_embeddings.extend(vectors)

        return all_embeddings

    # ----------------------------------------------
    # QUERY EMBEDDING
    # ----------------------------------------------

    def embed_query(
        self,
        text: str
    ) -> list[float]:

        vectors = self._create_embedding(
            texts=[text],
            input_type="query"
        )

        return vectors[0]


# --------------------------------------------------
# GET EMBEDDINGS
# --------------------------------------------------

def get_embeddings():

    global _embeddings

    if _embeddings is None:

        if not settings.openrouter_api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is missing"
            )

        _embeddings = OpenRouterEmbeddings()

    return _embeddings


# --------------------------------------------------
# PINECONE INDEX MANAGEMENT
# --------------------------------------------------

def ensure_index():

    if not settings.pinecone_api_key:
        raise RuntimeError(
            "PINECONE_API_KEY is missing"
        )

    desired_dimension = get_embedding_dimension()

    pc = Pinecone(
        api_key=settings.pinecone_api_key
    )

    index_names = pc.list_indexes().names()

    # Check existing index
    if settings.pinecone_index_name in index_names:

        index_info = pc.describe_index(
            settings.pinecone_index_name
        )

        current_dimension = index_info.dimension

        if current_dimension != desired_dimension:

            raise ValueError(
                f"Pinecone dimension mismatch! "
                f"Existing: {current_dimension}, "
                f"Required: {desired_dimension}. "
                "Create a new index with the correct dimension. "
                "Existing index will NOT be deleted."
            )

        logger.info(
            "Existing Pinecone index found: %s",
            settings.pinecone_index_name
        )

    # Create index if missing
    else:

        logger.info(
            "Creating Pinecone index: %s",
            settings.pinecone_index_name
        )

        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=desired_dimension,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            ),
        )

        # Wait until index is ready
        while not pc.describe_index(
            settings.pinecone_index_name
        ).status["ready"]:

            time.sleep(1)

        logger.info(
            "Pinecone index created successfully."
        )

    return pc.Index(
        settings.pinecone_index_name
    )


# --------------------------------------------------
# GET VECTOR STORE
# --------------------------------------------------

def get_vectorstore():

    global _vectorstore

    if _vectorstore is None:

        index = ensure_index()

        _vectorstore = PineconeVectorStore(
            index=index,
            embedding=get_embeddings(),
            namespace=settings.pinecone_namespace,
        )

        logger.info(
            "Pinecone vector store initialized. Namespace: %s",
            settings.pinecone_namespace
        )

    return _vectorstore


# --------------------------------------------------
# GET RETRIEVER
# --------------------------------------------------

def get_retriever():

    return get_vectorstore().as_retriever(
        search_kwargs={
            "k": settings.top_k
        }
    )


# --------------------------------------------------
# ADD DOCUMENTS
# --------------------------------------------------

def add_documents(chunks):

    if not chunks:
        logger.warning(
            "No document chunks provided for insertion."
        )
        return []

    store = get_vectorstore()

    logger.info(
        "Inserting %s document chunks into Pinecone.",
        len(chunks)
    )

    ids = store.add_documents(chunks)

    logger.info(
        "Successfully inserted %s vectors into Pinecone.",
        len(ids)
    )

    return ids
