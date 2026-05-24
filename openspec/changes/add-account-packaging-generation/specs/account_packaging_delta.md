# Delta: Account Packaging

**Change ID:** `add-account-packaging-generation`
**Affects:** account packaging generation, account strategy context, generation records, project detail workflow

---

## ADDED

### Requirement: Generate Account Packaging From Project Profile

The system SHALL generate a structured account packaging strategy from an existing project profile.

#### Scenario: Generate account packaging successfully
- GIVEN a project profile exists with industry, product/service, personal intro, target audience, platforms, and current stage
- WHEN the user requests account packaging generation for that project
- THEN the system returns a structured account packaging result
- AND the result includes account positioning, persona, target user profile, account name suggestions, platform bios, content columns, trust design, conversion path, and platform strategies

#### Scenario: Project does not exist
- GIVEN no project exists for the requested project id
- WHEN the user requests account packaging generation
- THEN the system rejects the request with a not found error

### Requirement: Route AI Calls Through LLM Gateway

The system SHALL route account packaging generation through `backend/app/llm/llm_gateway.py`.

#### Scenario: Mock provider generation
- GIVEN `LLM_PROVIDER=mock`
- WHEN account packaging generation is requested
- THEN the gateway returns deterministic structured account packaging data
- AND the API response uses that data without calling any external provider directly

#### Scenario: OpenAI-compatible provider failure
- GIVEN `LLM_PROVIDER=openai_compatible`
- AND the provider request fails
- WHEN account packaging generation is requested
- THEN the API returns a generation failure response
- AND no incomplete account strategy context is created

### Requirement: Persist Generation Audit Record

The system SHALL save a generation record for every account packaging generation handled by the LLM Gateway.

#### Scenario: Generation record is created
- GIVEN account packaging generation completes through the gateway
- WHEN the response is returned
- THEN a generation record exists with module name, project id, input data, output data, provider, model, prompt version, token usage, and latency
- AND the response includes the generation record id

### Requirement: Persist Account Strategy Context

The system SHALL persist the generated account packaging result as reusable account strategy context.

#### Scenario: Account strategy context is saved
- GIVEN account packaging generation succeeds
- WHEN the normalized result is persisted
- THEN an account strategy context exists for the project
- AND it is linked to the generation record when available
- AND it stores structured strategy fields and context metadata for downstream execution plan, topic, and script generation

### Requirement: Display Generated Account Packaging

The frontend SHALL provide a project-level account packaging page where users can trigger generation and inspect the result.

#### Scenario: User reviews generated strategy
- GIVEN the user is viewing a project
- WHEN the user opens account packaging and generates a strategy
- THEN the page displays the generated positioning, persona, target profile, account names, bios, content columns, trust design, conversion path, platform strategies, and generation metadata

#### Scenario: Generation fails in UI
- GIVEN the account packaging API returns an error
- WHEN the user triggers generation
- THEN the page stops loading and shows a user-facing error message

---

## MODIFIED

### Requirement: Project Profile Supports Downstream Strategy Generation

Project profiles SHALL provide the source context required by account packaging prompts, including industry, sub-industry, product/service, personal intro, target audience, platforms, and current account stage.

#### Scenario: Prompt uses project context
- GIVEN a complete project profile
- WHEN account packaging prompts are built
- THEN the prompt includes the project profile fields needed to produce platform-specific and industry-specific strategy output

---

## REMOVED

(None)
