#!/usr/bin/env python3
"""
setup.py - Interactive Setup Wizard for loom

This script automatically detects your project and sets up the framework:
- Detects programming languages and frameworks
- Detects IDEs in use
- Auto-discovers PROJECT.md or PROGETTO.md for context
- Creates all necessary files from templates
- Configures IDE-specific files
- Initializes task management system

Usage:
    python scripts/setup.py                    # Interactive mode
    python scripts/setup.py --auto             # Auto-detect everything
    python scripts/setup.py --project-name "MyProject" --ide windsurf,cursor
    python scripts/setup.py --from-project-file PROJECT.md
"""

import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Handle encoding for Windows terminals
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print colored header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.END}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.END}\n")

def print_success(text: str):
    """Print success message."""
    try:
        print(f"{Colors.GREEN}✅ {text}{Colors.END}")
    except UnicodeEncodeError:
        print(f"{Colors.GREEN}[OK] {text}{Colors.END}")

def print_info(text: str):
    """Print info message."""
    try:
        print(f"{Colors.CYAN}ℹ️  {text}{Colors.END}")
    except UnicodeEncodeError:
        print(f"{Colors.CYAN}[INFO] {text}{Colors.END}")

def print_warning(text: str):
    """Print warning message."""
    try:
        print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")
    except UnicodeEncodeError:
        print(f"{Colors.YELLOW}[WARN] {text}{Colors.END}")

def print_error(text: str):
    """Print error message."""
    try:
        print(f"{Colors.RED}❌ {text}{Colors.END}")
    except UnicodeEncodeError:
        print(f"{Colors.RED}[ERR] {text}{Colors.END}")


class ProjectDetector:
    """Detects project characteristics."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def detect_languages(self) -> Set[str]:
        """Detect programming languages used in project."""
        languages = set()
        
        # Check for common files
        if (self.project_root / "package.json").exists():
            languages.add("javascript")
        if (self.project_root / "requirements.txt").exists() or \
           (self.project_root / "pyproject.toml").exists() or \
           ((self.project_root / "setup.py").exists() and not (self.project_root / "loom").exists()):
            languages.add("python")
        if (self.project_root / "Cargo.toml").exists():
            languages.add("rust")
        if (self.project_root / "go.mod").exists():
            languages.add("go")
        if (self.project_root / "pom.xml").exists() or (self.project_root / "build.gradle").exists():
            languages.add("java")
        if (self.project_root / "Gemfile").exists():
            languages.add("ruby")
        
        # Scan for file extensions
        for ext_map in [
            (".py", "python"),
            (".js", "javascript"),
            (".ts", "typescript"),
            (".rs", "rust"),
            (".go", "go"),
            (".java", "java"),
            (".rb", "ruby"),
            (".php", "php"),
            (".cs", "csharp"),
        ]:
            ext, lang = ext_map
            if any(self.project_root.rglob(f"*{ext}")):
                languages.add(lang)
        
        return languages
    
    def detect_frameworks(self) -> Set[str]:
        """Detect frameworks used in project."""
        frameworks = set()
        
        # Check package.json
        package_json = self.project_root / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    
                    if "react" in deps:
                        frameworks.add("react")
                    if "vue" in deps:
                        frameworks.add("vue")
                    if "@angular/core" in deps:
                        frameworks.add("angular")
                    if "next" in deps:
                        frameworks.add("nextjs")
                    if "express" in deps:
                        frameworks.add("express")
                    if "@nestjs/core" in deps:
                        frameworks.add("nestjs")
            except:
                pass
        
        # Check requirements.txt
        requirements = self.project_root / "requirements.txt"
        if requirements.exists():
            try:
                content = requirements.read_text().lower()
                if "fastapi" in content:
                    frameworks.add("fastapi")
                if "flask" in content:
                    frameworks.add("flask")
                if "django" in content:
                    frameworks.add("django")
            except:
                pass
        
        return frameworks
    
    def detect_ides(self) -> Set[str]:
        """Detect IDEs in use based on config files."""
        ides = set()
        
        if (self.project_root / ".idea").exists():
            ides.add("intellij")
        if (self.project_root / ".vscode").exists():
            ides.add("vscode")
        if (self.project_root / ".cursor" / "rules").exists() or (self.project_root / ".cursorrules").exists():
            ides.add("cursor")
        if (self.project_root / ".windsurf" / "rules").exists() or (self.project_root / ".windsurfrules").exists():
            ides.add("windsurf")
        if (self.project_root / "CLAUDE.md").exists():
            ides.add("claude")
        if (self.project_root / "GEMINI.md").exists():
            ides.add("antigravity")
        if (self.project_root / "AGENTS.md").exists():
            ides.add("agents")
        if (self.project_root / ".github" / "copilot-instructions.md").exists():
            ides.add("vscode")
        
        return ides
    
    def detect_existing_docs(self) -> Set[str]:
        """Detect existing documentation files."""
        docs = set()
        
        docs_dir = self.project_root / "docs"
        if docs_dir.exists():
            if (docs_dir / "TASKS.md").exists():
                docs.add("TASKS.md")
            if (docs_dir / "BACKLOG.md").exists():
                docs.add("BACKLOG.md")
            if (docs_dir / "STORY.md").exists():
                docs.add("STORY.md")
            if (docs_dir / "CHANGELOG.md").exists():
                docs.add("CHANGELOG.md")
            if (docs_dir / "HANDOFF.md").exists():
                docs.add("HANDOFF.md")
        
        return docs

    def detect_project_meta_file(self) -> Optional[Path]:
        """Search for PROJECT.md or PROGETTO.md in root."""
        for name in ["PROJECT.md", "PROGETTO.md"]:
            path = self.project_root / name
            if path.exists():
                return path
        return None


class FrameworkSetup:
    """Sets up the loom."""
    
    def __init__(self, project_root: Path, framework_root: Path):
        self.project_root = project_root
        self.framework_root = framework_root
    
    def create_agent_md(self, project_name: str, languages: Set[str], frameworks: Set[str]):
        """Create AGENT.md from template."""
        template_path = self.framework_root / "templates" / "AGENT.md.template"
        target_path = self.project_root / "AGENT.md"
        
        if target_path.exists():
            print_warning(f"AGENT.md already exists, skipping")
            return
        
        # Read template
        if not template_path.exists():
             # Fallback if template missing
             content = f"# {project_name}\n\nStack: {', '.join(languages | frameworks)}\n"
        else:
             content = template_path.read_text(encoding="utf-8")
        
        # Replace placeholders
        content = content.replace("[NOME_PROGETTO]", project_name)
        content = content.replace("[STACK]", ", ".join(languages | frameworks))
        
        # Write file
        target_path.write_text(content, encoding="utf-8")
        print_success(f"Created AGENT.md")

    def parse_project_md(self, meta_path: Path) -> Dict[str, str]:
        """Parse PROJECT.md and extract key sections."""
        content = meta_path.read_text(encoding="utf-8")

        # Extract project name from first heading
        project_name_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        project_name = project_name_match.group(1) if project_name_match else "Project"

        # Extract Goal section
        goal_match = re.search(r'##\s*(?:Goal|Obiettivo)[^\n]*\n+([^#]+)', content, re.IGNORECASE)
        goal = goal_match.group(1).strip() if goal_match else ""

        # Extract Stack section
        stack_match = re.search(r'##\s*(?:Stack|Tecnologie)[^\n]*\n+([^#]+)', content, re.IGNORECASE)
        stack_raw = stack_match.group(1).strip() if stack_match else ""
        # Convert stack to bullet list
        stack_lines = []
        for line in stack_raw.split('\n'):
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*')):
                stack_lines.append(line)
            elif line and ':' in line:
                # Convert "Key: Value" to "- **Key**: Value"
                parts = line.split(':', 1)
                if len(parts) == 2:
                    stack_lines.append(f"- **{parts[0].strip()}**: {parts[1].strip()}")
        stack = '\n'.join(stack_lines) if stack_lines else stack_raw

        # Extract Architecture section
        arch_match = re.search(r'##\s*(?:Architecture|Architettura)[^\n]*\n+([^#]+)', content, re.IGNORECASE)
        architecture = arch_match.group(1).strip() if arch_match else ""
        # Convert to bullet list
        arch_lines = []
        for line in architecture.split('\n'):
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('*')):
                arch_lines.append(line)
            elif line and line[0].isalnum():
                arch_lines.append(f"- {line}")
        architecture = '\n'.join(arch_lines) if arch_lines else architecture

        # Extract Rules section  
        rules_match = re.search(r'##\s*(?:Rules|Regole)[^\n]*\n+([^#]+)', content, re.IGNORECASE)
        rules = rules_match.group(1).strip() if rules_match else ""

        # Extract Notes section
        notes_match = re.search(r'##\s*(?:Notes|Note)[^\n]*\n+([^#]+)', content, re.IGNORECASE)
        notes = notes_match.group(1).strip() if notes_match else ""

        return {
            "project_name": project_name,
            "goal": goal,
            "stack": stack,
            "architecture": architecture,
            "rules": rules,
            "notes": notes,
        }

    def create_agent_md_from_meta(self, meta_path: Path):
        """
        Create AGENT.md by selectively merging PROJECT.md data into AGENT.md template.
        AGENT.md keeps its structure; only replaces placeholders where PROJECT.md has data.
        """
        target_path = self.project_root / "AGENT.md"

        if target_path.exists():
            print_warning(f"AGENT.md already exists, skipping")
            return

        # Parse PROJECT.md
        project_data = self.parse_project_md(meta_path)

        # Read AGENT.md template
        template_path = self.framework_root / "templates" / "AGENT.md.template"
        if not template_path.exists():
            # Fallback: copy PROJECT.md if template missing
            content = meta_path.read_text(encoding="utf-8")
            target_path.write_text(content, encoding="utf-8")
            print_success(f"Created AGENT.md from {meta_path.name} (template missing)")
            return

        content = template_path.read_text(encoding="utf-8")

        # Only replace if PROJECT.md has meaningful data (not empty/placeholder)
        
        # 1. Project name - always use PROJECT.md title
        if project_data["project_name"] and project_data["project_name"] != "Project":
            content = content.replace("{PROJECT_NAME}", project_data["project_name"])
            content = content.replace("[NOME_PROGETTO]", project_data["project_name"])

        # 2. Goal/Description - only if present in PROJECT.md
        if project_data["goal"] and len(project_data["goal"]) > 10:
            # Replace the placeholder description
            content = content.replace(
                "{Brief description of your project — what problem it solves, who uses it, and why it matters.}",
                project_data["goal"]
            )
            content = content.replace(
                "{Breve descrizione del progetto — quale problema risolve, chi lo usa, perché è importante.}",
                ""
            )

        # 3. Stack - only if PROJECT.md has specific stack info
        if project_data["stack"] and len(project_data["stack"]) > 10:
            # Extract first items as one-line summary for the "Stack" field
            stack_summary = project_data["stack"].split('\n')[0].strip('- *').strip()
            if ':' in stack_summary:
                stack_summary = stack_summary.split(':', 1)[1].strip()
            
            # Replace the inline Stack reference
            content = content.replace(
                "{Language / Framework / Database / Hosting}",
                stack_summary[:80]
            )
            content = content.replace(
                "{e.g., Python 3.11, TypeScript 5.0, Rust}",
                project_data["goal"].split('\n')[0].strip()[:50] if project_data["goal"] else "[Language]"
            )

        # 4. Architecture - only if present in PROJECT.md
        if project_data["architecture"] and len(project_data["architecture"]) > 10:
            # Take first line as principle
            arch_lines = [l.strip('- *') for l in project_data["architecture"].split('\n') if l.strip()]
            if arch_lines:
                principle = arch_lines[0][:150]
                content = content.replace(
                    '{Your core architectural principle — e.g., "Business logic in services, not controllers"}',
                    principle
                )
                content = content.replace(
                    '{Il tuo principio architetturale — es: "Logica di business nei servizi, non nei controller"}',
                    ""
                )

        # 5. Rules - AGENT.md keeps its default rules, PROJECT.md rules are optional extra
        # Don't replace entire section, just append if needed

        # 6. Notes - append to existing Notes section if present in PROJECT.md
        if project_data["notes"] and len(project_data["notes"]) > 10:
            # Find the Notes section and append project-specific notes
            notes_match = re.search(r'(##\s*Notes.*?\n)(.*?)(?=##|$)', content, re.DOTALL | re.IGNORECASE)
            if notes_match:
                existing_notes = notes_match.group(2)
                new_notes = f"\n### From PROJECT.md\n{project_data['notes']}\n"
                content = content.replace(existing_notes, existing_notes + new_notes)

        # Remove remaining placeholder instructions (the {text} patterns)
        content = re.sub(r'\{[^}]+\}', '', content)

        target_path.write_text(content, encoding="utf-8")
        print_success(f"Created AGENT.md (merged template with {meta_path.name} data)")
    
    def setup_ide_config(self, ide: str):
        """Setup IDE-specific configuration."""
        ide_map = {
            "windsurf": (".windsurfrules", "ide-configs/windsurf/windsurfrules.template"),
            "claude": ("CLAUDE.md", "ide-configs/claude/CLAUDE.md.template"),
            "cursor": (".cursorrules", "ide-configs/cursor/cursorrules.template"),
            "antigravity": ("GEMINI.md", "ide-configs/antigravity/GEMINI.md.template"),
            "agents": ("AGENTS.md", "ide-configs/antigravity/AGENTS.md.template"),
            "vscode": (".github/copilot-instructions.md", "ide-configs/vscode/copilot-instructions.md.template"),
            "intellij": (".aiassistant/rules/loom.md", "ide-configs/intellij/LOOM.md.template"),
        }
        
        if ide not in ide_map:
            print_warning(f"Unknown IDE: {ide}")
            return
        
        target_file, template_file = ide_map[ide]
        target_path = self.project_root / target_file
        template_path = self.framework_root / template_file
        
        if not template_path.exists():
            print_warning(f"Template not found: {template_path}")
            return
        
        if target_path.exists():
            print_warning(f"{target_file} already exists, skipping")
            return
        
        # Create parent directory if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy template
        shutil.copy2(template_path, target_path)
        print_success(f"Created {target_file}")
        
        # For cursor: also generate modern .cursor/rules/loom.mdc
        if ide == "cursor":
            modern_path = self.project_root / ".cursor" / "rules" / "loom.mdc"
            modern_template = self.framework_root / "ide-configs/cursor/rules/loom.mdc"
            if modern_template.exists() and not modern_path.exists():
                modern_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(modern_template, modern_path)
                print_success(f"Created .cursor/rules/loom.mdc (modern format)")
        
        # For windsurf: also generate modern .windsurf/rules/loom.md
        if ide == "windsurf":
            modern_path = self.project_root / ".windsurf" / "rules" / "loom.md"
            modern_template = self.framework_root / "ide-configs/windsurf/rules/loom.md"
            if modern_template.exists() and not modern_path.exists():
                modern_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(modern_template, modern_path)
                print_success(f"Created .windsurf/rules/loom.md (modern format)")
    
    def extract_tasks_from_project(self, project_path: Path) -> List[Tuple[str, str, str]]:
        """
        Extract tasks from PROJECT.md content.
        Returns list of (task_id, description, priority) tuples.
        """
        content = project_path.read_text(encoding="utf-8")
        tasks = []

        # Pattern 1: Markdown checkboxes with task IDs: - [ ] TASK-001: Description
        checkbox_pattern = r'- \[ \]\s*([A-Z]+-\d+)[:\s]+([^\n]+)'
        for match in re.finditer(checkbox_pattern, content):
            task_id = match.group(1)
            description = match.group(2).strip()
            tasks.append((task_id, description, "Media"))

        # Pattern 2: Numbered lists with task IDs: 1. TASK-001: Description
        numbered_pattern = r'\d+\.\s*([A-Z]+-\d+)[:\s]+([^\n]+)'
        for match in re.finditer(numbered_pattern, content):
            task_id = match.group(1)
            description = match.group(2).strip()
            if not any(t[0] == task_id for t in tasks):
                tasks.append((task_id, description, "Media"))

        # Pattern 3: Phase/Sprint sections with numbered tasks
        phase_pattern = r'##?\s*(?:Fase|Phase|Sprint|Task)[\s:]+(\d+|\w+)[^\n]*\n([^#]*?)(?=##|\Z)'
        for match in re.finditer(phase_pattern, content, re.DOTALL):
            phase_num = match.group(1)
            phase_content = match.group(2)
            # Look for list items in phase content
            list_pattern = r'[-*]\s*([^\n]+)'
            for i, list_match in enumerate(re.finditer(list_pattern, phase_content), 1):
                description = list_match.group(1).strip()
                if description and len(description) > 5:
                    task_id = f"TASK-{phase_num}-{i:03d}"
                    if not any(t[0] == task_id for t in tasks):
                        tasks.append((task_id, description, "Media"))

        return tasks

    def import_tasks_to_tasks_md(self, tasks: List[Tuple[str, str, str]], auto: bool = False):
        """Import extracted tasks into TASKS.md."""
        tasks_file = self.project_root / "docs" / "TASKS.md"

        if not tasks_file.exists():
            print_warning("TASKS.md not found, skipping task import")
            return

        if not tasks:
            return

        # In auto mode, ask user; in interactive mode, ask interactively
        if auto:
            print_info(f"\n📋 Found {len(tasks)} potential tasks in PROJECT.md:")
            for task_id, desc, _ in tasks[:10]:
                print(f"  • {task_id}: {desc[:60]}{'...' if len(desc) > 60 else ''}")
            if len(tasks) > 10:
                print(f"  ... and {len(tasks) - 10} more")

            # In auto mode, we import all tasks by default
            response = "y"
        else:
            print(f"\n{Colors.CYAN}📋 Found {len(tasks)} potential tasks in PROJECT.md{Colors.END}")
            for task_id, desc, _ in tasks[:5]:
                print(f"  • {task_id}: {desc[:50]}{'...' if len(desc) > 50 else ''}")
            if len(tasks) > 5:
                print(f"  ... and {len(tasks) - 5} more")
            response = input(f"{Colors.CYAN}Import these tasks to TASKS.md? (y/n): {Colors.END}").strip().lower()

        if response not in ("y", "yes", "s", "si", "sì"):
            print_info("Skipping task import")
            return

        # Read current TASKS.md
        content = tasks_file.read_text(encoding="utf-8")

        # Find "Lavoro in Corso" section
        import re
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        new_tasks_section = ""

        for task_id, description, priority in tasks:
            # Check if task already exists
            if task_id in content:
                continue

            new_task = f"""### {task_id} — {description}

**Status:** Not Started
**Priorità:** {priority}
**Creato:** {today}

---

"""
            new_tasks_section += new_task

        if new_tasks_section:
            # Insert after "## 🚀 Lavoro in Corso" section header
            pattern = r'(## 🚀 Lavoro in Corso\n)'
            if re.search(pattern, content):
                updated_content = re.sub(pattern, rf'\1{new_tasks_section}', content)
                tasks_file.write_text(updated_content, encoding="utf-8")
                print_success(f"Imported {len(tasks)} tasks to TASKS.md")
            else:
                print_warning("Could not find 'Lavoro in Corso' section in TASKS.md")
        else:
            print_info("All tasks already exist in TASKS.md")

    def init_docs(self):
        """Initialize documentation files."""
        docs_dir = self.project_root / "docs"
        docs_dir.mkdir(exist_ok=True)

        templates = [
            "TASKS.md",
            "BACKLOG.md",
            "STORY.md",
            "CHANGELOG.md",
            "HANDOFF.md",
        ]

        for template_name in templates:
            target_path = docs_dir / template_name
            template_path = self.framework_root / "templates" / "docs" / template_name

            if target_path.exists():
                print_warning(f"docs/{template_name} already exists, skipping")
                continue

            if not template_path.exists():
                print_warning(f"Template not found: {template_path}")
                continue

            shutil.copy2(template_path, target_path)
            print_success(f"Created docs/{template_name}")


def interactive_setup():
    """Run interactive setup wizard."""
    print_header("loom Setup Wizard")
    
    # Detect project root
    project_root = Path.cwd()
    framework_root = Path(__file__).parent.parent
    
    print_info(f"Project root: {project_root}")
    print_info(f"Framework root: {framework_root}")
    
    # Detect project characteristics
    print_header("Detecting Project")
    detector = ProjectDetector(project_root)
    
    languages = detector.detect_languages()
    frameworks = detector.detect_frameworks()
    ides = detector.detect_ides()
    existing_docs = detector.detect_existing_docs()
    
    print_info(f"Languages detected: {', '.join(languages) if languages else 'None'}")
    print_info(f"Frameworks detected: {', '.join(frameworks) if frameworks else 'None'}")
    print_info(f"IDEs detected: {', '.join(ides) if ides else 'None'}")
    print_info(f"Existing docs: {', '.join(existing_docs) if existing_docs else 'None'}")
    
    # Ask for project name
    print_header("Project Configuration")
    project_name = input(f"{Colors.CYAN}Project name: {Colors.END}").strip()
    if not project_name:
        project_name = project_root.name
        print_info(f"Using directory name: {project_name}")
    
    # Ask for IDEs to configure
    print(f"\n{Colors.CYAN}Which IDEs do you want to configure?{Colors.END}")
    print("1. Windsurf")
    print("2. Claude Code")
    print("3. Cursor")
    print("4. Antigravity (GEMINI.md)")
    print("5. VS Code / VS Code Insider (GitHub Copilot)")
    print("6. IntelliJ IDEA (AI Assistant)")
    print("7. AGENTS.md (cross-tool: Antigravity + Windsurf + VS Code + Insider)")
    print("8. All")
    
    ide_choice = input(f"{Colors.CYAN}Enter numbers (comma-separated, e.g., 1,3,7): {Colors.END}").strip()
    
    ide_map = {
        "1": "windsurf",
        "2": "claude",
        "3": "cursor",
        "4": "antigravity",
        "5": "vscode",
        "6": "intellij",
        "7": "agents",
        "8": "all",
    }
    
    selected_ides = set()
    if "8" in ide_choice:
        selected_ides = {"windsurf", "claude", "cursor", "antigravity", "vscode", "intellij", "agents"}
    else:
        for num in ide_choice.split(","):
            num = num.strip()
            if num in ide_map:
                selected_ides.add(ide_map[num])
    
    # Setup
    print_header("Setting Up Framework")
    setup = FrameworkSetup(project_root, framework_root)
    
    # Create AGENT.md
    setup.create_agent_md(project_name, languages, frameworks)
    
    # Setup IDE configs
    for ide in selected_ides:
        setup.setup_ide_config(ide)
    
    # Initialize docs
    setup.init_docs()

    # Check for PROJECT.md and offer to import tasks
    meta_file = detector.detect_project_meta_file()
    if meta_file:
        tasks = setup.extract_tasks_from_project(meta_file)
        if tasks:
            setup.import_tasks_to_tasks_md(tasks, auto=False)

    # Success
    print_header("Setup Complete!")
    print_success("loom configured successfully!")
    print_info("\nNext steps:")
    print(f"  1. Review and customize {Colors.BOLD}AGENT.md{Colors.END}")
    print(f"  2. Start your first task: {Colors.BOLD}python loom/scripts/task.py start TASK-001 'Setup complete'{Colors.END}")
    print(f"  3. Read {Colors.BOLD}QUICKSTART.md{Colors.END} for more info")


def auto_setup(project_name: Optional[str] = None, ides: Optional[List[str]] = None, project_file: Optional[str] = None):
    """Run automatic setup without interaction."""
    print_header("loom Auto Setup")
    
    # Detect project root
    project_root = Path.cwd()
    framework_root = Path(__file__).parent.parent
    
    # Detect project characteristics
    detector = ProjectDetector(project_root)
    languages = detector.detect_languages()
    frameworks = detector.detect_frameworks()
    detected_ides = detector.detect_ides()
    
    # Use detected or provided values
    if not project_name:
        project_name = project_root.name
    
    if not ides:
        ides = list(detected_ides) if detected_ides else ["windsurf", "cursor", "agents"]
    
    print_info(f"Project: {project_name}")
    print_info(f"Languages: {', '.join(languages)}")
    print_info(f"Frameworks: {', '.join(frameworks)}")
    print_info(f"IDEs: {', '.join(ides)}")
    
    # Setup
    setup = FrameworkSetup(project_root, framework_root)
    
    if project_file:
        setup.create_agent_md_from_meta(Path(project_file))
    else:
        meta_file = detector.detect_project_meta_file()
        if meta_file:
            setup.create_agent_md_from_meta(meta_file)
        else:
            setup.create_agent_md(project_name, languages, frameworks)
    
    for ide in ides:
        setup.setup_ide_config(ide)

    setup.init_docs()

    # Extract and import tasks from PROJECT.md if available
    project_file_path = Path(project_file) if project_file else detector.detect_project_meta_file()
    if project_file_path:
        tasks = setup.extract_tasks_from_project(project_file_path)
        if tasks:
            setup.import_tasks_to_tasks_md(tasks, auto=True)

    print_success("Auto setup complete!")


def main():
    parser = argparse.ArgumentParser(description="loom Setup Wizard")
    parser.add_argument("--auto", action="store_true", help="Auto-detect and setup without interaction")
    parser.add_argument("--project-name", help="Project name")
    parser.add_argument("--ide", help="IDEs to configure (comma-separated)")
    parser.add_argument("--from-project-file", help="Path to PROJECT.md or PROGETTO.md")
    
    args = parser.parse_args()
    
    try:
        if args.auto:
            ides = args.ide.split(",") if args.ide else None
            auto_setup(args.project_name, ides, args.from_project_file)
        else:
            interactive_setup()
    except KeyboardInterrupt:
        print_error("\n\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nSetup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
