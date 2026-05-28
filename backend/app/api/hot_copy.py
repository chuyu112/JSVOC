from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.image_generation import run_image_generation_task
from app.api.video_generation import (
    normalize_video_options,
    run_video_generation_task,
    validate_video_model_access,
)
from app.db.session import get_db
from app.models.hot_copy import HotCopyRewrite
from app.models.user import User
from app.schemas.generation_task import GenerationTaskCreate, GenerationTaskSubmitResponse
from app.schemas.hot_copy import (
    DouyinProfileImportRequest,
    DouyinProfileTranscribeRequest,
    HotCopyAnalysisResponse,
    HotCopyMaterialAutoCreate,
    HotCopyMaterialManualCreate,
    HotCopyMaterialRead,
    HotCopyRedianbaoSearchRequest,
    HotCopyRewriteRequest,
    HotCopyRewriteResponse,
)
from app.schemas.image_generation import ImageGenerateRequest
from app.services import (
    credit_service,
    generation_task_service,
    hot_copy_service,
    project_reference_image_service,
    video_parsing_service,
)


router = APIRouter(tags=["hot_copy"])


def success_response(data: object, message: str = "") -> dict[str, object]:
    return {"success": True, "data": data, "message": message}


def failure_response(data: object, message: str) -> dict[str, object]:
    return {"success": False, "data": data, "message": message}


@router.post("/api/hot-copy/materials/manual", status_code=201)
def create_manual_material(
    payload: HotCopyMaterialManualCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    material = hot_copy_service.create_manual_material(db, payload, current_user.id)
    data = HotCopyMaterialRead.model_validate(material).model_dump(mode="json")
    return success_response(data, "爆款素材已保存")


@router.post("/api/hot-copy/materials/auto", status_code=201)
def create_auto_material(
    payload: HotCopyMaterialAutoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        material = hot_copy_service.create_auto_material(db, payload, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    data = HotCopyMaterialRead.model_validate(material).model_dump(mode="json")
    return success_response(data, "视频链接解析完成，素材已保存")


@router.post("/api/hot-copy/materials/auto-upload", status_code=201)
def create_auto_material_upload(
    project_id: int | None = None,
    platform: str = "douyin",
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    file_content = file.file.read()
    try:
        material = hot_copy_service.create_auto_material(
            db,
            HotCopyMaterialAutoCreate(project_id=project_id, platform=platform),
            current_user.id,
            file_content=file_content,
            filename=file.filename or "upload.mp4",
            content_type=file.content_type or "video/mp4",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    data = HotCopyMaterialRead.model_validate(material).model_dump(mode="json")
    return success_response(data, "视频上传并提取完成，素材已保存")


@router.post("/api/hot-copy/douyin-profile/import")
def import_douyin_profile(
    payload: DouyinProfileImportRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    _ = current_user
    try:
        data = video_parsing_service.import_douyin_profile_videos(payload.source_url, count=payload.count)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return success_response(data, "抖音主页最近作品已导入")


@router.post("/api/hot-copy/douyin-profile/transcribe")
def transcribe_douyin_profile_video(
    payload: DouyinProfileTranscribeRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        data = video_parsing_service.transcribe_douyin_profile_video(
            media_url=payload.media_url,
            aweme_id=payload.aweme_id,
            title=payload.title,
            user_id=current_user.id,
            project_id=payload.project_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return success_response(data, "ASR transcription completed")


@router.get("/api/hot-copy/materials")
def list_materials(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    materials = hot_copy_service.list_materials(db, current_user.id, skip=skip, limit=limit)
    data = [HotCopyMaterialRead.model_validate(material).model_dump(mode="json") for material in materials]
    return success_response(data)


@router.get("/api/hot-copy/materials/{material_id}")
def get_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    material = hot_copy_service.require_material(db, material_id, current_user.id)
    data = HotCopyMaterialRead.model_validate(material).model_dump(mode="json")
    return success_response(data)


@router.post("/api/hot-copy/materials/{material_id}/analyze")
def analyze_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    material, analysis, generation_record_id = hot_copy_service.analyze_material(db, material_id, current_user.id)
    response = HotCopyAnalysisResponse(
        material=HotCopyMaterialRead.model_validate(material),
        analysis=analysis,
        generation_record_id=generation_record_id,
    )
    return success_response(response.model_dump(mode="json"), "爆点拆解完成")


@router.post("/api/hot-copy/materials/{material_id}/rewrite")
def rewrite_material(
    material_id: int,
    payload: HotCopyRewriteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    rewrite, output, generation_record_id = hot_copy_service.rewrite_material(
        db,
        material_id,
        payload,
        current_user.id,
    )
    response = HotCopyRewriteResponse.model_validate(
        {
            "rewrite": rewrite,
            "output": output,
            "generation_record_id": generation_record_id,
        }
    )
    return success_response(response.model_dump(mode="json"), "文案仿写完成")


@router.post("/api/hot-copy/redianbao/search")
def search_redianbao(
    payload: HotCopyRedianbaoSearchRequest,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    _ = payload
    _ = current_user
    return failure_response(
        hot_copy_service.redianbao_reserved_response(),
        hot_copy_service.REDIANBAO_NOT_CONNECTED_MESSAGE,
    )


@router.post("/api/hot-copy/rewrites/{rewrite_id}/generate-video")
def generate_video_from_rewrite(
    rewrite_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    rewrite = db.scalars(
        select(HotCopyRewrite).where(
            HotCopyRewrite.id == rewrite_id,
            HotCopyRewrite.user_id == current_user.id,
        )
    ).first()
    if rewrite is None:
        raise HTTPException(status_code=404, detail="仿写记录不存在")

    output = rewrite.output_json if isinstance(rewrite.output_json, dict) else {}
    script = output.get("script") or output.get("title") or ""
    if not script:
        raise HTTPException(status_code=400, detail="仿写结果中没有可用脚本")

    project_id = rewrite.project_id
    if project_id is not None:
        project = hot_copy_service.get_optional_project(db, project_id, current_user.id)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")

    reference_images: list[str] = []
    if project_id is not None:
        ref_images = project_reference_image_service.list_reference_images_by_project(db, project_id)
        for img in ref_images:
            if img.reference_image_type == "persona" and img.source_image_base64:
                reference_images.append(img.source_image_base64)

    options = normalize_video_options({"ratio": "9:16", "resolution": "720p", "duration_mode": "smart"})
    validate_video_model_access(options)

    try:
        credit_cost = credit_service.video_generation_cost(options)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    credit_service.ensure_sufficient_credits(db, current_user.id, credit_cost)

    task = generation_task_service.create_generation_task(
        db,
        GenerationTaskCreate(
            task_type="video_generate",
            project_id=project_id,
            input_data={
                "project_id": project_id,
                "prompt": script,
                "options": options,
                "reference_images": reference_images,
                "rewrite_id": rewrite_id,
            },
        ),
        user_id=current_user.id,
    )
    transaction = credit_service.charge_credits(
        db,
        user_id=current_user.id,
        cost=credit_cost,
        reason="video_generation",
        reference_type="generation_task",
        reference_id=task.id,
        metadata={"options": options, "source": "hot_copy_rewrite", "rewrite_id": rewrite_id},
    )
    task = generation_task_service.attach_credit_charge(
        db,
        task.id,
        credit_cost=credit_cost,
        credit_transaction_id=transaction.id if transaction else None,
    ) or task

    background_tasks.add_task(
        run_video_generation_task,
        task.id,
        script,
        project_id,
        current_user.id,
        options,
        None,
        None,
        None,
        None,
        reference_images,
        None,
        None,
    )

    data = GenerationTaskSubmitResponse(
        task_id=task.id,
        task_type=task.task_type,
        status=task.status,
        credit_cost=credit_cost,
    )
    return success_response(data.model_dump(mode="json"), "视频生成任务已提交")


@router.post("/api/hot-copy/rewrites/{rewrite_id}/generate-scenes")
def generate_scenes_from_rewrite(
    rewrite_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    rewrite = db.scalars(
        select(HotCopyRewrite).where(
            HotCopyRewrite.id == rewrite_id,
            HotCopyRewrite.user_id == current_user.id,
        )
    ).first()
    if rewrite is None:
        raise HTTPException(status_code=404, detail="仿写记录不存在")

    output = rewrite.output_json if isinstance(rewrite.output_json, dict) else {}
    scene_breakdown = output.get("scene_breakdown") if isinstance(output, dict) else None
    if not isinstance(scene_breakdown, list) or not scene_breakdown:
        raise HTTPException(status_code=400, detail="仿写结果中没有场景分镜表")

    project_id = rewrite.project_id
    if project_id is not None:
        project = hot_copy_service.get_optional_project(db, project_id, current_user.id)
        if project is None:
            raise HTTPException(status_code=404, detail="项目不存在")

    tasks: list[dict[str, object]] = []
    for idx, scene in enumerate(scene_breakdown):
        if not isinstance(scene, dict):
            continue
        image_prompt = scene.get("image_prompt") or scene.get("setting") or ""
        if not image_prompt:
            continue

        credit_cost = credit_service.image_generation_cost(1, mode="generate")
        credit_service.ensure_sufficient_credits(db, current_user.id, credit_cost)

        payload = ImageGenerateRequest(
            project_id=project_id,
            prompt=str(image_prompt),
            n=1,
            size="1024x1024",
            quality="standard",
        )
        input_data = payload.model_dump(mode="json")
        input_data["rewrite_id"] = rewrite_id
        input_data["material_id"] = rewrite.material_id
        task = generation_task_service.create_generation_task(
            db,
            GenerationTaskCreate(
                task_type="image_generate",
                project_id=project_id,
                input_data=input_data,
            ),
            user_id=current_user.id,
        )
        transaction = credit_service.charge_credits(
            db,
            user_id=current_user.id,
            cost=credit_cost,
            reason="image_generation",
            reference_type="generation_task",
            reference_id=task.id,
            metadata={"scene_no": idx + 1, "source": "hot_copy_scene", "rewrite_id": rewrite_id},
        )
        task = generation_task_service.attach_credit_charge(
            db,
            task.id,
            credit_cost=credit_cost,
            credit_transaction_id=transaction.id if transaction else None,
        ) or task

        background_tasks.add_task(run_image_generation_task, task.id, "generate", task.input_data, current_user.id)
        tasks.append({
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "scene_no": idx + 1,
            "credit_cost": credit_cost,
        })

    return success_response({"tasks": tasks, "total": len(tasks)}, "分镜素材生成任务已提交")
