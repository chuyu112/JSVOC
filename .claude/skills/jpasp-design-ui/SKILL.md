---
name: jpasp-design-ui
description: JPASP project design system and UI/UX guidelines. Consolidates muted postal neo-minimalism, dark glass jade theme, glassmorphism patterns, content-generation-platform UX, and web frontend best practices. Use for all frontend pages, components, styling decisions, and UI reviews in the JPASP codebase.
---

# JPASP Design UI

Design intelligence for the JPASP content generation platform. Covers the project's specific design language, component patterns, UX guidelines, and visual decision frameworks.

## When to Use

Use this skill whenever the task involves:
- Building or refactoring pages/components in `frontend-v2/`
- Choosing colors, spacing, typography, or layout for new features
- Reviewing UI code for visual consistency or UX quality
- Making design decisions about cards, forms, navigation, or content display
- Animating UI elements or page transitions

## JPASP Design Language

The project follows a unified design language. All new work must align with these dimensions.

| Dimension | Rule |
|-----------|------|
| **Color** | Muted and postal, monochromatic. Low-saturation tones: gray-blue, gray-green, warm gray as base. No high-saturation accent colors. |
| **Layout** | Card based design with layered elements. Information organized in cards with clear hierarchy and stacking relationships. |
| **Style** | Neo-minimalism. Restrained elements, generous whitespace, thin borders, no superfluous decoration. |
| **Philosophy** | Approachable sophistication. Visually refined but not distant; professional but not cold. |

### Application Guidelines

- **Background**: Deep dark base (current: `#0a0a0a` / black). Layered surfaces use `rgba(255,255,255,0.02–0.08)`.
- **Cards**: Semi-transparent glass (`glass` class) or solid layered surfaces. Shadows are subtle and unified: `0 4px 24px rgba(0,0,0,0.3)` max.
- **Borders**: Thin, low-opacity dividers: `rgba(255,255,255,0.06–0.10)`. Never use high-contrast borders.
- **Interactive elements**: Minimal buttons/inputs. Hover feedback via opacity shift (`hover:bg-white/[0.04–0.08]`) or subtle scale. No glowing outlines or bright highlights.
- **Typography hierarchy**: Large titles bold (`font-bold`, `text-[28px]`), body regular (`text-[13–14px]`), auxiliary info muted (`text-[#9ca3af]`, `text-[12px]`).
- **Animation**: 150–300ms micro-interactions, `ease-out` or `[0.16, 1, 0.3, 1]` (custom expo-out). Never decorative-only.

---

## Design Thinking

Before coding any interface, answer these four questions:

1. **Purpose**: What problem does this interface solve? Who uses it? (content creators, brand managers, operators)
2. **Tone**: What is the emotional temperature? JPASP defaults to **calm authority** — confident but not aggressive, clean but not sterile.
3. **Constraints**: Technical requirements (Next.js 16, Tailwind 4, React 19, dark mode only, Chinese + English bilingual support).
4. **Differentiation**: What makes this page unforgettable? Pick **one** distinctive element: an unusual layout rhythm, a memorable animation moment, or an unexpected spatial composition.

**Critical**: Choose a clear direction and execute with precision. Do not converge on generic AI aesthetics (overused Inter font, purple gradients, predictable card grids).

---

## Priority Rule Categories

Follow priority 1 → 6. Do not skip lower priorities to chase visual polish.

| Priority | Category | Impact | Key Checks |
|----------|----------|--------|------------|
| 1 | **Accessibility** | CRITICAL | Contrast 4.5:1 for text, visible focus rings, keyboard nav, aria-labels on icon buttons |
| 2 | **Layout & Responsive** | HIGH | Mobile-first breakpoints (375/768/1024/1440), no horizontal scroll, viewport meta correct |
| 3 | **Style Consistency** | HIGH | Same aesthetic across all pages, glassmorphism effects aligned, semantic color tokens |
| 4 | **Typography & Color** | MEDIUM | Base 16px, line-height 1.5, font scale consistent, no raw hex in components |
| 5 | **Animation & Motion** | MEDIUM | 150–300ms micro-interactions, transform/opacity only, prefers-reduced-motion respected |
| 6 | **Forms & Feedback** | MEDIUM | Visible labels, error near field, empty states with action, loading skeletons |

### 1. Accessibility (CRITICAL)

- `color-contrast`: Minimum 4.5:1 for normal text on dark backgrounds. Test with tools; do not eyeball it.
- `focus-states`: Visible focus rings on all interactive elements. In dark mode, use `ring-2 ring-white/30` or similar.
- `aria-labels`: Icon-only buttons must have `aria-label`.
- `keyboard-nav`: Tab order matches visual order. Modals trap focus.
- `heading-hierarchy`: Sequential h1→h6, no skips.
- `reduced-motion`: Respect `prefers-reduced-motion`; disable/reduce animations when requested.

### 2. Layout & Responsive (HIGH)

- `mobile-first`: Design for 375px first, then scale up.
- `breakpoint-consistency`: Use systematic breakpoints: 375 / 768 / 1024 / 1440.
- `spacing-scale`: Use 4pt incremental spacing. JPASP common values: `gap-4` (16px), `gap-5` (20px), `gap-6` (24px), `p-5 md:p-6` for card padding.
- `container-width`: Consistent max-width on desktop. Use `max-w-7xl` or `max-w-[1440px]` for dashboards.
- `line-length`: Desktop 60–75 chars per line; mobile 35–60.
- `z-index-management`: Define layered scale: 0 / 10 / 20 / 40 / 100 / 1000. Do not invent random values.
- `fixed-element-offset`: Fixed navbar must reserve padding for underlying content (`pt-16` etc.).

### 3. Style Consistency (HIGH)

- `effects-match-style`: Glassmorphism cards use `backdrop-blur-xl`, `bg-white/[0.02–0.05]`, `border-white/[0.06–0.10]`. Do not mix glass with solid flat cards randomly.
- `dark-mode-pairing`: JPASP is dark-mode only. Design all surfaces for dark backgrounds. Light text on dark: primary `#f5f5f5`, secondary `#d0ddd6`, muted `#9ca3af`, subtle `#7a8a82`.
- `elevation-consistent`: Cards sit on subtle shadow. Sheets/modals sit higher. Use a consistent scale:
  - Card: `shadow-[0_2px_12px_rgba(0,0,0,0.2)]`
  - Sheet: `shadow-[0_8px_32px_rgba(0,0,0,0.4)]`
  - Modal: `shadow-[0_16px_48px_rgba(0,0,0,0.5)]`
- `icon-style-consistent`: Use one icon set (Lucide) with consistent stroke width (1.5px–2px).
- `no-emoji-icons`: SVG icons only. Never use emojis as UI elements.
- `blur-purpose`: Use backdrop blur for modals, sheets, and glass cards. Do not use blur as pure decoration.

### 4. Typography & Color (MEDIUM)

- `font-scale`: Consistent type scale:
  - Eyebrow: `text-[11px] uppercase tracking-wider text-[#9ca3af]`
  - Label: `text-[12px] text-[#9ca3af]`
  - Body: `text-[13–14px] text-[#d0ddd6] leading-relaxed`
  - Heading: `text-[15px] font-bold text-[#f5f5f5]`
  - Page title: `text-[28px] md:text-[36px] font-bold tracking-[-0.02em] text-[#f5f5f5]`
- `line-height`: Body 1.5–1.75. Headings 1.15–1.3.
- `color-semantic`: Define semantic tokens in CSS/Tailwind:
  - `text-primary`: `#f5f5f5`
  - `text-secondary`: `#d0ddd6`
  - `text-muted`: `#9ca3af`
  - `text-subtle`: `#7a8a82`
  - `border-subtle`: `rgba(255,255,255,0.06–0.10)`
  - `surface-glass`: `rgba(255,255,255,0.02–0.05)`
- `whitespace-balance`: Use whitespace intentionally to group related items and separate sections.

### 5. Animation & Motion (MEDIUM)

- `duration-timing`: 150–300ms for micro-interactions; page transitions ≤400ms.
- `easing`: Use `ease-out` for entering elements. JPASP custom expo-out: `[0.16, 1, 0.3, 1]` (Framer Motion).
- `transform-performance`: Animate `transform` and `opacity` only. Never animate `width`, `height`, `top`, `left`.
- `stagger-sequence`: Stagger list item entrance by 50–100ms per item. Avoid all-at-once.
- `exit-faster-than-enter`: Exit animations ~60–70% of enter duration.
- `scale-feedback`: Subtle scale `0.98` on press for tappable cards/buttons.
- `modal-motion`: Modals animate from trigger source (scale+fade) for spatial context.
- `motion-consistency`: Unify duration/easing tokens globally.

### 6. Forms & Feedback (MEDIUM)

- `input-labels`: Visible label per input. Never placeholder-only.
- `error-placement`: Show error below the related field, not just at top.
- `empty-states`: Helpful message + action button when no content exists. Never blank screens.
- `loading-states`: Skeleton screens / shimmer for >300ms loading. Not spinners for lists.
- `disabled-states`: Reduced opacity (0.4) + `disabled` attribute + cursor change.
- `submit-feedback`: Loading state on button during async submit, then success/error.
- `toast-dismiss`: Auto-dismiss toasts in 3–5s. Use `aria-live="polite"`.

---

## Visual System: Style × Layout × Effects

Build any page systematically across three dimensions. This framework is adapted from baoyu-skills' dimensional design system for JPASP's web context.

### Dimension 1: Style (Visual Aesthetic)

| Style | Keywords | Best For | JPASP Context |
|-------|----------|----------|---------------|
| **Glass Jade** | `glass`, `backdrop-blur`, `rgba(255,255,255,0.02–0.05)`, `border-white/[0.06]` | Default cards, modals, sidebars | Project default aesthetic |
| **Solid Layered** | `bg-[#111111]`, `bg-[#1a1a1a]`, subtle border | Dense data, tables, settings | When glass causes readability issues |
| **Minimal Dark** | pure black bg, ultra-thin borders, generous whitespace | Landing pages, hero sections, focus pages | High-impact moments |
| **Muted Postal** | gray-blue, gray-green, warm gray tones | Content-heavy pages, reading experiences | Aligns with brand philosophy |
| **Editorial** | asymmetric layouts, large typography, dramatic spacing | Showcase pages, brand stories | Break from grid when appropriate |

### Dimension 2: Layout Pattern

| Pattern | Structure | Best For |
|---------|-----------|----------|
| **Dashboard Grid** | `grid-cols-1 lg:grid-cols-[260px_1fr_380px]` or similar | Video generation page, project detail |
| **Card List** | Single column stack of glass cards with `gap-5` | History, lists, feeds |
| **Split Pane** | `grid-cols-1 lg:grid-cols-[1fr_280px]` left content + right sidebar | Project detail, settings |
| **Hero + Grid** | Full-width hero section + card grid below | Landing, project list |
| **Dense Modules** | Tight grid `grid-cols-2 md:grid-cols-3 lg:grid-cols-4` | Asset gallery, thumbnails |
| **Centered Focus** | Single centered column `max-w-2xl mx-auto` | Forms, auth, empty states |
| **Asymmetric Editorial** | Overlapping elements, broken grid, diagonal flow | Marketing pages, special features |

### Dimension 3: Surface Effects

| Effect | CSS Recipe | Use Case |
|--------|-----------|----------|
| **Glass Card** | `glass rounded-[1rem] p-5 md:p-6` | Default card container |
| **Glass Sidebar** | `glass rounded-[1rem] p-5` | Navigation panels, filters |
| **Elevated Sheet** | `bg-[#111] rounded-[1.25rem] border border-white/[0.08] shadow-[0_8px_32px_rgba(0,0,0,0.4)]` | Modals, bottom sheets |
| **Subtle Surface** | `bg-white/[0.02] rounded-md border border-white/[0.06]` | Tags, badges, inline elements |
| **Input Glass** | `input-glass` (project custom class) | Form inputs, textareas |
| **Button Secondary** | `btn btn-secondary` (project custom class) | Secondary actions |
| **Tag Success** | `tag tag-success` (project custom class) | Status indicators |

---

## Preset Page Combinations

Quick-start combos for common JPASP pages. Use as starting points, then customize.

| Page Type | Style | Layout | Effects | Notes |
|-----------|-------|--------|---------|-------|
| **Project List** | Glass Jade | Hero + Grid | Glass cards, stagger entrance | Eyebrow + title header, grid of project cards |
| **Project Detail** | Glass Jade | Split Pane | Left: stacked glass cards; Right: workflow sidebar | Editable info card + account package preview |
| **Video Generation** | Glass Jade | Dashboard Grid | Left: material sidebar; Center: prompt input; Right: params | 3-column: `260px 1fr 380px` |
| **Topic/Script** | Muted Postal | Card List | Glass cards with action rows | Content cards with generation entry points |
| **History/Assets** | Solid Layered | Dense Modules | Thumbnail grid with metadata overlay | Waterfall or uniform grid |
| **Account Package** | Glass Jade | Card Grid (2-col) | Glass cards per section | Group related fields into cards |
| **Settings** | Solid Layered | Centered Focus | Clean form layout | Minimal decoration, functional |
| **Auth/Login** | Minimal Dark | Centered Focus | Single centered glass panel | Maximum focus, no distractions |

---

## Auto-Selection for JPASP Pages

Match page purpose to the recommended combination. First match wins.

| Page Signals | Recommended Style | Layout | Preset |
|--------------|-------------------|--------|--------|
| 列表, list, projects, assets | Glass Jade | Card List or Dense Modules | Project List / History |
| 详情, detail, 项目主页 | Glass Jade | Split Pane | Project Detail |
| 生成, generation, create, video, image | Glass Jade | Dashboard Grid | Video Generation |
| 选题, topic, script, 文案 | Muted Postal | Card List | Topic/Script |
| 账号包装, account package, strategy | Glass Jade | Card Grid (2-col) | Account Package |
| 设置, settings, config, profile | Solid Layered | Centered Focus | Settings |
| 登录, login, auth, register | Minimal Dark | Centered Focus | Auth |
| 营销, landing, marketing, showcase | Editorial | Hero + Grid or Asymmetric | Landing |

---

## Component Patterns

### Card Header Pattern
Every content card should follow this structure:
```
[Card Container]
  ├── [Header Row: flex justify-between items-center mb-5]
  │     ├── [Title: text-[15px] font-bold text-[#f5f5f5]]
  │     └── [Meta/Action: text-[11–12px] text-[#9ca3af] or button]
  └── [Content Body]
```

### Section Header Pattern
Every page section should follow this structure:
```
[motion.div className="section-header"]
  ├── [div]
  │     ├── [p className="eyebrow"]Section Label[/p]
  │     └── [h1 className="text-[28px] md:text-[36px] font-bold ..."]Title[/h1]
  └── [Action Buttons]
```

### Empty State Pattern
Never show blank space. Always provide:
```
[Glass Card with text-center py-10]
  ├── [Icon or Illustration (optional, subtle)]
  ├── [p: text-[#7a8a82] text-sm mb-4] "暂无数据"
  └── [button: generate/create action]
```

### Loading State Pattern
For cards/lists:
```
[animate-pulse space-y-3]
  ├── [div: h-4 bg-white/[0.04] rounded w-2/3]
  └── [div: h-4 bg-white/[0.04] rounded w-full]
```
For full pages: skeleton screens that match the layout structure.

### Form Field Pattern
```
[div className="flex flex-col gap-1.5"]
  ├── [label: text-[12px] text-[#9ca3af]]
  └── [input/textarea: input-glass]
```

---

## Animation Patterns

### Page Entrance
```tsx
<motion.div
  initial={{ opacity: 0, y: 24 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
>
```

### Card Stagger
```tsx
<motion.div
  initial={{ opacity: 0, y: 20 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
>
```
Increment `delay` by 0.05–0.1s per card.

### Hover Feedback
```
className="transition-all hover:bg-white/[0.04] hover:border-white/[0.12]"
```

### Press Feedback
```
className="active:scale-[0.98] transition-transform"
```

### Modal Entrance
```tsx
<motion.div
  initial={{ opacity: 0, scale: 0.96 }}
  animate={{ opacity: 1, scale: 1 }}
  transition={{ duration: 0.2, ease: "easeOut" }}
>
```

---

## Content Display Guidelines

JPASP is a content generation platform. Displaying generated content (videos, images, text, strategies) has specific patterns:

### Displaying Generated Media (Video/Image)
- Use consistent aspect ratio containers with `aspect-ratio` to prevent layout shift
- Show resolution, creation time, and action buttons (download, delete, regenerate) as overlay or below
- Beijing time (zh-CN locale) for timestamps
- Waterfall layout for browsing: `columns-2 md:columns-3 lg:columns-4` with `gap-4`
- Provide empty state with regeneration action when no media exists

### Displaying Generated Text (Strategy, Package, Script)
- Break long text into scannable sections with clear subheadings
- Use `text-[14px] text-[#d0ddd6] leading-relaxed` for body
- Use tags/chips for list items (account names, trust points, platforms)
- Provide copy-to-clipboard action for generated prompts/scripts
- Show generation metadata (model, time, version) in footer

### Displaying Generation History
- Chronological list with generation module icon + name
- Collapsible detail view for input/output data
- Filter by module name and date range
- Status indicator (success / failed / pending) with color coding

---

## Pre-Output Checklist

Before delivering any UI code, verify:

### Visual Quality
- [ ] No emojis used as icons (SVG/Lucide only)
- [ ] Colors use semantic tokens or project-specific values, not raw hex exceptions
- [ ] Glassmorphism effects are consistent (same blur, same border opacity family)
- [ ] Hover/pressed states do not shift layout bounds
- [ ] Text hierarchy is clear: eyebrow → heading → body → auxiliary

### Interaction
- [ ] All tappable elements have hover feedback
- [ ] Async buttons show loading state (`disabled` + spinner or text change)
- [ ] Micro-interactions stay in 150–300ms range
- [ ] Empty states provide helpful message + action
- [ ] Errors show near the cause, not just console or top banner

### Responsive
- [ ] Mobile-first: works at 375px without horizontal scroll
- [ ] Breakpoints smooth at 768px and 1024px
- [ ] Touch targets ≥44px on mobile
- [ ] No content hidden behind fixed navbars

### Accessibility
- [ ] Focus rings visible on all interactive elements
- [ ] Color contrast ≥4.5:1 for body text
- [ ] Icon-only buttons have `aria-label`
- [ ] `prefers-reduced-motion` respected for animations

### JPASP Specific
- [ ] Design language aligns with muted postal / neo-minimalism / dark glass jade
- [ ] Card-based layout with layered elements
- [ ] No high-saturation accent colors introduced
- [ ] Animations are subtle and purposeful, not decorative
- [ ] Chinese text renders correctly with appropriate line-height
