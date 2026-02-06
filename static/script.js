/**
 * Sends a command to the Flask server (next, prev, blackout, etc.)
 */
function sendCommand(action) {
    fetch(`/command/${action}`)
        .then(response => response.json())
        .then(data => {
            console.log(`Action executed: ${action}`);
            // If the action was blackout, we could change button color here
        })
        .catch(err => console.error("Command failed:", err));
}

/**
 * Watchdog: Reconnects the stream if the connection drops
 */
function initStreamWatchdog() {
    const img = document.getElementById('screen-stream');
    if (!img) return;

    img.onerror = function() {
        console.warn("Stream lost. Retrying in 3s...");
        setTimeout(() => {
            // Append timestamp to prevent browser caching the "broken" image
            img.src = img.src.split('?')[0] + "?" + new Date().getTime();
        }, 3000);
    };
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initStreamWatchdog);