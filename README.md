# Turneat Report Automator

Generate monthly activity PDFs from your git commits. The tool filters commits by author email, optionally assigns hours per project, and uses Google Gemini to summarize work into a structured report (Spanish output by default).

## Requirements

- Python **3.11+**
- [Git](https://git-scm.com/) installed
- Local clones of the repositories you want to report on (absolute paths in config)
- A [Google AI Studio](https://aistudio.google.com/apikey) API key (Gemini)

## Quick start

```bash
git clone <your-repo-url>
cd turneat-report-automator   # or your clone directory name

python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp config.example.json config.json
cp .env.example .env
```

Edit **`config.json`**: set the reporting month/year, your git `author_emails`, repository paths, and projects.

Edit **`.env`**: set your API key:

```env
GOOGLE_API_KEY=your_key_here
```

Find your commit author email:

```bash
git -C /path/to/your/repo log -1 --format='%ae'
```

Run:

```bash
python reporter.py
```

PDFs are written to `reports/`. Debug files (if enabled) go to `debug/`. Each run clears both folders first.

## Configuration

Copy `config.example.json` to `config.json`. Two top-level sections:

### `report_settings`

| Field | Description |
|-------|-------------|
| `month`, `year` | Calendar month to report on |
| `responsible_name` | Shown on the PDF header |
| `author_emails` | **Required.** Only commits where `commit.author.email` matches (case-insensitive) |
| `calendar_timezone` | Timezone for month boundaries (e.g. `America/Mexico_City`) |
| `commit_date_basis` | `committer` (default) or `author` — which git date filters the month |
| `exclude_pr_merge_commits` | Skip typical PR/MR merge commits |
| `exclude_environment_sync_merges` | Skip merges from `development` / `main` into feature branches |
| `report_hours` | `true`: compute and print hours on PDFs; `false`: omit hours entirely |
| `tag_environment` | `true` (default): show environment label on each bullet in the PDF; `false`: plain bullets without labels |
| `env_map` | Maps environment names to branch name patterns (see below) |
| `env_default` | Label when no branch pattern matches (default: `dev`) |
| `total_hours` | Monthly budget when `report_hours` is `true` |
| `gemini_model` | Model for commit summaries |
| `gemini_paraphrase_model` | Model for extra-task paraphrasing |
| `write_ai_debug_file` | Write prompt/context files under `debug/` |

### `projects`

Each project becomes one PDF: `reports/Report_<name>_<month>_<year>.pdf`.

| Field | Description |
|-------|-------------|
| `name` | Project title on the PDF |
| `repos` | List of local repo paths (string) or objects with overrides (see below) |
| `hours` | Optional fixed hours for this project (when `report_hours` is `true`) |
| `extra_tasks` | Optional non-git tasks (`category` + `description`), paraphrased by Gemini |

**Environment mapping** (`env_map`): each key is the tag shown on commits and PDF bullets; each value is a list of branch names to match (case-insensitive, compared to the branch path and its last segment). Order matters: the first matching environment wins, so list higher-priority environments first (e.g. `prod` before `dev`).

```json
"env_default": "dev",
"env_map": {
  "prod": ["main", "master"],
  "stage": ["release"],
  "dev": ["development", "develop", "dev", "test"]
}
```

If `env_map` is omitted, the same structure above is used as the default.

The same mapping is used everywhere: each commit line sent to Gemini is prefixed with `[env]`, the prompt includes the full `env_map` rules, and PDF bullets use those labels when `tag_environment` is `true`.

**Hour assignment** (when `report_hours` is `true`):

- Projects with `hours` use that value.
- Projects without `hours` share the remainder of `total_hours` (after manual assignments), proportional to commit count.

**Repo entry** — either a path string or an object:

```json
"/absolute/path/to/repo"
```

```json
{
  "path": "/absolute/path/to/repo",
  "author_emails": ["other@company.com"],
  "exclude_pr_merge_commits": true
}
```

Per-repo `author_emails` overrides the global list for that repository only.

### Example

```json
{
  "report_settings": {
    "report_hours": true,
    "tag_environment": true,
    "env_default": "dev",
    "env_map": {
      "prod": ["main", "master"],
      "stage": ["release"],
      "dev": ["development", "develop", "dev", "test"]
    },
    "total_hours": 160,
    "month": 3,
    "year": 2026,
    "responsible_name": "Jane Doe",
    "author_emails": ["jane@company.com"],
    "calendar_timezone": "America/Mexico_City",
    "commit_date_basis": "committer",
    "exclude_pr_merge_commits": true,
    "exclude_environment_sync_merges": true,
    "gemini_model": "gemini-2.5-flash",
    "gemini_paraphrase_model": "gemini-2.5-flash",
    "write_ai_debug_file": true
  },
  "projects": [
    {
      "name": "Backend",
      "hours": 100,
      "repos": ["/Users/you/work/backend"],
      "extra_tasks": []
    },
    {
      "name": "Mobile",
      "repos": ["/Users/you/work/mobile-app"],
      "extra_tasks": [
        {
          "category": "Planning",
          "description": "Sprint planning and backlog grooming"
        }
      ]
    }
  ]
}
```

## Customizing AI prompts

Prompts live in `tra/prompts/` as Markdown files. They use `$variable` placeholders (Python `string.Template`):

- `commit_summary.md` — groups commits into report sections
- `extra_tasks_paraphrase.md` — rewrites extra tasks

Edit these files to change tone or rules without changing Python code.

## Output

| Path | Contents |
|------|----------|
| `reports/` | Generated PDFs (cleared each run) |
| `debug/` | Optional Gemini prompts and commit lists (cleared each run) |

## Security

- Never commit `config.json` or `.env` (both are gitignored).
- If an API key was ever pushed to git, revoke it in Google AI Studio and create a new one.

## Project layout

```
reporter.py           # entry point
tra/                  # application package
  prompts/            # editable Gemini prompt templates
config.example.json   # configuration template
.env.example          # API key template
requirements.txt
```

## License

MIT — see [LICENSE](LICENSE).
