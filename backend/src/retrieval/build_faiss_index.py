import numpy as np
import faiss
import json
import os
from pathlib import Path
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def build_faiss_index(embeddings_path: str, ids_path: str, out_path: str):
    try:
        # Create faiss_index directory if it doesn't exist
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Load embeddings and IDs
        logger.info("Loading embeddings and IDs...")
        embeddings = np.load(embeddings_path, allow_pickle=True)
        scheme_ids = np.load(ids_path, allow_pickle=True)
        
        # Verify shapes
        if len(embeddings) != len(scheme_ids):
            raise ValueError(f"Mismatch in number of embeddings ({len(embeddings)}) and IDs ({len(scheme_ids)})")
        
        dim = embeddings.shape[1]
        logger.info(f"Loaded {len(embeddings)} embeddings with dimension {dim}")
        
        # Create and build the FAISS index
        logger.info("Building FAISS index...")
        index = faiss.IndexFlatIP(dim)  # Inner product (cosine similarity) index

        # Add vectors to the index
        index.add(embeddings)

        # Save the FAISS index to faiss_index directory
        index_file = Path(out_path)
        faiss.write_index(index, str(index_file))

        # Save ID mapping in faiss_index directory
        id_map = {
            'index_to_id': scheme_ids.tolist(),
            'dimension': dim,
            'total_vectors': len(scheme_ids)
        }
        id_map_path = Path(out_path).with_suffix('').parent / (Path(out_path).stem + '_id_map.json')
        with open(id_map_path, 'w', encoding='utf-8') as f:
            json.dump(id_map, f, indent=2)

        logger.info(f"FAISS index saved to {index_file}")
        logger.info(f"Total vectors indexed: {index.ntotal}")
        logger.info(f"Index dimension: {dim}")
        
        return True
        
    except FileNotFoundError as e:
        logger.error(f"Required file not found: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    # Check if FAISS is installed
    try:
        import faiss
    except ImportError:
        logger.error("FAISS not installed. Please install it with: pip install faiss-cpu (or faiss-gpu)")
        exit(1)
        
    parser = argparse.ArgumentParser()
    parser.add_argument("--embeddings", default="backend/data/embeddings/scheme_embeddings.npy")
    parser.add_argument("--ids", default="backend/data/embeddings/scheme_ids.npy")
    parser.add_argument("--out", default="backend/data/embeddings/faiss_index.bin")
    args = parser.parse_args()
    build_faiss_index(args.embeddings, args.ids, args.out)
