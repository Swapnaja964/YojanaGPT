import re


def load_clusters(file_path: str):
    clusters = {}
    current_cluster = None

    with open(file_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue

            # Match: Cluster 1: OR Cluster 1 →
            m = re.match(r"^Cluster\s+(\d+)\s*(?:\:|→)\s*(.*)$", line)
            if m:
                cluster_id = m.group(1)
                label = (m.group(2) or "").strip()

                current_cluster = f"cluster_{cluster_id}".lower()
                clusters[current_cluster] = []

                if label:
                    clusters[current_cluster].append(label.lower())

                continue

            if current_cluster:
                tags = [v.strip().lower() for v in line.split(",") if v.strip()]
                clusters[current_cluster].extend(tags)

    return clusters


def clean_clusters(clusters: dict):
    cleaned_clusters = {}

    for cluster_name, tags in clusters.items():
        cleaned_set = set()

        for tag in tags:
            t = tag.lower().strip()

            # remove punctuation
            t = re.sub(r"[^\w\s%]", "", t)

            # normalize spacing
            t = re.sub(r"\s+", " ", t)

            # remove weak words
            t = t.replace("schemes", "").replace("scheme", "")
            t = t.replace("activities", "").replace("activity", "")

            t = t.strip()

            if t:
                cleaned_set.add(t)

        cleaned_clusters[cluster_name] = list(cleaned_set)

    return cleaned_clusters


def build_tag_map(cleaned_clusters: dict):
    tag_map = {}

    for cluster_name, tags in cleaned_clusters.items():
        if not tags:
            continue

        # sort tags by length (shortest first)
        sorted_tags = sorted(tags, key=lambda x: (len(x), x))

        # default canonical = shortest
        canonical = sorted_tags[0]

        # prefer single-word tag if available
        for t in sorted_tags:
            if " " not in t:
                canonical = t
                break

        tag_map[canonical] = tags

    return tag_map


def build_reverse_tag_map(tag_map: dict):
    reverse_map = {}

    for canonical, variants in tag_map.items():
        for v in variants:
            reverse_map[v] = canonical

    return reverse_map


def validate_tag_map(tag_map: dict):
    issues = {
        "bad_canonical": [],
        "noisy_clusters": [],
        "suspicious_tags": []
    }

    for canonical, variants in tag_map.items():

        # Rule 1: canonical too short or numeric
        if len(canonical) <= 3 or canonical.isdigit():
            issues["bad_canonical"].append((canonical, variants[:5]))

        # Rule 2: too many unrelated phrases (heuristic)
        unique_words = set()
        for v in variants:
            unique_words.update(v.split())

        if len(unique_words) > 20:
            issues["noisy_clusters"].append((canonical, variants[:5]))

        # Rule 3: garbage-like tags
        for v in variants:
            if re.match(r"^[0-9]+$", v) or len(v) <= 2:
                issues["suspicious_tags"].append(v)

    return issues


def improve_canonical_tags(tag_map: dict):
    improved_map = {}

    for canonical, variants in tag_map.items():

        # try to find better canonical (prefer meaningful word)
        candidates = [v for v in variants if len(v) > 4 and not v.isdigit()]

        if candidates:
            # pick most frequent word
            word_freq = {}
            for v in candidates:
                for word in v.split():
                    if len(word) > 3:
                        word_freq[word] = word_freq.get(word, 0) + 1

            if word_freq:
                better = max(word_freq, key=word_freq.get)
                improved_map[better] = variants
                continue

        improved_map[canonical] = variants

    return improved_map


if __name__ == "__main__":
    clusters = load_clusters("cluster_named.txt")
    cleaned_clusters = clean_clusters(clusters)

    tag_map = build_tag_map(cleaned_clusters)
    tag_map = improve_canonical_tags(tag_map)

    reverse_map = build_reverse_tag_map(tag_map)

    issues = validate_tag_map(tag_map)

    print("\nIMPROVED CANONICAL TAGS:\n", list(tag_map.keys())[:10])

    print("\nISSUES FOUND:\n")
    print("Bad Canonical:", issues["bad_canonical"][:5])
    print("Noisy Clusters:", issues["noisy_clusters"][:3])
    print("Suspicious Tags:", issues["suspicious_tags"][:10])
