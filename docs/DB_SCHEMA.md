# DB_SCHEMA

## projects

存储用户创建的短视频账号项目。

字段：
- id
- user_id
- project_name
- industry
- sub_industry
- product
- personal_intro
- target_audience
- platforms JSONB
- current_stage
- created_at
- updated_at

## account_strategy_contexts

存储账号包装方案和后续创作要使用的账号策略上下文。

字段：
- id
- project_id
- account_positioning
- persona
- target_user_profile JSONB
- content_style
- trust_points JSONB
- monetization_paths JSONB
- platform_strategies JSONB
- execution_stage
- context_data JSONB
- created_at
- updated_at

## generation_records

存储所有 AI 生成记录。

字段：
- id
- user_id
- project_id
- module_name
- input_data JSONB
- output_data JSONB
- model_provider
- model_name
- prompt_version
- token_usage JSONB
- latency_ms
- created_at

## topics

存储 AI 生成的选题。

字段：
- id
- project_id
- title
- content_type
- platform
- goal
- selling_point
- score
- topic_data JSONB
- created_at

## scripts

存储 AI 生成的视频文案。

字段：
- id
- project_id
- topic_id
- title
- script_type
- platform
- script_content
- shot_suggestions JSONB
- conversion_script
- script_data JSONB
- created_at

## industry_templates

存储行业模板。

字段：
- id
- industry_name
- sub_industry
- pain_points JSONB
- common_topics JSONB
- trust_points JSONB
- conversion_hooks JSONB
- content_scenes JSONB
- created_at

## platform_rules

存储平台规则。

字段：
- id
- platform_name
- content_style
- user_behavior
- recommended_tone
- hook_rules JSONB
- conversion_rules JSONB
- created_at

## prompt_templates

存储 Prompt 模板。

字段：
- id
- module_name
- prompt_name
- system_prompt
- user_prompt_template
- output_schema JSONB
- version
- is_active
- created_at
