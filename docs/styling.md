# Styling & UI

> **Draft:** this design isn't decided yet and will be revised. The brand palette (blues, purple, lavender, navy) is chosen; treat the fonts and screen layouts below as placeholders. The stack and the accessibility rules can be relied on.

## Stack
- **Tailwind CSS v4** for all styling. No CSS modules and no styled-components.
- **shadcn/ui** for primitives (Button, Card, Progress, Tabs, Select, Dialog, Toast/Sonner). They live in `src/components/ui/`. Edit them there; don't wrap them in more layers.
- **lucide-react** for icons.
- **next/font** for fonts. Never load fonts with a `<link>` tag.

## Design direction
A calm, focused tool. The score is the hero, so the surrounding UI stays quiet: neutral surfaces, one blue accent for actions, plenty of white space. Purple and lavender are supporting colors, used sparingly. It should feel like a music app, but not a toy.

## Color tokens
Colors are defined once as CSS variables in `src/app/globals.css` and exposed to Tailwind through `@theme`. **Components use token classes only** (`bg-surface`, `text-muted`), never raw hex values or Tailwind palette colors like `bg-gray-100`.

| Token | Light | Dark | Use |
|---|---|---|---|
| `--background` | `#FAFAF7` | `#0F1115` | Page background |
| `--surface` | `#FFFFFF` | `#202740` | Cards, panels |
| `--surface-muted` | `#F2F1EC` | `#1F232C` | Inputs, subtle fills |
| `--border` | `#E4E2DA` | `#2A2F3A` | Dividers, outlines |
| `--foreground` | `#202740` | `#ECEDEE` | Primary text |
| `--muted` | `#6B6B66` | `#9BA1AC` | Secondary text |
| `--accent` | `#3956AF` | `#527CDD` | Primary actions, focus, progress |
| `--accent-foreground` | `#FFFFFF` | `#0F1115` | Text on accent |
| `--accent-subtle` | `#E1CDE2` | `#3956AF` | Selected / drag-over fills. Put `foreground` text on it, not `accent` |
| `--highlight` | `#B669D5` | `#B669D5` | Playback cursor, decorative marks. Not for text (fails 4.5:1) |
| `--success` | `#15803D` | `#4ADE80` | Job done |
| `--danger` | `#B91C1C` | `#F87171` | Errors, failed jobs |
| `--recording` | `#DC2626` | `#EF4444` | Record button / live indicator |

**The score canvas is always light** (`#FFFFFF` paper, black notes), even in dark mode, because sheet music reads like paper. In dark mode, put the paper on the dark background with a subtle shadow.

Dark mode follows `prefers-color-scheme` by default and can be overridden with a toggle (`next-themes`, `class` strategy; `ThemeToggle` in the root layout).

shadcn's color names (`primary`, `card`, `destructive`, `ring`, …) are aliased to these tokens in `@theme`. Two of its names clash with ours: shadcn uses `bg-muted` and `bg-accent` for subtle fills, but here `muted` is text and `accent` is the action color. When adding a shadcn component, replace those fills with `bg-surface-muted`.

## Typography
- **UI:** Inter (via `next/font/google`), set as `--font-sans`.
- **Numbers** such as tempo, duration, and progress use `tabular-nums`.
- Type scale (Tailwind defaults): page title `text-3xl font-semibold tracking-tight` · section title `text-xl font-semibold` · body `text-base` · meta `text-sm text-muted`.

## Layout
- Content max width `max-w-5xl` on the landing page. The score page can use `max-w-7xl` so the score has room.
- Page padding: `px-4 sm:px-6 lg:px-8`. Vertical rhythm: `space-y-6` within sections, `py-12` between them.
- Radius: `rounded-xl` for cards, `rounded-lg` for inputs and buttons.
- Mobile first. Everything must work at 360 px wide, and the score viewer scrolls vertically, never horizontally.

## Key screens

### Landing (`/`)
- Headline plus a one-line explanation.
- A large drop zone (dashed `border-border`, `bg-surface-muted` on hover/drag) that accepts drag and drop or a click to browse.
- An "or record" button with a red dot. While recording, show a live waveform/level meter and a timer.
- Options row: Instrument (Select), Mode (Solo / Full song — disabled until phase 3).
- A primary "Transcribe" button.

### Job page (`/jobs/[id]`)
- **Running:** a stage list (Normalizing → Transcribing → Notating → Rendering) showing the current stage, plus a `Progress` bar. Show an estimate rather than a spinner alone.
- **Done:** a header with the title and a meta row (key · tempo · time signature · duration), a toolbar (Play/Pause, Zoom −/+, Download ▾ MusicXML / MIDI / PDF), and the score paper below.
- **Failed:** a danger-tinted card with the error message, a likely cause (e.g. "Try a recording of a single instrument"), and a "Try again" button.

## Components (planned)
- `UploadDropzone`, `Recorder`, `InstrumentSelect`
- `JobProgress` (stage list + bar)
- `ScoreViewer` (OSMD wrapper, client only), `ScoreToolbar`
- `DownloadMenu`
- `ErrorState`, `EmptyState`

## Motion
- Keep it subtle: `transition-colors` and `duration-150` on interactive elements.
- Pulse the recording indicator. Animate the progress bar width.
- Respect `prefers-reduced-motion` (`motion-safe:` / `motion-reduce:` variants).

## Accessibility
- Every interactive element is reachable by keyboard and has a visible focus ring (`focus-visible:ring-2 ring-accent ring-offset-2`).
- Text contrast is at least 4.5:1 against its background. Check new token pairs in both themes.
- Icon-only buttons need an `aria-label`.
- Announce job progress and state changes through an `aria-live="polite"` region.
- The drop zone must also work as a normal file input.
