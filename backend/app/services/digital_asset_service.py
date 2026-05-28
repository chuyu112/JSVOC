from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.digital_asset import DigitalAsset
from app.models.project import Project
from app.models.script import Script


def build_project_snapshot(project: Project) -> dict[str, object]:
    return {
        "project_id": project.id,
        "project_name": project.project_name,
        "industry": project.industry,
        "sub_industry": project.sub_industry,
        "product": project.product,
        "platforms": project.platforms,
        "current_stage": project.current_stage,
    }


def build_account_asset_snapshot(user_id: int) -> dict[str, object]:
    return {
        "scope": "account",
        "user_id": user_id,
        "project_name": "账户资产",
    }


def create_script_asset(
    db: Session,
    *,
    user_id: int,
    project: Project,
    script: Script,
    generation_record_id: int | None,
) -> DigitalAsset:
    asset = DigitalAsset(
        user_id=user_id,
        asset_type="script",
        source_project_id=project.id,
        project_snapshot=build_project_snapshot(project),
        title=script.title,
        preview_text=script.script_data.get("hook") if isinstance(script.script_data, dict) else None,
        content_text=script.script_content,
        generation_record_id=generation_record_id,
        mime_type="text/plain",
        asset_metadata={
            "script_id": script.id,
            "script_type": script.script_type,
            "platform": script.platform,
            "topic_id": script.topic_id,
            "shot_suggestions": script.shot_suggestions,
            "conversion_script": script.conversion_script,
            "script_data": script.script_data,
        },
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def create_image_asset(
    db: Session,
    *,
    user_id: int,
    project: Project | None,
    prompt: str,
    generation_record_id: int | None,
    oss_object_key: str | None,
    mime_type: str | None,
    file_size: int | None,
    asset_metadata: dict[str, object] | None = None,
    asset_type: str = "image",
    access_url: str | None = None,
    access_url_expires_at: int | None = None,
) -> DigitalAsset:
    type_label = "图片" if asset_type == "image" else "视频" if asset_type == "video" else "生成内容"
    clean_prompt = (prompt or "").strip()
    metadata = dict(asset_metadata or {})
    if clean_prompt:
        metadata.setdefault("prompt", clean_prompt)
    if project is not None:
        metadata.setdefault("source_project", build_project_snapshot(project))
    asset = DigitalAsset(
        user_id=user_id,
        asset_type=asset_type,
        source_project_id=None,
        project_snapshot=build_account_asset_snapshot(user_id),
        title=(clean_prompt or f"生成{type_label}")[:240] or f"生成{type_label}",
        preview_text=clean_prompt[:240] or None,
        content_text=clean_prompt or None,
        generation_record_id=generation_record_id,
        oss_object_key=oss_object_key,
        mime_type=mime_type,
        file_size=file_size,
        asset_metadata=metadata,
        access_url=access_url,
        access_url_expires_at=access_url_expires_at,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def list_digital_assets(
    db: Session,
    *,
    user_id: int,
    asset_type: str | None = None,
    source_project_id: int | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[DigitalAsset]:
    statement = select(DigitalAsset).where(DigitalAsset.user_id == user_id).order_by(
        DigitalAsset.created_at.desc(),
        DigitalAsset.id.desc(),
    )
    if asset_type is not None:
        statement = statement.where(DigitalAsset.asset_type == asset_type)
    if source_project_id is not None:
        statement = statement.where(DigitalAsset.source_project_id == source_project_id)

    statement = statement.offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_digital_asset_for_user(db: Session, asset_id: int, user_id: int) -> DigitalAsset | None:
    statement = select(DigitalAsset).where(DigitalAsset.id == asset_id, DigitalAsset.user_id == user_id)
    return db.scalars(statement).first()


def detach_project_assets(db: Session, project_id: int) -> None:
    assets = db.scalars(
        select(DigitalAsset).where(DigitalAsset.source_project_id == project_id)
    ).all()
    for asset in assets:
        metadata = dict(asset.asset_metadata or {})
        if asset.project_snapshot:
            metadata.setdefault("source_project", dict(asset.project_snapshot))
        asset.asset_metadata = metadata
        asset.source_project_id = None
        asset.project_snapshot = build_account_asset_snapshot(asset.user_id)
    db.commit()


def delete_digital_asset(db: Session, asset: DigitalAsset) -> None:
    db.delete(asset)
    db.commit()
