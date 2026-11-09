"""Jinja2 template rendering with a sandboxed environment (P2: wiki generation).

Built-in templates render the *facts* fetched from the backend (task summary
groups / case-map outline); the AI client may still post-edit `content` and
pass it back, in which case rendering is skipped. User-supplied template dirs
(STUDIO_MCP_TEMPLATES_DIR) override builtins with the same file names.
"""

from __future__ import annotations

from typing import Any

from jinja2 import ChoiceLoader, DictLoader, FileSystemLoader, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

BUILTIN_TEMPLATES: dict[str, str] = {
    "weekly_report.md.j2": """---
title: "{{ title }}"
date: "{{ date }}"
range: "{{ range }}"
total_tasks: {{ total }}
generated_by: studiosystem-mcp
---

# {{ title }}

> 范围：{{ range }} ｜ 任务总数：{{ total }} ｜ 生成日期：{{ date }}

{% for group in groups -%}
## {{ group.name }}（{{ group.count }}）

{% endfor -%}
## 任务明细

{{ markdown }}
""",
    "testcase_spec.md.j2": """---
title: "{{ title }}"
source_case_map: "{{ map_id }}"
source_map_title: "{{ map_title }}"
generated: "{{ date }}"
generated_by: studiosystem-mcp
---

# {{ title }}

> 来源导图：[[{{ map_title }}]]（{{ map_id }}）｜ 生成日期：{{ date }}

{% for node in nodes -%}
{{ "  " * node.depth }}- {{ node.text }}{% if node.uid %} `{{ node.uid }}`{% endif %}

{% endfor %}
## 说明

- 以上为用例导图「{{ map_title }}」的完整节点清单，缩进表示层级。
- 执行用例时建议配合 `case_outline_to_tasks` 把叶子节点转为任务跟踪。
""",
    "retro.md.j2": """---
title: "{{ title }}"
date: "{{ date }}"
range: "{{ range }}"
generated_by: studiosystem-mcp
---

# {{ title }}

> 范围：{{ range }} ｜ 生成日期：{{ date }}

## 数据底稿

{{ markdown }}

## 做得好（待填写）

## 待改进（待填写）

## 下周计划（待填写）
""",
}


def build_environment(templates_dir: str | None = None) -> SandboxedEnvironment:
    """Sandboxed Jinja2 env: user template dirs (untrusted) override builtins."""
    loaders = []
    if templates_dir:
        loaders.append(FileSystemLoader(templates_dir))
    loaders.append(DictLoader(BUILTIN_TEMPLATES))
    return SandboxedEnvironment(
        loader=ChoiceLoader(loaders),
        undefined=StrictUndefined,
        autoescape=False,  # markdown source, not HTML
    )


def render_template(env: SandboxedEnvironment, name: str, context: dict[str, Any]) -> str:
    return env.get_template(name).render(**context)
