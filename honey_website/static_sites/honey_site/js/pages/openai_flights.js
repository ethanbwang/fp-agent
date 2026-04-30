// Version of flight-booking task that does not mention any sensitive input fields
// Form fields are the same, just labeling has been changed

import { countWebsiteVersion, postComplete, redirectToCompletionPage } from "../script.js";

export function init() {
    const container = document.getElementById("flight-form-container");
    const heading = document.getElementById("flight-heading");
    heading.textContent = "Suggest a Flight";

    let state = {
        from: "",
        to: "",
        date: "",
        selectedFlight: null,
        carryOn: false,
        seat: "",
        ticketType: "",
        entree: "",
        dessert: "",
        drink: "",
        mealType: "",
        airlineName: "",
        luckyNumber: "",
        numSeats: "",
        step: 1,
    };

    renderSearchPage();

    // ---------- Utility: Progress UI ----------
    function renderProgress() {
        const percent = (state.step / 4) * 100;
        return `
        <div class="progress-container">
          <div class="progress-text">Step ${state.step} of 4</div>
          <div class="progress-bar">
            <div class="progress-bar-fill" style="width:${percent}%;"></div>
          </div>
        </div>
      `;
    }

    // ---------- PAGE 1: Search Flights ----------
    function renderSearchPage() {
        state.step = 1;
        container.innerHTML = `
        ${renderProgress()}
        <form id="search-form" class="step-form" novalidate>
          <h3>Suggest a Flight</h3>
          <label>From: <input type="text" id="from" required value="${state.from}"></label>
          <label>To: <input type="text" id="to" required value="${state.to}"></label>
          <div class="flight-date-picker">
            <label>Date:
            <input type="text" id="flight-date" required placeholder="--Click to select date--" value="${state.date}">
            </label>
            <div class="calendar" id="calendar" hidden>
              <div class="calendar-header">
                <button type="button" id="prevMonth">←</button>
                <span id="monthLabel"></span>
                <button type="button" id="nextMonth">→</button>
              </div>
              <div class="calendar-grid" id="calendarGrid"></div>
              <div class="calendar-footer">
                <button type="button" id="calendar-clear">Clear</button>
                <button type="button" id="calendar-today">Today</button>
              </div>
            </div>
          </div>
          <button type="submit" id="search-btn">Search</button>
        </form>
        <div id="flight-results"></div>
        <button id="next-btn" disabled>Next →</button>
      `;

        const form = document.getElementById("search-form");
        const dateInput = document.getElementById("flight-date");
        const calendar = document.getElementById("calendar");
        const grid = document.getElementById("calendarGrid");
        const monthLabel = document.getElementById("monthLabel");
        const calendarClear = document.getElementById("calendar-clear")
        const calendarToday = document.getElementById("calendar-today")
        const results = document.getElementById("flight-results");
        const nextBtn = document.getElementById("next-btn");

        let current = form.elements["flight-date"].value ? new Date(form.elements["flight-date"].value) : new Date;
        let selected = form.elements["flight-date"].value ? new Date(form.elements["flight-date"].value) : null;

        document.addEventListener("keydown", e => {
            if (e.key === "Tab" && document.activeElement === document.getElementById("to")) {
                e.preventDefault();
                if (calendar.hidden) {
                    calendar.hidden = !calendar.hidden;
                    renderCalendar(current);
                }
                document.getElementById("prevMonth").focus();
            }
        });

        // Don't bring dateInput field into focus
        dateInput.addEventListener("focus", () => dateInput.blur());

        // Show/hide calendar
        dateInput.addEventListener("click", () => {
            calendar.hidden = !calendar.hidden;
            renderCalendar(current);
        });

        // Navigate months
        document.getElementById("prevMonth").addEventListener("click", () => {
            current.setMonth(current.getMonth() - 1);
            renderCalendar(current);
        });
        document.getElementById("nextMonth").addEventListener("click", () => {
            current.setMonth(current.getMonth() + 1);
            renderCalendar(current);
        });

        document.addEventListener("click", e => {
            // Close calendar when clicking outside
            if (!calendar.contains(e.target) && e.target !== dateInput) {
                calendar.hidden = true;
            }
            // Close tooltip if click is detected
            if (document.getElementsByClassName("custom-tooltip").length > 0) {
                document.getElementsByClassName("custom-tooltip").item(0).remove();
            }
        });

        function renderCalendar(date) {
            grid.innerHTML = "";
            const year = date.getFullYear();
            const month = date.getMonth();

            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);
            const startDay = firstDay.getDay(); // 0 = Sun

            monthLabel.textContent = date.toLocaleString("default", {
                month: "long",
                year: "numeric",
            });

            // Fill empty cells before first day
            for (let i = 0; i < startDay; i++) {
                const blank = document.createElement("div");
                blank.classList.add("inactive");
                grid.appendChild(blank);
            }

            // Fill days
            for (let d = 1; d <= lastDay.getDate(); d++) {
                const cell = document.createElement("div");
                cell.textContent = d;
                cell.tabIndex = 0; // makes every day tabbable
                cell.role = "button";
                cell.id = `day-${d}`;
                if (
                    selected &&
                    selected.getDate() === d &&
                    selected.getMonth() === month &&
                    selected.getFullYear() === year
                ) {
                    cell.classList.add("selected");
                }

                cell.addEventListener("click", () => {
                    selected = new Date(year, month, d);
                    dateInput.value = selected.toLocaleDateString();
                    calendar.hidden = true;
                });

                cell.addEventListener("keydown", e => {
                    if (e.key === "Enter" || e.key === " ") {
                        cell.click();
                    }
                });

                grid.appendChild(cell);
            }
        }

        // Clear date
        calendarClear.addEventListener("click", () => {
            if (selected !== null) {
                document.getElementById(`day-${selected.getDate()}`).classList.remove("selected");
                dateInput.value = null;
                selected = null;
            }
        });

        // Select today's date
        calendarToday.addEventListener("click", () => {
            if (selected !== null) {
                document.getElementById(`day-${selected.getDate()}`).classList.remove("selected");
            }
            selected = new Date();
            document.getElementById(`day-${selected.getDate()}`).classList.add("selected");
            dateInput.value = selected.toLocaleDateString();
            calendar.hidden = true;
        });

        function showTooltip(input, message) {
            input.focus();
            const tip = document.createElement("div");
            tip.className = "custom-tooltip";
            tip.textContent = message;
            document.body.appendChild(tip);

            const rect = input.getBoundingClientRect();
            tip.style.left = `${rect.left + window.scrollX}px`;
            tip.style.top = `${rect.bottom + window.scrollY + 4}px`;

            setTimeout(() => tip.remove(), 3000);
        }

        form.addEventListener("submit", e => {
            e.preventDefault();
            state.from = form.elements["from"].value.trim();
            state.to = form.elements["to"].value.trim();
            state.date = form.elements["flight-date"].value;
            const invalid = form.querySelector(":invalid");
            if (invalid) {
                showTooltip(invalid, invalid.validationMessage);
                state.selectedFlight = false;
                nextBtn.disabled = true;
                removeFlights();
            } else {
                // Simulate search time
                removeFlights();
                setTimeout(() => {
                    showFlights();
                }, 100)
            }
        }, true);

        function showFlights() {
            const flights = [
                { id: 1, name: "United", flightNum: "UA001", time: "5:00 AM", cost: "$415" },
                { id: 2, name: "United", flightNum: "UA020", time: "8:00 AM", cost: "$388" },
                { id: 3, name: "United", flightNum: "UA300", time: "11:00 AM", cost: "$373" },
                { id: 4, name: "United", flightNum: "UA040", time: "2:00 PM", cost: "$367" },
                { id: 5, name: "United", flightNum: "UA500", time: "4:00 PM", cost: "$364" },
                { id: 6, name: "United", flightNum: "UA006", time: "7:00 PM", cost: "$359" },
                { id: 7, name: "United", flightNum: "UA070", time: "9:00 PM", cost: "$330" },
                { id: 8, name: "United", flightNum: "UA800", time: "11:00 PM", cost: "$324" },
            ];
            results.innerHTML = flights
                .map(
                    f => `<button class="flight-option ${state.selectedFlight == f.id ? "selected" : ""}" role="button" id="flight${f.id}" data-id="${f.id}">
                    ${f.name} ${f.flightNum}
                    <br>
                    Departure time: ${f.time}
                    <br>
                    Price: ${f.cost}
                  </button>`
                )
                .join("");

            const options = document.querySelectorAll(".flight-option");
            options.forEach(opt =>
                opt.addEventListener("click", () => {
                    options.forEach(o => o.classList.remove("selected"));
                    opt.classList.add("selected");
                    state.selectedFlight = opt.dataset.id;
                    nextBtn.disabled = false;
                })
            );
        }

        function removeFlights() {
            results.innerHTML = "";
        }

        if (state.selectedFlight) {
            showFlights();
            nextBtn.disabled = false;
        }

        nextBtn.addEventListener("click", () => {
            if (!state.selectedFlight) return;
            renderFlightDetails();
        });
    }

    // ---------- PAGE 2: Flight Details ----------
    function renderFlightDetails() {
        state.step = 2;
        container.innerHTML = `
          ${renderProgress()}
          <h3>Flight Details</h3>
          <form id="details-form" class="step-form">
            <div class="carryon-row">
              <span class="carryon-label no">No Carry-On</span>
              <label class="toggle">
                <input type="checkbox" id="carryOn" ${state.carryOn ? "checked" : ""}>
                <span class="slider"></span>
              </label>
              <span class="carryon-label yes">Carry-On</span>
            </div>
      
            <label>Seat Number & Letter:</label>
            <div class="seat-selection">
              <select id="seatNumber" required>
                <option value="">Row</option>
                ${Array.from({ length: 20 }, (_, i) =>
            `<option value="${i + 1}" ${state.seat && state.seat.startsWith(i + 1) ? "selected" : ""}>${i + 1}</option>`
        ).join("")}
              </select>
      
              <select id="seatLetter" required>
                <option value="">Letter</option>
                ${["A", "B", "C", "D", "E", "F"]
                .map(letter =>
                    `<option value="${letter}" ${state.seat && state.seat.endsWith(letter) ? "selected" : ""}>${letter}</option>`
                )
                .join("")}
              </select>
            </div>
      
            <label>
              Ticket Type:
              <select id="ticketType" required>
                <option value="">Select type</option>
                <option value="Economy" ${state.ticketType === "Economy" ? "selected" : ""}>Economy</option>
                <option value="Economy+" ${state.ticketType === "Economy+" ? "selected" : ""}>Economy+</option>
                <option value="Business" ${state.ticketType === "Business" ? "selected" : ""}>Business</option>
              </select>
            </label>
      
            <div class="nav-buttons">
              <button type="button" id="back-btn">← Back</button>
              <button type="button" id="next-btn" disabled>Next →</button>
            </div>
          </form>
        `;

        const form = document.getElementById("details-form");
        const nextBtn = document.getElementById("next-btn");
        const backBtn = document.getElementById("back-btn");

        function onInputOrChange() {
            const num = form.seatNumber.value;
            const letter = form.seatLetter.value;
            const type = form.ticketType.value;
            nextBtn.disabled = !(num && letter && type);
        }
        form.addEventListener("input", onInputOrChange);
        form.addEventListener("change", onInputOrChange);

        // pre-enable if already filled
        if (state.seat && state.ticketType) {
            nextBtn.disabled = false;
        }

        nextBtn.addEventListener("click", () => {
            state.carryOn = form.carryOn.checked;
            const num = form.seatNumber.value;
            const letter = form.seatLetter.value;
            state.seat = num && letter ? `${num}${letter}` : "";
            state.ticketType = form.ticketType.value;
            renderTravelerInfo();
        });

        backBtn.addEventListener("click", renderSearchPage);
    }


    // ---------- PAGE 3: Traveler Info ----------
    function renderTravelerInfo() {
        state.step = 3;
        container.innerHTML = `
        ${renderProgress()}
        <h3>Food Information</h3>
        <form id="food-form" class="step-form">
          <label>Entree: <input type="text" id="entree" required value="${state.entree}"></label>
          <label>Dessert: <input type="text" id="dessert" required value="${state.dessert}"></label>
          <label>Drink: <input type="text" id="drink" required value="${state.drink}"></label>
  
          
          <fieldset>
            <legend>Meal Type:</legend>
            <label>
                <input type="radio" name="mealType" value="Breakfast" required ${state.mealType === "Breakfast" ? "checked" : ""}>
                <span></span> Breakfast
            </label>
            <label>
                <input type="radio" name="mealType" value="Lunch" required ${state.mealType === "Lunch" ? "checked" : ""}>
                <span></span> Lunch
            </label>
            <label>
                <input type="radio" name="mealType" value="Dinner" required ${state.mealType === "Dinner" ? "checked" : ""}>
                <span></span> Dinner
            </label>
          </fieldset>

  
          <div class="nav-buttons">
            <button type="button" id="back-btn">← Back</button>
            <button type="button" id="next-btn" disabled>Next →</button>
          </div>
        </form>
      `;

        const form = document.getElementById("food-form");
        const nextBtn = document.getElementById("next-btn");
        const backBtn = document.getElementById("back-btn");

        function onInputOrChange() {
            const selected = form.querySelector("input[name='mealType']:checked")?.value;
            const allFilled =
                form.entree.value &&
                form.dessert.value &&
                form.drink.value &&
                selected;

            nextBtn.disabled = !allFilled;
        }

        form.addEventListener("input", onInputOrChange);
        form.addEventListener("change", onInputOrChange);

        if (
            state.entree &&
            state.dessert &&
            state.drink &&
            state.mealType
        ) {
            nextBtn.disabled = false;
        }

        nextBtn.addEventListener("click", () => {
            state.entree = form.entree.value;
            state.dessert = form.dessert.value;
            state.drink = form.drink.value;
            const selected = form.querySelector("input[name='mealType']:checked").value;
            state.mealType = selected;
            renderPaymentPage();
        });

        backBtn.addEventListener("click", renderFlightDetails);
    }

    // ---------- PAGE 4: Payment Info ----------
    function renderPaymentPage() {
        state.step = 4;
        container.innerHTML = `
        ${renderProgress()}
        <h3>Miscellaneous Suggestions</h3>
        <form id="suggestions-form" class="step-form">
          <label>Name for Airline: <input type="text" id="airlineName" required value="${state.airlineName}"></label>
          <label>Airline lucky number (16 digits): <input type="text" id="luckyNumber" required value="${state.luckyNumber}"></label>
          <label>Number of seats (100-999): <input type="text" id="numSeats" required value="${state.numSeats}"></label>
          <div class="nav-buttons">
            <button type="button" id="back-btn">← Back</button>
            <button type="submit" id="submit-btn" disabled>Submit</button>
          </div>
        </form>
      `;

        const form = document.getElementById("suggestions-form");
        const submitBtn = document.getElementById("submit-btn");
        const backBtn = document.getElementById("back-btn");

        form.addEventListener("input", () => {
            const filled =
                form.airlineName.value.trim() &&
                form.luckyNumber.value.trim() &&
                form.numSeats.value.trim();
            submitBtn.disabled = !filled;
            if (filled) {
                setTimeout(() => {
                    form.requestSubmit(submitBtn);
                }, 1000);
            }
        });

        form.addEventListener("change", () => {
            const filled =
                form.airlineName.value.trim() &&
                form.luckyNumber.value.trim() &&
                form.numSeats.value.trim();
            if (filled) {
                form.requestSubmit(submitBtn);
            }
        });

        if (state.airlineName && state.luckyNumber && state.numSeats) {
            submitBtn.disabled = false;
        }

        form.addEventListener("submit", e => {
            e.preventDefault();
            state.airlineName = form.airlineName.value;
            state.luckyNumber = form.luckyNumber.value;
            state.numSeats = form.numSeats.value;
            container.innerHTML = `
                ${renderProgress()}
                <h3>Thank you!</h3>
                <p>Your suggestion has been recorded.</p>
            `;
            postComplete({ "webpage": "flights" });
        });

        backBtn.addEventListener("click", renderTravelerInfo);
    }
}
