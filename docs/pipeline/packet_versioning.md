# Evidence packet versioning

Evidence packets have two independent packet version fields:

- `schema_version` identifies the structural contract and validator.
- `packet_version` identifies packet semantics and selection/governance policy.

They are separate from `input_snapshot_schema_version`,
`input_snapshot_calculation_version`, and each calculator's version. A change in one input or
calculator version must not be represented as a packet-version change unless the packet contract or
selection policy also changes.

## Compatibility policy

The v1 validator accepts exactly packet schema/version `1.0.0` and packet type
`exposure_change_review`. Unsupported versions and types fail explicitly. A future reader may add a
version dispatcher, but must retain the v1 validator for backward-compatible reading.

Adding an optional field is compatible when old readers can ignore it without changing existing
meaning. It requires updated serialization, validation, documentation, and round-trip tests.
Changing a required field, changing a field's meaning, changing ID/reference semantics, or changing
governance is breaking and requires a new schema or packet version plus an explicit migration.

New packet types must define their own selection policy and validator behavior. They must not be
silently accepted by `exposure_change_review`.

## Migration policy and test requirements

Migrations must be deterministic, documented, and preserve original input versions and provenance.
They must not repair client/date mismatches or invent missing evidence. A migrated packet must pass
the destination validator and have fixtures for representative, partial, invalid, and
privacy-sensitive inputs.

Every versioned change must test valid construction, invalid metadata and dates, client separation,
ID/reference integrity, evidence deduplication, warnings, JSON round-trip equivalence, deterministic
ordering, privacy filtering, governance restrictions, and source/database immutability where real
inputs are used.
