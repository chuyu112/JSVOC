from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services import digital_asset_service
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate

FIXED_PROJECT_INDUSTRY = '珠宝'
FIXED_PROJECT_SUB_INDUSTRY = '翡翠'


def apply_fixed_project_industry(data: dict[str, object]) -> dict[str, object]:
    return {
        **data,
        'industry': FIXED_PROJECT_INDUSTRY,
        'sub_industry': FIXED_PROJECT_SUB_INDUSTRY,
    }


def create_project(db: Session, project_in: ProjectCreate, user_id: int | None = None) -> Project:
    project = Project(**apply_fixed_project_industry(project_in.model_dump()), user_id=user_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_projects(db: Session, skip: int = 0, limit: int = 100) -> list[Project]:
    statement = select(Project).order_by(Project.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def get_projects_for_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list[Project]:
    statement = (
        select(Project)
        .where(Project.user_id == user_id)
        .order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def get_project(db: Session, project_id: int) -> Project | None:
    return db.get(Project, project_id)


def get_project_for_user(db: Session, project_id: int, user_id: int) -> Project | None:
    statement = select(Project).where(Project.id == project_id, Project.user_id == user_id)
    return db.scalars(statement).first()


def update_project(db: Session, project: Project, project_in: ProjectUpdate) -> Project:
    update_data = apply_fixed_project_industry(project_in.model_dump(exclude_unset=True))

    for field, value in update_data.items():
        setattr(project, field, value)

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def project_to_payload(project: Project) -> dict[str, object]:
    return {
        "project_name": project.project_name,
        "industry": FIXED_PROJECT_INDUSTRY,
        "sub_industry": FIXED_PROJECT_SUB_INDUSTRY,
        "product": project.product,
        "personal_intro": project.personal_intro,
        "target_audience": project.target_audience,
        "platforms": project.platforms,
        "benchmark_accounts": project.benchmark_accounts,
        "current_stage": project.current_stage,
    }


def delete_project(db: Session, project: Project) -> None:
    digital_asset_service.detach_project_assets(db, project.id)
    db.delete(project)
    db.commit()
