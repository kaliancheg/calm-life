(function () {
    const script = document.currentScript;
    const timeoutMs = Number(script.dataset.timeoutMs);
    const sessionUserId = script.dataset.userId;
    const loginUrl = script.dataset.loginUrl;
    const storageKey = `tourism-last-activity-${sessionUserId}`;
    const originalFetch = window.fetch.bind(window);
    let redirecting = false;
    let storageAvailable = true;
    let lastActivity = Date.now();
    let lastActivityRecordedAt = 0;
    let timeoutId;

    function redirectToLogin() {
        if (redirecting) return;
        redirecting = true;
        window.location.replace(loginUrl);
    }

    window.fetch = async function (...args) {
        const response = await originalFetch(...args);
        const redirectedToLogin = response.redirected
            && new URL(response.url, window.location.href).pathname === new URL(loginUrl, window.location.href).pathname;
        if (response.status === 401 || redirectedToLogin) redirectToLogin();
        return response;
    };

    function getLastActivity() {
        if (!storageAvailable) return lastActivity;
        try {
            const storedActivity = Number(localStorage.getItem(storageKey));
            if (Number.isFinite(storedActivity) && storedActivity > 0) {
                lastActivity = Math.max(lastActivity, storedActivity);
            }
        } catch (error) {
            storageAvailable = false;
            console.warn('Unable to synchronize session activity across tabs:', error);
        }
        return lastActivity;
    }

    function saveLastActivity() {
        if (!storageAvailable) return;
        try {
            localStorage.setItem(storageKey, String(lastActivity));
        } catch (error) {
            storageAvailable = false;
            console.warn('Unable to synchronize session activity across tabs:', error);
        }
    }

    function checkInactivity() {
        const remainingMs = timeoutMs - (Date.now() - getLastActivity());
        if (remainingMs <= 0) {
            redirectToLogin();
            return;
        }
        timeoutId = window.setTimeout(checkInactivity, remainingMs);
    }

    function scheduleInactivityCheck() {
        window.clearTimeout(timeoutId);
        checkInactivity();
    }

    function recordActivity() {
        if (redirecting) return;
        const now = Date.now();
        if (now - lastActivityRecordedAt < 1000) return;
        lastActivity = now;
        lastActivityRecordedAt = now;
        saveLastActivity();
        scheduleInactivityCheck();
    }

    function initialize() {
        if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || !sessionUserId || !loginUrl) return;

        lastActivity = Math.max(Date.now(), getLastActivity());
        lastActivityRecordedAt = lastActivity;
        saveLastActivity();
        scheduleInactivityCheck();

        ['pointerdown', 'keydown', 'scroll', 'touchstart', 'wheel'].forEach(eventName => {
            document.addEventListener(eventName, recordActivity, {passive: true});
        });

        let lastPointerMove = 0;
        document.addEventListener('pointermove', () => {
            const now = Date.now();
            if (now - lastPointerMove >= 1000) {
                lastPointerMove = now;
                recordActivity();
            }
        }, {passive: true});

        window.addEventListener('storage', event => {
            if (event.key === storageKey) scheduleInactivityCheck();
        });
        window.addEventListener('pageshow', scheduleInactivityCheck);
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) scheduleInactivityCheck();
        });

        const heartbeatIntervalMs = Math.min(5 * 60 * 1000, timeoutMs / 3);
        window.setInterval(() => {
            if (Date.now() - getLastActivity() >= heartbeatIntervalMs) return;
            window.fetch('/api/session/heartbeat', {method: 'POST'})
                .then(response => {
                    if (!response.ok) {
                        console.error('Session heartbeat failed:', response.status);
                    }
                })
                .catch(error => console.error('Session heartbeat request failed:', error));
        }, heartbeatIntervalMs);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize, {once: true});
    } else {
        initialize();
    }
})();
