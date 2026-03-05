import pandas as pd
import re

MAX_EMBED_DOC_LEN = 4000  # max characters for embed_doc


def clean_text(text):
    """Clean and normalize text by handling None/NaN and normalizing whitespace."""
    if pd.isna(text):
        return ""
    # Convert to string in case it's not already
    text = str(text)
    # Normalize whitespace (collapse multiple spaces/newlines)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def build_single_embed_doc(row: pd.Series) -> str:
    """
    Build a single embed_doc string for a given scheme row.

    Priority:
    1. Always keep scheme_name, Description, and Eligibility.
    2. Add Benefits and Process only if space allows.
    3. Always include State scope, Category, and Source at the end.
    4. Never exceed MAX_EMBED_DOC_LEN characters (hard cap).
    """
    scheme_name = row["scheme_name"]
    description = row["description_raw"]
    benefits = row["benefits_raw"]
    eligibility = row["eligibility_raw"]
    process = row["process_raw"]
    state_scope = row["state_scope"]
    category = row["category"]
    source_url = row["source_url"]

    # Metadata block (always appended at the end)
    meta_block = (
        f"State scope: {state_scope}\n"
        f"Category: {category}\n"
        f"Source: {source_url}"
    )

    # Core head: scheme + description + eligibility
    head = (
        f"{scheme_name}\n\n"
        f"Description:\n{description}\n\n"
        f"Eligibility:\n{eligibility}\n\n"
    )

    # Optional sections
    benefits_block = ""
    if benefits:
        benefits_block = f"Benefits:\n{benefits}\n\n"

    process_block = ""
    if process:
        process_block = f"Process:\n{process}\n\n"

    # Start assembling the document
    embed_doc = head

    # We will try to add Benefits and Process in order, as long as we don't exceed limit
    optional_sections = [benefits_block, process_block]

    for section in optional_sections:
        if not section:
            continue

        # Remaining capacity before we MUST reserve room for meta_block
        remaining_for_sections = MAX_EMBED_DOC_LEN - len(embed_doc) - len(meta_block) - 1
        if remaining_for_sections <= 0:
            break

        if len(section) <= remaining_for_sections:
            # We can fit the whole section
            embed_doc += section
        else:
            # We can only fit part of the section
            truncated_text = section[:remaining_for_sections]

            # Avoid cutting a word in the middle if possible
            if " " in truncated_text:
                truncated_text = truncated_text.rsplit(" ", 1)[0]

            truncated_text += "..."
            embed_doc += truncated_text + "\n\n"
            # No need to try adding more sections after this; we are basically full
            break

    # Finally, append metadata
    embed_doc += meta_block

    # Final safety: hard truncate if for some reason we still exceed the limit
    if len(embed_doc) > MAX_EMBED_DOC_LEN:
        safe_trunc = embed_doc[: MAX_EMBED_DOC_LEN - 3]
        if " " in safe_trunc:
            safe_trunc = safe_trunc.rsplit(" ", 1)[0]
        embed_doc = safe_trunc + "..."

    return embed_doc


def build_embedding_docs():
    # Load the input parquet file
    df = pd.read_parquet("backend/data/processed/schemes_with_rules.parquet")

    # Ensure the expected columns exist (basic sanity check)
    expected_cols = [
        "scheme_name",
        "description_raw",
        "benefits_raw",
        "eligibility_raw",
        "process_raw",
        "state_scope",
        "category",
        "source_url",
    ]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in schemes_with_rules.parquet: {missing}")

    # Clean relevant text columns once (vectorized) instead of per-row in the loop
    for col in expected_cols:
        df[col] = df[col].apply(clean_text)

    # Build embed_doc for each row
    df["embed_doc"] = df.apply(build_single_embed_doc, axis=1)

    # Save the result
    output_path = "backend/data/processed/scheme_embed_docs.parquet"
    df.to_parquet(output_path, index=False)
    print(f"Successfully saved {len(df)} schemes with embedding documents to '{output_path}'")


if __name__ == "__main__":
    build_embedding_docs()
