import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from pathlib import Path
import argparse

def build_embed_doc_row(row: pd.Series) -> str:
    name = str(row.get("scheme_name", "")).strip()
    desc = str(row.get("description_raw", "")).strip()
    elig = str(row.get("eligibility_raw", "")).strip()
    state_scope = str(row.get("state_scope", "")).strip()
    category = str(row.get("category", "")).strip()
    source = str(row.get("source_url", "")).strip()
    parts = [
        name,
        "Description:\n" + desc if desc else "",
        "Eligibility:\n" + elig if elig else "",
        f"State scope: {state_scope}" if state_scope else "",
        f"Category: {category}" if category else "",
        f"Source: {source}" if source else "",
    ]
    doc = "\n\n".join([p for p in parts if p])
    if len(doc) > 4000:
        doc = doc[:3997] + "..."
    return doc

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="backend/data/processed/scheme_embed_docs.parquet")
    parser.add_argument("--model", default="sentence-transformers/paraphrase-mpnet-base-v2")
    parser.add_argument("--out", default="backend/data/embeddings/scheme_embeddings.npy")
    parser.add_argument("--ids_out", default="backend/data/embeddings/scheme_ids.npy")
    args = parser.parse_args()

    print("Loading scheme data...")
    df = pd.read_parquet(args.input)

    if 'embed_doc' not in df.columns:
        if {'scheme_name','description_raw','eligibility_raw'}.issubset(df.columns):
            df['embed_doc'] = df.apply(build_embed_doc_row, axis=1)
        else:
            raise ValueError("Input must have 'embed_doc' or the core text columns ('scheme_name','description_raw','eligibility_raw')")
    if 'scheme_id' not in df.columns:
        # If not present, derive from index
        df['scheme_id'] = df.index.astype(str)

    print("Loading sentence transformer model...")
    model = SentenceTransformer(args.model)

    print("Computing embeddings (this may take a while)...")
    embed_docs = df['embed_doc'].tolist()
    embeddings = model.encode(
        embed_docs,
        convert_to_numpy=True,
        normalize_embeddings=True,
        batch_size=64,
        show_progress_bar=True
    )

    scheme_ids = df['scheme_id'].astype(str).values.astype("U")

    Path(args.out).parent.mkdir(exist_ok=True, parents=True)
    print("Saving results...")
    np.save(args.out, embeddings.astype(np.float32))
    np.save(args.ids_out, scheme_ids)

    print("\nResults saved successfully:")
    print(f"Embeddings shape: {embeddings.shape} (num_schemes × embedding_dim)")
    print(f"Scheme IDs shape: {scheme_ids.shape}")

if __name__ == "__main__":
    main()
