# Village Market v97

Changes:
- App/PWA logo now contains the complete supplied Village Market artwork without cropping.
- Full artwork is letterboxed inside the square app icon so no part of the source image is cut off.
- Admin sign-out/login navigation now uses `/admin`, not `/admin.html`.
- PWA service-worker cache version bumped so updated icons are picked up after redeployment.

After deployment, uninstall the old installed PWA and reinstall it to force Android to refresh the icon.
