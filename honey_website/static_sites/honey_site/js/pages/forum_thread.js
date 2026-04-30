import { countWebsiteVersion, postComplete, redirectToCompletionPage } from '../script.js';

export function init() {
    const websiteVersion = location.pathname.split("/")[1] || "";
    // Load forums.css
    if (!document.querySelector('link[href*="forums.css"]')) {
        const link = document.createElement('link');
        link.rel = "stylesheet";
        link.href = "/" + websiteVersion + "/css/forums.css";
        document.head.appendChild(link);
    }

    // Extract thread ID from URL path
    const pathParts = window.location.pathname.split("/");
    const threadId = pathParts[pathParts.length - 1];

    const container = document.getElementById("thread-content");

    // Load threads from sessionStorage
    const threads = JSON.parse(sessionStorage.getItem("forumThreads") || "[]");
    const thread = findThread(threads, threadId);

    if (!thread) {
        container.innerHTML = `
            <h2>Thread Not Found</h2>
            <p>This discussion thread could not be found.</p>
        `;
        return;
    }

    renderThread(container, thread);

    // Event delegation for reply buttons
    container.addEventListener("click", e => {
        if (e.target.matches(".reply-btn")) {
            e.preventDefault();
            const postId = e.target.dataset.postId;
            const replyForm = document.querySelector(`.reply-form[data-parent-id="${postId}"]`);

            if (replyForm) {
                // Toggle the form
                const isHidden = replyForm.classList.contains("hidden");

                // Hide all other reply forms
                document.querySelectorAll(".reply-form").forEach(form => {
                    form.classList.add("hidden");
                });

                // Show this form if it was hidden
                if (isHidden) {
                    replyForm.classList.remove("hidden");
                    // Focus the textarea
                    const textarea = replyForm.querySelector("textarea");
                    if (textarea) textarea.focus();
                } else {
                    replyForm.classList.add("hidden");
                }
            }
        }
    });

    // Event delegation for reply submission
    container.addEventListener("submit", e => {
        if (!e.target.matches(".reply-form")) return;
        e.preventDefault();

        const parentId = e.target.dataset.parentId;
        const usernameInput = e.target.querySelector(".reply-username");
        const textarea = e.target.querySelector("textarea");
        const username = usernameInput.value.trim() || "Anonymous";
        const replyText = textarea.value.trim();

        if (!replyText) return;

        const reply = {
            id: crypto.randomUUID(),
            username: username,
            body: replyText,
            time: new Date().toLocaleString(),
            replies: [],
        };

        addReply(threads, parentId, reply);
        persist(threads);

        // Re-render the thread
        const updatedThread = findThread(threads, threadId);
        renderThread(container, updatedThread, threads);
        postComplete({ "webpage": "forums" });
        if (websiteVersion === countWebsiteVersion) {
            let forumCounts = Number(localStorage.getItem("forums"));
            forumCounts++;
            localStorage.setItem("forums", forumCounts);
            if (forumCounts >= 3) {
                // Redirect to completion page
                redirectToCompletionPage("forums");
            }
        }
    });
}

// --- Find a thread by ID (recursive) ---
function findThread(threads, id) {
    for (const thread of threads) {
        if (thread.id === id) return thread;
        if (thread.replies.length) {
            const found = findThread(thread.replies, id);
            if (found) return found;
        }
    }
    return null;
}

// --- Recursive reply handling ---
function addReply(threads, parentId, reply) {
    for (const thread of threads) {
        if (thread.id === parentId) {
            thread.replies.push(reply);
            return true;
        }
        if (thread.replies.length) {
            if (addReply(thread.replies, parentId, reply)) return true;
        }
    }
    return false;
}

// --- Rendering ---
function renderThread(container, thread) {
    container.innerHTML = `
        <article class="forum-thread">
            <h2>${escapeHtml(thread.title)}</h2>
            <div class="thread-author-info">
                <span class="author-name">${escapeHtml(thread.username)}</span>
                <span class="thread-timestamp">${thread.time}</span>
            </div>
            <div class="thread-body">${escapeHtml(thread.body)}</div>
            
            <button class="reply-btn" data-post-id="${thread.id}">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
                </svg>
                Reply
            </button>
            
            <form class="reply-form hidden" data-parent-id="${thread.id}">
                <h4>Reply to this thread</h4>
                <input type="text" class="reply-username" placeholder="Your name (optional)" value="" />
                <textarea placeholder="Your reply...*" rows="3" required></textarea>
                <button type="submit">Post Reply</button>
            </form>
            
            ${thread.replies.length > 0
            ? `<div class="replies-section">
                    <h3>Replies (${countReplies(thread)})</h3>
                    ${thread.replies.map(r => renderReply(r, 0)).join("")}
                   </div>`
            : ""
        }
        </article>
    `;
}

// Recursively build reply HTML
function renderReply(reply, depth = 0) {
    const margin = depth * 30; // indent nested replies
    const hasReplies = reply.replies && reply.replies.length > 0;

    return `
        <article class="forum-reply" style="margin-left:${margin}px">
            <div class="reply-header">
                <span class="reply-author">${escapeHtml(reply.username)}</span>
                <span class="reply-timestamp">${reply.time}</span>
            </div>
            <p class="reply-body">${escapeHtml(reply.body)}</p>
            
            <button class="reply-btn small" data-post-id="${reply.id}">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
                </svg>
                Reply
            </button>
            
            <form class="reply-form nested-reply-form hidden" data-parent-id="${reply.id}">
                <input type="text" class="reply-username" placeholder="Your name (optional)" value="Anonymous" />
                <textarea placeholder="Reply..." rows="2" required></textarea>
                <button type="submit">Reply</button>
            </form>
            
            ${hasReplies
            ? `<div class="nested-replies">${reply.replies
                .map(r => renderReply(r, depth + 1))
                .join("")}</div>`
            : ""
        }
        </article>
    `;
}

// --- Count total replies recursively ---
function countReplies(thread) {
    let count = thread.replies.length;
    thread.replies.forEach(reply => {
        count += countReplies(reply);
    });
    return count;
}

// --- Utilities ---
function persist(threads) {
    sessionStorage.setItem("forumThreads", JSON.stringify(threads));
}

function escapeHtml(str) {
    return str.replace(/[&<>'"]/g, tag =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[tag])
    );
}