import json
import time
from typing import Any

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.schemas.generation_record import GenerationRecordCreate
from app.services.gateway_provider_service import get_default_gateway_provider
from app.services.generation_record_service import create_generation_record


class LLMGatewayRequest(BaseModel):
    module_name: str = Field(min_length=1, max_length=80)
    system_prompt: str = Field(default="")
    user_prompt: str = Field(default="")
    output_schema: dict[str, Any] | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMGatewayResponse(BaseModel):
    success: bool
    provider: str
    model: str
    content: str
    data: Any = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    latency_ms: int
    error: str | None = None
    generation_record_id: int | None = None


class RuntimeProviderConfig(BaseModel):
    source: str = "environment"
    provider: str
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class LLMGateway:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    def generate(
        self,
        db: Session,
        request: LLMGatewayRequest,
        project_id: int | None = None,
        user_id: int | None = None,
        prompt_version: str | None = "v1",
    ) -> LLMGatewayResponse:
        runtime_provider = self._resolve_chat_provider(db)
        provider = runtime_provider.provider.strip().lower().replace("-", "_")

        if provider == "mock":
            result = self._generate_mock(request, runtime_provider)
        elif provider == "openai_compatible":
            result = self._generate_openai_compatible(request, runtime_provider)
        else:
            result = self._error_response(
                provider=provider or "unknown",
                model=runtime_provider.model or self.settings.llm_model,
                started_at=time.perf_counter(),
                error=f"Unsupported chat provider: {runtime_provider.provider}",
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

    def _resolve_chat_provider(self, db: Session) -> RuntimeProviderConfig:
        provider_config = get_default_gateway_provider(db, "chat")
        if provider_config is not None:
            return RuntimeProviderConfig(
                source="database",
                provider=provider_config.provider,
                base_url=provider_config.base_url or "",
                api_key=provider_config.api_key or "",
                model=provider_config.model,
                config=provider_config.config or {},
            )

        return RuntimeProviderConfig(
            source="environment",
            provider=self.settings.llm_provider,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
            model=self.settings.llm_model,
            config={},
        )

    def _generate_mock(
        self,
        request: LLMGatewayRequest,
        runtime_provider: RuntimeProviderConfig,
    ) -> LLMGatewayResponse:
        started_at = time.perf_counter()
        data = self._mock_data_for_module(request.module_name, request.metadata)
        content = json.dumps(data, ensure_ascii=False, indent=2)
        return LLMGatewayResponse(
            success=True,
            provider="mock",
            model=runtime_provider.model or self.settings.llm_model or "mock-model",
            content=content,
            data=data,
            usage={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            latency_ms=self._elapsed_ms(started_at),
        )

    def _generate_openai_compatible(
        self,
        request: LLMGatewayRequest,
        runtime_provider: RuntimeProviderConfig,
    ) -> LLMGatewayResponse:
        started_at = time.perf_counter()
        provider = "openai_compatible"
        model = runtime_provider.model or self.settings.llm_model
        base_url = runtime_provider.base_url.strip()
        timeout_seconds = float(
            runtime_provider.config.get("timeout_seconds") or self.settings.llm_timeout_seconds
        )

        if not base_url:
            return self._error_response(
                provider=provider,
                model=model,
                started_at=started_at,
                error="LLM_BASE_URL is required when LLM_PROVIDER=openai_compatible",
            )

        url = self._chat_completions_url(base_url)
        headers = {"Content-Type": "application/json"}
        if runtime_provider.api_key:
            headers["Authorization"] = f"Bearer {runtime_provider.api_key}"
        extra_headers = runtime_provider.config.get("headers")
        if isinstance(extra_headers, dict):
            headers.update({str(key): str(value) for key, value in extra_headers.items()})

        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.user_prompt},
            ],
            "temperature": request.temperature,
        }
        extra_payload = runtime_provider.config.get("payload")
        if isinstance(extra_payload, dict):
            payload.update(extra_payload)

        try:
            response = httpx.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout_seconds,
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
                error=f"LLM request timed out after {timeout_seconds} seconds: {exc}",
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
        if "account" in normalized or "package" in normalized or "账号" in normalized:
            return self._mock_account_package()
        if "execution" in normalized or "plan" in normalized or "执行" in normalized:
            return self._mock_execution_plan(metadata or {})
        if "topic" in normalized or "选题" in normalized:
            return self._mock_topics(metadata or {})
        if "script" in normalized or "copy" in normalized or "文案" in normalized:
            return self._mock_script(metadata or {})

        return {
            "module_name": module_name,
            "summary": "mock provider 示例输出",
            "next_step": "请使用 account_package、execution_plan、topics 或 script 模块名测试固定 JSON。",
        }

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
        count = int(metadata.get("count") or 20)
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
        for index in range(count):
            title, content_type, pain, hook, shooting, conversion, score = templates[
                index % len(templates)
            ]
            topics.append(
                {
                    "title": title if index < len(templates) else f"{title}（第 {index + 1} 版）",
                    "platform": platform,
                    "content_type": content_type,
                    "goal": goal,
                    "selling_point": "四会源头市场真实看货、翡翠避坑和预算选品建议",
                    "user_pain_point": pain,
                    "hook": hook,
                    "shooting_suggestion": shooting,
                    "conversion_method": conversion,
                    "score": score,
                }
            )

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

    def _extract_openai_content(self, body: dict[str, Any]) -> str:
        choices = body.get("choices") or []
        if not choices:
            return ""

        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
        return json.dumps(content, ensure_ascii=False)

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
            latency_ms=self._elapsed_ms(started_at),
            error=error,
        )

    def _elapsed_ms(self, started_at: float) -> int:
        return max(0, int((time.perf_counter() - started_at) * 1000))
