# Mobile Overhaul Plan

## Phase 1 — Foundation (low risk, enables later work)

**1.1 Add a `useIsMobile` hook**
New `frontend/src/hooks/useIsMobile.js` wrapping `window.matchMedia("(max-width: 640px)")` with a resize listener. Used by charts to pick margins/heights/widths conditionally.

**1.2 Verify viewport meta**
Confirm `<meta name="viewport" content="width=device-width, initial-scale=1">` exists in `frontend/index.html`. Add if missing.

## Phase 2 — Navigation (`Navbar.jsx`)

**2.1 Replace horizontal-scroll pill nav with a hamburger sheet at `< sm`**
- Desktop (`sm:` and up): current inline links.
- Mobile: show a hamburger button; tapping opens a slide-down panel below the top bar with the 5 links stacked full-width.
- Close on link click and on outside click (reuse the existing `dropdownRef` pattern).

**2.2 Condense brand + avatar row**
Ensure the 3 regions (brand / nav / avatar) fit in 48px height on a 320px device. Brand stays left, avatar stays right, hamburger sits next to avatar.

## Phase 3 — Charts (highest user-visible impact)

**3.1 `BoxPlotChart.jsx`**
- Wrap the chart in `<div className="overflow-x-auto -mx-4 px-4">` in `SalaryInsights.jsx` so the existing `minWidth: 600` becomes a swipeable surface instead of viewport overflow.
- On mobile, reduce `YAxis width` from `140` → `90`, `fontSize` `13` → `11`, and `margin.left` `20` → `8`.
- Add a thin "swipe →" hint the first time the chart is wider than its container.

**3.2 `Dashboard.jsx` Top Skills chart (line 78-94)**
- Mobile: reduce `margin.left` `80` → `10`, `YAxis width` `75` → `70`, and increase chart height to `500` to let long skill names breathe (vertical layout already works).
- Desktop: unchanged.

**3.3 `Dashboard.jsx` Pie chart (line 105-115)**
- On mobile, drop the external labels (`label={…}`) and rely on the `<Legend>` that's already there.
- Reduce `outerRadius` from `100` → `70`.

**3.4 `Dashboard.jsx` Salary by Language chart**
- Already serviceable; reduce left/right margins to `4` on mobile.

**3.5 `SkillExplorer.jsx` (lines 106, 171)**
- Same treatment as 3.2: shrink `margin.left` and `YAxis width` on mobile.

**3.6 Replace fixed chart heights with Tailwind responsive wrappers**
Pattern: wrap each chart in `<div className="h-64 sm:h-80 lg:h-96">` and set `<ResponsiveContainer width="100%" height="100%">`. Applies to every page that uses Recharts.

## Phase 4 — Tables (`SalaryInsights.jsx:135-166`)

**4.1 Dual layout for the salary table**
- Desktop (`hidden sm:block`): keep current 8-column table, but wrap in `overflow-x-auto` as a safety net.
- Mobile (`sm:hidden`): render each row as a card — name as heading, a 2-column mini-grid for Min/Max/Mean/Std Dev/Jobs. No horizontal scroll.

## Phase 5 — Forms & modals

**5.1 `JobBoard.jsx` filter footer (lines 106-126)**
Stack "Remote only" checkbox and sort `<select>` vertically at `< sm`. Make the select full-width on mobile.

**5.2 `TailorModal.jsx` and `ResumeForm.jsx`**
Audit for:
- `max-h-[90vh] overflow-y-auto` on the modal container so content scrolls.
- `w-full sm:max-w-2xl` so the modal fills the viewport on mobile.
- Button rows stack vertically (`flex-col sm:flex-row`) and use `w-full sm:w-auto` to avoid cramped tap targets.

**5.3 Touch targets**
Audit buttons for ≥44px height. Current `py-1.5 text-xs` buttons (~28px) are too small for primary actions on mobile — bump the "Tailor Resume" / "Apply" / "Search" buttons to `py-2.5` at `< sm`.

## Phase 6 — Chart interactivity

**6.1 Touch-friendly tooltips**
Recharts hover tooltips are flaky on touch. Options (pick one):
- Add `trigger="click"` on `<Tooltip>` on mobile.
- Render a collapsible "Details" list under each chart showing the same data.

Lean toward option B for the Dashboard + SkillExplorer bar charts since the data is already in `skillChartData` / `locationChartData`.

## Phase 7 — QA

- Test in Chrome DevTools device emulation at 320px / 375px / 414px widths.
- Test on a real phone for each page: Dashboard, JobBoard, SkillExplorer, SalaryInsights, ResumeAnalyzer, Account, Tailoring.
- Verify `npm run build` and `npm run lint` both pass.

## Rough order of execution

1. Phase 1 (foundation) — 30 min.
2. Phase 3 (charts) — biggest win, ~2 hrs.
3. Phase 4 (salary table) — ~45 min.
4. Phase 2 (navbar) — ~1 hr.
5. Phase 5 (forms/modals) — ~1 hr.
6. Phase 6 (interactivity) — ~45 min.
7. Phase 7 (QA) — ~30 min.
