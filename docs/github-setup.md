# GitHub handoff

Target repository: [Thanmay-codes/INS-mini-project](https://github.com/Thanmay-codes/INS-mini-project).

The user creates the remote repository and performs authentication/credential-requiring commands. Local initialization/configuration can be prepared here; it does not create the GitHub repository or publish files. No remote contents have been assumed checked.

## Prepared local material

- Package/server starters and dependency files.
- Project plans, future-context notes, team allocation and research audit.
- Ignore rules for the virtual environment, generated secrets/tickets/databases, logs and unreviewed outputs.
- Pull-request and task templates in `.github/`.
- Tracked locations for reviewed paper evidence and manuscript source.

Inspect local state with `git status` and `git remote -v`. Local Git preparation targets branch `main` and remote `origin`; no initial commit or push is implied by the files existing.

## First publication — user runs

For the simplest handoff, create an empty GitHub repository without separately initializing a README, license, or `.gitignore`; these local files provide the initial content. Choose public/private according to your college/team needs. If the remote already contains a commit, reconcile that history before pushing rather than forcing over it.

From this project's root:

```bash
git status --short
git remote -v
git add .
git diff --cached --stat
git diff --cached --name-only
git commit -m "Prepare INS project structure and implementation plan"
git push -u origin main
```

Inspect the staged filenames before committing: `.venv`, `data/private` generated contents, credentials, live tickets, databases, and runtime logs should be absent. If Git asks for your commit author identity, configure it yourself with the name/email you want associated with the repository. Complete any GitHub sign-in in your own terminal; credentials do not belong in chat or project files.

If local Git has not been initialized yet, use these local commands before staging:

```bash
git init -b main
git remote add origin https://github.com/Thanmay-codes/INS-mini-project.git
```

If an `origin` remote already exists, inspect it first. Change it only if its target is wrong. Avoid force pushes or resetting history during the initial handoff.

## Team workflow

After the initial push, add teammates through GitHub and share `docs/team-work.md`. Each teammate uses their own credentials and branch. Use the pull-request template for handoffs. Keep the security/shared-interface branch owned by A and the KDC/runner branch owned by B.

Use the finer [prompt/workflow sequence](workflow/README.md) rather than long-lived role branches: one fresh `work/<task>` branch per prompt from current main, with the starting SHA recorded. Share [the prompt index](prompts/README.md). A01/B00/C01/D01 can begin first; dependent implementation waits for merged gate releases. Each person creates a local virtual environment after clone.

CI can be added when meaningful protocol tests exist. The current project has health-check verification only; do not present an empty pytest directory as a passing security test suite. Select a repository license explicitly before distributing under a named license; none has been assumed.
