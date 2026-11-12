import csv
import io
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentbench.database import Dataset, DatasetVersion, TestCaseRow
from agentbench.schemas import DatasetFile, TestCase, checksum


def parse_import(content: str, format: str, name: str = "imported") -> DatasetFile:
    if len(content.encode()) > 8_000_000:
        raise ValueError("Dataset import exceeds 8 MB")
    if format == "json":
        return DatasetFile.model_validate_json(content)
    cases = []
    if format == "jsonl":
        for line_no, line in enumerate(content.splitlines(), 1):
            if line.strip():
                try:
                    cases.append(TestCase.model_validate_json(line))
                except ValueError as exc:
                    raise ValueError(f"JSONL line {line_no}: {exc}") from exc
    elif format == "csv":
        for line_no, row in enumerate(csv.DictReader(io.StringIO(content)), 2):
            try:
                for key in ["expected", "fixture", "conversation", "budget", "tags"]:
                    if row.get(key):
                        row[key] = json.loads(row[key])
                    else:
                        row.pop(key, None)
                cases.append(TestCase.model_validate(row))
            except ValueError as exc:
                raise ValueError(f"CSV row {line_no}: {exc}") from exc
    else:
        raise ValueError("Supported formats: json, jsonl, csv")
    return DatasetFile(name=name, cases=cases)


async def create_version(
    db: AsyncSession, dataset: Dataset, payload: DatasetFile, frozen=False
) -> DatasetVersion:
    payload = payload.model_copy(update={"cases": sorted(payload.cases, key=lambda c: c.id)})
    body = payload.model_dump(mode="json")
    version = DatasetVersion(
        dataset_id=dataset.id,
        version=payload.version,
        manifest={k: v for k, v in body.items() if k != "cases"},
        checksum=checksum(body),
        frozen=False,
    )
    db.add(version)
    await db.flush()
    for case in payload.cases:
        db.add(TestCaseRow(version_id=version.id, case_id=case.id, body=case.model_dump(mode="json")))
    await db.flush()
    version.frozen = frozen
    await db.flush()
    return version


async def export_version(db: AsyncSession, version: DatasetVersion) -> DatasetFile:
    cases = (
        await db.scalars(
            select(TestCaseRow).where(TestCaseRow.version_id == version.id).order_by(TestCaseRow.case_id)
        )
    ).all()
    return DatasetFile.model_validate({**version.manifest, "cases": [c.body for c in cases]})


def export_format(payload: DatasetFile, format: str) -> str:
    if format == "json":
        return payload.model_dump_json(indent=2)
    if format == "jsonl":
        return "\n".join(c.model_dump_json() for c in payload.cases) + "\n"
    if format == "csv":
        out = io.StringIO(newline="")
        fields = list(TestCase.model_fields)
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for case in payload.cases:
            writer.writerow(
                {
                    k: json.dumps(v) if isinstance(v, (dict, list)) else v
                    for k, v in case.model_dump(mode="json").items()
                }
            )
        return out.getvalue()
    raise ValueError("Unsupported export format")
