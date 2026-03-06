import numpy as np
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss


def build_embed_doc_row(row: pd.Series) -> str:
    name = str(row.get("scheme_name", "")).strip()
    desc = str(row.get("description_raw", "")).strip()
    elig = str(row.get("eligibility_raw", "")).strip()
    benefits = str(row.get("benefits_raw", "")).strip()
    process = str(row.get("process_raw", "")).strip()
    state_scope = str(row.get("state_scope", "")).strip()
    category = str(row.get("category", "")).strip()
    source = str(row.get("source_url", "")).strip()
    parts = [
        name,
        "Description:\n" + desc if desc else "",
        "Eligibility:\n" + elig if elig else "",
        "Benefits:\n" + benefits if benefits else "",
        "Process:\n" + process if process else "",
        f"State scope: {state_scope}" if state_scope else "",
        f"Category: {category}" if category else "",
        f"Source: {source}" if source else "",
    ]
    return "\n\n".join([p for p in parts if p])


def main():
    input_path = Path("backend/data/processed/schemes_with_rules.parquet")
    out_index = Path("backend/data/embeddings/faiss_index.bin")
    out_ids = Path("backend/data/embeddings/scheme_ids.npy")

    print("Loading schemes...")
    df = pd.read_parquet(input_path)
    n = len(df)
    print(f"Loaded {n} schemes from {input_path}")

    if "scheme_id" not in df.columns:
        df["scheme_id"] = df.index.astype(str)
    scheme_ids = df["scheme_id"].astype(str).values.astype("U")

    print("Building text documents for embedding...")
    embed_docs = df.apply(build_embed_doc_row, axis=1).tolist()

    print("Loading embedding model: BAAI/bge-large-en-v1.5")
    model = SentenceTransformer("BAAI/bge-large-en-v1.5")

    print("Encoding and normalizing embeddings...")
    embeddings = model.encode(
        embed_docs,
        convert_to_numpy=True,
        normalize_embeddings=True,
        batch_size=32,
        show_progress_bar=True,
    ).astype(np.float32)

    dim = embeddings.shape[1]
    print(f"Embedding dimension: {dim}")

    print("Building FAISS IndexFlatIP (cosine similarity)...")
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    print(f"Index size: {index.ntotal}")

    out_index.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out_index))
    np.save(out_ids, scheme_ids)

    print("Saved FAISS index and IDs:")
    print(f"- Index: {out_index}")
    print(f"- IDs:   {out_ids}")
    print("Rebuild complete.")


if __name__ == "__main__":
    main()
