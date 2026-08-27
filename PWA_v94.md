# Village Market v94 — PWA Ready

Added:
- Web App Manifest
- 192px and 512px install icons
- Service worker
- Standalone Android display mode
- Theme metadata
- Offline fallback page
- Service worker registration

The service worker does NOT cache API POST/OTP/order requests. Dynamic application actions continue to use the live Railway backend.

Android test:
1. Deploy v94 to Railway.
2. Open the HTTPS Village Market URL in Chrome on Android.
3. Chrome menu > Install app / Add to Home screen.
4. Open Village Market from the new home-screen icon.
5. Verify OTP, crop photos, orders and language switching while online.
