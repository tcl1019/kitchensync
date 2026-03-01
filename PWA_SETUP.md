# PantryPal Progressive Web App (PWA) Setup

This document describes the PWA features added to PantryPal, allowing it to be installed on iOS and Android devices.

## What is a PWA?

A Progressive Web App (PWA) is a web application that provides a native app-like experience. PantryPal can now be:
- Installed on iPhones via "Add to Home Screen"
- Installed on Android devices via the install prompt
- Used offline with cached content
- Added to the home screen with a custom icon and splash screen

## Files Added/Modified

### New PWA Files

#### 1. `/static/manifest.json`
The Web App Manifest file that defines PWA metadata:
- **name**: "PantryPal" - Full application name
- **short_name**: "PantryPal" - Short name for home screen
- **description**: "Kitchen inventory & AI recipe suggestions"
- **start_url**: "/" - Entry point when installed
- **display**: "standalone" - Full-screen app experience
- **theme_color**: "#2d6a4f" - Kitchen green theme
- **background_color**: "#ffffff" - White background
- **icons**: Multiple SVG and PNG icons (192x192 and 512x512)
- **orientation**: "any" - Works in any orientation
- **scope**: "/" - Available on entire domain

#### 2. `/static/sw.js`
Service Worker for offline support and caching:
- **Install**: Caches core static assets on first visit
- **Cache Strategies**:
  - **Cache-First**: Static assets (CSS, JS, fonts, images)
  - **Network-First**: HTML pages and API calls
  - **Fallback**: Offline page when unable to fetch
- **Activation**: Cleans up old cache versions
- **Version Management**: Uses CACHE_VERSION variable for easy updates

#### 3. `/static/icons/icon-192.svg`
Small app icon (192x192px):
- Green circle background (#2d6a4f)
- Simple white pantry shelf design
- Used on home screen and app launcher

#### 4. `/static/icons/icon-512.svg`
Large app icon (512x512px):
- Green circle background (#2d6a4f)
- Detailed pantry shelf with colorful containers
- Used in the app store and installation dialogs

#### 5. `/static/offline.html`
Offline fallback page:
- User-friendly offline notification
- Retry button for connection
- Clean design matching app theme

### Modified Files

#### 1. `/templates/base.html`
Added PWA meta tags to `<head>`:
```html
<!-- PWA Meta Tags -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="PantryPal">
<meta name="theme-color" content="#2d6a4f">

<!-- PWA Manifest -->
<link rel="manifest" href="/static/manifest.json">

<!-- Apple Touch Icon -->
<link rel="apple-touch-icon" href="/static/icons/icon-192.svg">
```

Added service worker registration at end of `<body>`:
```javascript
<script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js')
            .then((registration) => {
                console.log('Service Worker registered successfully:', registration);
            })
            .catch((error) => {
                console.warn('Service Worker registration failed:', error);
            });
    }
</script>
```

Updated viewport meta tag for better mobile support:
```html
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
```

#### 2. `/app.py`
Added two routes for PWA asset serving:
```python
@app.route('/manifest.json')
def manifest():
    """Serve the PWA manifest from the static directory."""
    return app.send_static_file('manifest.json')

@app.route('/offline.html')
def offline():
    """Serve the offline fallback page."""
    return app.send_static_file('offline.html')
```

## How to Use

### On iPhone
1. Open PantryPal in Safari
2. Tap the Share button
3. Scroll down and tap "Add to Home Screen"
4. Enter a name (e.g., "PantryPal")
5. Tap "Add"
6. PantryPal now appears as an app icon on your home screen

**Features on iPhone:**
- App launches in full-screen mode
- Cached content allows offline use
- Custom icon and splash screen
- Appears in the app switcher

### On Android
1. Open PantryPal in Chrome
2. Tap the menu button (three dots)
3. Tap "Install app"
4. Confirm the installation
5. PantryPal appears on your home screen

**Features on Android:**
- Same as iPhone
- Additional install prompt in Chrome
- Push notification support (if implemented)

## Caching Strategy

### What Gets Cached

**On First Visit (Install):**
- HTML pages
- CSS stylesheets
- JavaScript files
- Manifest and offline page

**During Use (Runtime):**
- Images and other static assets
- API responses
- User interactions

### Cache Versioning

To update the cache after changes:
1. Bump the `CACHE_VERSION` in `/static/sw.js`
2. The service worker will automatically delete old caches
3. Users get fresh content on next visit

Example:
```javascript
const CACHE_VERSION = 'v2'; // Change from v1 to v2
```

## Offline Support

When users go offline:
- Cached pages and assets continue to work
- API calls fall back to cached data
- Users see a friendly offline notification if a page wasn't cached
- Service worker automatically retries network requests

### Offline Page
- Shown when a page isn't cached and user is offline
- Provides helpful retry option
- Assures users data is safe

## Browser Support

| Browser | Support |
|---------|---------|
| Safari iOS | Full (PWA capable) |
| Chrome Android | Full (PWA capable) |
| Firefox Android | Full (PWA capable) |
| Edge | Full (PWA capable) |
| Chrome Desktop | Full (PWA capable) |

## Security Considerations

1. **HTTPS Required**: PWAs require HTTPS in production (localhost works for development)
2. **Same-Origin Policy**: Service worker only works for same domain
3. **Secure Cookies**: API calls use standard cookie authentication
4. **No Direct Access**: Users can't access cached API responses outside the app

## Performance Impact

**Positive:**
- Faster load times with caching
- Works offline
- Reduced bandwidth usage
- Better mobile UX

**Neutral:**
- Initial download includes manifest and service worker
- Minimal overhead (< 50KB for full PWA setup)

## Testing the PWA

### Chrome DevTools
1. Open DevTools (F12)
2. Go to Application tab
3. Check "Service Workers" section
4. View "Cache Storage" to see cached assets
5. Use offline mode (Network tab > Offline checkbox)

### Lighthouse Audit
1. Open DevTools
2. Go to Lighthouse tab
3. Run audit for "PWA"
4. Check score and recommendations

## Future Enhancements

Potential PWA features to add:
- Web Push Notifications for recipe ideas
- Background Sync for offline inventory updates
- Share Target API for sharing recipes
- App Shortcuts for quick actions
- Maskable Icons for adaptive icons on Android 12+

## Troubleshooting

### Service Worker Not Registering
- Ensure HTTPS is used (or localhost)
- Check browser console for errors
- Clear browser cache and try again
- Check that `/static/sw.js` is accessible

### App Not Installable
- Verify manifest.json is valid JSON
- Check icons are accessible
- Ensure `display: "standalone"` is set
- Verify `start_url` is correct

### Offline Page Shows Unexpectedly
- Check service worker cache size limits
- Verify network connectivity
- Clear browser cache
- Check browser console for fetch errors

## References

- [Web App Manifest Spec](https://www.w3.org/TR/appmanifest/)
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [PWA Documentation](https://web.dev/progressive-web-apps/)
- [iOS PWA Support](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html)

