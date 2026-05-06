# 🧠 REAL-TIME LLM LEARNING DASHBOARD

## Overview

A complete real-time monitoring system to watch what your application learns from AI in real-time. Three ways to monitor:

1. **Web Dashboard** - Beautiful live interface with statistics and event log
2. **Terminal Monitor** - Real-time updates in terminal
3. **REST API** - Programmatic access to learning events

---

## 🌐 WEB DASHBOARD

### Access

```
http://localhost:8000/dashboard/learning
```

### Features

#### 📊 Statistics Cards
- **Total Events**: All events processed
- **Aliases Learned**: New mappings created
- **LLM Calls**: Number of Claude analyses
- **Errors**: Failed operations
- **Success Rate**: Percentage of successful learning
- **Last Event**: Most recent learning action

#### 📈 Real-time Progress Bars
Visual progress for each metric with smooth animations

#### 📝 Event Log
Live-updating list of recent events with:
- ✅ Alias learned (with match score)
- 🔍 LLM call analysis
- ❌ Errors with details
- ⏱️ Timestamps

#### 🔌 WebSocket Connection
- Automatic reconnection if connection drops
- Live updates every time learning happens
- Connection status indicator

### Usage

1. **Open Dashboard**
   ```
   http://your-app/dashboard/learning
   ```

2. **Upload a PDF**
   - Use the normal upload interface
   - The dashboard updates in real-time

3. **Watch the Learning Happen**
   - Events appear in the log instantly
   - Statistics update as learning progresses
   - Success rate increases with each learned alias

---

## 💻 TERMINAL MONITOR

### Start Monitor

```bash
python learning_monitor_live.py
```

### Features

```
╔══════════════════════════════════════════════════════════════════════════════╗
║             🧠 LLM LEARNING MONITOR (REAL-TIME)                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

📊 STATISTICS:
  Total Events: 42 | Aliases Learned: 12 | LLM Calls: 15 | Errors: 0

  Success Rate: 80.0%
  [████████████████░░░░]

📝 RECENT EVENTS:
  ✅ K → Potassium (86.5%) 14:23:45
  ✅ Na → Sodium (89.2%) 14:23:44
  🔍 Analyzing pH... 14:23:43
  ✅ Ca → Calcium (87.1%) 14:23:42
  ...

Last update: 2026-05-06 14:23:45
Refreshing every 1 second... (Press Ctrl+C to exit)
```

### Benefits

- Live monitoring in SSH/terminal
- Colors for different event types
- Progress bar for success rate
- Automatic refresh every second
- No web browser needed

### Usage

```bash
# Terminal 1: Run the application
python start.py

# Terminal 2: Start the monitor
python learning_monitor_live.py

# Now watch learning happen in real-time!
```

---

## 📡 REST API

### Get Recent Events

```bash
curl http://localhost:8000/api/learning/events?limit=50
```

Response:
```json
{
  "events": [
    {
      "id": "alias_learned_1715000625000000",
      "type": "alias_learned",
      "analysis_name": "K",
      "mapped_to": "Potassium",
      "score": 86.5,
      "laborator_id": 1,
      "timestamp": "2026-05-06T14:23:45.123456",
      "details": {"analiza_standard_id": 42}
    },
    ...
  ]
}
```

### Get Statistics

```bash
curl http://localhost:8000/api/learning/stats
```

Response:
```json
{
  "total_events": 42,
  "aliases_learned": 12,
  "errors": 0,
  "llm_calls": 15,
  "success_rate": 80.0,
  "recent_events": [...]
}
```

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/learning');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Learning event:', data);
};

// Request stats
ws.send('stats');
```

---

## 🎯 WORKFLOW EXAMPLE

### Scenario: Testing Learning System

1. **Start Application**
   ```bash
   python start.py
   ```

2. **Open Dashboard in Browser**
   ```
   http://localhost:8000/dashboard/learning
   ```

3. **Start Terminal Monitor (Optional)**
   ```bash
   python learning_monitor_live.py
   ```

4. **Upload Test PDF with Unknown Analyses**
   - Upload a buletin containing unknown short names like "K", "Na", "pH"
   - These should NOT exist in your catalog

5. **Watch Real-Time Learning**
   
   **Browser Dashboard:**
   - Statistics increase
   - Event log shows learning progress
   - Success rate updates

   **Terminal Monitor:**
   - Shows live updates
   - Colors indicate success/failure
   - Real-time progress bars

6. **Verify Learning Saved**
   ```bash
   python check_llm_learning.py
   ```
   - Should show new aliases in database
   - Same data as in dashboard

---

## 📊 EVENT TYPES

### alias_learned
✅ **When:** A new analysis was successfully mapped to a standard analysis

```json
{
  "type": "alias_learned",
  "analysis_name": "K",
  "mapped_to": "Potassium",
  "score": 86.5,
  "details": {"analiza_standard_id": 42}
}
```

### llm_call
🔍 **When:** Claude API is analyzing an unknown analysis

```json
{
  "type": "llm_call",
  "analysis_name": "K"
}
```

### error
❌ **When:** Something went wrong during learning

```json
{
  "type": "error",
  "analysis_name": "K",
  "error": "API key invalid"
}
```

---

## 📈 STATISTICS EXPLAINED

### Total Events
Sum of all events (aliases learned + LLM calls + errors)

### Aliases Learned
Count of successful new aliases created in the database

### LLM Calls
Number of times Claude API was called to analyze an unknown analysis

### Errors
Count of failed operations

### Success Rate
```
Success Rate = (Aliases Learned / LLM Calls) * 100%
```

Example:
- LLM Calls: 15
- Aliases Learned: 12
- Success Rate: 80%

This means 80% of analyses got successfully mapped to standard analyses.

---

## 🔧 CONFIGURATION

### Enable Learning

In `.env`:
```bash
LLM_LEARN_FROM_UPLOAD_ENABLED=true
ANTHROPIC_API_KEY=sk-ant-...
```

### Thresholds

In `.env` or default in `backend/config.py`:
```bash
# Minimum confidence score to auto-apply alias (default 86%)
LLM_LEARN_AUTO_APPLY_MIN_SCORE=86.0

# Max LLM calls per upload (default 40)
LLM_LEARN_MAX_CALLS_PER_UPLOAD=40
```

---

## 🐛 TROUBLESHOOTING

### Dashboard shows "Disconnected"
- Check if application is running
- Check if WebSocket port is accessible
- Browser console should show connection errors

### No events appearing
1. Verify `.env` has `LLM_LEARN_FROM_UPLOAD_ENABLED=true`
2. Upload a PDF with unknown analyses (not in your catalog)
3. Check application logs for errors

### Terminal monitor shows empty
- Same as above - need to upload a PDF first
- Check if event bus is initialized

### Events not saving to database
1. Check if database connection works
2. Verify `alias_analiza` table exists
3. Check application logs

---

## 🚀 PRODUCTION DEPLOYMENT

### Railway/Cloud

The dashboard is automatically available at:
```
https://your-app.railway.app/dashboard/learning
```

### Behind Reverse Proxy

Ensure WebSocket is properly proxied:

**Nginx:**
```nginx
location /ws/learning {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

**Apache:**
```apache
ProxyPass /ws/learning ws://localhost:8000/ws/learning
ProxyPassReverse /ws/learning ws://localhost:8000/ws/learning
```

---

## 📚 INTEGRATION EXAMPLES

### Python Script
```python
import requests

# Get stats
response = requests.get('http://localhost:8000/api/learning/stats')
stats = response.json()

print(f"Learned {stats['aliases_learned']} aliases")
print(f"Success rate: {stats['success_rate']}%")
```

### JavaScript
```javascript
async function monitorLearning() {
    const response = await fetch('/api/learning/events?limit=10');
    const data = await response.json();
    
    data.events.forEach(event => {
        if (event.type === 'alias_learned') {
            console.log(`✅ Learned: ${event.analysis_name} → ${event.mapped_to}`);
        }
    });
}
```

---

## ✨ FEATURES

✅ Real-time WebSocket updates  
✅ Beautiful responsive web dashboard  
✅ Terminal-based monitoring  
✅ REST API access  
✅ Event history (last 500 events)  
✅ Statistics tracking  
✅ Connection status indicator  
✅ Automatic reconnection  
✅ Color-coded events  
✅ Mobile-friendly dashboard  

---

## 🎓 LEARNING

This system shows you:
- **What:** What analyses are being learned
- **When:** Exact timestamps of learning
- **Score:** Confidence level of mapping (0-100%)
- **Status:** Success or failure of each attempt
- **Rate:** How fast the system learns
- **Trends:** Success rate over time

Use this to:
1. Verify learning is working
2. Identify problematic analyses
3. Monitor LLM API usage
4. Track learning performance
5. Debug issues

---

**Status:** ✅ Complete and ready to use
**Last Updated:** May 6, 2026
