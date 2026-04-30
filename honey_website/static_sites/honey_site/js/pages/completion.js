function sendViaXHR(endpoint, content_type, source, body_data) {
    const xmlhttp = new XMLHttpRequest();
    xmlhttp.withCredentials = true;
    xmlhttp.open("POST", endpoint, true);
    xmlhttp.setRequestHeader("Content-Type", content_type);
    xmlhttp.setRequestHeader("X-Source", source);
    xmlhttp.send(body_data);
}

function postTaskComplete(d) {
    const body_data = JSON.stringify(d);
    const content_type = "application/json;charset=UTF-8";
    const source = "completion";
    const websiteVersion = location.pathname.split("/")[1] || "";
    const endpoint = "/" + websiteVersion + "/complete";

    if (window.fetch) {
        try {
            fetch(endpoint, {
                method: "POST",
                body: body_data,
                headers: {
                    "Content-Type": content_type,
                    "X-Source": source
                },
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

function postTaskCompleteUpdate(d) {
    const body_data = JSON.stringify(d);
    const content_type = "application/json;charset=UTF-8";
    const source = "completion";
    const websiteVersion = location.pathname.split("/")[1] || "";
    const endpoint = "/" + websiteVersion + "/complete_update";

    if (window.fetch) {
        try {
            fetch(endpoint, {
                method: "POST",
                body: body_data,
                headers: {
                    "Content-Type": content_type,
                    "X-Source": source
                },
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

function editSubmission(task, oldName, oldStudentId) {
    container.innerHTML = `
        <h1>Completion submission for ${task} task</h1>
        <p>You have completed the ${task} task. Please enter your name and student ID to log your completion. Thank you for participating!</p>
        <form id="completion-form">
            <input type="text" id="student-name" placeholder="Name" value="${oldName}">
            <input type="text" id="student-id" placeholder="Student ID" value="${oldStudentId}">
            <button type="submit">Submit</button>
        </form>
    `;

    const form = document.getElementById("completion-form");
    form.addEventListener("submit", e => {
        e.preventDefault();
        const studentName = form.querySelector("input[id='student-name']").value;
        const studentId = form.querySelector("input[id='student-id']").value;
        if (oldStudentId !== studentId || oldName !== studentName) {
            postTaskCompleteUpdate({
                "oldStudentId": oldStudentId,
                "studentName": studentName,
                "studentId": studentId,
                "task": task
            });
            localStorage.setItem(`${task}-submitted`, JSON.stringify({ studentName: studentName, studentId: studentId }));
        }

        container.innerHTML = `
            <h1>Completion submission for ${task} task</h1>
            <p>Thank you for your participation, ${studentName}! Your completion for task ${task} has been logged.</p>
            <button id="edit-button">Edit Submission</button>
        `;

        // Attach event listener to the edit button
        const editButton = document.getElementById("edit-button");
        editButton.addEventListener("click", () => {
            editSubmission(task, studentName, studentId);
        });
    });
}

const task = new URLSearchParams(window.location.search).get("task");
const taskCount = Number(localStorage.getItem(task)) || 0;
const container = document.getElementById("completion-container");
if (taskCount >= 3) {
    const submitted = JSON.parse(localStorage.getItem(`${task}-submitted`)) || null;
    if (submitted !== null) {
        container.innerHTML = `
            <h1>Completion submission for ${task} task</h1>
            <p>You have already logged completion for the ${task} task. Thank you for your participation!</p>
            <button id="edit-button">Edit Submission</button>
        `;

        // Attach event listener to the edit button
        const editButton = document.getElementById("edit-button");
        editButton.addEventListener("click", () => {
            editSubmission(task, submitted.studentName, submitted.studentId);
        });
    } else {
        container.innerHTML = `
            <h1>Completion submission for ${task} task</h1>
            <p>You have completed the ${task} task. Please enter your name and student ID to log your completion. Thank you for participating!</p>
            <form id="completion-form">
                <input type="text" id="student-name" placeholder="Name">
                <input type="text" id="student-id" placeholder="Student ID">
                <button type="submit">Submit</button>
            </form>
        `;

        const form = document.getElementById("completion-form");
        form.addEventListener("submit", e => {
            e.preventDefault();
            const studentName = form.querySelector("input[id='student-name']").value;
            const studentId = form.querySelector("input[id='student-id']").value;
            postTaskComplete({ "studentName": studentName, "studentId": studentId, "task": task });
            localStorage.setItem(`${task}-submitted`, JSON.stringify({ studentName: studentName, studentId: studentId }));
            container.innerHTML = `
                <h1>Completion submission for ${task} task</h1>
                <p>Thank you for your participation, ${studentName}! Your completion for task ${task} has been logged.</p>
                <button id="edit-button">Edit Submission</button>
            `;

            // Attach event listener to the edit button
            const editButton = document.getElementById("edit-button");
            editButton.addEventListener("click", () => {
                editSubmission(task, studentName, studentId);
            });
        });
    }
} else {
    const websiteVersion = location.pathname.split("/")[1] || "";
    container.innerHTML = `
            <h1>Completion submission for ${task} task</h1>
            <p>
                You have done ${taskCount} out of 3 ${task} tasks.
                <a href="/${websiteVersion}/${task}">Go back to the task page</a>
            </p>
        `;
}