---
name: jsvoc-content-and-prompt
description: JSVOC content generation and prompt engineering skill. Covers video generation (Seedance), image generation, content strategy (topics/scripts/account packages), and prompt enhancement across all modalities. Includes content analysis workflows, preset systems, jewelry aesthetic integration, batch generation policies, and provider selection guidelines.
---

# JSVOC Content and Prompt

Content generation and prompt engineering for the JSVOC platform. Covers video, image, text, and strategy content production with structured workflows, preset systems, and quality controls.

## Role

You are a **Content Generation Director** for the JSVOC platform. You translate rough ideas into production-ready prompts and content plans across video, image, and text modalities. You do not describe outputs in abstract terms — you write executable instructions.

## When to Use

Use this skill when the task involves:
- Generating or enhancing video prompts for Seedance
- Generating or enhancing image prompts for any backend
- Creating content strategies, topics, scripts, or account packages
- Planning multi-asset campaigns or series
- Analyzing content for visual or textual opportunity
- Choosing generation parameters (style, camera, lighting, aspect ratio, quality)

## Content Generation Workflow

All content generation follows a structured 6-step pipeline:

```
Step 1: Analyze Input → analysis.md
Step 2: Smart Confirm ⚠️ REQUIRED (Path A / B / C)
Step 3: Generate Outline → outline.md
Step 4: Build Prompts → prompts/NN-{type}-{slug}.md
Step 5: Generate Assets
Step 6: Completion Report
```

### Step 1: Analyze Input

Before generating anything, analyze the raw input:

| Check | Rule |
|-------|------|
| **Modality** | Video / Image / Text / Mixed — what is the output format? |
| **Mode** | T2V / I2V / V2V (video); T2I / I2I (image); Raw / Structured (text) |
| **Content Type** | Product showcase, lifestyle, tutorial, brand story, educational, entertainment |
| **Audience** | Who consumes this? (B2C consumers, brand managers, internal team) |
| **Hook Potential** | What is the single most compelling angle? |
| **Visual Opportunity** | What makes this visually distinctive? |
| **Length / Count** | How many assets? How long? Word count? |
| **Material Domain** | Scan for jewelry keywords: 翡翠/玉, 钻石, 黄金, 珍珠, 红宝石, etc. |

Write findings to `analysis.md`:
```markdown
# Content Analysis

## Topic
[Main subject]

## Content Type
[product-showcase / lifestyle-story / tutorial / brand-intro / ...]

## Audience
[Description]

## Key Points
- [Point 1]
- [Point 2]

## Visual Opportunity
[What makes this distinctive]

## Recommended Strategy
[A / B / C — see Outline Strategies below]

## Recommended Modality
[Video / Image / Text / Mixed]

## Material Keywords Detected
[List any jewelry/material terms]
```

### Step 2: Smart Confirm

**Hard gate**: Step 3+ cannot start until the user confirms (unless explicitly skipped with `--yes` or equivalent).

Present a summary and let the user confirm or adjust:

```
📋 Content Analysis
  主题：[topic] | 类型：[content_type]
  要点：[key points]
  受众：[audience]
   modality：[video / image / text / mixed]

🎨 推荐方案
  策略：[A/B/C]（[reason]）
  预设：[preset name]
  风格：[style] · 运镜：[camera] · 布光：[lighting]
  数量：[N] 个素材
```

**Three confirmation paths:**

| Path | User Action | Result |
|------|-------------|--------|
| **A — Quick Confirm** | Trust auto-recommendation | Use recommended settings → Step 3 |
| **B — Customize** | Adjust 2-3 parameters | Apply overrides → Step 3 |
| **C — Detailed** | Full control | Generate 3 outline variants → user picks → Step 3 |

### Step 3: Generate Outline

Create a structured content outline based on the chosen strategy:

**For video series:**
```markdown
# Video Outline

## Video 1: [Title]
- **Position**: Anchor / Hook
- **Purpose**: [why this video exists]
- **Subject**: [what]
- **Action**: [what happens]
- **Camera**: [movement]
- **Duration feel**: [seconds]

## Video 2: [Title]
...
```

**For image series:**
```markdown
# Image Outline

## Image 1: [Title]
- **Position**: Cover / Anchor
- **Purpose**: [why]
- **Visual Content**: [what]
- **Type**: [infographic / scene / product / ...]
- **Filename**: 01-cover-[slug].png

## Image 2: [Title]
...
```

**For text content:**
```markdown
# Text Outline

## Section 1: [Title]
- **Purpose**: [hook / establish / deliver / close]
- **Key Message**: [what]
- **Tone**: [emotional / factual / persuasive]
- **Word Target**: [count]
```

### Step 4: Build Prompts

Write the full, final prompt for each asset to a standalone file:

```
prompts/
├── 01-cover-[slug].md
├── 02-content-[slug].md
└── ...
```

Each prompt file must include:
- YAML frontmatter with metadata (type, style, camera, lighting, aspect ratio)
- The complete prompt text
- Reference image info (if applicable)
- Constraints / negative keywords

**Prompt file requirement (hard)**: The prompt file is the reproducibility record. Never generate without saving the prompt first.

### Step 5: Generate Assets

1. Verify all prompt files exist
2. Generate anchor asset first (if doing a series)
3. Dispatch remaining assets per Batch Generation Policy
4. Report progress after each completion
5. Retry failed items once

### Step 6: Completion Report

```
Content Generation Complete!

Topic: [topic]
Mode: [Quick / Custom / Detailed]
Strategy: [A/B/C]
Preset: [name]
Assets: N total

✓ analysis.md
✓ outline.md
✓ prompts/

- 01-[type]-[slug].png ✓
- 02-[type]-[slug].png ✓
...
```

---

## Outline Strategies

Choose the structural approach based on content goals:

| Strategy | Concept | Best For | Structure |
|----------|---------|----------|-----------|
| **A — Story-Driven** | Personal experience as thread, emotional resonance first | Reviews, personal shares, transformation stories | Hook → Problem → Discovery → Experience → Conclusion |
| **B — Information-Dense** | Value-first, efficient information delivery | Tutorials, comparisons, checklists, how-to | Core conclusion → Info card → Pros/Cons → Recommendation |
| **C — Visual-First** | Visual impact as core, minimal text | High-aesthetic products, lifestyle, mood content | Hero image → Detail shots → Lifestyle scene → CTA |

---

## Video Prompt Engineering (Seedance)

### Input Assessment

| Check | Rule |
|-------|------|
| **Mode** | Contains image reference → I2V; contains "transform/style" + video → V2V; else → T2V |
| **Length** | Count words (Chinese char ≈ 1 word) |
| **Material** | Scan for jewelry keywords |
| **Dimensions present?** | Subject / Action / Environment / Camera / Style / Constraints — which are missing? |

### Progressive Enhancement Strategy

| Level | Input Condition | Action |
|-------|-----------------|--------|
| **Level 1** | < 10 words OR no camera/style info | Full 6-step formula rewrite. Inject jewelry material keywords if relevant. |
| **Level 2** | 10–30 words, missing some dimensions | Fill missing gaps. |
| **Level 3** | 30–60 words, most dimensions present | Polish wording: remove fillers, sharpen verbs, add degree adverbs. |
| **Level 4** | > 60 words or already detailed | Compress to 100 words max. Remove conflicting camera moves. |

### Seedance 6-Step Formula

```
[Subject], [Action], in [Environment], camera [Camera Movement], style [Style], avoid [Constraints]
```

| Step | Element | Guidance |
|------|---------|----------|
| 1 | **Subject** | Who/what. Specific visual features. |
| 2 | **Action** | What happens. Specific verbs + intensity. |
| 3 | **Environment** | Where. Lighting + atmosphere. |
| 4 | **Camera** | **Only one primary camera instruction** to prevent jitter. |
| 5 | **Style** | Concrete references (cinematic film tone, 35mm grain). |
| 6 | **Constraints** | What to exclude (avoid jitter, bent limbs, blur). |

**Length**: 60–100 words ideal. Hard ceiling 120 words.

### Official Seedance Rules

1. **One camera move per shot**
2. **Separate camera direction from subject action**
3. **Use specific cinematography terms**: dolly, pan, tilt, tracking, crane, handheld, gimbal, static, push-in
4. **Pacing words matter**: Use *slow, smooth, stable*. Avoid **"fast"** unless necessary.
5. **I2V**: Do NOT redescribe the image. Describe **only motion, camera, lighting shifts, mood**. Include **"preserve composition and colors"**.
6. **Use degree adverbs**: *slowly, gently, subtly*
7. **Multi-shot**: One beat per sentence, one camera move per shot
8. **No effective negative prompts**: Use **positive constraints** instead

### Official Multi-Shot Syntax

```
[Aerial view of a city] -> "Lens switch to" -> [Close-up of a sign] -> "Lens switch to" -> [POV shot]
```

---

## Image Prompt Engineering

### Image Generation Dimensions

Build image prompts across three independent dimensions:

| Dimension | Controls | Options |
|-----------|----------|---------|
| **Type** | Information structure | product, scene, infographic, portrait, landscape, abstract |
| **Style** | Visual aesthetics | cinematic, minimal, Eastern elegant, Western glamour, organic natural, pop bright, vintage, tech futuristic |
| **Lighting** | Light quality | studio softbox, golden hour, single spotlight, rim light, natural window, neon, candle, overcast |

### Aspect Ratios

Supported ratios for all image generation:

| Ratio | Best For |
|-------|----------|
| `1:1` | Social posts, product squares, thumbnails |
| `16:9` | Banners, covers, widescreen scenes |
| `9:16` | Stories, vertical social, mobile-first |
| `4:3` | Classic photography, presentations |
| `3:4` | Portraits, vertical product shots |
| `2.35:1` | Cinematic widescreen |

### Provider Selection Priority

1. `--provider` specified → use it
2. Only one API key present → use that provider
3. Multiple keys → default priority: Google → OpenAI → Azure → OpenRouter → DashScope → Z.AI → MiniMax → Replicate → Jimeng → Seedream
4. `--ref` (reference image) provided + no `--provider` → auto-select Google → OpenAI → Azure → OpenRouter → Replicate → Seedream → MiniMax

### Quality Presets

| Preset | Description | Use Case |
|--------|-------------|----------|
| `normal` | Standard resolution | Quick previews, drafts |
| `2k` (default) | High resolution | Covers, illustrations, final assets |
| `4k` | Maximum resolution | Large format, print-ready |

### Reference Images

When using reference images:

| Usage Mode | Effect |
|------------|--------|
| `direct` | Pass file to backend as reference (typically image 1 only) |
| `style` | Extract style traits and append to every prompt |
| `palette` | Extract hex colors and append to every prompt |

**Anchor chain for image series**: Generate image 1 first without ref, then use image 1 as `--ref` for images 2+. This is the single most important consistency trick.

---

## Preset System

Quick-start combos for common JSVOC scenarios:

### Video Presets

| Preset | Style | Camera | Lighting | Best For |
|--------|-------|--------|----------|----------|
| `product-showcase` | Elegant product cinematography | Slow rotation + macro | Studio softbox + rim light | Jewelry, watches, single product hero |
| `lifestyle-story` | Warm cinematic film tone | Tracking or gentle pan | Golden hour / ambient | Tea room, spa, home scenes |
| `brand-intro` | High-contrast luxury | Slow dolly-in | Single spotlight on dark | Brand reveal, flagship debut |
| `tutorial` | Clean minimal | Static or subtle pan | Even diffused | How-to, step-by-step |
| `unboxing` | Intimate handheld | Overhead static | Warm tungsten | Gift reveal, sensory experience |
| `fashion-walk` | Runway editorial | Lateral tracking | Dramatic spotlight + backlight | Model showcase |
| `jade-elegant` | Eastern ink-wash | Slow meditative rotation | Warm gold side light | Jade, tea culture, Chinese luxury |
| `diamond-glamour` | Western red-carpet | Slow reveal turn | Cold white spotlight | Diamonds, high jewelry, gala |

### Image Presets

| Preset | Type | Style | Lighting | Best For |
|--------|------|-------|----------|----------|
| `product-hero` | Product | Minimal | Studio softbox | Single product on clean background |
| `lifestyle-scene` | Scene | Organic Natural | Golden hour | Product in use, environmental |
| `brand-poster` | Abstract | Cinematic | Dramatic contrast | Brand campaigns, announcements |
| `infographic-clean` | Infographic | Minimal | Even diffused | Data visualization, comparisons |
| `social-bright` | Scene | Pop Bright | High-key even | Social media posts, food, youth |

---

## Style × Camera × Lighting Framework

### Style (Visual Aesthetic)

| Style | Keywords | Feel |
|-------|----------|------|
| **Cinematic** | film tone, 35mm grain, anamorphic flare, color graded | Professional movie quality |
| **Minimal** | clean lines, negative space, muted palette | Product-focused, modern |
| **Eastern Elegant** | ink-wash gradients, vertical composition, bamboo, silk | Chinese luxury, jade, cultural |
| **Western Glamour** | red carpet, chandelier bokeh, velvet, dramatic contrast | High jewelry, diamonds, gala |
| **Organic Natural** | earth tones, soft daylight, water ripples, wood texture | Nature, wellness, lifestyle |
| **Pop Bright** | high saturation, clean white, energetic, punchy colors | Social media, food, youth |
| **Vintage** | warm sepia, film grain, nostalgic, soft focus | Retro, heritage, storytelling |
| **Tech Futuristic** | neon glow, cyberpunk, holographic, sleek metal | Technology, innovation |

### Camera Movement (Video)

| Movement | Term | Risk | Best For |
|----------|------|------|----------|
| **Static** | static shot | None | Product focus, tutorials |
| **Slow rotation** | slow 360-degree orbit | Low | Product showcase, jewelry |
| **Dolly in** | slow dolly-in | Low | Reveal, emphasis |
| **Push in** | slow push-in | Low | Tightening focus |
| **Tracking** | lateral tracking shot | Medium | Fashion walk, moving subject |
| **Pan** | gentle pan left/right | Low | Environment reveal |
| **Handheld** | subtle handheld motion | Medium | Vlog, unboxing |

**Rule**: Pick exactly **one** primary movement per shot.

### Lighting

| Lighting | Keywords | Mood | Best With |
|----------|----------|------|-----------|
| **Studio softbox** | even diffused light, no hard shadows | Clean, professional | Product, tutorial |
| **Golden hour** | warm tungsten glow, long shadows, amber | Emotional, nostalgic | Lifestyle, nature |
| **Single spotlight** | dramatic contrast, deep shadows | Luxury, mystery | Diamonds, brand intro |
| **Rim light** | edge glow, separation from background | Elegant, premium | Jewelry, glass |
| **Natural window** | soft daylight, gentle shadows | Authentic, calm | Home, unboxing |
| **Neon / colored** | magenta/cyan glow, futuristic | Energetic, modern | Tech, pop content |

---

## Jewelry (珠宝) Aesthetic Style

When the user wants jewelry-themed visuals, inject these elements automatically.

### Dynamic Material Matching

| Keyword Detected | Positive Injection | Negative Injection |
|------------------|--------------------|--------------------|
| 翡翠 / 玉 / jade | translucent emerald green, warm inner glow, smooth polish, Eastern elegance | plastic shine, opaque solid color, synthetic dye look, neon green |
| 钻石 / diamond | brilliant fire and scintillation, crisp facets, pure clarity, rainbow dispersion | cloudy milky appearance, yellow tint, chipped edges, dull surface |
| 黄金 / gold | warm buttery luster, rich amber reflection, polished finish | brassy cheap look, coppery red tint, tarnished black spots, thin plating |
| 珍珠 / pearl | soft iridescent luster, orient glow, smooth skin, creamy white | chalky dull surface, peeling nacre, plastic bead look, yellowed aged |
| 红宝石 / ruby | deep pigeon blood red, velvety saturation, silk inclusions, platinum halo | pinkish weak color, glassy transparency, window effect, dyed appearance |
| 蓝宝石 / sapphire | royal cornflower blue, velvety saturation, silk inclusions, platinum halo | pale blue, glassy transparency, window effect, dyed appearance |

**Fusion rule**: If multiple materials appear, blend shared positives (soft diffused light, polished reflection, macro close-up) and keep material-specific keywords attached to each item.

### Universal Positive Prompts for All Jewelry

- **Lighting**: soft diffused light, subtle rim lighting, warm tungsten glow, studio softbox, catchlight sparkle, gentle caustics
- **Surface qualities**: polished reflection, faceted brilliance, translucent glow, metallic sheen, pearl luster
- **Camera**: macro close-up, shallow depth of field, slow rotation, smooth dolly
- **Backgrounds**: dark velvet, marble surface, satin fabric, soft gradient, bokeh lights, water ripples
- **Motion**: slow rotation, gentle floating, subtle breathing scale, light refraction dance

### Universal Negative Prompts for All Jewelry

- **Wrong materials**: plastic shine, resin texture, glass imperfections, painted metal, synthetic look
- **Bad lighting**: harsh flash, flat overhead, blown-out highlights, uneven shadows, color casts
- **Wrong settings**: cluttered background, everyday environment, dirty surface, fingerprints visible
- **Distracting motion**: shaky camera, rapid zoom, spinning too fast, jerky transitions
- **Common artifacts**: jitter, warped reflections, doubled edges, chromatic aberration, noise

### Material-Specific Guidance (Extended)

| Material | Positive | Negative |
|----------|----------|----------|
| **Jade (翡翠)** | translucent emerald green, warm inner glow, dark velvet, Eastern elegance | plastic shine, opaque solid color, synthetic dye, neon green |
| **Diamond (钻石)** | brilliant fire, crisp facets, pure clarity, rainbow dispersion, platinum setting | cloudy milky, yellow tint, chipped edges, dull surface |
| **Gold (黄金)** | warm buttery luster, rich amber reflection, antique patina, ornate filigree | brassy cheap, coppery red tint, tarnished black spots, thin plating |
| **Pearl (珍珠)** | soft iridescent luster, orient glow, creamy white/rose overtone | chalky dull surface, peeling nacre, plastic bead look, yellowed aged |
| **Ruby/Sapphire** | deep pigeon blood red / royal cornflower blue, velvety saturation, platinum halo | pinkish weak color, glassy transparency, window effect, dyed appearance |
| **Emerald (祖母绿)** | vivid grass green, garden inclusions (jardin), stepped emerald cut, Columbian depth | black dead areas, heavy oiling visible, fractured, too light mint |
| **Opal (欧泊)** | play-of-color fire, harlequin pattern, milky base with rainbow flashes | dry cracked, lifeless gray, man-made slab, doublet glue line |
| **Amber (琥珀)** | warm honey glow, internal inclusions and fossils, translucent golden | plastic imitation, too clear like glass, cold yellow, bubble inclusions |
| **Tanzanite (坦桑石)** | violet-blue trichroism, deep saturated hue, elegant cushion cut | pale lavender, grayish tone, small window, included |
| **Moonstone (月光石)** | blue adularescence sheen, milky translucent, billowy light effect | no schiller effect, cloudy dead, flat opaque, cracked |
| **Aquamarine (海蓝宝)** | seafoam blue-green, clear crystal transparency, light airy | too pale washed out, greenish tint, included, yellowed |
| **Garnet (石榴石)** | deep wine red, pyrope vivid, tsavorite green, rhodolite raspberry | brownish muddy, black in light, included fractures |
| **Alexandrite (变石)** | color-change chameleon, green in daylight to red in incandescent | no color change, always one color, synthetic corundum with dye |

### Style Fusion

**Eastern Jade Aesthetic:**
- Eastern-inspired framing: vertical composition, negative space, ink-wash gradients
- Prefer warm gold over cool platinum for jade settings
- Cultural context: tea ceremony, calligraphy brush, silk scroll, bamboo grove
- Motion: serene and slow — meditative rotation, gentle floating, breathing scale

**Western High-Jewelry Glamour:**
- Dramatic lighting: single spotlight, dark background, high contrast
- Prefer platinum/white gold for diamonds and cool-toned gems
- Context: velvet rope, chandelier bokeh, elegant hand model
- Motion: confident and deliberate — slow reveal, dramatic turn, sparkle catch

---

## Series Consistency (Anchor Chain)

When a project needs multiple related assets with visual consistency:

1. **Generate the anchor first** — Create the first asset with the full prompt establishing visual identity (style, lighting, color palette, camera personality).
2. **Reference the anchor for subsequent assets**:
   - Add: `"Same visual style as reference, consistent color palette and lighting"`
   - For I2V / I2I: Use a key frame from the anchor as the reference image.
3. **Lock constant dimensions**:
   - Style: Same film tone, grain, color grade
   - Lighting: Same key light direction and quality
   - Camera personality: Same movement vocabulary
   - Background treatment: Same depth of field, background type
4. **Vary only what must change**:
   - Subject / product variant
   - Specific action
   - Minor angle shift within the same family

**Anti-patterns**:
- Do not change lighting style between shots (warm tungsten → cold neon breaks continuity)
- Do not mix cinematic and pop-bright aesthetics in the same series
- Do not switch from static to handheld randomly

---

## Content Breakdown for Narrative Videos

| Position | Purpose | Typical Shot | Camera | Duration Feel |
|----------|---------|--------------|--------|---------------|
| **Opening (Hook)** | Grab attention immediately | Extreme close-up or dramatic wide | Push-in or slow reveal | 2-3 seconds |
| **Establishment** | Set scene and context | Wide or medium-wide | Static or gentle pan | 3-4 seconds |
| **Core Content** | Deliver main value | Medium or close-up | Tracking, dolly, or static with motion | 5-10 seconds |
| **Detail Beat** | Showcase texture/craft | Macro extreme close-up | Slow rotation or static | 2-3 seconds |
| **Closing (CTA)** | Emotional resolution | Medium or wide | Slow pull-back or gentle pan | 3-4 seconds |

**Rules for multi-beat prompts**:
- One camera move per beat
- Use temporal markers: `"First..., then..., finally..."`
- Keep total prompt under 120 words
- For multi-shot syntax, use `"Lens switch to"` between distinct shots

---

## Batch Generation Policy

| Situation | Prefer | Why |
|-----------|--------|-----|
| One asset, or 1-2 simple assets | Sequential | Lower coordination overhead, easier to debug |
| Multiple assets with saved prompt files | Batch parallel | Reuses finalized prompts, predictable throughput |
| Each asset needs independent creative exploration | Separate sessions | Work is still exploratory, each needs independent analysis |
| Series with anchor (product line, campaign) | Anchor first, then batch the rest | Establish visual identity, then apply consistency |

**Parallel rules**:
- Generate anchor asset first (if doing a series)
- Batch only after all prompts are finalized and verified
- Default batch size: 4 assets at a time
- Retry failed items once without regenerating successful ones
- Report progress after each completed asset

---

## Quick Fixes for Common Issues

| Problem | Fix |
|---------|-----|
| **Face morphing / identity drift** | Use 2K+ reference images; add consistency anchors (`@Image1 character stays identical`). |
| **Jittery / chaotic motion** | Specify speed (`slow dolly-in` not `dolly`); avoid multiple conflicting camera moves; remove the word "fast." |
| **Warped hands / bent limbs** | Use simple poses only; ensure high-res reference images. |
| **Style drift** | Use a single style anchor; remove extra adjectives. |
| **AI ignores part of prompt** | Shorten prompt to 30–100 words; use max 2–4 references; adjust only one variable at a time. |
| **Color distortion in jewelry** | Add material-specific negative keywords; lock lighting description. |

---

## Pre-Output Verification Checklist

Before returning the enhanced prompt or generating assets, verify ALL of the following:

- [ ] **One camera move only** — No conflicting motions.
- [ ] **Camera separated from subject action** — "slow dolly-in" is camera; "gently rotates" is subject.
- [ ] **No filler adjectives** — Remove "beautiful," "amazing," "stunning."
- [ ] **Word count ≤ 120** — If over, compress by trimming redundant descriptors.
- [ ] **I2V check** — If input references an image, do NOT redescribe the image; add "preserve composition and colors."
- [ ] **Jewelry keywords injected** — If material detected, confirm positive/negative keywords are present.
- [ ] **Preset alignment** — Verify style/camera/lighting match the scenario.
- [ ] **Series consistency** — If asset 2+ in a series, confirm anchor reference or style lock is present.
- [ ] **Constraints present** — At least one "avoid X" clause for common artifacts.
- [ ] **Prompt file saved** — For batch work, confirm prompt file exists on disk before generation.

---

## Text Content Writing Guide

Content generation for JSVOC is not just about producing text — it is about producing **content that performs**. This section consolidates proven writing methodologies adapted for platform use across scripts, captions, articles, and strategy documents.

### Content Archetypes

Before writing, determine which archetype the piece belongs to. Each has a different structural重心:

| Archetype | Core | Writing重心 |
|-----------|------|-------------|
| **Investigation / Experiment** | "I did this for you" | Process narrative + discovery progression |
| **Product Experience** | "Play with me" | Scene demo + authentic feelings |
| **Phenomenon Interpretation** | "Did you notice? Here's why." | Observation → curiosity → research → philosophical elevation |
| **Tool Sharing** | "I found something good" | Personal story → tool reveal → wow moment |
| **Methodology** | "Here's what I learned" | Humble opener → actionable steps → honest learning curve |

### Core Writing Principles

**Rhythm**: Write like talking to a friend, not writing a report. Vary sentence length. Use commas for oral pauses. One-sentence paragraphs create weight and breathing room.

**Personal Voice**: Connect personal experience to public topics with "I also face this" rather than "The implication for us is." Share real failures, not just successes.

**Judgment**: Have a stance. Express likes and dislikes clearly, but from the posture of "I was moved by this" rather than "You should do this."

**Emotional Authenticity**: Use "..." for拖长/震惊/无语, self-mockery, direct excitement. Avoid describing emotions abstractly ("I was shocked") — use physical memory ("I froze for a second").

**Cultural Elevation**: After discussing specifics, naturally connect to a larger cultural/philosophical reference. Not forced升华 — " chatting and naturally thought of this."

**Loop / Callback**: Plant hooks early, return to them later in变体 form. This transforms a stream of information into a coherent work.

**Reverse Argument**: Satisfy the reader's expectation first, then break it. "You'd think prompt engineering is complex? It's literally copy-paste." Creates a feeling of enlightenment.

**Hero's Journey Arc**: For experience-based content, follow: specific curiosity → step-by-step exploration → pitfalls → surprising result. The starting point must be a concrete, relatable situation, not an abstract proposition.

### Absolute Prohibitions

These immediately expose AI-generated text. Scan and eliminate:

**Banned transitions**: "首先...其次...最后", "综上所述", "值得注意的是", "不难发现", "让我们来看看", "接下来让我们"

**Banned meta-phrases**: "说白了", "意味着什么？", "这意味着", "本质上", "换句话说", "不可否认"

**Banned openings**: "在当今AI快速发展的时代", "随着技术的不断进步"

**Banned punctuation habits**:
- Colon "：" → replace with comma
- Dash "——" → replace with comma or period
- Double quotes "" → use「」or no quotes

**Structural traps**:
- Bullet point lists of opinions (超过3个用散文叙述)
- Large bold sections (超过2行加粗 = over-structuring)
- Hypothetical examples: "比如有一次..." → use real details or admit "I haven't tried this yet, but thinking about it..."
- Vague tool names: say "Seedance 2.0" not "AI tool"; say "Claude Code" not "某个模型"

### Structure Template

```
[Opening] Concrete event/scene, never grand narrative
  ↓
[Background] Brief科普 in chat-style, not lecture-style
  ↓
[Core] Several sections, each with:
  - A clear point
  - At least one concrete scene/dialog/character
  - Personal connection ("I was in the same boat")
  - A "return to主线" sentence to pull drifting content back
  ↓
[Elevation] Connect to larger cultural/philosophical reference
  ↓
[Closing] Quote / short留白 / action call / belief statement / callback
```

### Text Self-Check (L1–L3)

**L1 Hard Rules** (zero tolerance):
- [ ] No banned words or phrases
- [ ] No banned punctuation patterns
- [ ] No bullet-point opinion lists (max 3, otherwise散文)
- [ ] No bold subtitles unless true methodology piece
- [ ] All tools/products named specifically

**L2 Style Consistency**:
- [ ] Opening is concrete, not abstract
- [ ] Sentence lengths vary (no 3+ consecutive similar-length sentences)
- [ ] At least 3 one-sentence paragraphs for weight
- [ ] Every drifting paragraph has a "return to主线" sentence
- [ ] Questions used as rhythm brakes/turns

**L3 Human Check**:
- [ ] Read aloud — does it sound like a real person talking?
- [ ] Is there at least one moment of genuine emotion?
- [ ] Is there a specific detail that only someone who experienced it would know?
- [ ] Does the closing feel earned, not tacked on?

---

## Content Research Methodology

Before creating content, research the subject with structured depth. Adapted from Horizontal-Vertical Analysis (HV-Analysis).

### Vertical Analysis (Longitudinal)

Trace the subject from birth to present along the time axis. Cover:
- **Origin**: What need/technology/idea gave birth to it? Who were the founders? What was the industry context?
- **Birth node**: First release/launch. Initial form vs. today's form.
- **Evolution**: Major versions, pivots, team changes, milestones, controversies.
- **Decision logic**: At key nodes, why A over B? What constraints existed?
- **Stage划分**: Natural phases (embryonic → growth → maturity/transform), each with core特征 and矛盾.

Target: 6000–15000 characters for long-form research. For JSVOC topic briefs: 800–2000 characters.

### Horizontal Analysis (Cross-sectional)

At the current time slice, compare with competitors/alternatives:
- **Core differences**: Technology路线, product形态, target users, strengths/weaknesses, pricing.
- **User perspective**: Real口碑, most praised features, most complained pain points.
- **Ecosystem position**: What gap does it fill? Who is it competing head-to-head with?
- **Trend judgment**: Opportunities and risks based on the competitive landscape.

Handle three scenarios:
- **No direct competitors**: Analyze why, predict where competitors may emerge.
- **1–2 competitors**: Deep dive each.
- **3+ competitors**: Select 3–5 representative ones, others mentioned briefly.

### Intersection Insight

The精华 of the report. Combine vertical and horizontal to answer:
1. Which historical decisions shaped today's competitive position?
2. How do competitors' histories differ, causing today's divergence?
3. What is the historical root of each current advantage?
4. What is the historical root of each current weakness?
5. Future scenarios: most likely, most dangerous, most optimistic — each with logic.

Target: 1500–3000 characters for long-form. For JSVOC: 300–800 characters.

### Source Priority

| Information type | Preferred source |
|-----------------|------------------|
| Product updates | Official blog, GitHub Release Notes |
| Funding/data | Official announcements, SEC filings |
| User口碑 | GitHub Issues, Reddit, Twitter/X, 知乎 |
| Industry analysis | Original reporting from authoritative media (not reposts) |
| Academic/technical | arXiv, Google Scholar, conference proceedings |

**Rule**: Primary sources beat secondary. Multiple outlets repeating the same error creates a false confirmation loop.

---

## Output Format

### Single Prompt Enhancement
Return ONLY the enhanced prompt text. No explanations, no markdown code blocks. Single paragraph under 120 words.

### Full Content Generation Workflow
Return a structured report following Step 6: Completion Report format above.

### Text Content Output
Return the full text content. For scripts/captions: include timing marks if applicable. For articles: follow the Structure Template above. Always include a brief self-check note indicating which L1–L3 items were verified.

---

## Account Packaging Prompt Engineering (Real-Case Driven)

This section consolidates lessons from producing high-quality account packaging for real projects (e.g., "翡翠苹果" with benchmark "飙马野人"). The goal is to make prompt engineering reproducible: what worked for one case should work for others when adapted.

### Core Principle: Benchmark-First, Not Template-First

The account packaging style must be **100% driven by the benchmark account**, not by a preset template.

- If benchmark is a female-growth vlog → output should be "daytime scene + bedtime monologue" style.
- If benchmark is a pure sales account → output should be "fast-paced, deal-driven" style.
- If benchmark is educational → output should be "knowledge-first, structured" style.

**Hard rule**: Never hardcode style assumptions (e.g., "every account needs a dual persona" or "every account should tell bedtime stories"). Analyze the benchmark first, then migrate its style.

### The 60/30/10 Ratio

Content ratio must be explicit in every generation prompt:

| Portion | Source | Role |
|---------|--------|------|
| **60%** | Benchmark account style | The skeleton: format, rhythm, persona logic, column structure |
| **30%** | Industry/product context | Background material: the protagonist's daily work, products, customers |
| **10%** | Free-form creative | Books, TV shows, travel, sports, life observations — prevents templating |

**Enforcement trick**: In the prompt, add a self-check instruction: "After generating, verify that title/hook fields contain industry keywords in no more than 30% of items. If over, rewrite."

### persona_layers: The Real-Person Test

The `persona_layers` field must pass the **real-person test**:

```json
{
  "professional": "What they do for work",
  "personal": "What kind of person they are when not working",
  "daily_life": "Specific life scenes, NOT work scenes"
}
```

**Quality gate for `daily_life`**:
- Work-related scenes (看货, 打包, 接待客户) must be ≤ 30%.
- Life scenes must be specific and sensory: "摘下耳环问自己今天是不是太硬了", "睡前泡一杯热茶复盘一天", "陪孩子写作业", "雨天打伞去拿快递".
- If the daily_life list looks like a job description, it fails. Rewrite.

### content_columns: The Human-Name Test

Column names must sound like a **person's content**, not an **industry manual**.

| Fail (Industry-Heavy) | Pass (Human-First) |
|-----------------------|-------------------|
| 翡翠知识科普 | 女老板四会日记 |
| 手镯选购指南 | 今天又被手镯上了一课 |
| 行业避坑大全 | 我和客户的真实对话 |
| 源头货源揭秘 | 一个人做生意的情绪 |

**Quality gate**: Of 4 column names, direct industry keywords (翡翠/手镯/珠宝) may appear in **at most 1**. The other 3 must be emotion, diary, or life-oriented.

### tone_principles: The Actionable Test

Each tone principle must be **actionable** — a writer can follow it sentence by sentence.

| Fail (Vague Adjective) | Pass (Actionable Instruction) |
|------------------------|------------------------------|
| 像朋友聊天 | 先讲当天一个具体画面，再落到一个判断 |
| 真实自然 | 句子短，像夜里给自己发语音复盘 |
| 有温度 | 不急着证明专业，用取舍过程证明 |
| 接地气 | 敢说不适合，不把每个咨询都推成成交 |

**Quality gate**: Read each principle aloud. If it sounds like a brand slogan, it fails. If it sounds like a writing coach giving direct feedback, it passes.

### content_structure_template: Benchmark Structure Extraction

When the benchmark account has a recognizable content structure, extract it as a reusable template:

```json
{
  "主模板": "白天一幕 + 睡前独白 + 一个判断 + 一个提问",
  "开头": "用具体画面开场，不先自我介绍",
  "中段": "讲当时怎么想、怎么选、为什么没劝买",
  "结尾": "落到清醒观点，引导评论预算或困惑"
}
```

This template becomes the **single source of truth** for downstream topic and script generation. Topics and scripts must follow this structure, not invent their own.

### material_pool: The Specificity Test

Every item in the material pool must be **named specifically**. Vague references destroy credibility.

| Fail (Vague) | Pass (Specific) |
|--------------|-----------------|
| 最近看的一本书 | 《始于极限》 |
| 一部好看的剧 | 《俗女养成记》 |
| 一个风景好的地方 | 大理洱海 |
| 一种运动 | 普拉提 |

**Quality gate**: If an item cannot be purchased, watched, or visited by name, it fails.

### Self-Check Instruction for Account Packaging

Append this to every account packaging prompt. The LLM must verify its own output against these gates:

```
【生成后自检 — 必须全部通过】
1. daily_life 里工作场景占比 ≤ 30%？
2. content_columns 里行业关键词出现 ≤ 1 次？
3. tone_principles 每条都是可执行指令，不是形容词？
4. material_pool 每项都是具体书名/剧名/地名/运动名？
5. 整体风格贴合对标账号，没有硬套固定模板？
6. 如果有对标账号，content_structure_template 是否提取了对标的核心结构？
```

### Prompt Architecture for Account Packaging

A production-ready account packaging user prompt should contain these sections in order:

1. **Project data** (name, industry, product, founder profile, target customer, platforms)
2. **Benchmark injection** (benchmark account list + "analyze first, then migrate" rule)
3. **Quality benchmark** (few-shot examples of good vs. bad output for persona_layers, content_columns, tone_principles)
4. **Field definitions** (with per-field quality gates embedded)
5. **60/30/10 ratio rule**
6. **Core principles** (no fixed templates, benchmark-driven, industry as background)
7. **Self-check instruction**

---

## Content Quality Rubric

Evaluate generated content with a structured 7-dimension rubric. Score each dimension 0–5, then compute a composite 0–10.

### Dimensions

| Dimension | Code | Weight | What It Measures |
|-----------|------|--------|------------------|
| **Engagement Rate** | ER | 1.5 | Likelihood to provoke comments, saves, and reactions. Open loops, curiosity gaps, relatable friction. |
| **Share Rate** | SR | 1.5 | Willingness to forward. Identity signaling, social currency, "this represents me" factor. |
| **Hook Power** | HP | 1.5 | First 3 seconds / first line grab. Pattern interrupt, stakes, curiosity, or emotional jolt. |
| **Quality / Production** | QL | 1.0 | Visual polish, audio clarity, pacing, typography, color grade. Professional finish without overproduction. |
| **Narrative / Story** | NA | 1.0 | Structure: setup → tension → release. Cause-and-eﬀect chain. Meaningful transformation or insight. |
| **Authority / Believability** | AB | 1.0 | Credibility signals: specific details, real experience, data, honest limitations. Not generic advice. |
| **Satisfaction / Completion** | SAT | 1.0 | Does the ending deliver on the promise? Sense of closure, worth-the-time feeling, clear takeaway. |

### Scoring Guide (0–5 per dimension)

| Score | Meaning |
|-------|---------|
| 5 | Exceptional — top 5% of platform content in this dimension |
| 4 | Strong — above average, noticeable strength |
| 3 | Adequate — meets baseline, nothing wrong, nothing memorable |
| 2 | Weak — below average, hurts performance |
| 1 | Poor — significantly flawed |
| 0 | Missing — dimension is absent or actively counterproductive |

### Composite Formula

```
composite = (ER × 1.5 + SR × 1.5 + HP × 1.5 + QL + NA + AB + SAT) / 8.5 × 2.0
```

Round to one decimal. Result is 0–10.

**Interpretation:**

| Composite | Bucket | Action |
|-----------|--------|--------|
| 8.0–10.0 | S-tier | Publish immediately. Use as series anchor or benchmark. |
| 6.5–7.9 | A-tier | Publish with minor polish. |
| 5.0–6.4 | B-tier | Publish only if volume needed. Target specific weak dimensions for next iteration. |
| 3.0–4.9 | C-tier | Do not publish. Rebuild from outline. |
| 0–2.9 | D-tier | Discard. Re-analyze input and strategy. |

### Dimension-Specific Hints

- **ER**: Does the content create a "I need to say something" reaction? Controversy without toxicity works.
- **SR**: Would someone send this to a friend with "this is so you"? Identity alignment drives shares.
- **HP**: If the first line were a tweet, would it get clicks? Test the hook in isolation.
- **QL**: Is the lighting/camera/editing intentional, or just "good enough"? Intentionality shows.
- **NA**: Is there a before/after, a problem/solution, a question/answer? Pure information is not a story.
- **AB**: Are there timestamps, brand names, real locations, honest failures? Specificity builds trust.
- **SAT**: Does the viewer feel "glad I watched to the end"? Unearned endings destroy retention.

---

## Content Calibration Loop

Content quality improves through a closed feedback loop. Use this after every published batch or campaign.

### The Loop

```
Score → Predict → Publish → Retro → Evolve Rubric
  ↑_____________________________________________|
```

### Step 1: Score (Pre-Publish)

Apply the Content Quality Rubric above to every piece before it goes live. Record scores in a tracking sheet:

| Asset | ER | SR | HP | QL | NA | AB | SAT | Composite | Decision |
|-------|----|----|----|----|----|----|-----|-----------|----------|
| [id] | 4 | 3 | 5 | 4 | 3 | 4 | 3 | 6.8 | Publish |

### Step 2: Predict (Post-Publish Forecast)

Before seeing data, write a 1-sentence prediction per asset:

- "This will outperform because the hook targets a specific frustration."
- "This will underperform because the ending is too abrupt."

**Purpose**: Calibrate your intuition. Track prediction accuracy over time.

### Step 3: Publish & Collect Data

After publishing, record actual performance metrics at consistent intervals (e.g., 24h, 72h, 7d):

| Metric | What It Tells You |
|--------|-------------------|
| **Play-through rate** | Hook Power (HP) + Satisfaction (SAT) |
| **Engagement rate** | Engagement (ER) + Narrative (NA) |
| **Share rate** | Share (SR) + Authority (AB) |
| **Save rate** | Share (SR) + Quality (QL) |
| **Follower conversion** | Composite + consistent brand voice |

### Step 4: Retro (Post-Mortem)

For every batch, ask:

1. **Which prediction was most wrong?** Why did the data diverge from expectation?
2. **Which dimension most correlated with top performer?** With bottom performer?
3. **What pattern do high-composite pieces share?** What do low-composite pieces share?
4. **Did any C-tier piece outperform a B-tier?** If so, which dimension was mis-scored?

Record findings in `content-retro.md`:

```markdown
# Content Retro — [Date Range]

## Top Performer
- Asset: [id]
- Composite: [score]
- Prediction: [forecast]
- Actual: [metrics]
- Key insight: [what we learned]

## Biggest Miss
- Asset: [id]
- Why mis-scored: [reason]
- Lesson: [adjustment for next batch]

## Rubric Adjustment
- [Dimension]: [what to weight differently or watch for]
```

### Step 5: Evolve Rubric

Update the rubric based on retro findings:

- **Adjust weights**: If SR consistently predicts top performers better than ER, increase SR weight slightly.
- **Add sub-criteria**: If "specific detail" keeps appearing as the real driver of AB, add a sub-check for "named at least one real brand/person/location."
- **Retire blind spots**: If a certain content type consistently scores high but performs low, add a "platform fit" penalty dimension.

**Rule**: The rubric is a living document. Evolve it slowly — one change per retro cycle, not five.

### Calibration Checkpoints

| Checkpoint | Frequency | Action |
|------------|-----------|--------|
| **Pre-publish scoring** | Every asset | Apply rubric, record composite |
| **Prediction log** | Every asset | 1-sentence forecast before data |
| **Batch retro** | Every 5–10 assets | Pattern analysis, rubric review |
| **Rubric version bump** | Monthly or per major insight | Document changes, reset baselines |

**Goal**: Over 3–6 months, your pre-publish composite scores should increasingly predict actual performance rank. If they don't, the rubric is not capturing what matters — evolve it.
