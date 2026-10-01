export function connectWebSocket() {
	const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
	if (apiUrl.startsWith("/")) {
		const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
		return new WebSocket(`${protocol}//${window.location.host}/ws`);
	}
	return new WebSocket(apiUrl.replace(/^http/, "ws") + "/ws");
}
