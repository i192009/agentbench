from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentbench.api.common import access, audit, editor, owned, page, public
from agentbench.database import Dataset, DatasetVersion, TestCaseRow, User, get_db
from agentbench.schemas import Contract, DatasetFile, Page, TestCase, checksum
from agentbench.services.datasets import create_version, export_format, export_version, parse_import

router = APIRouter(prefix="/projects/{project_id}", tags=["Datasets"])


async def version_owned(db, version_id, project_id):
    row = await owned(db, DatasetVersion, version_id, project_id)
    await owned(db, Dataset, row.dataset_id, project_id)
    return row


@router.get("/datasets", response_model=Page)
async def datasets(
    project_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
):
    return await page(
        db,
        select(Dataset).where(Dataset.project_id == project_id).order_by(Dataset.created_at),
        offset,
        limit,
    )


@router.post("/datasets", status_code=201)
async def create_dataset(
    project_id: str, body: DatasetFile, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    row = Dataset(
        project_id=project_id,
        name=body.name,
        description=body.description,
        domain=body.domain,
        owner_id=user.id,
    )
    db.add(row)
    await db.flush()
    version = await create_version(db, row, body)
    audit(db, user, "dataset.created", row.id, checksum=version.checksum)
    await db.commit()
    return {"dataset": public(row), "version": public(version)}


class ImportBody(Contract):
    format: str = Field(pattern="^(json|jsonl|csv)$")
    content: str = Field(max_length=8_000_000)
    name: str = "imported"


@router.post("/datasets/import", status_code=201)
async def import_dataset(
    project_id: str, body: ImportBody, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    payload = parse_import(body.content, body.format, body.name)
    return await create_dataset(project_id, payload, user, db)


@router.get("/datasets/{dataset_id}/versions", response_model=Page)
async def versions(
    project_id: str, dataset_id: str, user: User = Depends(access), db: AsyncSession = Depends(get_db)
):
    await owned(db, Dataset, dataset_id, project_id)
    return await page(
        db,
        select(DatasetVersion)
        .where(DatasetVersion.dataset_id == dataset_id)
        .order_by(DatasetVersion.version.desc()),
    )


@router.post("/datasets/{dataset_id}/versions", status_code=201)
async def new_version(
    project_id: str,
    dataset_id: str,
    body: DatasetFile,
    user: User = Depends(editor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    dataset = await owned(db, Dataset, dataset_id, project_id)
    row = await create_version(db, dataset, body)
    audit(db, user, "dataset.version.created", row.id)
    await db.commit()
    return public(row)


@router.post("/dataset-versions/{version_id}/clone", status_code=201)
async def clone_version(
    project_id: str,
    version_id: str,
    next_version: int = Query(ge=1),
    user: User = Depends(editor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    source = await version_owned(db, version_id, project_id)
    dataset = await db.get(Dataset, source.dataset_id)
    if dataset is None:
        raise HTTPException(404, "Dataset not found")
    payload = await export_version(db, source)
    payload.version = next_version
    row = await create_version(db, dataset, payload)
    await db.commit()
    return public(row)


@router.get("/dataset-versions/{version_id}/cases", response_model=Page)
async def cases(
    project_id: str,
    version_id: str,
    category: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
):
    await version_owned(db, version_id, project_id)
    query = select(TestCaseRow).where(TestCaseRow.version_id == version_id)
    if category:
        query = query.where(TestCaseRow.body["category"].as_string() == category)
    return await page(db, query.order_by(TestCaseRow.case_id), offset, limit)


@router.put("/dataset-versions/{version_id}/cases/{case_id}")
async def put_case(
    project_id: str,
    version_id: str,
    case_id: str,
    body: TestCase,
    user: User = Depends(editor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    version = await version_owned(db, version_id, project_id)
    if version.frozen:
        raise HTTPException(409, "Frozen versions are immutable; clone a new version")
    if body.id != case_id:
        raise HTTPException(422, "Case ID mismatch")
    row = await db.scalar(
        select(TestCaseRow).where(TestCaseRow.version_id == version_id, TestCaseRow.case_id == case_id)
    )
    if row is None:
        row = TestCaseRow(version_id=version_id, case_id=case_id, body=body.model_dump(mode="json"))
        db.add(row)
    else:
        row.body = body.model_dump(mode="json")
    await db.flush()
    payload = await export_version(db, version)
    version.checksum = checksum(payload.model_dump(mode="json"))
    audit(db, user, "dataset.case.updated", row.id)
    await db.commit()
    return public(row)


@router.post("/dataset-versions/{version_id}/freeze")
async def freeze(
    project_id: str, version_id: str, user: User = Depends(editor), db: AsyncSession = Depends(get_db)
) -> dict:
    row = await version_owned(db, version_id, project_id)
    payload = await export_version(db, row)
    if checksum(payload.model_dump(mode="json")) != row.checksum:
        raise HTTPException(409, "Checksum validation failed")
    if not row.frozen:
        row.frozen = True
        audit(db, user, "dataset.frozen", row.id)
        await db.commit()
    return public(row)


@router.get("/dataset-versions/{version_id}/export")
async def export(
    project_id: str,
    version_id: str,
    format: str = Query("json", pattern="^(json|jsonl|csv)$"),
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
):
    version = await version_owned(db, version_id, project_id)
    payload = await export_version(db, version)
    media = {"json": "application/json", "jsonl": "application/x-ndjson", "csv": "text/csv"}[format]
    return Response(
        export_format(payload, format),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="dataset-v{version.version}.{format}"'},
    )


@router.get("/dataset-versions/{version_id}/compare/{other_id}")
async def compare_datasets(
    project_id: str,
    version_id: str,
    other_id: str,
    user: User = Depends(access),
    db: AsyncSession = Depends(get_db),
) -> dict:
    a = await export_version(db, await version_owned(db, version_id, project_id))
    b = await export_version(db, await version_owned(db, other_id, project_id))
    old, new = {c.id: c.model_dump() for c in a.cases}, {c.id: c.model_dump() for c in b.cases}
    return {
        "added": sorted(new.keys() - old.keys()),
        "removed": sorted(old.keys() - new.keys()),
        "changed": sorted(k for k in old.keys() & new.keys() if old[k] != new[k]),
    }
