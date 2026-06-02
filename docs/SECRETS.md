# Secrets Guide

This document explains how to rotate a leaked Google API key, purge it from Git history, and store the new key securely for deployment.

## 1. Rotate / Revoke the compromised key (Google Cloud)
Preferred: use the Google Cloud Console:
- Console → APIs & Services → Credentials → find the API key → Delete or Restrict.

CLI (gcloud):
```bash
# List API keys
gcloud services api-keys list

# Delete a key (replace KEY_ID with the numeric id)
gcloud services api-keys delete KEY_ID

# Create a new key
gcloud services api-keys create --display-name="talentlens-prod-key"
```

After creating, restrict the key immediately (HTTP referrers, IPs, allowed APIs).

## 2. Store the new key securely
Recommended options:
- Google Secret Manager
- GitHub/GitLab/Bitbucket Actions secrets
- Cloud provider secret manager
- HashiCorp Vault

Example: Google Secret Manager
```bash
# create secret and add value
gcloud secrets create google-api-key --replication-policy="automatic"
echo -n "NEW_KEY" | gcloud secrets versions add google-api-key --data-file=-
```

## 3. Use secrets in GitHub Actions (example)
Add `GOOGLE_API_KEY` as a repository secret.

`.github/workflows/deploy.yml` will read it:
```yaml
name: Deploy
on: workflow_dispatch
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy with env
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: |
          echo "Starting deploy"
          # use your deployment commands here
```

## 4. Purge the key from Git history (local step)
### Using `git filter-repo` (recommended)
1. Install: `pip install git-filter-repo`
2. Backup branch:
```bash
git branch backup-before-purge
```
3. Create a `replacements.txt` file with the secret on the left and `REDACTED` on the right (see git-filter-repo docs) or run the replace-text inline:
```bash
git filter-repo --replace-text replacements.txt
```
4. Force-push (coordinate with team):
```bash
git push --force --all
git push --force --tags
```

### Using BFG (alternative)
Refer to https://rtyley.github.io/bfg-repo-cleaner/ for examples.

## 5. Audit
- Check Google Cloud usage logs and revoke any tokens if misuse detected.
- Rotate any other secrets that may have been exposed.

## 6. Local development
- Put secrets only in local `.env.development` (already in `.gitignore`).

## 7. If you want me to help
I cannot rotate keys or run `git filter-repo` in your environment; I can:
- Provide the exact commands and scripts (below) for you to run locally or on a CI runner.
- Add a GitHub Actions template to deploy using a repo secret.
- Add scripts to automate the purge locally.

