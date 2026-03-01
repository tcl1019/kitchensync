# PantryPal PWA - Key Code Snippets

This file contains the key code snippets used in the PWA implementation for quick reference.

## manifest.json - Web App Configuration

```json
{
  "name": "PantryPal",
  "short_name": "PantryPal",
  "description": "Kitchen inventory & AI recipe suggestions",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "any",
  "background_color": "#ffffff",
  "theme_color": "#2d6a4f",
  "icons": [
    {
      "src": "/static/icons/icon-192.svg",
      "sizes": "192x192",
      "type": "image/svg+xml",
      "purpose": "any"
    },
    {
      "src": "/static/icons/icon-512.svg",
      "sizes": "512x512",
      "type": "image/svg+xml",
      "purpose": "any"
    }
  ]
}
```

## Service Worker - Installation Phase

```javascript
const CACHE_VERSION = 'v1';
const CACHE_NAME = `pantrypal-${CACHE_VERSION}`;

const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/pantry.js',
  '/static/js/recipes.js',
  '/static/manifest.json',
  '/offline.html'
];

self.addEventListener('install', (event) => {
  console.log('Service Worker installing...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('Caching static assets');
      return cache.addAll(STATIC_ASSETS).catch((error) => {
        console.warn('Some assets failed to cache:', error);
        return Promise.resolve();
      });
    }).then(() => {
      return self.skipWaiting();
    })
  );
});
```

## Service Worker - Cache-First Strategy (Static Assets)

```javascript
if (request.destination === 'style' ||
    request.destination === 'script' ||
    request.destination === 'font' ||
    request.destination === 'image' ||
    url.pathname.includes('/static/')) {
  event.respondWith(
    caches.match(request).then((cached) => {
      return cached || fetch(request).then((response) => {
        if (response.ok) {
          const cache = caches.open(RUNTIME_CACHE_NAME);
          cache.then((c) => c.put(request, response.clone()));
        }
        return response;
      }).catch(() => {
        return createOfflineFallback(request);
      });
    })
  );
  return;
}
```

## Service Worker - Network-First Strategy (API Calls)

```javascript
if (url.pathname.startsWith('/api/')) {
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const cache = caches.open(API_CACHE_NAME);
          cache.then((c) => c.put(request, response.clone()));
        }
        return response;
      })
      .catch(() => {
        return caches.match(request).then((cached) => {
          return cached || createOfflineResponse();
        });
      })
  );
  return;
}
```

## Service Worker - Cache Cleanup on Activation

```javascript
self.addEventListener('activate', (event) => {
  console.log('Service Worker activating...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && 
              cacheName !== RUNTIME_CACHE_NAME && 
              cacheName !== API_CACHE_NAME) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});
```

## base.html - PWA Meta Tags (in <head>)

```html
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>{% block title %}PantryPal - Household Pantry & Recipe Suggester{% endblock %}</title>

<!-- PWA Meta Tags -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="PantryPal">
<meta name="theme-color" content="#2d6a4f">
<meta name="description" content="Kitchen inventory & AI recipe suggestions">

<!-- PWA Manifest -->
<link rel="manifest" href="/static/manifest.json">

<!-- Apple Touch Icon -->
<link rel="apple-touch-icon" href="/static/icons/icon-192.svg">

<!-- Stylesheets -->
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
```

## base.html - Service Worker Registration (in <body>)

```html
<!-- Service Worker Registration -->
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

## app.py - Manifest Route

```python
@app.route('/manifest.json')
def manifest():
    """Serve the PWA manifest from the static directory."""
    return app.send_static_file('manifest.json')
```

## app.py - Offline Route

```python
@app.route('/offline.html')
def offline():
    """Serve the offline fallback page."""
    return app.send_static_file('offline.html')
```

## SVG Icon - 192x192 (icon-192.svg)

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
  <!-- Background circle -->
  <circle cx="96" cy="96" r="96" fill="#2d6a4f"/>
  
  <!-- Kitchen shelf/pantry icon -->
  <!-- Left vertical support -->
  <rect x="40" y="55" width="8" height="82" fill="#ffffff" rx="2"/>
  
  <!-- Right vertical support -->
  <rect x="144" y="55" width="8" height="82" fill="#ffffff" rx="2"/>
  
  <!-- Top shelf -->
  <rect x="40" y="65" width="112" height="10" fill="#ffffff" rx="2"/>
  
  <!-- Middle shelf -->
  <rect x="40" y="100" width="112" height="10" fill="#ffffff" rx="2"/>
  
  <!-- Bottom shelf -->
  <rect x="40" y="135" width="112" height="10" fill="#ffffff" rx="2"/>
  
  <!-- Items on shelves (simple shapes representing containers) -->
  <circle cx="62" cy="70" r="8" fill="#a8dadc"/>
  <circle cx="96" cy="70" r="8" fill="#f4a261"/>
  <circle cx="130" cy="70" r="8" fill="#e76f51"/>
  <!-- ... more items ... -->
</svg>
```

## offline.html - Offline Fallback Page

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PantryPal - Offline</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #2d6a4f 0%, #40916c 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            text-align: center;
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            max-width: 400px;
        }
        
        h1 {
            color: #2d6a4f;
            margin-bottom: 10px;
            font-size: 28px;
        }
        
        p {
            color: #666;
            margin-bottom: 20px;
            line-height: 1.6;
        }
        
        .button {
            display: inline-block;
            padding: 12px 30px;
            background-color: #2d6a4f;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            transition: background-color 0.3s;
            border: none;
            cursor: pointer;
        }
        
        .button:hover {
            background-color: #1b4332;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📡</div>
        <h1>You're Offline</h1>
        <p>PantryPal is currently offline. Please check your internet connection and try again.</p>
        <button class="button" onclick="location.reload()">Retry Connection</button>
    </div>
</body>
</html>
```

## Updating Cache Version

To trigger a cache update for all users, modify the version number in `/static/sw.js`:

```javascript
// Before:
const CACHE_VERSION = 'v1';
const CACHE_NAME = `pantrypal-${CACHE_VERSION}`;

// After:
const CACHE_VERSION = 'v2';
const CACHE_NAME = `pantrypal-${CACHE_VERSION}`;
```

The Service Worker automatically cleans up old caches (`v1`) and creates new ones (`v2`).

## Testing in Chrome DevTools

**Open Application Tab:**
```
1. Press F12 to open DevTools
2. Click "Application" tab
3. Look for "Service Workers" section
4. Check "Cache Storage" to see cached files
5. Go to "Network" tab and check "Offline" to simulate offline mode
```

**Check Service Worker Status:**
```
1. DevTools → Application → Service Workers
2. See status: "activated and running"
3. Can manually unregister for testing
4. Shows any errors or warnings
```

## Testing on Real Device

**iPhone (Safari):**
```
1. Open Safari
2. Navigate to PantryPal URL
3. Tap Share button (bottom)
4. Scroll down and tap "Add to Home Screen"
5. App appears on home screen as icon
6. Launch from home screen for full-screen experience
7. Turn off WiFi/cellular to test offline mode
```

**Android (Chrome):**
```
1. Open Chrome
2. Navigate to PantryPal URL
3. Tap menu button (three dots, top right)
4. Tap "Install app" (or "Add to Home screen")
5. Confirm installation
6. App appears on home screen as icon
7. Launch from home screen for full-screen experience
8. Turn off WiFi/cellular to test offline mode
```

## Lighthouse PWA Audit

```
1. Open DevTools (F12)
2. Click "Lighthouse" tab
3. Select "Progressive Web App" category
4. Click "Analyze page load"
5. Check score and recommendations
6. Fix any issues and re-run
```

## Performance Monitoring

```javascript
// Check if service worker is registered
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(registrations => {
        console.log('Registered service workers:', registrations.length);
    });
}

// Check cache contents
caches.keys().then(cacheNames => {
    console.log('Available caches:', cacheNames);
    cacheNames.forEach(cacheName => {
        caches.open(cacheName).then(cache => {
            cache.keys().then(keys => {
                console.log(`Items in ${cacheName}:`, keys.length);
            });
        });
    });
});
```

## Browser Compatibility Check

```javascript
// Check PWA support
const features = {
    serviceWorker: 'serviceWorker' in navigator,
    caches: 'caches' in window,
    manifests: document.querySelector('link[rel="manifest"]') !== null,
    webApp: navigator.standalone !== undefined
};

console.log('PWA Support:', features);
```

---

All code snippets are production-ready and follow best practices for PWA development.
