export function init() {
    // Load forums.css
    if (!document.querySelector('link[href*="forums.css"]')) {
        const pathPrepend = "/" + (location.pathname.split("/")[1] || "");
        const link = document.createElement('link');
        link.rel = "stylesheet";
        link.href = pathPrepend + "/css/forums.css";
        document.head.appendChild(link);
    }

    const threadsContainer = document.getElementById("forum-threads");
    const form = document.getElementById("new-post-form");
    const usernameInput = document.getElementById("post-username");
    const titleInput = document.getElementById("post-title");
    const bodyInput = document.getElementById("post-body");

    const base_thread =
    {
        id: "thread-1",
        username: "Jordan",
        title: "Which AI chatbot do you prefer - Claude, ChatGPT, or others?",
        body: "I've been using both Claude and ChatGPT for different tasks and I'm curious what others think. They each seem to have their strengths. What's your go-to AI assistant and why?",
        time: "12/4/2025, 2:30:00 PM",
        replies: [
            {
                id: "reply-1",
                username: "frontend_jenny",
                body: "I switch between them depending on the task. Claude seems better for longer, more nuanced conversations and coding. ChatGPT is great for quick answers and has a huge plugin ecosystem.",
                time: "12/4/2025, 3:15:00 PM",
                replies: [
                    {
                        id: "reply-2",
                        username: "devops_guru",
                        body: "That's interesting! I've noticed Claude is really good at following complex instructions too.",
                        time: "12/4/2025, 4:00:00 PM",
                        replies: []
                    }
                ]
            },
            {
                id: "reply-3",
                username: "techie_sarah92",
                body: "Claude all the way! The responses feel more natural and thoughtful. Plus the longer context window is a game-changer for working with large documents.",
                time: "12/4/2025, 5:20:00 PM",
                replies: []
            },
            {
                id: "reply-4",
                username: "Anonymous",
                body: "Don't forget about Gemini! Google's AI is getting really good, especially for research and fact-checking since it has web search built in.",
                time: "12/5/2025, 9:45:00 AM",
                replies: []
            }
        ]
    };

    // Load from sessionStorage
    let local_threads = JSON.parse(sessionStorage.getItem("forumThreads") || "[]");
    if (!local_threads || !local_threads.some(thread => thread.id === "thread-1")) {
        local_threads = [base_thread, ...local_threads];
    }

    const threads = local_threads;
    persist(threads);


    renderThreadList(threadsContainer, threads);

    // Create a new top-level thread
    form.addEventListener("submit", e => {
        e.preventDefault();
        const newThread = {
            id: crypto.randomUUID(),
            username: usernameInput.value.trim() || "Anonymous",
            title: titleInput.value.trim(),
            body: bodyInput.value.trim(),
            time: new Date().toLocaleString(),
            replies: [],
        };
        threads.unshift(newThread);
        persist(threads);
        renderThreadList(threadsContainer, threads);
        titleInput.value = "";
        bodyInput.value = "";
        usernameInput.value = "";
    });
}

// --- Rendering thread list ---
function renderThreadList(container, threads) {
    if (!threads.length) {
        container.innerHTML = `<p class="dim">No discussions yet. Start one below!</p>`;
        return;
    }

    container.innerHTML = threads.map(thread => {
        const replyCount = countReplies(thread);
        const preview = thread.body.length > 150
            ? thread.body.substring(0, 150) + "..."
            : thread.body;

        return `
            <article class="thread-item">
                <a href="/forums/${thread.id}" data-route="/forums/${thread.id}" class="thread-link">
                    <h3>${escapeHtml(thread.title)}</h3>
                    <p class="thread-preview">${escapeHtml(preview)}</p>
                    <div class="thread-meta">
                        <span class="thread-author">By ${escapeHtml(thread.username)}</span>
                        <span class="thread-time">${thread.time}</span>
                        <span class="thread-replies">${replyCount} ${replyCount === 1 ? 'reply' : 'replies'}</span>
                    </div>
                </a>
            </article>
        `;
    }).join("");
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