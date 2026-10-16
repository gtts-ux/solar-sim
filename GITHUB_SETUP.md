# Publish Solar Sim

This is a separate copy prepared for GitHub. The original Desktop `solar sim` folder is unchanged. The app does not need GitHub credentials to run.

## Upload the repository

The easiest route uses GitHub Desktop: sign in, choose **File → Add local repository**, select this folder, review and commit the files, then choose **Publish repository**. Name it **solar-sim** (or another name) and select the visibility you want. Desktop creates the repository for you.

Alternatively, create an empty repository on GitHub first. Leave the automatic README, license and gitignore options unchecked because this folder already contains the project files. Open Terminal in this folder and use Git. Replace `YOUR_USERNAME` and `YOUR_REPOSITORY` with your actual values:

```sh
git add .
git commit -m "Prepare Solar Sim for distribution"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

This prepared local folder already has a Git repository on branch `main`. If you are using an extracted ZIP instead, run `git init -b main` first. Git may ask you to configure a commit name and email. Authentication is handled by GitHub Desktop, GitHub CLI or your Git credential manager; no token belongs in project files.

The repository name and account have deliberately not been hardcoded into download links. README links work with any repository name. Select a project license through GitHub's **Add file → Create new file → LICENSE → Choose a license template** when you decide the reuse terms; no license has been assigned in this copy.

## Give people an easy download

People can immediately use **Code → Download ZIP**, extract it and follow README.md. To offer a clearly named release download:

1. Update `VERSION.txt` for each release. The first prepared version is `1.0.0`.
2. Push that change to `main`. The **Release ZIP** workflow runs automatically when `VERSION.txt` or its workflow file changes.
3. The workflow tests and packages the project, creates the corresponding release (for example `v1.0.0`), attaches `solar-sim.zip` and `solar-sim.zip.sha256`, then publishes it. If the workflow fails, its Actions log explains the error; the release is published only after the assets are uploaded.
4. You can also start **Release ZIP** manually from the Actions tab. Publishing a release through GitHub still triggers attachment of the matching version's ZIP and checksum.
5. Share your repository's Releases page. After the asset is attached, a direct latest-release link has this form:

```text
https://github.com/YOUR_USERNAME/YOUR_REPOSITORY/releases/latest/download/solar-sim.zip
```

Python 3.10+ must already be installed by the person downloading. The ZIP is a portable source package, not an installer or a bundled Python executable. macOS/Linux support full-screen animation; the Windows launcher intentionally opens the supported text interface.

## Manual ZIP option

The initial tested ZIP is also supplied separately on the Desktop. To rebuild it after changes:

```sh
python3 -m unittest -v
python3 tools/build_release.py
```

Upload `dist/solar-sim.zip` and `dist/solar-sim.zip.sha256` as release assets if you prefer manual releases or GitHub Actions is disabled. Rebuilding replaces those generated files. The local build does not contact GitHub, publish anything or need third-party packages.

The release includes code, guides, launchers, tests and workflows. It omits `.git`, `__pycache__`, exports, ephemeris caches and personal Desktop files. The original `solar sim` folder remains your existing working app; further changes there will not automatically update this separate GitHub copy.

GitHub references: [downloading ZIP archives](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives), [release workflow events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#release), [attaching release assets](https://cli.github.com/manual/gh_release_upload).
