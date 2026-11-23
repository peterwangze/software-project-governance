"""Check documentation paths, reference cycles and adapter quotations."""
from pathlib import Path
import re


def check_cross_references(*, product_root, validator_path, quote_sync_issues, check_exploration_channels):
    """Scan .md and .py files for path references, build a reference graph,
    and detect: (1) dangling references (target file does not exist),
    (2) deprecated path patterns, (3) circular references (cycle detection).

    Path reference patterns extracted:
    - Markdown: [text](path), bare `` file.md `` paths, `` `path/to/file` ``
    - Python: ROOT / "relative/path" format
    """
    import collections

    scan_dirs = [
        "skills/software-project-governance/",
        "commands/",
        "agents/",
    ]

    # Collect all .md files from scan directories
    md_files = []
    for d in scan_dirs:
        p = product_root / d
        if p.is_dir():
            md_files.extend(p.rglob("*.md"))

    # Also include verify_workflow.py itself
    py_files = [validator_path]

    # Build: dict[source_relpath] -> list of (target_raw, line_num)
    refs = {}
    source_lines = {}

    for f in md_files + py_files:
        try:
            content = f.read_text(encoding="utf-8")
        except Exception:
            continue
        source = str(f.relative_to(product_root)).replace("\\", "/")
        refs[source] = []
        source_lines[source] = content.split("\n")

        in_code_block = False
        for i, line in enumerate(source_lines[source], 1):
            if f.suffix == ".py":
                # Python: ROOT / "relative/path"  pattern
                for m in re.finditer(r'\bROOT\s*/\s*"([^"]+)"', line):
                    target = m.group(1)
                    if Path(target).suffix:
                        refs[source].append((target, i))
            else:
                # ── Code block tracking: skip fenced and indented code blocks ──
                # Fenced code blocks (``` or ~~~). Strip language tag if present.
                if re.match(r'^\s*```', line):
                    in_code_block = not in_code_block
                    continue
                if re.match(r'^\s*~~~', line):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    continue
                # Indented code block (4+ spaces or 1+ tab at line start)
                if re.match(r'^ {4,}', line) or line.startswith('\t'):
                    continue

                # Backticked explicit paths with a directory separator are
                # intentional references and should still be validated.
                for m in re.finditer(r"`([^`]+/[^\s`]+\.(?:md|py)(?:\.template)?)`", line):
                    refs[source].append((m.group(1), i))

                # ── Strip inline code (backtick-quoted) from the line ──
                stripped_line = re.sub(r'`+[^`]*`+', '', line)

                # Markdown: [text](path) — skip http/https/#/mailto links
                for m in re.finditer(r'\[([^\]]*)\]\(([^)]+)\)', stripped_line):
                    target = m.group(2)
                    if not target.startswith(("http://", "https://", "#", "mailto:")):
                        refs[source].append((target, i))
                # Bare paths must include a directory separator.  A lone
                # filename such as "SKILL.md" is often prose shorthand and
                # caused hundreds of dangling-reference false positives after
                # archive cleanup. Markdown links still cover explicit
                # same-directory references.
                for m in re.finditer(r'(?<!["\w/\-.])([a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-/]+\.(?:md|py)(?:\.template)?)(?!\w|\.\w)', stripped_line):
                    refs[source].append((m.group(1), i))

    # ── Detect dangling references ──
    dangling = []
    root_relative_prefixes = (
        "skills/", "agents/", "agent-presets/", "commands/", "adapters/", "project/", "docs/",
        ".governance/", ".github/", ".agents/", ".claude-plugin/", ".codex-plugin/",
    )
    skill_root_relative_prefixes = ("core/", "infra/", "references/")
    placeholder_prefixes = ("skill/", "relative/")
    placeholder_markers = ("<", ">", "{", "}", "*")
    entry_source = "skills/software-project-governance/SKILL.md"
    validator_source = "skills/software-project-governance/infra/verify_workflow.py"

    def normalize_ref_target(target):
        target = target.strip()
        if target.startswith("python "):
            target = target.split(None, 1)[1]
        if target.startswith("./"):
            target = target[2:]
        return target

    def is_placeholder_ref(target):
        return target.startswith(placeholder_prefixes) or any(m in target for m in placeholder_markers)

    def source_supports_skill_root_relative(source):
        return (
            source.startswith("skills/software-project-governance/")
            or source.startswith("commands/")
            or source.startswith("agents/")
        )

    def resolve_ref(source, target):
        source_dir = (product_root / source).parent
        if source.endswith(".py"):
            return (product_root / target).resolve()
        if target.startswith(root_relative_prefixes):
            return (product_root / target).resolve()
        if (source_supports_skill_root_relative(source)
                and target.startswith(skill_root_relative_prefixes)):
            return (product_root / "skills/software-project-governance" / target).resolve()
        return (source_dir / target).resolve()

    def line_text(source, line_num):
        lines = source_lines.get(source, [])
        if 1 <= line_num <= len(lines):
            return lines[line_num - 1].strip()
        return ""

    def is_in_generated_output_section(source, line_num):
        if not source.startswith("agents/"):
            return False
        lines = source_lines.get(source, [])
        in_output = False
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if idx > line_num:
                break
            if stripped.startswith("## "):
                in_output = stripped == "## 输出格式"
                continue
        return in_output

    def is_generated_output_ref(source, target, line_num):
        if not is_in_generated_output_section(source, line_num):
            return False
        if not target.startswith(("docs/", ".github/", "Dockerfile", "docker-compose.yml")):
            return False
        context = "\n".join(source_lines.get(source, [])[max(0, line_num - 4):line_num + 1])
        return "必须生成" in context or line_text(source, line_num).startswith("-")

    def is_external_or_runtime_generated_ref(source, target, line_num):
        current_line = line_text(source, line_num)
        if target.startswith(".governance/"):
            return True
        if target.startswith((
            "project/e2e-test-project/agents/",
            "project/e2e-test-project/commands/",
            "project/e2e-test-project/skills/",
        )):
            return True
        if target == "archive/index.md" and ("不" in current_line and "自动生成" in current_line):
            return True
        return False

    def should_ignore_ref(source, target, line_num):
        return (
            is_placeholder_ref(target)
            or is_generated_output_ref(source, target, line_num)
            or is_external_or_runtime_generated_ref(source, target, line_num)
        )

    for source, targets in refs.items():
        for target, line_num in targets:
            target = normalize_ref_target(target)
            if should_ignore_ref(source, target, line_num):
                continue
            # Resolve target relative to the source file's directory
            try:
                resolved = resolve_ref(source, target)
                resolved.relative_to(product_root)
            except (ValueError, OSError):
                continue  # outside project or unresolvable
            if not resolved.exists():
                dangling.append({
                    "source": source,
                    "line": line_num,
                    "target": target,
                })

    # ── Detect deprecated path patterns ──
    deprecated_patterns = [
        "skills/software-project-governance/skills/",
        "skills/software-project-governance/agents/",
    ]
    deprecated = []
    for source, targets in refs.items():
        for target, line_num in targets:
            for dp in deprecated_patterns:
                if dp in target:
                    deprecated.append({
                        "source": source,
                        "line": line_num,
                        "target": target,
                        "deprecated_pattern": dp,
                    })

    # ── Detect circular references (DFS on directed graph) ──
    graph = collections.defaultdict(list)
    for source, targets in refs.items():
        # verify_workflow.py contains coverage constants and check fixtures that
        # cite product files. Those are validation edges, not runtime or
        # architecture dependencies, so they must not create source↔validator
        # circular-reference failures.
        if source in (entry_source, validator_source):
            continue
        for target, line_num in targets:
            target = normalize_ref_target(target)
            if should_ignore_ref(source, target, line_num):
                continue
            try:
                resolved = resolve_ref(source, target)
                rel_target = str(resolved.relative_to(product_root)).replace("\\", "/")
            except (ValueError, OSError):
                continue
            if rel_target in (entry_source, validator_source):
                continue
            if rel_target in refs:  # only edges within scanned scope
                graph[source].append(rel_target)

    cycles = []
    seen_nodes = set()
    WHITE, GRAY, BLACK = 0, 1, 2

    def _dfs_cycle(node, colors, parent_map, stack):
        colors[node] = GRAY
        stack.append(node)
        for neighbor in graph.get(node, []):
            ncolors_key = neighbor
            if colors.get(ncolors_key, WHITE) == WHITE:
                parent_map[neighbor] = node
                _dfs_cycle(neighbor, colors, parent_map, stack)
            elif colors.get(ncolors_key, WHITE) == GRAY:
                # Found a cycle — extract the subsequence
                try:
                    idx = stack.index(neighbor)
                    cycle = stack[idx:] + [neighbor]
                    cycles.append(cycle)
                except ValueError:
                    pass
        colors[node] = BLACK
        stack.pop()

    colors_map = {}
    for node in list(graph):
        if colors_map.get(node, WHITE) == WHITE:
            _dfs_cycle(node, colors_map, {}, [])

    # Deduplicate cycles (same set of nodes in different rotations)
    unique_cycles = []
    seen_cycles = set()
    for cycle in cycles:
        if len(cycle) == 2 and cycle[0] == cycle[1]:
            continue
        key = tuple(sorted(cycle))
        if key not in seen_cycles:
            seen_cycles.add(key)
            unique_cycles.append(cycle)

    # ── FIX-432 (F-4 / F-A2): citation/note quote-sync guard ──
    quote_sync = quote_sync_issues()

    # ── FEAT-088 (F-A3): exploration-channel evidence-form guard ──
    # Same carrier discipline as quote_sync: a related-but-distinct manifest
    # sub-face riding the manifest/cross-reference machine-check surface
    # instead of a new numbered check section (registry/frozen-snapshot zero
    # churn; fact source stays plugin-package like its host section).
    exploration_channels = check_exploration_channels()

    return {
        "dangling": dangling,
        "deprecated": deprecated,
        "cycles": unique_cycles,
        "quote_sync": quote_sync,
        "exploration_channels": exploration_channels,
        "total_files_scanned": len(md_files) + len(py_files),
        "total_refs": sum(len(t) for t in refs.values()),
    }
