// Debug Logging
console.log("Moon Study: timer.js loaded");

// Wake Lock
let wakeLock = null;

async function enableWakeLock() {
    try {
        if ('wakeLock' in navigator) {
            wakeLock = await navigator.wakeLock.request("screen");
            console.log("Wake lock acquired");
        }
    } catch (err) {
        console.error('Wake lock error:', err);
    }
}

function disableWakeLock() {
    if (wakeLock) {
        wakeLock.release();
        wakeLock = null;
        console.log("Wake lock released");
    }
}

// Register Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').then(reg => {
            console.log("Service Worker registered:", reg.scope);
        }).catch(err => {
            console.error("Service Worker registration failed:", err);
        });
    });
}

// Generate stars
function initStars() {
    const starsContainer = document.getElementById('stars');
    if (!starsContainer) {
        console.warn("Stars container not found");
        return;
    }
    for (let i = 0; i < 100; i++) {
        const star = document.createElement('div');
        star.className = 'star';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.width = Math.random() * 2 + 1 + 'px';
        star.style.height = star.style.width;
        star.style.animationDelay = Math.random() * 4 + 's';
        star.style.opacity = Math.random() * 0.5 + 0.2;
        starsContainer.appendChild(star);
    }
    console.log("Stars initialized");
}

// Timer state
let selectedDuration = 25;
let isRunning = false;
let isOvertime = false;
let timerInterval = null;
let startTime = null;
let accumulatedMs = 0;
let sessionSaved = false;
let savedSessionId = null;

const MIN_SESSION_MS = 60000; // 1 minute minimum

// Helper to get elements safely
const getEl = (id) => document.getElementById(id);

function formatTime(seconds) {
    const mins = Math.floor(Math.abs(seconds) / 60);
    const secs = Math.abs(seconds) % 60;
    const prefix = isOvertime ? '+' : '';
    return `${prefix}${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

function updateTimerDisplay(elapsedSeconds) {
    const timerDisplay = getEl('timer');
    if (!timerDisplay) return;
    
    const totalSeconds = selectedDuration * 60;
    let displaySeconds;

    if (isOvertime) {
        displaySeconds = elapsedSeconds - totalSeconds;
        timerDisplay.classList.add('text-red-400');
    } else {
        displaySeconds = Math.max(0, totalSeconds - elapsedSeconds);
        timerDisplay.classList.remove('text-red-400');
    }

    const timeStr = formatTime(displaySeconds);
    timerDisplay.textContent = timeStr;
    // console.log("Timer updated:", timeStr);
}

function updateMoon(totalMinutes) {
    const moon = getEl("moon");
    if (!moon) return;
    
    let src = "/static/moon/new.jpg";
    if (totalMinutes >= 60) src = "/static/moon/full.jpg";
    else if (totalMinutes >= 45) src = "/static/moon/gibbous.jpg";
    else if (totalMinutes >= 30) src = "/static/moon/half.jpg";
    else if (totalMinutes >= 15) src = "/static/moon/crescent.jpg";
    
    moon.src = src;
}

async function fetchStats() {
    try {
        const res = await fetch('/stats');
        const data = await res.json();
        
        const totalMinutes = data.total_minutes;
        const hours = Math.floor(totalMinutes / 60);
        const mins = totalMinutes % 60;
        const totalTimeEl = getEl('totalTime');
        if (totalTimeEl) totalTimeEl.textContent = `${hours}h ${mins}m`;
        
        updateMoon(totalMinutes);
        
        const sessionList = getEl('sessionList');
        if (sessionList) {
            if (data.sessions.length === 0) {
                sessionList.innerHTML = '<p class="text-gray-600 text-xs">No sessions yet</p>';
            } else {
                sessionList.innerHTML = data.sessions.map(s => `
                    <div class="session-item flex justify-between px-4">
                        <span>${s.time}</span>
                        <span>${s.duration} min</span>
                    </div>
                `).join('');
            }
        }
    } catch (err) {
        console.error('Failed to fetch stats:', err);
    }
}

async function saveSession(duration, sessionId = null) {
    if (duration <= 0) return false;
    console.log(`Saving session: ${duration}min, ID: ${sessionId}`);

    try {
        const res = await fetch('/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ duration, session_id: sessionId })
        });

        if (!res.ok) throw new Error("Offline or Server Error");

        const data = await res.json();
        if (data.status === 'saved' && !sessionId) {
            savedSessionId = data.session_id;
            console.log("Session saved, new ID:", savedSessionId);
        }
        await fetchStats();
        return true;
    } catch (err) {
        if (!sessionId) {
            const offline = JSON.parse(localStorage.getItem("offlineSessions") || "[]");
            offline.push({ duration, timestamp: new Date().toISOString() });
            localStorage.setItem("offlineSessions", JSON.stringify(offline));
            console.warn("Saved session to offline storage");
        }
        return false;
    }
}

function tick() {
    if (!isRunning) return;
    const now = Date.now();
    const elapsedMs = accumulatedMs + (now - startTime);
    const elapsedSeconds = Math.floor(elapsedMs / 1000);
    const totalSeconds = selectedDuration * 60;

    if (!isOvertime && elapsedSeconds >= totalSeconds) {
        isOvertime = true;
        console.log("Timer finished, entering overtime");
        if (!sessionSaved && elapsedMs >= MIN_SESSION_MS) {
            saveSession(selectedDuration);
            sessionSaved = true;
        }
        if ("Notification" in window && Notification.permission === "granted") {
            new Notification("Session complete", { body: "Your study session is done." });
        }
    }

    updateTimerDisplay(elapsedSeconds);
    updateMoon(Math.floor(elapsedSeconds / 60));
}

function startTimer() {
    if (isRunning) return;
    console.log("Starting timer");
    isRunning = true;
    startTime = Date.now();
    sessionSaved = false;
    savedSessionId = null;
    enableWakeLock();
    timerInterval = setInterval(tick, 200);
    const startBtn = getEl('startBtn');
    if (startBtn) startBtn.textContent = 'Running';
    const durationSelect = getEl('durationSelect');
    if (durationSelect) durationSelect.disabled = true;
}

function pauseTimer() {
    if (!isRunning) return;
    console.log("Pausing timer");
    accumulatedMs += Date.now() - startTime;
    isRunning = false;
    clearInterval(timerInterval);
    disableWakeLock();
    const startBtn = getEl('startBtn');
    if (startBtn) startBtn.textContent = 'Resume';
}

function resetTimer() {
    if (isRunning && !confirm("Timer is running. Reset will discard your current session. Are you sure?")) {
        return;
    }
    console.log("Resetting timer");
    clearInterval(timerInterval);
    isRunning = false;
    isOvertime = false;
    accumulatedMs = 0;
    startTime = null;
    sessionSaved = false;
    savedSessionId = null;
    updateTimerDisplay(0);
    const startBtn = getEl('startBtn');
    if (startBtn) startBtn.textContent = 'Start';
    const durationSelect = getEl('durationSelect');
    if (durationSelect) durationSelect.disabled = false;
    disableWakeLock();
}

async function completeSession() {
    const currentElapsedMs = isRunning ? accumulatedMs + (Date.now() - startTime) : accumulatedMs;
    console.log("Completing session, total ms:", currentElapsedMs);
    
    if (currentElapsedMs < MIN_SESSION_MS) {
        if (confirm("Session is too short (under 1 minute). Discard?")) {
            resetTimer();
        }
        return;
    }

    const durationMinutes = Math.ceil(currentElapsedMs / 60000);
    
    clearInterval(timerInterval);
    isRunning = false;
    
    await saveSession(durationMinutes, savedSessionId);
    resetTimer();
}

// Bind events
window.addEventListener('DOMContentLoaded', () => {
    console.log("DOM loaded, binding events");
    const startBtn = getEl('startBtn');
    const pauseBtn = getEl('pauseBtn');
    const resetBtn = getEl('resetBtn');
    const doneBtn = getEl('doneBtn');
    const durationSelect = getEl('durationSelect');

    if (startBtn) startBtn.addEventListener('click', startTimer);
    if (pauseBtn) pauseBtn.addEventListener('click', pauseTimer);
    if (resetBtn) resetBtn.addEventListener('click', resetTimer);
    if (doneBtn) doneBtn.addEventListener('click', completeSession);

    if (durationSelect) {
        durationSelect.addEventListener('change', function() {
            if (!isRunning) {
                selectedDuration = parseInt(this.value);
                updateTimerDisplay(0);
            }
        });
    }

    // Initial load
    initStars();
    fetchStats();
    updateTimerDisplay(0);
    syncOfflineSessions();
});

async function syncOfflineSessions() {
    const offline = JSON.parse(localStorage.getItem("offlineSessions") || "[]");
    if (offline.length === 0) return;

    console.log("Syncing offline sessions...");
    const stillOffline = [];
    for (const session of offline) {
        try {
            const res = await fetch('/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ duration: session.duration })
            });
            if (!res.ok) stillOffline.push(session);
        } catch (err) {
            stillOffline.push(session);
        }
    }
    
    if (stillOffline.length > 0) {
        localStorage.setItem("offlineSessions", JSON.stringify(stillOffline));
    } else {
        localStorage.removeItem("offlineSessions");
        console.log("Offline sessions synced successfully");
    }
    await fetchStats();
}

window.addEventListener('online', () => {
    console.log("Connection restored, syncing...");
    syncOfflineSessions();
});

if ("Notification" in window && Notification.permission !== "granted") {
    Notification.requestPermission();
}
