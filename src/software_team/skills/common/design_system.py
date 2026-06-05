"""Design-system intelligence for the UI/UX Designer.

This is a dependency-free re-implementation of the "UI UX Pro Max" design-system
reasoning engine, adapted to this project's deterministic, offline-first orchestration.
Given a short product description it BM25-searches a vendored knowledge base of product
types, styles, colour palettes, font pairings, landing patterns and UX guidelines
(``uiux_data/``), applies per-product reasoning rules, and synthesises a complete design
system — pattern, visual style, semantic colour tokens, typography, key effects and the
anti-patterns to avoid — rendered as markdown the UX node folds into its prompt and
persists as a document.

It is exposed both as plain functions (used by the deterministic UX node) and as LangChain
``@tool``s (so a tool-capable model can call them in a ReAct loop), mirroring the other
skills in ``common/``.

Source: the reasoning model and the ``uiux_data/`` CSV knowledge base are adapted from
``nextlevelbuilder/ui-ux-pro-max-skill`` (MIT licence, © 2024 Next Level Builder);
https://github.com/nextlevelbuilder/ui-ux-pro-max-skill. See ``uiux_data/ATTRIBUTION.md``.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from math import log
from pathlib import Path

from langchain_core.tools import tool

DATA_DIR = Path(__file__).resolve().parent / "uiux_data"
MAX_RESULTS = 3

# Each searchable domain maps to a vendored CSV plus the columns to match against
# (``search``) and the columns to return (``output``). Keeping this declarative makes the
# knowledge base easy to extend: drop a CSV in ``uiux_data/`` and add an entry here.
CSV_CONFIG: dict[str, dict[str, object]] = {
    "product": {
        "file": "products.csv",
        "search": [
            "Product Type",
            "Keywords",
            "Primary Style Recommendation",
            "Key Considerations",
        ],
        "output": [
            "Product Type",
            "Keywords",
            "Primary Style Recommendation",
            "Secondary Styles",
            "Landing Page Pattern",
            "Color Palette Focus",
        ],
    },
    "style": {
        "file": "styles.csv",
        "search": ["Style Category", "Keywords", "Best For", "Type", "AI Prompt Keywords"],
        "output": [
            "Style Category",
            "Type",
            "Keywords",
            "Primary Colors",
            "Effects & Animation",
            "Best For",
            "Light Mode ✓",
            "Dark Mode ✓",
            "Performance",
            "Accessibility",
            "Complexity",
        ],
    },
    "color": {
        "file": "colors.csv",
        "search": ["Product Type", "Notes"],
        "output": [
            "Product Type",
            "Primary",
            "On Primary",
            "Secondary",
            "Accent",
            "On Accent",
            "Background",
            "Foreground",
            "Muted",
            "Border",
            "Destructive",
            "Ring",
            "Notes",
        ],
    },
    "typography": {
        "file": "typography.csv",
        "search": ["Font Pairing Name", "Category", "Mood/Style Keywords", "Best For"],
        "output": [
            "Font Pairing Name",
            "Heading Font",
            "Body Font",
            "Mood/Style Keywords",
            "Best For",
            "Google Fonts URL",
            "CSS Import",
        ],
    },
    "landing": {
        "file": "landing.csv",
        "search": ["Pattern Name", "Keywords", "Conversion Optimization", "Section Order"],
        "output": [
            "Pattern Name",
            "Section Order",
            "Primary CTA Placement",
            "Color Strategy",
            "Conversion Optimization",
        ],
    },
    "chart": {
        "file": "charts.csv",
        "search": ["Data Type", "Keywords", "Best Chart Type", "When to Use"],
        "output": [
            "Data Type",
            "Best Chart Type",
            "Secondary Options",
            "When to Use",
            "When NOT to Use",
            "Color Guidance",
            "Accessibility Notes",
            "Library Recommendation",
        ],
    },
    "ux": {
        "file": "ux-guidelines.csv",
        "search": ["Category", "Issue", "Description", "Platform"],
        "output": ["Category", "Issue", "Platform", "Description", "Do", "Don't", "Severity"],
    },
}

# Keyword hints that bias ``detect_domain`` when the caller does not name a domain.
_DOMAIN_HINTS: dict[str, tuple[str, ...]] = {
    "color": ("color", "colour", "palette", "hex", "token", "accent", "contrast"),
    "chart": ("chart", "graph", "visualization", "trend", "bar", "pie", "dashboard data"),
    "landing": ("landing", "cta", "conversion", "hero", "testimonial", "pricing", "section"),
    "typography": ("font", "typeface", "typography", "serif", "heading font", "body font"),
    "ux": ("ux", "usability", "accessibility", "wcag", "touch", "animation", "navigation"),
    "product": ("saas", "ecommerce", "fintech", "healthcare", "portfolio", "dashboard", "app"),
    "style": ("style", "glassmorphism", "minimalism", "brutalism", "dark mode", "flat"),
}


class BM25:
    """Okapi BM25 ranking over a small in-memory corpus.

    A compact, dependency-free implementation used to rank knowledge-base rows against a
    free-text query. Defaults (``k1=1.5``, ``b=0.75``) are the conventional values.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """Initialise an empty index with the given BM25 parameters."""
        self.k1 = k1
        self.b = b
        self.corpus: list[list[str]] = []
        self.doc_lengths: list[int] = []
        self.avgdl = 0.0
        self.idf: dict[str, float] = {}
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.n = 0

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Lowercase ``text``, strip punctuation, and drop tokens of two chars or fewer."""
        text = re.sub(r"[^\w\s]", " ", str(text).lower())
        return [word for word in text.split() if len(word) > 2]

    def fit(self, documents: list[str]) -> None:
        """Build the BM25 index (document frequencies and IDF) from ``documents``."""
        self.corpus = [self.tokenize(doc) for doc in documents]
        self.n = len(self.corpus)
        if self.n == 0:
            return
        self.doc_lengths = [len(doc) for doc in self.corpus]
        self.avgdl = sum(self.doc_lengths) / self.n
        for doc in self.corpus:
            for word in set(doc):
                self.doc_freqs[word] += 1
        for word, freq in self.doc_freqs.items():
            self.idf[word] = log((self.n - freq + 0.5) / (freq + 0.5) + 1)

    def score(self, query: str) -> list[tuple[int, float]]:
        """Score every indexed document against ``query``, ranked highest-first.

        Args:
            query: The free-text query to rank documents against.

        Returns:
            ``(document_index, score)`` pairs sorted by descending score.
        """
        query_tokens = self.tokenize(query)
        scores: list[tuple[int, float]] = []
        for idx, doc in enumerate(self.corpus):
            doc_len = self.doc_lengths[idx]
            term_freqs: dict[str, int] = defaultdict(int)
            for word in doc:
                term_freqs[word] += 1
            score = 0.0
            for token in query_tokens:
                if token in self.idf:
                    freq = term_freqs[token]
                    numerator = freq * (self.k1 + 1)
                    denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                    score += self.idf[token] * numerator / denominator
            scores.append((idx, score))
        return sorted(scores, key=lambda pair: pair[1], reverse=True)


def _load_csv(filepath: Path) -> list[dict[str, str]]:
    """Load a CSV file into a list of row dicts (empty when the file is missing)."""
    if not filepath.exists():
        return []
    with open(filepath, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _search_rows(
    rows: list[dict[str, str]],
    search_cols: list[str],
    output_cols: list[str],
    query: str,
    max_results: int,
) -> list[dict[str, str]]:
    """BM25-rank ``rows`` by ``search_cols`` and project the top hits to ``output_cols``.

    Args:
        rows: The CSV rows to search.
        search_cols: Columns concatenated into each row's searchable document.
        output_cols: Columns to keep in each returned hit.
        query: The free-text query.
        max_results: Maximum number of hits to return.

    Returns:
        The top matching rows (score > 0), each trimmed to ``output_cols``.
    """
    if not rows:
        return []
    documents = [" ".join(str(row.get(col, "")) for col in search_cols) for row in rows]
    bm25 = BM25()
    bm25.fit(documents)
    hits: list[dict[str, str]] = []
    for idx, score in bm25.score(query)[:max_results]:
        if score > 0:
            row = rows[idx]
            hits.append({col: row.get(col, "") for col in output_cols if col in row})
    return hits


def detect_domain(query: str) -> str:
    """Guess the most relevant search domain from ``query`` (defaults to ``style``)."""
    query_lower = query.lower()
    scores = {
        domain: sum(1 for hint in hints if hint in query_lower)
        for domain, hints in _DOMAIN_HINTS.items()
    }
    best = max(scores, key=lambda domain: scores[domain])
    return best if scores[best] > 0 else "style"


def search(query: str, domain: str | None = None, max_results: int = MAX_RESULTS) -> dict:
    """Search one knowledge-base domain and return ranked results.

    Args:
        query: The free-text query.
        domain: A key of ``CSV_CONFIG``; auto-detected from ``query`` when omitted.
        max_results: Maximum number of results to return.

    Returns:
        A dict with the resolved ``domain``, ``query``, source ``file``, result ``count``
        and the ``results`` list.
    """
    if domain is None or domain not in CSV_CONFIG:
        domain = detect_domain(query)
    config = CSV_CONFIG[domain]
    rows = _load_csv(DATA_DIR / str(config["file"]))
    results = _search_rows(
        rows,
        list(config["search"]),  # type: ignore[arg-type]
        list(config["output"]),  # type: ignore[arg-type]
        query,
        max_results,
    )
    return {
        "domain": domain,
        "query": query,
        "file": config["file"],
        "count": len(results),
        "results": results,
    }


class DesignSystemGenerator:
    """Synthesise a complete design system from multi-domain searches plus reasoning rules.

    The flow matches the upstream engine: find the product category, look up its reasoning
    rule (pattern, style priority, colour/type mood, key effects, anti-patterns), then run
    biased searches for the best-matching style, palette, font pairing and landing pattern.
    """

    def __init__(self):
        """Load the per-product reasoning rules from the vendored knowledge base."""
        self.reasoning = _load_csv(DATA_DIR / "ui-reasoning.csv")

    def _find_rule(self, category: str) -> dict[str, str]:
        """Find the reasoning rule whose ``UI_Category`` best matches ``category``."""
        category_lower = category.lower()
        for rule in self.reasoning:
            if rule.get("UI_Category", "").lower() == category_lower:
                return rule
        for rule in self.reasoning:
            ui_cat = rule.get("UI_Category", "").lower()
            if ui_cat and (ui_cat in category_lower or category_lower in ui_cat):
                return rule
        for rule in self.reasoning:
            ui_cat = rule.get("UI_Category", "").lower()
            keywords = ui_cat.replace("/", " ").replace("-", " ").split()
            if any(keyword in category_lower for keyword in keywords):
                return rule
        return {}

    def _reasoning_for(self, category: str) -> dict:
        """Return the parsed reasoning rule for ``category`` (with sensible defaults)."""
        rule = self._find_rule(category)
        if not rule:
            return {
                "pattern": "Hero + Features + CTA",
                "style_priority": ["Minimalism", "Flat Design"],
                "typography_mood": "Clean",
                "key_effects": "Subtle hover transitions",
                "anti_patterns": "",
                "severity": "MEDIUM",
            }
        try:
            decision_rules = json.loads(rule.get("Decision_Rules", "{}"))
        except json.JSONDecodeError:
            decision_rules = {}
        return {
            "pattern": rule.get("Recommended_Pattern", ""),
            "style_priority": [s.strip() for s in rule.get("Style_Priority", "").split("+")],
            "typography_mood": rule.get("Typography_Mood", ""),
            "key_effects": rule.get("Key_Effects", ""),
            "anti_patterns": rule.get("Anti_Patterns", ""),
            "decision_rules": decision_rules,
            "severity": rule.get("Severity", "MEDIUM"),
        }

    @staticmethod
    def _best_style(results: list[dict], priority: list[str]) -> dict:
        """Pick the style hit that best matches the reasoning rule's ``priority`` list."""
        if not results:
            return {}
        for name in priority:
            name_lower = name.lower().strip()
            if not name_lower:
                continue
            for result in results:
                style_name = result.get("Style Category", "").lower()
                if name_lower in style_name or style_name in name_lower:
                    return result
        return results[0]

    def generate(self, query: str, project_name: str | None = None) -> dict:
        """Generate a structured design-system recommendation for ``query``.

        Args:
            query: A short product description (e.g. "fintech banking dashboard").
            project_name: Optional display name for the recommendation header.

        Returns:
            A structured dict with ``pattern``, ``style``, ``colors``, ``typography``,
            ``key_effects`` and ``anti_patterns`` sections.
        """
        product_hits = search(query, "product", 1).get("results", [])
        category = product_hits[0].get("Product Type", "General") if product_hits else "General"

        reasoning = self._reasoning_for(category)
        priority = reasoning.get("style_priority", [])

        style_query = f"{query} {' '.join(priority[:2])}".strip()
        style = self._best_style(search(style_query, "style", 3).get("results", []), priority)
        color = (search(query, "color", 1).get("results") or [{}])[0]
        typography = (search(query, "typography", 1).get("results") or [{}])[0]
        landing = (search(query, "landing", 1).get("results") or [{}])[0]

        return {
            "project_name": project_name or query.title(),
            "category": category,
            "pattern": {
                "name": landing.get(
                    "Pattern Name", reasoning.get("pattern", "Hero + Features + CTA")
                ),
                "sections": landing.get("Section Order", ""),
                "cta_placement": landing.get("Primary CTA Placement", ""),
                "color_strategy": landing.get("Color Strategy", ""),
                "conversion": landing.get("Conversion Optimization", ""),
            },
            "style": {
                "name": style.get("Style Category", "Minimalism & Swiss Style"),
                "keywords": style.get("Keywords", ""),
                "best_for": style.get("Best For", ""),
                "light_mode": style.get("Light Mode ✓", ""),
                "dark_mode": style.get("Dark Mode ✓", ""),
                "performance": style.get("Performance", ""),
                "accessibility": style.get("Accessibility", ""),
                "effects": style.get("Effects & Animation", ""),
            },
            "colors": {
                "Primary": color.get("Primary", "#2563EB"),
                "On Primary": color.get("On Primary", "#FFFFFF"),
                "Secondary": color.get("Secondary", "#3B82F6"),
                "Accent": color.get("Accent", "#EA580C"),
                "Background": color.get("Background", "#F8FAFC"),
                "Foreground": color.get("Foreground", "#1E293B"),
                "Muted": color.get("Muted", ""),
                "Border": color.get("Border", ""),
                "Destructive": color.get("Destructive", ""),
                "Ring": color.get("Ring", ""),
                "notes": color.get("Notes", ""),
            },
            "typography": {
                "heading": typography.get("Heading Font", "Inter"),
                "body": typography.get("Body Font", "Inter"),
                "mood": typography.get("Mood/Style Keywords", reasoning.get("typography_mood", "")),
                "best_for": typography.get("Best For", ""),
                "google_fonts_url": typography.get("Google Fonts URL", ""),
                "css_import": typography.get("CSS Import", ""),
            },
            "key_effects": style.get("Effects & Animation", "") or reasoning.get("key_effects", ""),
            "anti_patterns": reasoning.get("anti_patterns", ""),
        }


_CHECKLIST = (
    "No emojis as icons (use SVG: Heroicons/Lucide)",
    "cursor-pointer on all clickable elements",
    "Hover/press states with smooth transitions (150-300ms)",
    "Text contrast at least 4.5:1 (3:1 for large text), in light and dark mode",
    "Focus states visible for keyboard navigation",
    "prefers-reduced-motion respected",
    "Responsive at 375 / 768 / 1024 / 1440px; no horizontal scroll",
)

# Semantic colour tokens rendered into the design-system table, in display order.
_COLOR_TOKENS = (
    ("Primary", "--color-primary"),
    ("On Primary", "--color-on-primary"),
    ("Secondary", "--color-secondary"),
    ("Accent", "--color-accent"),
    ("Background", "--color-background"),
    ("Foreground", "--color-foreground"),
    ("Muted", "--color-muted"),
    ("Border", "--color-border"),
    ("Destructive", "--color-destructive"),
    ("Ring", "--color-ring"),
)


def format_markdown(design_system: dict) -> str:
    """Render a structured design system (from ``DesignSystemGenerator``) as markdown.

    Args:
        design_system: The structured recommendation to render.

    Returns:
        A markdown document with pattern, style, colour-token table, typography, key
        effects, anti-patterns and a pre-delivery checklist.
    """
    pattern = design_system.get("pattern", {})
    style = design_system.get("style", {})
    colors = design_system.get("colors", {})
    typography = design_system.get("typography", {})

    lines = [
        f"# Design System — {design_system.get('project_name', 'Project')}",
        "",
        f"_Recommended for product category: **{design_system.get('category', 'General')}**._",
        "",
        "## Page Pattern",
        f"- **Pattern:** {pattern.get('name', '')}",
    ]
    if pattern.get("sections"):
        lines.append(f"- **Section order:** {pattern['sections']}")
    if pattern.get("cta_placement"):
        lines.append(f"- **Primary CTA:** {pattern['cta_placement']}")
    if pattern.get("conversion"):
        lines.append(f"- **Conversion focus:** {pattern['conversion']}")

    lines += ["", "## Visual Style", f"- **Style:** {style.get('name', '')}"]
    if style.get("keywords"):
        lines.append(f"- **Keywords:** {style['keywords']}")
    if style.get("light_mode") or style.get("dark_mode"):
        lines.append(
            f"- **Mode support:** Light {style.get('light_mode', '')} | "
            f"Dark {style.get('dark_mode', '')}"
        )
    if style.get("performance") or style.get("accessibility"):
        lines.append(
            f"- **Performance:** {style.get('performance', '')} | "
            f"**Accessibility:** {style.get('accessibility', '')}"
        )

    lines += ["", "## Colour Tokens", ""]
    lines += ["| Token | Hex | CSS Variable |", "|------|-----|--------------|"]
    for label, css_var in _COLOR_TOKENS:
        hex_val = colors.get(label, "")
        if hex_val:
            lines.append(f"| {label} | `{hex_val}` | `{css_var}` |")
    if colors.get("notes"):
        lines.append(f"\n_Notes: {colors['notes']}_")

    lines += [
        "",
        "## Typography",
        f"- **Heading:** {typography.get('heading', '')}",
        f"- **Body:** {typography.get('body', '')}",
    ]
    if typography.get("mood"):
        lines.append(f"- **Mood:** {typography['mood']}")
    if typography.get("google_fonts_url"):
        lines.append(f"- **Google Fonts:** {typography['google_fonts_url']}")
    if typography.get("css_import"):
        lines += ["- **CSS import:**", "```css", typography["css_import"], "```"]

    if design_system.get("key_effects"):
        lines += ["", "## Key Effects", design_system["key_effects"]]

    if design_system.get("anti_patterns"):
        lines += ["", "## Avoid (Anti-Patterns)"]
        lines += [
            f"- {item.strip()}"
            for item in design_system["anti_patterns"].split("+")
            if item.strip()
        ]

    lines += ["", "## Pre-Delivery Checklist"]
    lines += [f"- [ ] {item}" for item in _CHECKLIST]
    lines.append("")
    return "\n".join(lines)


def generate_design_system(query: str, project_name: str | None = None) -> str:
    """Generate a complete design system for ``query`` and render it as markdown.

    This is the plain-function entry point the UX node calls deterministically (no model,
    no network), so the recommendation is reproducible and works in ``--dry-run``.

    Args:
        query: A short product description (e.g. "beauty spa wellness booking").
        project_name: Optional display name for the recommendation header.

    Returns:
        The design system as a markdown document.
    """
    return format_markdown(DesignSystemGenerator().generate(query, project_name))


# --- LangChain tool wrappers (for ReAct-style agents on tool-capable models) ---


@tool
def design_system(query: str, project_name: str = "") -> str:
    """Recommend a complete design system (pattern, style, colours, fonts, effects).

    Given a short product description, returns markdown with the recommended page pattern,
    visual style, semantic colour tokens, font pairing, key effects, anti-patterns to
    avoid, and a pre-delivery checklist. Use before designing or implementing any UI.
    """
    return generate_design_system(query, project_name or None)


@tool
def ui_ux_search(query: str, domain: str = "") -> str:
    """Search the UI/UX knowledge base for a single domain and return ranked guidance.

    Domains: product, style, color, typography, landing, chart, ux. When ``domain`` is
    empty it is inferred from the query. Use to deep-dive one dimension (e.g. a colour
    palette, a chart type, or accessibility rules) after recommending a design system.
    """
    result = search(query, domain or None)
    out = [f"## UI/UX search — domain: {result['domain']} | query: {result['query']}"]
    for i, row in enumerate(result["results"], 1):
        out.append(f"\n### Result {i}")
        out += [f"- **{key}:** {value}" for key, value in row.items() if value]
    if not result["results"]:
        out.append("\n_No matching guidance found._")
    return "\n".join(out)
