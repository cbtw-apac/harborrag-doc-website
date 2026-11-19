set -euo pipefail
URL=https://github.com/cbtw-apac/HarborRAG.git
SRC="../../source"
FAILED=()
# Dummy data
TARGETS='[
    {
        "key":"current",
        "ref":"refs/heads/main",
        "sha":"dc001f49baf19bf084dc5a444f773a0095022fff",
        "channel":"main",
        "product_version":"auto",
        "label":"Next"
    },
    {
        "key":"2.1",
        "ref":"refs/tags/harborrag-v2.1.0",
        "sha":"81789ac950e0e488a3e17973278b46dfa0878cff",
        "channel":"stable",
        "product_version":"2.1.0",
        "label":"2.1.0"
    },
    {
        "key":"2.2",
        "ref":"refs/tags/harborrag-v2.2.0",
        "sha":"a3524cae36d03aa52d5bf24aa85f51a5852c619c",
        "channel":"stable",
        "product_version":"2.2.0",
        "label":"2.2.0"
    }
]'

while IFS= read -r ITEM; do
    KEY=$(jq -r .key <<<"$ITEM")
    REF=$(jq -r .ref <<<"$ITEM")
    SHA=$(jq -r .sha <<<"$ITEM")
    CHANNEL=$(jq -r .channel <<<"$ITEM")
    VERSION=$(jq -r .product_version <<<"$ITEM")

    if ! { [[ "$SHA" =~ ^[0-9a-f]{40}$ ]] \
        && [[ "$REF" =~ ^refs/(heads|tags)/[A-Za-z0-9._/-]+$ ]] \
        && [[ "$CHANNEL" =~ ^(main|prerelease|stable)$ ]] \
        && [[ "$VERSION" =~ ^[A-Za-z0-9.+-]+$ ]]; }; then
        echo "::error::invalid target: $ITEM"; FAILED+=("$KEY"); continue
    fi

    echo "::group::$KEY ← $REF @ ${SHA:0:7} ($CHANNEL)"
    if ! {
        rm -rf "$SRC" && git init -q "$SRC" \
        && git -C "$SRC" fetch -q --depth 1 "$URL" "$SHA" \
        && git -C "$SRC" checkout -q --detach FETCH_HEAD \
        && uv run --locked ingest.py --source "$SRC" --site ../../website \
                --channel "$CHANNEL" --product-version "$VERSION" \
                --source-ref "$REF" --source-sha "$SHA"
    }; then
        echo "::error::sync failed for $KEY ($REF)"; FAILED+=("$KEY")
    fi
    echo "::endgroup::"
done < <(jq -c '.[]' <<<"$TARGETS")

rm -rf "$SRC"
echo "changed=$(git -C ../../ status --porcelain | grep -q . && echo true || echo false)"
echo "failed=${FAILED[*]:-}"