# GitHub Repository Setup Guide

This guide explains how to publish the PriAge project to GitHub at https://github.com/PPICKO

---

## Before You Start

### Important: Model Files
The YOLO model files (`my_model.pt` and `holog_best.pt`) are **56MB total** and **should NOT** be committed to GitHub directly.

**Options:**
1. **Git LFS (Large File Storage)** - Recommended
2. **External hosting** - Google Drive, Dropbox, etc.
3. **Release attachments** - Upload as GitHub release assets

---

## Step 1: Initialize Git Repository

```bash
cd PriAge_GitHub

# Initialize git
git init

# Add all files (models excluded by .gitignore)
git add .

# Initial commit
git commit -m "Initial commit: PriAge v1.0 - Privacy-Preserving Age Verification"
```

---

## Step 2: Create GitHub Repository

1. Go to https://github.com/PPICKO
2. Click "New Repository"
3. Repository name: `PriAge`
4. Description: `Privacy-Preserving Age Verification System - GDPR Compliant`
5. **Public** or **Private** (your choice)
6. **DO NOT** initialize with README (we already have one)
7. Click "Create repository"

---

## Step 3: Connect and Push

```bash
# Add remote
git remote add origin https://github.com/PPICKO/PriAge.git

# Verify remote
git remote -v

# Push to GitHub
git push -u origin main
```

If using `master` branch instead:
```bash
git branch -M main
git push -u origin main
```

---

## Step 4: Handle Model Files

### Option A: Git LFS (Recommended)

```bash
# Install Git LFS
# Windows: Download from https://git-lfs.github.com
# Linux: sudo apt-get install git-lfs
# Mac: brew install git-lfs

# Initialize LFS
git lfs install

# Track model files
git lfs track "*.pt"

# Add .gitattributes
git add .gitattributes

# Now add model files
git add my_model.pt holog_best.pt

# Commit and push
git commit -m "Add: YOLO model files via Git LFS"
git push
```

### Option B: External Hosting

1. Upload models to Google Drive/Dropbox
2. Get shareable links
3. Update README.md with download links:

```markdown
### Download Models

- [my_model.pt (50MB)](https://drive.google.com/file/d/YOUR_LINK)
- [holog_best.pt (6MB)](https://drive.google.com/file/d/YOUR_LINK)
```

4. Commit README update:
```bash
git add README.md
git commit -m "Add: Model download links"
git push
```

### Option C: GitHub Releases

1. Go to repository page
2. Click "Releases" → "Create a new release"
3. Tag: `v1.0`
4. Title: `PriAge v1.0 - Initial Release`
5. Upload `my_model.pt` and `holog_best.pt`
6. Publish release

---

## Step 5: Repository Settings

### Topics (Tags)
Add these topics to help others find your project:
- `age-verification`
- `gdpr-compliance`
- `privacy`
- `facial-recognition`
- `yolo`
- `deep-learning`
- `pytorch`
- `computer-vision`

Go to: Repository → About → Settings (gear icon) → Topics

### Description
`Privacy-Preserving Age Verification System with GDPR compliance, featuring hologram detection, OCR, facial recognition, and secure data deletion.`

### GitHub Pages (Optional)
Enable GitHub Pages to host documentation:
1. Settings → Pages
2. Source: Deploy from branch `main`
3. Folder: `/docs` or `root`

---

## Step 6: Add Badges to README

Your README already has badges, but verify they work:
- Python version badge
- License badge
- GDPR compliance badge
- Status badge

---

## Step 7: Create Initial Release

```bash
# Tag the release
git tag -a v1.0 -m "PriAge v1.0 - Initial Release"

# Push tags
git push origin v1.0
```

Then on GitHub:
1. Go to Releases → Draft a new release
2. Choose tag: `v1.0`
3. Release title: `v1.0 - Initial Release`
4. Description:
```markdown
## PriAge v1.0 - Initial Release

Privacy-Preserving Age Verification System

### Features
- 5-phase verification pipeline
- GDPR compliant (full data deletion)
- AES-256-GCM encryption
- Anti-spoofing protection
- GUI and CLI interfaces

### Model Files
Due to size, model files are distributed separately:
- my_model.pt (50MB) - YOLO ID detection
- holog_best.pt (6MB) - YOLO hologram detection

Contact repository owner for model access.

### Installation
See [INSTALL.txt](INSTALL.txt) for setup instructions.
```

5. **Attach model files** (if using this option)
6. Publish release

---

## Step 8: Additional Files (Optional)

### Issue Templates
Create `.github/ISSUE_TEMPLATE/bug_report.md`:
```markdown
---
name: Bug report
about: Report a bug
---

**Describe the bug**
A clear description of the bug.

**To Reproduce**
Steps to reproduce the behavior.

**Expected behavior**
What you expected to happen.

**System Info**
- OS: [e.g. Windows 10]
- Python version: [e.g. 3.10]
- PriAge version: [e.g. 1.0]
```

### Pull Request Template
Create `.github/pull_request_template.md`:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Tested locally
- [ ] All tests pass
- [ ] Documentation updated
```

---

## Verification Checklist

Before going public, verify:

- [ ] All files committed
- [ ] .gitignore excludes personal data
- [ ] Model files handled (LFS or external)
- [ ] README.md complete
- [ ] LICENSE included (MIT)
- [ ] CONTRIBUTING.md present
- [ ] GDPR documentation included
- [ ] No sensitive data in repository
- [ ] All links work
- [ ] Requirements.txt up to date

---

## Git Commands Reference

```bash
# Check status
git status

# View changes
git diff

# Add specific files
git add filename.py

# Add all changes
git add .

# Commit
git commit -m "message"

# Push
git push

# Pull latest
git pull

# Create branch
git checkout -b feature-name

# Switch branch
git checkout main

# View history
git log --oneline
```

---

## Maintenance

### Regular Updates

```bash
# Make changes
git add .
git commit -m "Update: description"
git push
```

### Version Tagging

```bash
# For new versions
git tag -a v1.1 -m "Version 1.1 - Description"
git push origin v1.1
```

---

## Support

For issues with GitHub setup:
- [GitHub Docs](https://docs.github.com)
- [Git LFS Docs](https://git-lfs.github.com)

---

## Current Status

Repository ready for:
- Git initialization
- GitHub push
- Model file distribution
- Public release

---

**Last Updated:** March 22, 2026
