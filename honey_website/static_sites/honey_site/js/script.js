import { additionalCreep } from './creep.min.js';

// var mus = new Mus();
// A bit of naming confusion here:
// - visitorId cookie is a generated session ID.
// - visitId cookie is a visit ID that is unique for each visit.
// - visitorId variable is the fingerprintJS hash. If any response payload
//   contains the visitorId, it is the fingerprintJS hash.
var cookieName = "visitorId";
var visitIDCookieName = "visitId";
var fingerprintCookieName = "visitorFingerprint";
var visitorId = null;
var eventFrames = [];
export const countWebsiteVersion = "XXXXXXXXXX";

const EVENT_FRAMES_LIMIT = 50;
const VERSION_PREFIX = "/" + (location.pathname.split("/")[1] || "");
const PRIVACY = false;
const EVENT_HANDLERS = new Map([
	["keydown", recordKeyboardEvent],
	["keyup", recordKeyboardEvent],
	["paste", (event) => eventFrames.push(["p", getUniqueSelector(event.target), event.clipboardData.getData("text"), performance.now()])],
	["input", (event) => eventFrames.push(["i", getUniqueSelector(event.target), event.inputType, event.target.value, performance.now()])],
	["change", recordChangeEvent],
	["scroll", recordScrollEvent],
	["scrollend", recordScrollEvent],
	["mousemove", recordMouseEvent],
	["mousedown", recordMouseEvent],
	["mouseup", recordMouseEvent],
]);

// Events that should be attached to window
const WINDOW_EVENTS = ["keydown", "keyup", "paste", "mousemove", "mousedown", "mouseup", "input", "change"];

// Events that need capture phase on document (for bubbling from any element)
const DOCUMENT_CAPTURE_EVENTS = ["scroll", "scrollend"];

function sendViaXHR(endpoint, content_type, source, body_data) {
	const xmlhttp = new XMLHttpRequest();
	xmlhttp.withCredentials = true;
	xmlhttp.open("POST", endpoint, true);
	xmlhttp.setRequestHeader("Content-Type", content_type);
	xmlhttp.setRequestHeader("X-Source", source);
	xmlhttp.send(body_data);
}

function sendData(d, endpoint) {
	const body_data = JSON.stringify(d);
	const content_type = "application/json;charset=UTF-8";

	let source = "mouseMovements";
	if ("addedFP" in d) {
		source = "addedFP";
	} else if ("result" in d) {
		source = "result"
	} else if ("eventFrames" in d) {
		source = "eventFrames"
	} else if (endpoint === "/start") {
		source = "start";
	} else if (endpoint === "/end") {
		source = "end";
	}

	endpoint = VERSION_PREFIX + endpoint;
	const keep_alive = source === "result";

	if (window.fetch) {
		try {
			fetch(endpoint, {
				method: "POST",
				body: body_data,
				headers: {
					"Content-Type": content_type,
					"X-Source": source
				},
				keepalive: keep_alive,
				credentials: "include",
			});
			return;
		} catch (e) {
			sendViaXHR(endpoint, content_type, source, body_data);
		}
	} else {
		sendViaXHR(endpoint, content_type, source, body_data);
	}
}

export function postComplete(d) {
	sendData(d, "/end");
}

function flushEventFrames() {
	const eventObject = {
		visitorId: visitorId || null,
		sourcePage: window.location.href,
		eventFrames: eventFrames
	};
	sendData(eventObject, "/mm");
	eventFrames = [];
}

function getUniqueSelector(element) {
	if (element.id) return `#${element.id}`;

	// Build path from element to root
	const path = [];
	while (element && element.nodeType === Node.ELEMENT_NODE) {
		let selector = element.tagName.toLowerCase();

		if (element.parentElement) {
			const siblings = Array.from(element.parentElement.children);
			const index = siblings.indexOf(element) + 1;
			selector += `:nth-child(${index})`;
		}

		path.unshift(selector);

		if (element.parentElement) {
			element = element.parentElement;
		} else {
			break;
		}
	}

	return path.join(' > ');
}

function recordMouseEvent(event) {
	// Event type, button pressed (if mdwn/mup), x, y, timestamp
	// Mouse buttons: 0 = left, 1 = middle/wheel, 2 = right, 3 = MB4 (back), 4 = MB5 (forward)
	const selector = getUniqueSelector(event.target);
	if (event.type === "mousemove") {
		eventFrames.push(["mm", selector, event.x, event.y, performance.now()])
	} else if (event.type === "mousedown") {
		eventFrames.push(["md", selector, event.button, event.x, event.y, performance.now()])
	} else if (event.type === "mouseup") {
		eventFrames.push(["mu", selector, event.button, event.x, event.y, performance.now()])
	}
}


function getCookie(name) {
	var match = document.cookie.match(RegExp('(?:^|;\\s*)' + name + '=([^;]*)'));
	return match ? match[1] : null;
}

function recordEventWrapper(event) {
	if (EVENT_HANDLERS.has(event.type)) {
		EVENT_HANDLERS.get(event.type)(event);
	} else {
		console.error("Unhandled event type: " + event.type);
	}

	// Flush event frames to server if limit is reached
	if (eventFrames.length >= EVENT_FRAMES_LIMIT) {
		flushEventFrames();
	}
}

function recordKeyboardEvent(event) {
	// Don't record characters for privacy reasons if PRIVACY is enabled
	const key = PRIVACY && event.key.length === 1 ? "*" : event.key;
	const selector = getUniqueSelector(event.target);

	if (event.type === "keydown") {
		eventFrames.push(["kd", selector, key, event.repeat, performance.now()]);
	} else if (event.type === "keyup") {
		eventFrames.push(["ku", selector, key, event.repeat, performance.now()]);
	}
}

function recordScrollEvent(event) {
	const eventType = event.type === "scroll" ? "sc" : "se";
	const target = event.target;
	let scrolledX, scrolledY, scrolledElement;

	if (target === document || target === document.documentElement) {
		// Document/window scroll
		scrolledX = window.scrollX || document.documentElement.scrollLeft || 0;
		scrolledY = window.scrollY || document.documentElement.scrollTop || 0;
		scrolledElement = "document";
	} else {
		// Scrollable element
		scrolledX = target.scrollLeft || 0;
		scrolledY = target.scrollTop || 0;
		scrolledElement = getUniqueSelector(target);
	}

	eventFrames.push([eventType, scrolledElement, scrolledX, scrolledY, performance.now()]);
}

function recordChangeEvent(event) {
	const target = event.target;
	const selector = getUniqueSelector(target);
	if (target.type === "checkbox" || target.type === "radio") {
		eventFrames.push(["c", selector, target.value, target.checked, performance.now()])
	} else {
		eventFrames.push(["c", selector, target.value, performance.now()])
	}
}

// Set session ID cookie
if (!getCookie(cookieName)) {
	var now = new Date();
	var time = now.getTime();
	var expireTime = time + 3000000 * 3600;
	now.setTime(expireTime);

	document.cookie = cookieName + "=" + crypto.randomUUID() +
		";expires=" + now.toUTCString() + ";path=/";

}

// Set visit ID cookie every new visit
var now = new Date();
var time = now.getTime();
var expireTime = time + 3000000 * 3600;
now.setTime(expireTime);

document.cookie = visitIDCookieName + "=" + `${getCookie(cookieName)}-${Date.now()}` +
	";expires=" + now.toUTCString() + ";path=/";

// Attach window event listeners
WINDOW_EVENTS.forEach(eventType => {
	if (EVENT_HANDLERS.has(eventType)) {
		window.addEventListener(eventType, recordEventWrapper, { passive: true });
	}
});

// Attach document-level capture listeners for scroll events (captures scroll on any element)
DOCUMENT_CAPTURE_EVENTS.forEach(eventType => {
	if (EVENT_HANDLERS.has(eventType)) {
		document.addEventListener(eventType, recordEventWrapper, { passive: true, capture: true });
	}
});

// Attach input listeners to text-like inputs
// document.querySelectorAll('textarea, input[type=text], input[type=email], input[type=number], input[type=password], input[type=tel], input[type=search], input[type=url], input[type=search], input[type=week], input[type=month], input[type=datetime-local]').forEach(element => {
// 	element.addEventListener("input", recordEventWrapper, { passive: true });
// });

// Attach change listeners to selection/toggle inputs
// document.querySelectorAll('select, input[type=checkbox], input[type=radio], input[type=color], input[type=date], input[type=file], input[type=number], input[type=range], input[type=time]').forEach(element => {
// 	element.addEventListener("change", recordEventWrapper, { passive: true });
// });

const websiteVersion = location.pathname.split("/")[1] || "";
if (websiteVersion === countWebsiteVersion) {
	if (!("forums" in localStorage)) {
		localStorage.setItem("forums", 0);
	}
	if (!("flights" in localStorage)) {
		localStorage.setItem("flights", 0);
	}
	if (!("sort" in localStorage)) {
		localStorage.setItem("sort", 0);
	}
	if (!("shop" in localStorage)) {
		localStorage.setItem("shop", 0);
	}
}

export async function redirectToCompletionPage(task) {
	const websiteVersion = location.pathname.split("/")[1] || "";
	if (websiteVersion === countWebsiteVersion) {
		await new Promise(res => setTimeout(res, 500));
		window.location.href = "/" + websiteVersion + "/completion?task=" + task;
	}
}

// Fingerprinting code
const fpPromise = import('./flib.js')
	.then(FingerprintJS => FingerprintJS.load())

fpPromise
	.then(fp => fp.get())
	.then(result => {
		const now = new Date();
		const expireTime = now.getTime() + 3000000 * 3600;
		now.setTime(expireTime);
		document.cookie = fingerprintCookieName + "=" + result.visitorId +
			";expires=" + now.toUTCString() + ";path=/";
		const fpObject = {
			sourcePage: window.location.href,
			result: result
		};
		sendData(fpObject, "/fp");
		visitorId = result.visitorId
	});

additionalCreep().then(addedFP => {
	const fpObject = {
		sourcePage: window.location.href,
		addedFP: addedFP
	};
	sendData(fpObject, "/fp")
});

// Add event recording code on window load
// Periodically flush event frames
window.addEventListener("load", () => {
	// Send event frames every 500ms
	setInterval(() => {
		if (eventFrames.length > 0) {
			flushEventFrames();
		}
	}, 500);
});

// Flush event frames when user navigates away
window.addEventListener("beforeunload", () => {
	if (eventFrames.length > 0) {
		flushEventFrames();
	}
});

window.addEventListener("visibilitychange", () => {
	if (eventFrames.length > 0) {
		flushEventFrames();
	}
});

window.addEventListener("pagehide", () => {
	if (eventFrames.length > 0) {
		flushEventFrames();
	}
});
