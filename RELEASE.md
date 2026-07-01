# Release Process (sampler-cli)

## Current status (as of 2026-07-01)
- Version: 0.2.0
- Artifacts ready in `dist/`
- Full clean install + demo flow verified
- GitHub publish workflow ready (`.github/workflows/publish.yml`)

## For immediate demo (even before making repo public)

1. Build (if you don't have fresh dist/):
   ```bash
   python -m pip install --upgrade build
   rm -rf dist
   python -m build
   ```

2. Upload to **TestPyPI** (you can do this with a personal API token right now):
   ```bash
   python -m pip install --upgrade twine
   twine upload --repository testpypi dist/*
   ```

3. Test the "released" package:
   ```bash
   python -m venv /tmp/test-sampler
   source /tmp/test-sampler/bin/activate
   pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple sampler-cli
   sampler --version
   # then run the normal demo flow
   deactivate
   rm -rf /tmp/test-sampler
   ```

## When the repo is public

1. Go to https://pypi.org/manage/account/publishing/ and configure **Trusted Publishing** for this repository (environment `pypi`).
2. (Optional but recommended) Do the same on TestPyPI.
3. Create a new GitHub Release with tag `v0.2.0` (or whatever the current version is).
4. The workflow `.github/workflows/publish.yml` will automatically build and publish.

## Checklist before tagging a release
- [ ] All tests green (`pytest -q`)
- [ ] `python -m build` succeeds cleanly
- [ ] Full demo flow works after `pip install` the wheel
- [ ] README and docs reflect the new version
- [ ] CHANGELOG updated
- [ ] No `build/`, `dist/`, or `.egg-info/` in the source tree

## Notes
- We use compact/minimal output by default (big win for LLM context size).
- `build/` and `dist/` must stay in `.gitignore` (they are never published).
