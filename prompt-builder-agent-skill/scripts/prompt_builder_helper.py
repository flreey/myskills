#!/usr/bin/env python3
# Optional local helper for Prompt Builder Skill.
# This script can run a lightweight CLI version of the skill.

def ask(q, options, default=0):
    print("\n" + q)
    for i, o in enumerate(options, 1):
        print(f"{i}. {o}")
    raw = input(f"> Enter for default ({options[default]}): ").strip()
    if not raw:
        return options[default]
    try:
        return options[int(raw)-1]
    except Exception:
        return raw

def classify(text):
    if any(k in text.lower() for k in ["image", "poster", "visual", "logo"]) or any(k in text for k in ["图", "图片", "海报", "画面", "视觉"]):
        return "Image / visual"
    if any(k in text.lower() for k in ["app", "website", "tool", "calculator", "saas"]) or any(k in text for k in ["网站", "工具", "计算器", "产品", "平台"]):
        return "Product / tool"
    if any(k in text.lower() for k in ["write", "article", "copy", "email"]) or any(k in text for k in ["文章", "文案", "邮件", "写"]):
        return "Writing / copy"
    if any(k in text.lower() for k in ["code", "script", "api"]) or any(k in text for k in ["代码", "脚本", "自动化"]):
        return "Code / automation"
    return "General task"

def main():
    print("Prompt Builder Skill Helper")
    idea = input("Your rough idea: ").strip()
    t = classify(idea)
    print(f"\nDetected type: {t}")

    direction = ask("What direction is closest?", [
        "Basic: solve one clear problem",
        "Decision: compare options and recommend",
        "Commercial: useful for paying users",
        "Not sure, choose a practical MVP"
    ], 3)

    complexity = ask("How complete should the first version be?", [
        "Very small MVP",
        "Medium complete",
        "Full product spec"
    ], 0)

    print("\nCopy-ready prompt:\n")
    print(f"""Goal:
Turn this rough idea into a concrete {t} plan: {idea}

Direction:
{direction}

First version:
{complexity}

Please produce:
- Restated goal
- Target user or audience
- Inputs
- Outputs
- Constraints
- Structure
- Key mechanism
- MVP scope
- Avoid list
- Acceptance criteria

Use simple language, make reasonable defaults when information is missing, and ask at most 3 focused questions only if absolutely necessary.
""")

if __name__ == "__main__":
    main()
