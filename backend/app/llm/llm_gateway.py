import json
import time
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.schemas.generation_record import GenerationRecordCreate
from app.services import llm_channel_service
from app.services.generation_record_service import create_generation_record


_HTTP_CLIENT: httpx.Client | None = None


def get_http_client() -> httpx.Client:
    """Return a module-level httpx.Client so LLM calls reuse TCP connections."""
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None:
        _HTTP_CLIENT = httpx.Client(
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            timeout=httpx.Timeout(60.0),
            follow_redirects=True,
        )
    return _HTTP_CLIENT


def close_http_client() -> None:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is not None:
        _HTTP_CLIENT.close()
        _HTTP_CLIENT = None


def _post_json(url: str, headers: dict[str, str], json: dict[str, Any], timeout: float) -> httpx.Response:
    """Wrapper around the shared httpx client; exposed at module scope so tests can patch it."""
    return get_http_client().post(url, headers=headers, json=json, timeout=timeout)


class LLMGatewayRequest(BaseModel):
    module_name: str = Field(min_length=1, max_length=80)
    system_prompt: str = Field(default="")
    user_prompt: str = Field(default="")
    output_schema: dict[str, Any] | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
    web_search: bool = False
    web_search_context_size: str = Field(default="medium", pattern="^(low|medium|high)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMGatewayResponse(BaseModel):
    success: bool
    provider: str
    model: str
    content: str
    data: Any = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    latency_ms: int
    error: str | None = None
    generation_record_id: int | None = None


class LLMGateway:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._explicit_settings = settings is not None

    def generate(
        self,
        db: Session,
        request: LLMGatewayRequest,
        project_id: int | None = None,
        user_id: int | None = None,
        prompt_version: str | None = "v1",
    ) -> LLMGatewayResponse:
        previous_settings = self.settings
        if not self._explicit_settings:
            self.settings = llm_channel_service.get_effective_llm_settings(db, get_settings())
        try:
            return self._generate_with_current_settings(db, request, project_id, user_id, prompt_version)
        finally:
            self.settings = previous_settings

    def _generate_with_current_settings(
        self,
        db: Session,
        request: LLMGatewayRequest,
        project_id: int | None,
        user_id: int | None,
        prompt_version: str | None,
    ) -> LLMGatewayResponse:
        provider = self._normalized_provider()

        if provider == "mock":
            result = self._generate_mock(request)
        elif provider in {"openai_compatible", "dataeye", "moyu"}:
            result = self._generate_openai_compatible(request, provider=provider)
        elif provider == "anthropic_compatible":
            result = self._generate_anthropic_compatible(request)
        else:
            result = self._error_response(
                provider=provider or "unknown",
                model=self.settings.llm_model,
                started_at=time.perf_counter(),
                error=f"Unsupported LLM_PROVIDER: {self.settings.llm_provider}",
            )

        record = create_generation_record(
            db,
            GenerationRecordCreate(
                user_id=user_id,
                project_id=project_id,
                module_name=request.module_name,
                input_data=request.model_dump(mode="json"),
                output_data={
                    "success": result.success,
                    "content": result.content,
                    "data": result.data,
                    "error": result.error,
                },
                model_provider=result.provider,
                model_name=result.model,
                prompt_version=prompt_version,
                token_usage=result.usage,
                latency_ms=result.latency_ms,
            ),
        )
        result.generation_record_id = record.id
        return result

    def _generate_mock(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        started_at = time.perf_counter()
        data = self._mock_data_for_module(request.module_name, request.metadata)
        content = json.dumps(data, ensure_ascii=False, indent=2)
        sources = []
        if request.web_search:
            sources = [{"title": "Mock Search Source", "url": "https://example.com/mock-search"}]
        return LLMGatewayResponse(
            success=True,
            provider="mock",
            model=self.settings.llm_model or "mock-model",
            content=content,
            data=data,
            usage={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            sources=sources,
            latency_ms=self._elapsed_ms(started_at),
        )

    def _generate_openai_compatible(
        self,
        request: LLMGatewayRequest,
        provider: str = "openai_compatible",
    ) -> LLMGatewayResponse:
        started_at = time.perf_counter()
        base_url = self._web_search_base_url(provider) if request.web_search else self._openai_compatible_base_url(provider)
        model = self._web_search_model(request, base_url) if request.web_search else self._openai_compatible_model(request, base_url)

        if not base_url:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM_BASE_URL is required when LLM_PROVIDER={provider}",
            )

        if request.web_search:
            return self._generate_openai_responses_with_web_search(
                request=request,
                provider=provider,
                started_at=started_at,
                base_url=base_url,
                model=model,
            )

        url = self._chat_completions_url(base_url)
        headers = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens or self.settings.llm_max_tokens_default,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
        }
        if self._is_deepseek_endpoint(base_url, model):
            payload.update(self._deepseek_openai_options(request, model))

        try:
            response = _post_json(
                url,
                headers=headers,
                json=payload,
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            content = self._extract_openai_content(body)
            data = self._parse_json_content(content)

            return LLMGatewayResponse(
                success=True,
                provider=provider,
                model=body.get("model") or model,
                content=content,
                data=data,
                usage=body.get("usage") or {},
                latency_ms=self._elapsed_ms(started_at),
            )
        except httpx.TimeoutException as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM request timed out after {self.settings.llm_timeout_seconds} seconds: {exc}",
            )
        except httpx.HTTPStatusError as exc:
            response_text = exc.response.text[:500] if exc.response is not None else ""
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM HTTP error {exc.response.status_code}: {response_text}",
            )
        except httpx.RequestError as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM request failed: {exc}",
            )
        except ValueError as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM response parse failed: {exc}",
            )
        except Exception as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=str(exc),
            )

    def _generate_openai_responses_with_web_search(
        self,
        *,
        request: LLMGatewayRequest,
        provider: str,
        started_at: float,
        base_url: str,
        model: str,
    ) -> LLMGatewayResponse:
        url = self._responses_url(base_url)
        headers = {"Content-Type": "application/json"}
        api_key = self.settings.web_search_api_key.strip() or self.settings.llm_api_key
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        context_size = request.web_search_context_size or self.settings.web_search_context_size
        if context_size not in {"low", "medium", "high"}:
            context_size = "medium"

        payload: dict[str, Any] = {
            "model": model,
            "instructions": request.system_prompt,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": request.user_prompt},
                    ],
                }
            ],
            "tools": [{"type": "web_search", "search_context_size": context_size}],
            "tool_choice": "auto",
            "include": ["web_search_call.action.sources"],
        }

        try:
            response = _post_json(
                url,
                headers=headers,
                json=payload,
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            body = self._decode_responses_body(response)
            content = self._extract_responses_content(body)
            sources = self._extract_responses_sources(body)
            data = self._parse_json_content(content)
            if isinstance(data, dict):
                data.setdefault("sources", sources)

            return LLMGatewayResponse(
                success=True,
                provider=provider,
                model=body.get("model") or model,
                content=content,
                data=data,
                usage=body.get("usage") or {},
                sources=sources,
                latency_ms=self._elapsed_ms(started_at),
            )
        except httpx.TimeoutException as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM web search timed out after {self.settings.llm_timeout_seconds} seconds: {exc}",
            )
        except httpx.HTTPStatusError as exc:
            response_text = exc.response.text[:500] if exc.response is not None else ""
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM web search HTTP error {exc.response.status_code}: {response_text}",
            )
        except httpx.RequestError as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM web search request failed: {exc}",
            )
        except ValueError as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM web search response parse failed: {exc}",
            )
        except Exception as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=str(exc),
            )

    def _generate_anthropic_compatible(self, request: LLMGatewayRequest) -> LLMGatewayResponse:
        started_at = time.perf_counter()
        provider = "anthropic_compatible"
        model = self.settings.llm_model
        base_url = self.settings.llm_base_url.strip()

        if not base_url:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error="LLM_BASE_URL is required when LLM_PROVIDER=anthropic_compatible",
            )

        url = self._anthropic_messages_url(base_url)
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self.settings.llm_api_key:
            headers["x-api-key"] = self.settings.llm_api_key

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens or self.settings.llm_max_tokens_default,
            "messages": [{"role": "user", "content": request.user_prompt}],
            "temperature": request.temperature,
        }
        payload["thinking"] = {"type": "disabled"}
        if request.system_prompt:
            payload["system"] = request.system_prompt

        try:
            response = _post_json(
                url,
                headers=headers,
                json=payload,
                timeout=self.settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            body = response.json()
            content = self._extract_anthropic_content(body)
            data = self._parse_json_content(content)

            return LLMGatewayResponse(
                success=True,
                provider=provider,
                model=body.get("model") or model,
                content=content,
                data=data,
                usage=self._normalize_anthropic_usage(body.get("usage") or {}),
                latency_ms=self._elapsed_ms(started_at),
            )
        except httpx.TimeoutException as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM request timed out after {self.settings.llm_timeout_seconds} seconds: {exc}",
            )
        except httpx.HTTPStatusError as exc:
            response_text = exc.response.text[:500] if exc.response is not None else ""
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM HTTP error {exc.response.status_code}: {response_text}",
            )
        except httpx.RequestError as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM request failed: {exc}",
            )
        except ValueError as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=f"LLM response parse failed: {exc}",
            )
        except Exception as exc:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error=str(exc),
            )

    def _mock_data_for_module(
        self,
        module_name: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized = module_name.lower().replace("-", "_")
        if normalized == "strategy_bundle":
            return {
                "account_package": self._mock_account_package(),
                "execution_plan": self._mock_execution_plan(metadata or {}),
            }
        if "account" in normalized or "package" in normalized or "账号" in normalized:
            return self._mock_account_package()
        if "execution" in normalized or "plan" in normalized or "执行" in normalized:
            return self._mock_execution_plan(metadata or {})
        if "topic" in normalized or "选题" in normalized:
            return self._mock_topics(metadata or {})
        if "script" in normalized or "copy" in normalized or "文案" in normalized:
            return self._mock_script(metadata or {})
        if normalized == "hot_video_search":
            return self._mock_hot_video_search(metadata or {})
        if normalized == "image_prompt_enhance":
            return {
                "enhanced_prompt": "画面主体必须是满绿镶嵌戒面，生成高级清透的珠宝产品展示图，主体居中清晰，柔和自然光，背景干净留白，突出翡翠的通透感、饱满色泽、镶嵌工艺和真实材质纹理。避免乱码文字、可识别人脸、项目名图形化、夸张特效、假绿、塑料感和廉价反光。",
                "subject": "满绿镶嵌戒面",
                "removed_terms": metadata.get("interference_terms", []) if metadata else [],
                "notes": ["已过滤项目名、人名和昵称", "已将主体绑定到产品字段"],
            }
        if normalized == "ai_chat":
            return {
                "reply": "可以。先把目标账号、人设和产品卖点收紧，再按选题、文案、提示词三个层级推进；如果要继续落地，建议先进入项目档案确认基础信息。",
            }

        return {
            "module_name": module_name,
            "summary": "mock provider 示例输出",
            "next_step": "请使用 account_package、execution_plan、topics 或 script 模块名测试固定 JSON。",
        }

    def _mock_hot_video_search(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata = metadata or {}
        platform = str(metadata.get("platform") or "抖音")
        keyword = str(metadata.get("keyword") or "翡翠避坑")
        count = int(metadata.get("count") or 3)
        templates = [
            ("先别问价格，新手买翡翠先看这三处", "用反常识开头拦住新手焦虑"),
            ("四会档口实拍：同样绿色为什么差价这么大", "用真实场景和强对比制造停留"),
            ("客户预算一万，我会先劝她放弃这类货", "用客户故事制造信任和转化"),
        ]
        items = []
        for index in range(count):
            title, reason = templates[index % len(templates)]
            items.append(
                {
                    "title": f"{keyword}｜{title}",
                    "platform": platform,
                    "creator": "",
                    "source_url": "https://example.com/hot-video",
                    "source_title": "Mock 热门视频搜索结果",
                    "publish_time": "",
                    "metrics": {"status": "mock"},
                    "why_trending": reason,
                    "hook": "新手买翡翠，别一上来就问最低价。",
                    "structure": ["一句话打破误区", "展示真实货品细节", "解释判断标准", "给出私信承接动作"],
                    "remake_angle": "结合项目产品，用自己的货品和客户场景重写，不照搬原视频表达。",
                    "rewrite_brief": "生成一条 60 秒短视频文案：开头反常识，正文讲三步判断，结尾引导评论预算。",
                    "risk_notes": ["不要搬运原视频画面", "不要使用原作者口播原文"],
                    "tags": ["翡翠", "避坑", "同赛道拆解"],
                }
            )
        return {"items": items}

    def _mock_account_package(self) -> dict[str, Any]:
        return {
            "account_positioning": "四会翡翠源头市场的靠谱选品顾问",
            "persona": "多年翡翠从业者，熟悉源头市场，表达真实直接，重点解决怕买贵、怕踩坑的问题。",
            "target_user_profile": {
                "core_audience": "喜欢翡翠、想买翡翠但担心踩坑的人",
                "needs": ["看懂品质", "判断价格是否合理", "找到靠谱源头卖家"],
                "concerns": ["怕买贵", "怕买到处理货", "怕商家说不清楚"],
            },
            "account_names": ["四会阿杰说翡翠", "源头翡翠老友记", "靠谱翡翠选品人"],
            "bios": {
                "抖音": "在四会源头市场帮你看懂翡翠，少踩坑，买得明白。",
                "视频号": "多年翡翠从业经验，分享真实市场观察和实用选购建议。",
                "快手": "四会翡翠源头一线，真实看货，实在说货。",
                "小红书": "翡翠入门、避坑、审美和选购笔记。",
            },
            "content_columns": ["源头市场见闻", "翡翠避坑", "价格判断", "客户案例", "日常看货"],
            "trust_design": ["展示四会市场场景", "讲清选品标准", "用真实案例建立信任"],
            "conversion_path": ["评论区提问", "私信发预算和喜好", "一对一推荐适合款式"],
            "platform_strategies": {
                "抖音": "用强钩子开场，突出翡翠避坑和源头市场价格差异，结尾引导评论预算。",
                "视频号": "强化多年经验和靠谱人设，用熟人信任感讲真实案例。",
                "快手": "表达更接地气，展示四会市场日常和真实看货过程。",
                "小红书": "强调审美、种草、搭配和新手选购笔记，降低购买决策压力。",
            },
        }

    def _mock_execution_plan(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata = metadata or {}
        cycle = str(metadata.get("cycle") or "30天")
        daily_time = str(metadata.get("daily_time") or "2小时")
        topics = [
            "四会源头市场今天这类翡翠为什么价格差很大",
            "新手买翡翠先看种水还是先看颜色",
            "同样叫冰种，实物细节差在哪里",
            "预算 1000 到 3000 怎么挑不容易后悔",
            "看翡翠手镯时最容易忽略的瑕疵",
            "翡翠挂件适合送礼还是日常戴",
            "商家说的起胶起光到底怎么看",
            "源头市场拿货和直播间买货的区别",
            "怕买贵的人应该先问哪三个问题",
            "一条翡翠手镯从看货到决定的流程",
            "小白怎样用手机灯看翡翠细节",
            "颜色漂亮但价格低时要重点检查什么",
            "四会市场里哪些场景能看出商家是否靠谱",
            "客户预算有限时如何取舍种水和颜色",
            "翡翠证书能解决哪些问题，不能解决哪些问题",
            "视频号用户更关心的翡翠信任点",
            "快手老铁喜欢看的真实看货过程",
            "小红书适合讲的翡翠佩戴和搭配场景",
            "抖音短视频开头如何一句话讲清避坑点",
            "客户常问的翡翠价格为什么差这么多",
            "同一预算买手镯、吊坠、戒面怎么选",
            "翡翠有纹有裂有棉分别怎么影响购买",
            "怎样用真实客户案例讲清选品逻辑",
            "源头市场当天看货复盘：哪类货值得重点拍",
            "把一件翡翠从远景到细节拍完整",
            "粉丝发图咨询时应该怎样回应更专业",
            "月底复盘：哪类翡翠内容更容易引来有效咨询",
            "把高评论问题改成下一条视频选题",
            "30 天内容里最适合继续放大的三个栏目",
            "下个月执行计划要保留和砍掉哪些内容",
        ]
        daily_plan = []
        for index, topic in enumerate(topics, start=1):
            daily_plan.append(
                {
                    "day": index,
                    "task": f"用{daily_time}完成 1 条翡翠短视频：先列 3 个要点，拍 6-8 个素材镜头，剪成 45-90 秒。",
                    "topic": topic,
                    "shooting_task": (
                        "真人出镜开场说明问题，接着拍翡翠实物近景、侧光细节和四会市场环境，"
                        "最后用一句话引导用户评论预算或私信发图。"
                    ),
                    "review_metrics": ["完播率", "评论问题数", "私信咨询数", "收藏率"],
                }
            )

        return {
            "cycle": cycle,
            "weekly_plan": [
                {
                    "week": 1,
                    "goal": "让用户记住你是四会翡翠源头市场的靠谱选品人",
                    "focus": "账号定位、人设露出、基础避坑认知",
                    "key_tasks": ["完善主页三件套", "连续测试 7 条翡翠避坑内容", "记录每条评论问题"],
                },
                {
                    "week": 2,
                    "goal": "建立稳定更新节奏并筛出高咨询选题",
                    "focus": "源头市场看货、预算选择、实物细节",
                    "key_tasks": ["每天拍 1 条实物讲解", "对比不同预算货品", "沉淀粉丝常问问题"],
                },
                {
                    "week": 3,
                    "goal": "强化信任背书，把评论问题转成私信咨询",
                    "focus": "真实案例、证书解释、客户预算推荐",
                    "key_tasks": ["拍客户问答", "展示市场场景", "设置评论到私信的承接话术"],
                },
                {
                    "week": 4,
                    "goal": "复盘高表现内容，形成可复制的栏目模板",
                    "focus": "钩子优化、栏目复用、平台差异化发布",
                    "key_tasks": ["找出高完播视频结构", "重拍 3 个高评论问题", "整理下月栏目清单"],
                },
                {
                    "week": 5,
                    "goal": "完成 30 天收尾复盘并确定下月执行重点",
                    "focus": "数据复盘、咨询质量、内容取舍",
                    "key_tasks": ["统计 30 天核心数据", "筛选有效咨询来源", "决定下月保留栏目"],
                },
            ],
            "daily_plan": daily_plan,
            "notes": ["每天优先保证选题具体、实物清楚、结尾有评论或私信承接。"],
        }

    def _mock_topics(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata = metadata or {}
        platform = str(metadata.get("platform") or "抖音")
        goal = str(metadata.get("goal") or "获客")
        content_format = str(metadata.get("content_format") or "video")
        count = int(metadata.get("count") or 20)

        # 口播专用话题型标题模板
        spoken_templates = [
            ("买手镯还是买挂件，今天我来告诉你", "选购对比", "很多人纠结买手镯还是挂件，其实要看你的佩戴场景和预算。"),
            ("打麻将戴什么首饰最旺？", "风水话题", "打麻将戴翡翠有讲究，不同生肖适合不同款式。"),
            ("12生肖都戴什么珠宝最合适？", "生肖话题", "每个生肖都有适合自己的珠宝，选对了更旺运势。"),
            ("翡翠是智商税吗？", "争议话题", "有人说翡翠是智商税，今天聊聊我的真实看法。"),
            ("几百块和几万块的翡翠，差别到底在哪？", "价格对比", "同样是翡翠，价格差几十倍，到底差在哪里？"),
            ("新手买翡翠最容易踩的5个坑", "避坑指南", "新手买翡翠，这几个坑踩了就亏大了。"),
            ("为什么行家看翡翠先看瑕疵？", "行家视角", "普通人看颜色，行家先看瑕疵，这是为什么？"),
            ("送长辈翡翠，选什么款式最合适？", "送礼话题", "送长辈翡翠有讲究，选错了反而尴尬。"),
            ("翡翠手镯有裂纹还能买吗？", "瑕疵话题", "手镯有裂纹到底能不能买？今天说清楚。"),
            ("直播间买翡翠，这3点一定要记住", "直播避坑", "直播间买翡翠水很深，记住这3点不踩坑。"),
            ("戴翡翠有什么讲究？这5件事别做", "佩戴禁忌", "戴翡翠有些事不能做，老一辈说的有道理吗？"),
            ("翡翠越戴越透是真的吗？", "养护话题", "有人说翡翠越戴越透，是真的还是心理作用？"),
            ("预算3000，买手镯还是买吊坠？", "预算话题", "预算有限，手镯和吊坠哪个更值得买？"),
            ("为什么有些翡翠越戴越绿？", "变色话题", "翡翠戴久了变色，是好事还是坏事？"),
            ("四会市场买翡翠，这些话别信", "市场避坑", "四会市场水很深，商家说这些话时要多留心。"),
        ]

        # 视频/图片用的详细模板
        templates = [
            (
                "四会源头市场同样叫冰种，价格为什么差这么多",
                "避坑科普",
                "冰种翡翠名字听起来一样，但种水、棉、裂和工艺会让价格差几倍。",
                "同样叫冰种，为什么这件能卖三千，那件只要几百？",
                "真人拿两件翡翠在市场档口前对比，先拍整体，再给棉、裂、光感特写。",
                "引导评论预算和用途，私信发图帮用户判断是否值得看。",
                96,
            ),
            (
                "新手到四会买翡翠，第一眼不要先看颜色",
                "新手入门",
                "用户容易被鲜艳颜色吸引，忽略种水、瑕疵和佩戴场景。",
                "新手看翡翠，第一眼只盯颜色，很容易踩坑。",
                "手持一件颜色亮但瑕疵明显的货，再对比一件种水更稳的日常款。",
                "结尾让用户评论“日常戴/送礼/收藏”，按用途给建议。",
                94,
            ),
            (
                "预算 2000 买翡翠手镯，在源头市场怎么取舍",
                "预算选品",
                "目标客户有预算但不知道该优先选种水、颜色还是圈口。",
                "两千预算买手镯，不是不能买，是要知道该放弃什么。",
                "拍 3 只不同取舍的手镯，逐只说明圈口、底子、纹裂和适合人群。",
                "引导私信发送预算、圈口和佩戴场景，承接一对一推荐。",
                95,
            ),
            (
                "翡翠证书能证明什么，不能替你判断什么",
                "信任答疑",
                "用户以为有证书就等于值得买，忽略品质和价格判断。",
                "有证书不等于买得值，这句话新手一定要知道。",
                "展示证书和实物，同步讲 A 货证明、品质判断和价格判断的区别。",
                "评论区收集证书疑问，私信发证书和实物图做基础判断。",
                92,
            ),
            (
                "四会档口看货时，靠谱商家通常会主动讲这三点",
                "信任建立",
                "用户害怕遇到只报喜不报忧的商家，不知道怎么判断可靠性。",
                "在源头市场看货，靠谱的人通常不会只说好话。",
                "边走市场边口播，穿插档口看货、自然光看货和细节确认镜头。",
                "引导用户把遇到的话术发来，帮忙判断是否需要谨慎。",
                93,
            ),
            (
                "翡翠有棉是不是不值钱，要看这两个位置",
                "误区拆解",
                "用户听到有棉就害怕，可能错过适合预算的货。",
                "翡翠有棉就不能买？这要看它长在哪里。",
                "用灯光和自然光拍棉的位置，标出影响美观和不影响佩戴的差别。",
                "引导评论“棉”获取检查清单，私信发图看具体情况。",
                91,
            ),
            (
                "直播间看翡翠和四会现场看货，最大差别在哪里",
                "场景对比",
                "用户在线上看货担心灯光、滤镜和角度影响判断。",
                "直播间很好看，现场也一定好看吗？不一定。",
                "同一件翡翠分别在直播灯、自然光、室内光下拍摄对比。",
                "让用户私信直播截图和预算，提示需要补看哪些角度。",
                90,
            ),
            (
                "买翡翠送礼，别只问贵不贵，先确认这三个场景",
                "送礼建议",
                "用户为送礼买翡翠，容易只看价格，不看年龄、风格和寓意。",
                "送翡翠不是越贵越稳，关键是送给谁、什么场合戴。",
                "摆出吊坠、手镯、平安扣三类货，按年龄和场景快速讲选择逻辑。",
                "评论送礼对象和预算，私信承接款式范围建议。",
                89,
            ),
            (
                "小红书用户最该看的翡翠日常佩戴避坑",
                "平台种草",
                "用户喜欢好看搭配，但担心实物和上身效果不一致。",
                "翡翠日常戴好不好看，别只看柜台灯下那一眼。",
                "拍自然光上身、通勤穿搭、近景细节，展示颜色和肤色匹配。",
                "引导收藏搭配清单，私信肤色和预算给款式方向。",
                88,
            ),
            (
                "快手真实看货：这只手镯为什么我不建议新手冲",
                "真实看货",
                "用户想听实话，尤其怕商家只推利润高的货。",
                "这只镯子看着挺亮，但新手我不建议急着买。",
                "现场拿货口播，直接指出纹裂、底子或价格不匹配的问题。",
                "引导评论“想看实话看货”，私信预算做避坑建议。",
                93,
            ),
            (
                "视频号适合讲的翡翠老客户复购案例",
                "案例复盘",
                "熟人关系用户更重视长期靠谱和售后沟通。",
                "为什么老客户第二次买翡翠，会先问我这三个问题？",
                "用匿名客户案例讲需求变化，展示选品过程和最终取舍。",
                "引导私信说明第一次购买经历，判断下一件适合怎么选。",
                90,
            ),
            (
                "翡翠吊坠看厚度，别只看正面颜色",
                "细节避坑",
                "用户看吊坠只看正面，忽略厚薄影响质感和价值。",
                "吊坠正面好看不够，侧面厚度也要看。",
                "手持吊坠正面、侧面、透光三组镜头，对比薄料和厚装差异。",
                "评论吊坠用途，私信发图帮看厚度和佩戴效果。",
                91,
            ),
            (
                "翡翠手镯有纹有裂，买之前怎么分清风险",
                "风险判断",
                "用户分不清纹裂，担心后期佩戴断裂或亏钱。",
                "纹和裂不是一回事，买手镯前一定要分清。",
                "用灯照、指甲轻触、侧面特写演示纹裂判断方法。",
                "引导私信发细节视频，提醒先看清再决定。",
                95,
            ),
            (
                "四会市场一天看 30 件货，我会先淘汰哪几类",
                "源头市场",
                "用户想知道专业卖家如何筛货，降低自己试错成本。",
                "我在四会一天看几十件货，最先淘汰的是这几类。",
                "边走边拍档口货盘，逐类讲淘汰原因和保留标准。",
                "评论“筛货标准”获取清单，私信预算匹配货品方向。",
                94,
            ),
            (
                "买翡翠怕买贵，先学会问这四个问题",
                "成交引导",
                "用户不会问问题，容易只问最低价而失去判断依据。",
                "别一开口就问最低价，先问这四个问题更有用。",
                "真人口播列问题，配实物镜头演示每个问题对应看哪里。",
                "引导评论“问题”，私信发送问价话术模板。",
                92,
            ),
            (
                "翡翠戒面为什么小小一颗也可能很贵",
                "品类科普",
                "用户用大小判断价格，不理解戒面对颜色和净度要求更高。",
                "戒面这么小，为什么比大吊坠还贵？",
                "拍戒面微距、颜色饱满度、瑕疵位置，和普通吊坠做对比。",
                "引导私信预算和喜欢的颜色，推荐适合入门的品类。",
                87,
            ),
            (
                "客户说想要冰透又便宜，我通常会怎么劝",
                "客户问答",
                "用户既想高品质又想低价，需要被真实预期管理。",
                "想要冰透又便宜，可以，但你要接受这几个取舍。",
                "模拟客户问答，拿实物讲颜色、大小、瑕疵和预算的取舍。",
                "评论预算区间，私信承接具体取舍建议。",
                93,
            ),
            (
                "抖音 60 秒讲清一件翡翠值不值得继续看",
                "短视频钩子",
                "用户刷到货品时没有快速判断框架。",
                "一件翡翠值不值得继续看，我先看这三步。",
                "用快节奏镜头拍整体、细节、价格档位，字幕列三步判断。",
                "引导用户收藏判断框架，私信发图按三步看。",
                94,
            ),
            (
                "四会卖翡翠多年，我最怕新手忽略售后沟通",
                "信任背书",
                "用户只关注成交前价格，忽略售后、复检和沟通边界。",
                "买翡翠不是付完钱就结束，售后沟通也很重要。",
                "真人出镜讲多年经验，配打包、复检、沟通记录等非敏感镜头。",
                "引导私信咨询购买流程，说明可提前确认哪些事项。",
                89,
            ),
            (
                "月底复盘：哪类翡翠视频最容易带来有效咨询",
                "数据复盘",
                "创作者和商家想知道哪些内容更容易获客成交。",
                "这个月最容易带来有效咨询的，不是最热闹的视频。",
                "展示不含隐私的数据表，复盘评论、私信、成交意向和选题类型。",
                "引导同行或买家评论最关心的问题，沉淀下月选题。",
                88,
            ),
        ]

        topics = []
        if content_format == "video_spoken":
            # 口播使用专门的话题型模板
            for index in range(count):
                title, content_type, intro = spoken_templates[index % len(spoken_templates)]
                topic = {
                    "title": title if index < len(spoken_templates) else f"{title}（第 {index + 1} 期）",
                    "platform": platform,
                    "content_type": content_type,
                    "goal": goal,
                    "score": 90 + (index % 7),
                    "spoken_script": (
                        f"大家好，今天我们来聊一个话题：{title}。\n\n"
                        f"{intro}\n\n"
                        f"我在四会源头市场多年，见过太多翠友在这个问题上纠结。"
                        f"其实答案很简单——根据你的实际情况来选，适合自己的才是最好的。\n\n"
                        f"如果你也有这方面的困惑，欢迎在评论区留言，或者私信我聊聊你的具体情况。"
                    ),
                }
                topics.append(topic)
        else:
            # 视频/图片使用详细模板
            for index in range(count):
                title, content_type, pain, hook, shooting, conversion, score = templates[
                    index % len(templates)
                ]
                topic = {
                    "title": title if index < len(templates) else f"{title}（第 {index + 1} 版）",
                    "platform": platform,
                    "content_type": content_type,
                    "goal": goal,
                    "selling_point": "四会源头市场真实看货、翡翠避坑和预算选品建议",
                    "score": score,
                }
                if content_format in ("video", "video_script"):
                    topic["user_pain_point"] = pain
                    topic["hook"] = hook
                    topic["shooting_suggestion"] = shooting
                    topic["conversion_method"] = conversion
                    topic["shooting_script"] = f"开场用这句话引出痛点：{hook} 随后按实物近景、自然光细节、对比说明和结尾承接四段拍摄。"
                    topic["seedance_video_prompt"] = f"参考图为翡翠实物，生成短视频：真人在四会市场自然光环境中展示产品细节，主题是{title}，画面真实清透。"
                elif content_format == "image":
                    # 图片选题只需要 title，不需要其他字段
                    pass
                elif content_format == "image_to_image":
                    # 图生图选题只需要 title
                    pass
                topics.append(topic)

        return {"topics": topics}

    def _mock_script(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata = metadata or {}
        topic_title = str(metadata.get("topic_title") or "新手买翡翠别先问价格")
        platform = str(metadata.get("platform") or "抖音")
        script_type = str(metadata.get("script_type") or "聊观点")
        duration = str(metadata.get("duration") or "60秒")
        goal = str(metadata.get("goal") or "私信获客")
        return {
            "title": topic_title,
            "hook": "同样在四会源头市场看翡翠，为什么有人买得明白，有人一开口就容易被带着走？",
            "script_content": (
                f"今天用{duration}聊一个{script_type}选题：{topic_title}。\n"
                "如果你喜欢翡翠、也想买翡翠，第一步不要急着问最低多少钱。"
                "在四会源头市场，同样叫冰种、同样看着很亮，实际的种水、棉、纹裂、厚度和工艺都可能差很多。\n"
                "我在四会卖翡翠多年，给客户看货时通常先做三件事：第一，看自然光下整体是否干净；"
                "第二，看细节有没有明显纹裂和影响佩戴的瑕疵；第三，把预算、用途和款式放在一起判断。"
                "比如日常戴，不一定要追求最冰最透，稳定、耐看、少瑕疵更重要；如果是送礼，就要考虑年龄、场合和寓意。\n"
                f"所以这条内容在{platform}上不是让你冲动下单，而是先学会问对问题。"
                f"如果你的目标是{goal}，结尾一定要把预算、用途和实物图收回来，才能给到更准确的建议。"
            ),
            "shot_suggestions": [
                "真人在四会市场档口前开场，手里拿一件翡翠实物提出痛点。",
                "切两件价格差异明显的翡翠近景，对比种水、棉和纹裂。",
                "用自然光和室内光各拍 3 秒，展示同一件货的真实观感。",
                "正面出镜总结三步判断法，并引导评论或私信。",
            ],
            "subtitle_points": [
                "别先问最低价",
                "先看自然光和细节",
                "预算、用途、款式一起判断",
                "四会源头看货更要问对问题",
            ],
            "conversion_script": "想买翡翠但怕踩坑，可以在评论区说预算和用途，或者私信发实物图，我帮你先看该重点注意哪里。",
            "comment_guidance": "评论区引导：你的预算是多少？日常戴、送礼还是收藏？我按用途给你一个选品方向。",
            "private_message_guidance": "私信引导：发预算、圈口或款式偏好，再发 1-2 张实物图，我先帮你判断是否值得继续看。",
        }

    def _chat_completions_url(self, base_url: str) -> str:
        cleaned = base_url.rstrip("/")
        if cleaned.endswith("/chat/completions"):
            return cleaned
        return f"{cleaned}/chat/completions"

    def _responses_url(self, base_url: str) -> str:
        cleaned = self._prefer_https_for_public_url(self._strip_url_method_prefix(base_url).rstrip("/"))
        if cleaned.endswith("/responses"):
            return cleaned
        if cleaned.endswith("/chat/completions"):
            cleaned = cleaned[: -len("/chat/completions")]
        return f"{cleaned}/responses"

    def _prefer_https_for_public_url(self, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme.lower() != "http":
            return value
        hostname = (parsed.hostname or "").lower()
        if (
            hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
            or hostname.startswith("10.")
            or hostname.startswith("192.168.")
            or hostname.endswith(".local")
        ):
            return value
        if hostname.startswith("172."):
            parts = hostname.split(".")
            if len(parts) > 1 and parts[1].isdigit() and 16 <= int(parts[1]) <= 31:
                return value
        return urlunsplit(("https", parsed.netloc, parsed.path, parsed.query, parsed.fragment))

    def _openai_compatible_base_url(self, provider: str) -> str:
        base_url = self._strip_url_method_prefix(self.settings.llm_base_url).rstrip("/")
        if provider != "dataeye" or not base_url:
            return base_url
        if base_url.endswith("/v1") or base_url.endswith("/chat/completions"):
            return base_url
        return f"{base_url}/v1"

    def _web_search_base_url(self, provider: str) -> str:
        override = self._strip_url_method_prefix(self.settings.web_search_base_url).rstrip("/")
        if override:
            return override
        return self._openai_compatible_base_url(provider)

    def _strip_url_method_prefix(self, value: str) -> str:
        cleaned = value.strip()
        parts = cleaned.split(maxsplit=1)
        if len(parts) == 2 and parts[0].upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            return parts[1].strip()
        return cleaned

    def _anthropic_messages_url(self, base_url: str) -> str:
        cleaned = base_url.rstrip("/")
        if cleaned.endswith("/v1/messages") or cleaned.endswith("/messages"):
            return cleaned
        return f"{cleaned}/v1/messages"

    def _is_deepseek_endpoint(self, base_url: str, model: str) -> bool:
        return "deepseek" in base_url.lower() or "deepseek" in model.lower()

    def _openai_compatible_model(self, request: LLMGatewayRequest, base_url: str) -> str:
        module_name = request.module_name.lower().replace("-", "_")
        module_override = self._module_model_override(module_name)
        if module_override:
            return module_override

        if not self._is_deepseek_endpoint(base_url, self.settings.llm_model):
            return self.settings.llm_model

        if module_name == "topics":
            return self.settings.deepseek_topics_model
        if module_name == "account_package":
            return self.settings.deepseek_account_package_model
        return self.settings.llm_model

    def _web_search_model(self, request: LLMGatewayRequest, base_url: str) -> str:
        override = self.settings.web_search_model.strip()
        if override:
            return override
        return self._openai_compatible_model(request, base_url)

    def _module_model_override(self, module_name: str) -> str:
        if module_name == "account_package":
            return self.settings.account_package_model.strip()
        if module_name == "execution_plan":
            return self.settings.execution_plan_model.strip()
        return ""

    def _normalized_provider(self) -> str:
        provider = self.settings.llm_provider.strip().lower().replace("-", "_")
        if provider == "gpt_api":
            return "openai_compatible"
        return provider

    def _deepseek_openai_options(self, request: LLMGatewayRequest, model: str) -> dict[str, Any]:
        if "deepseek" not in model.lower():
            return {}
        if "flash" in model.lower():
            return {}

        module_name = request.module_name.lower().replace("-", "_")
        if module_name == "account_package":
            return {
                "thinking": {"type": "enabled"},
                "reasoning_effort": "max",
            }
        return {"thinking": {"type": "disabled"}}

    def _extract_openai_content(self, body: dict[str, Any]) -> str:
        choices = body.get("choices") or []
        if not choices:
            return ""

        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)

    def _extract_responses_content(self, body: dict[str, Any]) -> str:
        output_text = body.get("output_text")
        if isinstance(output_text, str):
            return output_text

        parts: list[str] = []
        for output_item in body.get("output") or []:
            if not isinstance(output_item, dict):
                continue
            for content_item in output_item.get("content") or []:
                if isinstance(content_item, str):
                    parts.append(content_item)
                    continue
                if not isinstance(content_item, dict):
                    continue
                text = content_item.get("text") or content_item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()

    def _decode_responses_body(self, response: httpx.Response) -> dict[str, Any]:
        content_type = response.headers.get("content-type", "")
        text = response.text
        if "text/event-stream" in content_type.lower() or text.lstrip().startswith(("event:", "data:")):
            return self._parse_responses_event_stream(text)
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Responses API returned non-object JSON")
        return body

    def _parse_responses_event_stream(self, text: str) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        data_lines: list[str] = []

        def flush_event() -> None:
            if not data_lines:
                return
            raw_data = "\n".join(data_lines).strip()
            data_lines.clear()
            if not raw_data or raw_data == "[DONE]":
                return
            payload = json.loads(raw_data)
            if isinstance(payload, dict):
                events.append(payload)

        for raw_line in text.splitlines():
            line = raw_line.rstrip("\r")
            if not line:
                flush_event()
                continue
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
        flush_event()

        for event in reversed(events):
            if event.get("type") == "response.completed" and isinstance(event.get("response"), dict):
                return event["response"]

        text_parts = [
            event["text"]
            for event in events
            if event.get("type") == "response.output_text.done" and isinstance(event.get("text"), str)
        ]
        if text_parts:
            return {"output_text": "\n".join(text_parts), "output": [], "usage": {}}
        raise ValueError("Responses API event stream did not include a completed response")

    def _extract_responses_sources(self, body: dict[str, Any]) -> list[dict[str, Any]]:
        sources: list[dict[str, Any]] = []

        def add_source(value: dict[str, Any]) -> None:
            url = value.get("url")
            if not isinstance(url, str) or not url.strip():
                return
            if any(source.get("url") == url for source in sources):
                return
            title = value.get("title")
            sources.append(
                {
                    "url": url,
                    "title": title if isinstance(title, str) and title.strip() else url,
                }
            )

        for output_item in body.get("output") or []:
            if not isinstance(output_item, dict):
                continue
            action = output_item.get("action")
            if isinstance(action, dict):
                for source in action.get("sources") or []:
                    if isinstance(source, dict):
                        add_source(source)
            for content_item in output_item.get("content") or []:
                if not isinstance(content_item, dict):
                    continue
                for annotation in content_item.get("annotations") or []:
                    if isinstance(annotation, dict):
                        add_source(annotation)
        return sources

    def _extract_anthropic_content(self, body: dict[str, Any]) -> str:
        content = body.get("content") or []
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return json.dumps(content, ensure_ascii=False)

        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)

    def _normalize_anthropic_usage(self, usage: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(usage)
        input_tokens = normalized.get("input_tokens", 0) or 0
        output_tokens = normalized.get("output_tokens", 0) or 0
        normalized["prompt_tokens"] = input_tokens
        normalized["completion_tokens"] = output_tokens
        normalized["total_tokens"] = input_tokens + output_tokens
        return normalized

    def _parse_json_content(self, content: str) -> Any:
        if not content:
            return {}

        normalized = self._strip_markdown_json_fence(content.strip())
        try:
            return json.loads(normalized)
        except json.JSONDecodeError:
            extracted = self._extract_first_json_value(normalized)
            if extracted is not None:
                try:
                    return json.loads(extracted)
                except json.JSONDecodeError:
                    repaired = self._repair_unescaped_inner_quotes(extracted)
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError:
                        pass
            return {"text": content}

    def _strip_markdown_json_fence(self, content: str) -> str:
        if not content.startswith("```"):
            return content

        lines = content.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            if lines[-1].strip().startswith("```"):
                return "\n".join(lines[1:-1]).strip()
            return "\n".join(lines[1:]).strip()
        return content

    def _extract_first_json_value(self, content: str) -> str | None:
        starts = [index for index in (content.find("{"), content.find("[")) if index >= 0]
        if not starts:
            return None

        start = min(starts)
        opener = content[start]
        closer = "}" if opener == "{" else "]"
        depth = 0
        in_string = False
        escaped = False

        for index in range(start, len(content)):
            char = content[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
            elif char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
                if depth == 0:
                    return content[start : index + 1]

        return None

    def _repair_unescaped_inner_quotes(self, content: str) -> str:
        repaired = []
        in_string = False
        escaped = False

        for index, char in enumerate(content):
            if escaped:
                repaired.append(char)
                escaped = False
                continue

            if char == "\\":
                repaired.append(char)
                escaped = in_string
                continue

            if char == '"':
                if not in_string:
                    in_string = True
                    repaired.append(char)
                    continue

                next_non_space = self._next_non_space(content, index + 1)
                if next_non_space in {":", ",", "]", "}", None}:
                    in_string = False
                    repaired.append(char)
                else:
                    repaired.append('\\"')
                continue

            repaired.append(char)

        return "".join(repaired)

    def _next_non_space(self, content: str, start: int) -> str | None:
        for char in content[start:]:
            if not char.isspace():
                return char
        return None

    def _error_response(
        self,
        provider: str,
        model: str,
        started_at: float,
        error: str,
    ) -> LLMGatewayResponse:
        return LLMGatewayResponse(
            success=False,
            provider=provider,
            model=model,
            content="",
            data={},
            usage={},
            sources=[],
            latency_ms=self._elapsed_ms(started_at),
            error=error,
        )

    def _elapsed_ms(self, started_at: float) -> int:
        return max(0, int((time.perf_counter() - started_at) * 1000))
