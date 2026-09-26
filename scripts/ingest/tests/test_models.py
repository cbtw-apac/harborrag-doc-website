import json
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

import pytest

from ingest.models import Channel, IngestRequest, SyncEntry, SyncState


def test_sync_state_round_trips_through_json_with_expected_keys():
    state = SyncState(
        current=SyncEntry(
            label="Next",
            channel=Channel.MAIN,
            source_ref="refs/heads/main",
            source_sha="60609c8",
            synced_at="2026-09-16T10:00:00Z",
        ),
        versions={
            "2.0": SyncEntry(
                label="2.0.1",
                channel=Channel.STABLE,
                source_ref="refs/tags/harborrag-v2.0.1",
                source_sha="abc123",
                synced_at="2026-09-15T08:00:00Z",
            ),
        },
    )

    payload = json.loads(json.dumps(asdict(state)))

    assert set(payload.keys()) == {"current", "versions"}
    assert set(payload["current"].keys()) == {
        "label",
        "channel",
        "source_ref",
        "source_sha",
        "synced_at",
    }
    assert payload["current"]["label"] == "Next"
    assert payload["current"]["channel"] == "main"
    assert payload["current"]["source_ref"] == "refs/heads/main"
    assert payload["current"]["source_sha"] == "60609c8"
    assert payload["current"]["synced_at"] == "2026-09-16T10:00:00Z"

    assert set(payload["versions"].keys()) == {"2.0"}
    assert set(payload["versions"]["2.0"].keys()) == {
        "label",
        "channel",
        "source_ref",
        "source_sha",
        "synced_at",
    }
    assert payload["versions"]["2.0"]["label"] == "2.0.1"
    assert payload["versions"]["2.0"]["channel"] == "stable"
    assert payload["versions"]["2.0"]["source_ref"] == "refs/tags/harborrag-v2.0.1"
    assert payload["versions"]["2.0"]["source_sha"] == "abc123"
    assert payload["versions"]["2.0"]["synced_at"] == "2026-09-15T08:00:00Z"


def test_sync_entry_allows_null_fields_before_first_sync():
    entry = SyncEntry(
        label="Next",
        channel=Channel.MAIN,
        source_ref=None,
        source_sha=None,
        synced_at=None,
    )

    payload = json.loads(json.dumps(asdict(entry)))

    assert payload["source_ref"] is None
    assert payload["source_sha"] is None
    assert payload["synced_at"] is None


def test_sync_entry_is_immutable():
    entry = SyncEntry(
        label="Next",
        channel=Channel.MAIN,
        source_ref=None,
        source_sha=None,
        synced_at=None,
    )

    with pytest.raises(FrozenInstanceError):
        entry.label = "changed"


def test_ingest_request_defaults():
    request = IngestRequest(
        source=Path("/tmp/HarborRAG"),
        site=Path("/tmp/harborrag-doc-website"),
        channel=Channel.STABLE,
        product_version="2.0.1",
        source_ref="refs/tags/harborrag-v2.0.1",
        source_sha="abc123",
    )

    assert request.keep_minors == 2
    assert request.dry_run is False
    assert request.force is False
