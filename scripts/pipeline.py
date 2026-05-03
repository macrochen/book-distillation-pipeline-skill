import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


STATE_FILE = ".pipeline-state.json"
PROJECT_ROOT = Path("outputs/book-distillation-pipeline-skill")

STAGES = [
    {"id": "step_0_init", "kind": "action"},
    {"id": "checkpoint_0_book_info", "kind": "checkpoint"},
    {"id": "step_1_classify", "kind": "action"},
    {"id": "checkpoint_1_classify_review", "kind": "checkpoint"},
    {"id": "step_2_author_voice", "kind": "action"},
    {"id": "checkpoint_2_voice_review", "kind": "checkpoint"},
    {"id": "step_3_instructions", "kind": "action"},
    {"id": "checkpoint_3_instructions_review", "kind": "checkpoint"},
    {"id": "step_4_knowledge_base", "kind": "action"},
    {"id": "checkpoint_4_kb_review", "kind": "checkpoint"},
    {"id": "step_5_cross_validate", "kind": "action"},
    {"id": "checkpoint_5_validate_review", "kind": "checkpoint"},
    {"id": "step_6_package", "kind": "action"},
    {"id": "checkpoint_6_package_review", "kind": "checkpoint"},
    {"id": "step_7_deploy", "kind": "action"},
]

STAGE_INDEX = {stage["id"]: index for index, stage in enumerate(STAGES)}

STAGE_CONTRACTS = {
    "checkpoint_0_book_info": {
        "type": "checkpoint",
        "goal": "确认书籍信息（书名、作者、PDF路径、目标平台）",
        "choices": ["confirmed"],
    },
    "step_1_classify": {
        "type": "action",
        "goal": "根据决策树确定书籍主类型和辅模块",
        "inputs": ["00-book-info.md"],
        "required_artifacts": ["01-classification.md"],
        "complete_action_keys": ["classification_md"],
    },
    "checkpoint_1_classify_review": {
        "type": "checkpoint",
        "goal": "展示分类结果，等待用户确认或修正",
        "needs_user_confirmation": True,
    },
    "step_2_author_voice": {
        "type": "action",
        "goal": "从书中提取作者原声特征（口头禅、反问句式、比喻习惯等）",
        "inputs": ["book_pdf"],
        "required_artifacts": ["02-author-voice.md"],
        "complete_action_keys": ["voice_md"],
    },
    "checkpoint_2_voice_review": {
        "type": "checkpoint",
        "goal": "展示作者原声提取结果，用户可补充或修正",
        "needs_user_confirmation": True,
    },
    "step_3_instructions": {
        "type": "action",
        "goal": "根据分类结果选择模板，结合作者原声，生成指令",
        "inputs": ["01-classification.md", "02-author-voice.md"],
        "required_artifacts": ["03-instructions.md"],
        "complete_action_keys": ["instructions_md"],
    },
    "checkpoint_3_instructions_review": {
        "type": "checkpoint",
        "goal": "展示指令全文，按审核清单检查",
        "needs_user_confirmation": True,
    },
    "step_4_knowledge_base": {
        "type": "action",
        "goal": "根据分类结果选择知识库模板，结合指令生成知识库",
        "inputs": ["01-classification.md", "03-instructions.md"],
        "required_artifacts": ["04-knowledge-base.md"],
        "complete_action_keys": ["kb_md"],
    },
    "checkpoint_4_kb_review": {
        "type": "checkpoint",
        "goal": "展示知识库条目数量和关键条目预览",
        "needs_user_confirmation": True,
    },
    "step_5_cross_validate": {
        "type": "action",
        "goal": "交叉验证指令和知识库的一致性",
        "inputs": ["03-instructions.md", "04-knowledge-base.md"],
        "required_artifacts": ["05-cross-validation.md"],
        "complete_action_keys": ["validation_md"],
    },
    "checkpoint_5_validate_review": {
        "type": "checkpoint",
        "goal": "展示验证结果，如有缺失项返回补充",
        "needs_user_confirmation": True,
    },
    "step_6_package": {
        "type": "action",
        "goal": "生成打包配置（名称、说明、Conversation Starters）",
        "inputs": ["01-classification.md", "03-instructions.md", "04-knowledge-base.md"],
        "required_artifacts": ["06-package-config.md"],
        "complete_action_keys": ["package_md"],
    },
    "checkpoint_6_package_review": {
        "type": "checkpoint",
        "goal": "展示打包配置，用户可修改名称、说明等",
        "needs_user_confirmation": True,
    },
    "step_7_deploy": {
        "type": "action",
        "goal": "半自动部署到Gemini Gem或ChatGPT GPTs",
        "inputs": ["06-package-config.md", "04-knowledge-base.md"],
        "required_meta": ["platform", "deploy_status"],
    },
}

CHECKPOINT_RULES = {
    "checkpoint_0_book_info": {
        "choices": {"confirmed"},
        "decision_key": "book_info_confirmed",
    },
    "checkpoint_1_classify_review": {
        "choices": {"approved", "revised"},
        "decision_key": "classify_approved",
    },
    "checkpoint_2_voice_review": {
        "choices": {"approved", "revised"},
        "decision_key": "voice_approved",
    },
    "checkpoint_3_instructions_review": {
        "choices": {"approved", "revised"},
        "decision_key": "instructions_approved",
    },
    "checkpoint_4_kb_review": {
        "choices": {"approved", "revised"},
        "decision_key": "kb_approved",
    },
    "checkpoint_5_validate_review": {
        "choices": {"approved", "needs_fix"},
        "decision_key": "validation_approved",
    },
    "checkpoint_6_package_review": {
        "choices": {"approved", "revised"},
        "decision_key": "package_approved",
    },
}

AUTO_MODE_DEFAULTS = {
    "checkpoint_0_book_info": "confirmed",
    "checkpoint_1_classify_review": "approved",
    "checkpoint_2_voice_review": "approved",
    "checkpoint_3_instructions_review": "approved",
    "checkpoint_4_kb_review": "approved",
    "checkpoint_5_validate_review": "approved",
    "checkpoint_6_package_review": "approved",
}


class PipelineError(RuntimeError):
    pass


SUPPORTED_FORMATS = {".pdf", ".md", ".markdown", ".txt", ".epub"}


def detect_format(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_FORMATS:
        raise PipelineError(f"unsupported format: {ext}. supported: {', '.join(sorted(SUPPORTED_FORMATS))}")
    return ext


def parse_book_entries(book_paths, book_titles=None) -> list:
    """Parse multiple book paths into structured entries with title and format."""
    entries = []
    titles = book_titles or []
    for i, raw_path in enumerate(book_paths):
        p = Path(raw_path).expanduser().resolve()
        if not p.exists():
            raise PipelineError(f"book file does not exist: {p}")
        fmt = detect_format(p)
        title = titles[i] if i < len(titles) else p.stem
        entries.append({
            "path": str(p),
            "title": title,
            "format": fmt,
        })
    return entries


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def print_json(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def parse_pairs(items):
    result = {}
    for item in items or []:
        if "=" not in item:
            raise PipelineError(f"invalid key=value pair: {item}")
        key, value = item.split("=", 1)
        if not key or not value:
            raise PipelineError(f"invalid key=value pair: {item}")
        result[key] = value
    return result


def default_project_dir(title):
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in title).strip("-") or "book-project"
    slug = f"{datetime.now().strftime('%Y%m%d')}-{safe}"
    return (PROJECT_ROOT / slug).resolve()


def ensure_valid_project_dir(project_dir: Path):
    normalized = project_dir.expanduser().resolve()
    expected_root = PROJECT_ROOT.resolve()
    try:
        normalized.relative_to(expected_root)
    except ValueError as exc:
        raise PipelineError(
            f"project_dir must live under {expected_root}, not {normalized}"
        ) from exc
    return normalized


def next_stage(current_stage):
    index = STAGE_INDEX[current_stage]
    if index + 1 >= len(STAGES):
        return None
    return STAGES[index + 1]["id"]


def state_path(project_dir: Path):
    return project_dir / STATE_FILE


def load_state(project_dir: Path):
    path = state_path(project_dir)
    if not path.exists():
        raise PipelineError(f"missing state file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(project_dir: Path, state):
    path = state_path(project_dir)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def append_history(state, kind, stage, detail=None):
    state.setdefault("history", []).append(
        {
            "timestamp": now_iso(),
            "kind": kind,
            "stage": stage,
            "detail": detail or {},
        }
    )


def require_current_stage(state, stage_id):
    current = state["current_stage"]
    if current != stage_id:
        raise PipelineError(f"current stage is {current}, not {stage_id}")


def require_file(path_str, key_name):
    if not path_str:
        raise PipelineError(f"required file for {key_name} is missing")
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise PipelineError(f"required file for {key_name} does not exist: {path}")
    return str(path)


def init_project(args):
    book_entries = parse_book_entries(args.book_path, args.book_title)
    project_dir = Path(args.project_dir) if args.project_dir else default_project_dir(args.title)
    project_dir = ensure_valid_project_dir(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    # Build book info
    multi_book = len(book_entries) > 1
    book_info = {
        "title": args.title,
        "author": args.author,
        "project_type": args.project_type or ("multi-book" if multi_book else "single"),
        "books": book_entries,
        "target_platform": args.platform or "gemini",
        "gemini_create_url": args.gemini_url or "https://gemini.google.com/gems/create",
    }

    # Generate book info markdown
    book_info_md = project_dir / "00-book-info.md"
    books_section = ""
    for i, b in enumerate(book_entries, 1):
        books_section += (
            f"### 书籍 {i}\n"
            f"- **书名**: {b['title']}\n"
            f"- **格式**: {b['format']}\n"
            f"- **路径**: {b['path']}\n\n"
        )

    book_info_content = (
        f"# 书籍信息\n\n"
        f"- **项目名称**: {book_info['title']}\n"
        f"- **作者/人物**: {book_info['author']}\n"
        f"- **项目类型**: {book_info['project_type']}\n"
        f"- **书籍数量**: {len(book_entries)}\n"
        f"- **目标平台**: {book_info['target_platform']}\n"
        f"- **Gemini创建页面**: {book_info['gemini_create_url']}\n\n"
        f"## 书籍列表\n\n{books_section}"
    )
    book_info_md.write_text(book_info_content, encoding="utf-8")

    state = {
        "version": 2,
        "title": args.title,
        "author": args.author,
        "project_dir": str(project_dir),
        "created_at": now_iso(),
        "current_stage": "checkpoint_0_book_info",
        "completed_stages": ["step_0_init"],
        "decisions": {},
        "artifacts": {
            "book_info_md": str(book_info_md.resolve()),
        },
        "meta": {
            "project_type": book_info["project_type"],
            "book_count": len(book_entries),
            "books": book_entries,
            "target_platform": book_info["target_platform"],
            "gemini_create_url": book_info["gemini_create_url"],
        },
        "history": [],
        "auto_mode": args.auto if hasattr(args, "auto") else False,
    }
    append_history(state, "init", "step_0_init", {
        "book_count": len(book_entries),
        "books": [b["title"] for b in book_entries],
    })
    save_state(project_dir, state)

    print_json(
        {
            "status": "ok",
            "project_dir": str(project_dir),
            "state_file": str(state_path(project_dir)),
            "current_stage": state["current_stage"],
            "book_count": len(book_entries),
            "project_type": book_info["project_type"],
            "artifacts": state["artifacts"],
        }
    )


def show_status(args):
    project_dir = ensure_valid_project_dir(Path(args.project_dir))
    state = load_state(project_dir)
    stage = state["current_stage"]
    print_json(
        {
            "status": "ok",
            "project_dir": str(project_dir),
            "current_stage": stage,
            "current_stage_kind": STAGES[STAGE_INDEX[stage]]["kind"] if stage else None,
            "completed_stages": state["completed_stages"],
            "decisions": state["decisions"],
            "artifacts": state["artifacts"],
            "meta": state.get("meta", {}),
        }
    )


def show_stage_brief(args):
    project_dir = ensure_valid_project_dir(Path(args.project_dir))
    state = load_state(project_dir)
    stage_id = args.stage or state["current_stage"]
    if stage_id not in STAGE_INDEX:
        raise PipelineError(f"unknown stage: {stage_id}")

    contract = STAGE_CONTRACTS.get(stage_id, {}).copy()
    contract["stage"] = stage_id
    contract["current_stage"] = state["current_stage"]
    contract["decisions"] = state.get("decisions", {})
    contract["known_artifacts"] = state.get("artifacts", {})
    contract["next_stage_after_success"] = next_stage(stage_id)
    print_json(contract)


def validate_action_requirements(stage_id, artifacts, meta, state):
    if stage_id == "step_1_classify":
        artifacts["classification_md"] = require_file(artifacts.get("classification_md", ""), "classification_md")
    elif stage_id == "step_2_author_voice":
        artifacts["voice_md"] = require_file(artifacts.get("voice_md", ""), "voice_md")
    elif stage_id == "step_3_instructions":
        artifacts["instructions_md"] = require_file(artifacts.get("instructions_md", ""), "instructions_md")
    elif stage_id == "step_4_knowledge_base":
        artifacts["kb_md"] = require_file(artifacts.get("kb_md", ""), "kb_md")
    elif stage_id == "step_5_cross_validate":
        artifacts["validation_md"] = require_file(artifacts.get("validation_md", ""), "validation_md")
    elif stage_id == "step_6_package":
        artifacts["package_md"] = require_file(artifacts.get("package_md", ""), "package_md")
    elif stage_id == "step_7_deploy":
        platform = meta.get("platform")
        if not platform:
            raise PipelineError("platform is required for step_7_deploy")
        if platform not in {"gemini", "chatgpt"}:
            raise PipelineError("platform must be gemini or chatgpt")
        deploy_status = meta.get("deploy_status")
        if not deploy_status:
            raise PipelineError("deploy_status is required for step_7_deploy")


def advance_after_action(state, stage_id):
    next_id = next_stage(stage_id)
    state["current_stage"] = next_id


def complete_action(args):
    project_dir = ensure_valid_project_dir(Path(args.project_dir))
    state = load_state(project_dir)
    require_current_stage(state, args.stage)

    stage = STAGES[STAGE_INDEX[args.stage]]
    if stage["kind"] not in {"action", "optional"}:
        raise PipelineError(f"{args.stage} is not an action stage")

    artifacts = parse_pairs(args.artifact)
    meta = parse_pairs(args.meta)
    validate_action_requirements(args.stage, artifacts, meta, state)

    state["artifacts"].update(artifacts)
    state["meta"].update(meta)
    if args.stage not in state["completed_stages"]:
        state["completed_stages"].append(args.stage)
    append_history(
        state,
        "complete_action",
        args.stage,
        {"artifacts": artifacts, "meta": meta, "note": args.note or ""},
    )
    advance_after_action(state, args.stage)
    save_state(project_dir, state)

    print_json(
        {
            "status": "ok",
            "completed_stage": args.stage,
            "current_stage": state["current_stage"],
            "artifacts": state["artifacts"],
            "decisions": state["decisions"],
        }
    )


def approve_checkpoint(args):
    project_dir = ensure_valid_project_dir(Path(args.project_dir))
    state = load_state(project_dir)
    require_current_stage(state, args.stage)

    stage = STAGES[STAGE_INDEX[args.stage]]
    if stage["kind"] != "checkpoint":
        raise PipelineError(f"{args.stage} is not a checkpoint stage")

    rule = CHECKPOINT_RULES.get(args.stage)
    if rule:
        if not args.value:
            raise PipelineError(f"{args.stage} requires --value")
        if args.value not in rule["choices"]:
            allowed = ", ".join(sorted(rule["choices"]))
            raise PipelineError(f"{args.stage} value must be one of: {allowed}")
        state["decisions"][rule["decision_key"]] = args.value

    if args.stage not in state["completed_stages"]:
        state["completed_stages"].append(args.stage)
    append_history(state, "approve", args.stage, {"value": args.value or "approved", "note": args.note or ""})
    state["current_stage"] = next_stage(args.stage)
    save_state(project_dir, state)

    print_json(
        {
            "status": "ok",
            "completed_stage": args.stage,
            "current_stage": state["current_stage"],
            "decisions": state["decisions"],
            "artifacts": state["artifacts"],
        }
    )


def auto_approve(args):
    """Auto-approve current checkpoint using default values for auto mode."""
    project_dir = ensure_valid_project_dir(Path(args.project_dir))
    state = load_state(project_dir)

    if not state.get("auto_mode"):
        raise PipelineError("auto-approve only works when auto_mode is enabled (use --auto during init)")

    current_stage = state["current_stage"]
    stage = STAGES[STAGE_INDEX.get(current_stage, -1)]

    if stage.get("kind") != "checkpoint":
        raise PipelineError(f"current stage {current_stage} is not a checkpoint")

    default_value = AUTO_MODE_DEFAULTS.get(current_stage)
    if not default_value:
        raise PipelineError(f"no default value defined for checkpoint {current_stage}")

    class AutoArgs:
        def __init__(self):
            self.project_dir = args.project_dir
            self.stage = current_stage
            self.value = default_value
            self.note = f"auto-approved with default: {default_value}"

    approve_checkpoint(AutoArgs())


def build_parser():
    parser = argparse.ArgumentParser(description="Stateful controller for book-distillation-pipeline-skill")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--project-dir")
    init_parser.add_argument("--book-path", required=True, nargs="+", help="Path(s) to book files (PDF, MD, TXT, EPUB). Multiple paths for multi-book projects.")
    init_parser.add_argument("--book-title", nargs="*", help="Title(s) for each book (optional, defaults to filename)")
    init_parser.add_argument("--title", required=True, help="Project/agent title")
    init_parser.add_argument("--author", required=True, help="Author or subject person name")
    init_parser.add_argument("--project-type", choices=["single", "multi-book", "person-series"], help="Project type (auto-detected if omitted)")
    init_parser.add_argument("--platform", default="gemini", help="Target platform: gemini or chatgpt")
    init_parser.add_argument("--gemini-url", default="https://gemini.google.com/gems/create", help="Gemini Gem creation URL")
    init_parser.add_argument("--auto", action="store_true", help="Enable auto mode")
    init_parser.set_defaults(func=init_project)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--project-dir", required=True)
    status_parser.set_defaults(func=show_status)

    brief_parser = subparsers.add_parser("stage-brief")
    brief_parser.add_argument("--project-dir", required=True)
    brief_parser.add_argument("--stage")
    brief_parser.set_defaults(func=show_stage_brief)

    complete_parser = subparsers.add_parser("complete-action")
    complete_parser.add_argument("--project-dir", required=True)
    complete_parser.add_argument("--stage", required=True)
    complete_parser.add_argument("--artifact", action="append", default=[])
    complete_parser.add_argument("--meta", action="append", default=[])
    complete_parser.add_argument("--note")
    complete_parser.set_defaults(func=complete_action)

    approve_parser = subparsers.add_parser("approve")
    approve_parser.add_argument("--project-dir", required=True)
    approve_parser.add_argument("--stage", required=True)
    approve_parser.add_argument("--value")
    approve_parser.add_argument("--note")
    approve_parser.set_defaults(func=approve_checkpoint)

    auto_approve_parser = subparsers.add_parser("auto-approve")
    auto_approve_parser.add_argument("--project-dir", required=True)
    auto_approve_parser.set_defaults(func=auto_approve)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except PipelineError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
