# DQN Scaler Dashboard - Angular Web Application

Beautiful, modern Angular dashboard for managing the DQN Kubernetes Resource Scaler.

## Features

- **Real-time Dashboard** - View statistics, action distribution, and system status
- **Pod Management** - List and manually scale individual pods
- **Decisions Log** - Review all scaling decisions with detailed information
- **Configuration** - Update scaler settings in real-time
- **Auto-refresh** - Dashboard updates automatically every 10 seconds
- **Responsive Design** - Works on desktop, tablet, and mobile

## Prerequisites

- Node.js 18+ and npm
- Angular CLI (`npm install -g @angular/cli`)
- Flask backend running on `localhost:5000`

## Quick Start

### 1. Install Dependencies

```bash
cd dqn-scaler-dashboard
npm install
```

### 2. Start the Backend

In another terminal:
```bash
cd ../model-impl
python3 app.py
```

The Flask API should be running on `http://localhost:5000`

### 3. Start the Dashboard

```bash
npm start
```

The dashboard will open at `http://localhost:4200`

## Development

### Project Structure

```
dqn-scaler-dashboard/
├── src/
│   ├── app/
│   │   ├── components/
│   │   │   ├── dashboard/      # Main dashboard view
│   │   │   ├── pods/           # Pods list and management
│   │   │   ├── decisions/      # Scaling decisions log
│   │   │   ├── config/         # Configuration editor
│   │   │   └── navbar/         # Navigation bar
│   │   ├── models/             # TypeScript interfaces
│   │   ├── services/           # API service
│   │   └── app.component.ts    # Root component
│   ├── index.html
│   ├── main.ts
│   └── styles.css              # Global styles
├── angular.json
├── package.json
└── proxy.conf.json             # API proxy configuration
```

### Available Scripts

- `npm start` - Start development server (http://localhost:4200)
- `npm run build` - Build for production
- `npm run watch` - Build and watch for changes

### API Proxy

The dashboard uses a proxy to avoid CORS issues. Requests to `/api/*` are forwarded to `http://localhost:5000`.

Configuration in `proxy.conf.json`:
```json
{
  "/api": {
    "target": "http://localhost:5000",
    "secure": false,
    "changeOrigin": true
  }
}
```

## Components

### Dashboard
- Statistics cards (total decisions, applied changes, confidence, rate)
- Auto-scaling controls
- Action distribution charts
- Configuration summary

### Pods
- List all managed pods
- View pod details (namespace, owner)
- Manual scaling for individual pods
- Real-time scaling status

### Decisions
- Detailed log of all scaling decisions
- Filter by count (10, 25, 50, 100)
- Color-coded actions (increase=green, decrease=red, maintain=blue)
- Confidence visualization
- Applied/not applied status

### Configuration
- Edit scaling parameters
- Toggle dry-run mode
- Adjust scale factor, CPU/memory limits
- Configure auto-scaling interval and cooldown
- Save changes to backend

## API Integration

The dashboard communicates with the Flask backend via the `ApiService`:

```typescript
// Get statistics
this.apiService.getStatistics().subscribe(response => {
  this.statistics = response.statistics;
});

// Scale a pod
this.apiService.scalePod(namespace, podName).subscribe(response => {
  console.log(response.result);
});

// Update configuration
this.apiService.updateConfig({ dry_run: false }).subscribe(...);
```

## Styling

The dashboard uses a custom CSS design system with:
- Gradient color scheme (purple/blue)
- Card-based layout
- Responsive grid system
- Smooth animations
- Badge system for status indicators

## Build for Production

```bash
npm run build
```

Output will be in `dist/dqn-scaler-dashboard/`

Serve with any static file server:
```bash
cd dist/dqn-scaler-dashboard
python3 -m http.server 8080
```

## Deploy with Backend

### Option 1: Serve Angular from Flask

Build the Angular app and copy to Flask static folder:

```bash
npm run build
cp -r dist/dqn-scaler-dashboard/* ../model-impl/static/
```

Update Flask to serve Angular:
```python
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')
```

### Option 2: Separate Servers

Keep Angular on port 4200 and Flask on port 5000 (development setup).

### Option 3: Reverse Proxy

Use nginx to serve both:

```nginx
location / {
    proxy_pass http://localhost:4200;
}

location /api {
    proxy_pass http://localhost:5000;
}
```

## Troubleshooting

### Cannot connect to backend

1. Verify Flask is running: `curl http://localhost:5000/api/health`
2. Check proxy configuration in `proxy.conf.json`
3. Restart Angular dev server

### Module not found errors

```bash
rm -rf node_modules package-lock.json
npm install
```

### CORS errors

The proxy should handle this. If you still see CORS errors:
1. Ensure proxy.conf.json is correctly configured
2. Start Angular with `npm start` (not `ng serve` directly)
3. Check Flask has CORS enabled (flask-cors)

## Screenshots

### Dashboard
- Statistics overview
- Auto-scaling controls
- Action distribution

### Pods View
- All managed pods
- Scaling actions

### Decisions Log
- Detailed decision history
- Color-coded visualization

### Configuration
- Real-time settings update
- Dry-run toggle

## License

Part of MSC Research Project - DQN Kubernetes Resource Scaler

## Support

For issues related to:
- **Dashboard**: Check browser console for errors
- **Backend connection**: Verify Flask is running
- **API errors**: Check Flask logs

See main project README for complete documentation.
