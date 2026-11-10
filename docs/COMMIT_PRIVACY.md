# Git commit email privacy

## What is and is not protected

Git author and committer email strings are part of **commit metadata**, separate from file contents. Removing a private email from README, CSV or current Git configuration **does not remove it from past public commits**. Existing history must not be claimed sanitized unless the public Git objects have been reviewed after a carefully authorized history migration.

## Prevent disclosure on future commits

1. In GitHub **Settings → Emails**, enable **Keep my email addresses private** and **Block command line pushes that expose my email** (if available). Copy the account's exact GitHub-provided `...@users.noreply.github.com` address; do not invent an ID or email.
2. On a local clone, use `git config --local user.email "YOUR_GITHUB_NOREPLY_ADDRESS"` and an appropriate `user.name`. Check with `git config --local --get user.email`.
3. Before publication, inspect `git log --format='%h %an <%ae> | %cn <%ce>'` and `git show -s --format=fuller HEAD` to confirm **both author and committer** fields. CI bots and commits created via GitHub integrations can have different attribution; review them too.
4. Never add personal email addresses, private source spreadsheets, EXW costs, inventory, rebates, secrets or unpublished correspondence to this public repository. A `.gitignore` file alone is **not** a history privacy audit.

## Existing publicly exposed metadata: unresolved until independently rechecked

Prior Phase 1 review identified personal email information in published commit author metadata. This documentation change **does not cure that exposure**, and this branch does **not** rewrite previously published commits. The original objects may remain accessible by SHA, in forks, caches and third-party clones even after rewriting branch references.

For historical remediation, repository owner approval and coordinated maintainer handling are required: enumerate all refs/tags, back up safely, select pseudonymous author and committer information, rewrite the affected commits using a tool such as `git filter-repo`, publish replacement refs with a controlled force-with-lease process, prevent reintroduction from old clones, and ask GitHub Support about removal of cached sensitive data where appropriate. Coordinate with collaborators because hashes and outstanding PRs change. **Do not force-push or declare the history clean without explicit authorization and a fresh audit.**

This is a checklist, not evidence that account settings have been changed or historic email addresses erased.
