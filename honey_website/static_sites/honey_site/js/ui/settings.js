export function openSettings(popup, overlay) {
    popup.innerHTML = `
      <h3>Settings</h3>
      <label>
        Theme:
        <select id="theme">
          <option>Light</option>
          <option>Dark</option>
        </select>
      </label>
      <button id="close-settings">Close</button>
    `;

    document.getElementById("close-settings").addEventListener("click", () => {
        popup.classList.remove("show");
        overlay.classList.remove("show");
    });

    overlay.addEventListener("click", () => {
        popup.classList.remove("show");
        overlay.classList.remove("show");
    });
}
