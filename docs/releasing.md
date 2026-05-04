The release process
===

Once a release is ready, all you have to do is create a GitHub Release and tag from the GitHub Web UI. 

1. Go to your GitHub repository's **Releases** page and click **Draft a new release**.
2. Create a new tag (e.g., `v1.0.1`) matching the version you want to release.
3. Click **Generate release notes** to automatically generate the changelog.
4. Click **Publish release**.

Once the release is published, it will kick off the `.github/workflows/release.yml` GitHub Action. This workflow will do all the work for you to get a new release out:
- It compiles the project for your ESP8266 board.
- It attaches the compiled binaries (`HTGDO-${{ latest-tag }}.bin`) to your GitHub Release.
- It automatically updates `docs/manifest.json` with the absolute GitHub Release download URLs and commits the changes back to the repository.

Because `manifest.json` is updated and committed automatically, the web flasher page will instantly point to the latest firmware release. You do not need to manually commit any `.bin` files to the repository, keeping the repository size small.

Releases tags should follow semantic versioning, e.g., `v1.0.1`.
