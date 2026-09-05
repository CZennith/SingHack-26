# Result contract versioning

Current result-contract version: **1.0.0**.

Version numbers use `MAJOR.MINOR.PATCH`:

- **MAJOR** means a breaking removal, rename, type/meaning change, or incompatible validation rule.
- **MINOR** means a backward-compatible addition of an optional field or capability.
- **PATCH** means documentation or validation correction without a compatibility change.

`schema_version` identifies this result envelope. It is different from
`calculator_version`, `input_snapshot_schema_version`, and
`input_snapshot_calculation_version`. A calculator must record all four concepts where applicable.

## Compatibility rules

`validate_result()` dispatches on `result_metadata.schema_version`. Version 1.0.0 is supported;
unsupported versions fail explicitly with `UnsupportedResultSchemaVersion`. Old results are not
silently migrated. A future migration must be an explicit, separately named function that returns
the new version and documents every changed field.

Within a minor version, consumers may rely on existing required fields and meanings. New optional
fields may be added in a minor release. Consumers should reject unknown fields until a contract
version that defines them is selected.

## Adding or deprecating a field

1. Decide whether the change is breaking, optional-compatible, or documentation-only.
2. Update the typed model and strict validator together.
3. Update `generate_json_schema()` and regenerate `analysis_result.schema.json`.
4. Add valid and invalid fixtures for the new behavior.
5. Update `analysis_result.md`, this document, and `CHANGELOG.md`.
6. Run `python3 -m pytest` and review the serialized round-trip.

To deprecate a field, keep it valid for the supported compatibility window, document the replacement
and removal target, and add a warning or migration path. Do not silently reinterpret or remove it.

## Migrating old result files

There is no implicit migration. Load and inspect the old `schema_version`, then call an explicit
migration function supplied by the version that owns the migration. If none exists, reject the file
and request a producer upgrade. The existing client snapshot is not a calculator result and must be
adapted explicitly with `result_metadata_from_snapshot()` before a calculator result is built.

## Regenerating the schema

The schema is generated from the Python contract code:

```bash
python3 -c "from src.contracts.serialization import write_json_schema; write_json_schema('docs/contracts/analysis_result.schema.json')"
```

Tests compare the checked-in schema with `generate_json_schema()` and validate the example fixture
using Draft 2020-12.
