import { countWebsiteVersion, postComplete, redirectToCompletionPage } from "../script.js";

export function init() {
  const container = document.getElementById("flight-form-container");

  let state = {
    from: "",
    to: "",
    date: "",
    selectedFlight: null,
    carryOn: false,
    seat: "",
    ticketType: "",
    name: "",
    email: "",
    phone: "",
    sex: "",
    otherSex: "",
    cardNumber: "",
    cardName: "",
    securityCode: "",
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
          <h3>Book a Flight</h3>
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
        <h3>Traveler Information</h3>
        <form id="traveler-form" class="step-form">
          <label>Name: <input type="text" id="name" required value="${state.name}"></label>
          <label>Email: <input type="email" id="email" required value="${state.email}"></label>
          <label>Phone: <input type="tel" id="phone" required value="${state.phone}"></label>
  
          
          <fieldset>
            <legend>Biological Sex:</legend>
            <label>
                <input type="radio" name="sex" value="M" required ${state.sex === "M" ? "checked" : ""}>
                <span></span> M
            </label>
            <label>
                <input type="radio" name="sex" value="F" required ${state.sex === "F" ? "checked" : ""}>
                <span></span> F
            </label>
            <label>
                <input type="radio" name="sex" value="Other" required ${state.sex === "Other" ? "checked" : ""}>
                <span></span> Other
            </label>
            <input type="text" id="other-sex" placeholder="Please specify" style="display:${state.sex === "Other" ? "block" : "none"};" value="${state.otherSex}">
          </fieldset>

  
          <div class="nav-buttons">
            <button type="button" id="back-btn">← Back</button>
            <button type="button" id="next-btn" disabled>Next →</button>
          </div>
        </form>
      `;

    const form = document.getElementById("traveler-form");
    const nextBtn = document.getElementById("next-btn");
    const backBtn = document.getElementById("back-btn");
    const otherSex = document.getElementById("other-sex");

    function onInputOrChange() {
      const selected = form.querySelector("input[name='sex']:checked")?.value;
      const allFilled =
        form.name.value &&
        form.email.value &&
        form.phone.value &&
        selected;

      if (selected === "Other") {
        otherSex.style.display = "block";
        nextBtn.disabled = !(allFilled && otherSex.value.trim());
      } else {
        otherSex.style.display = "none";
        nextBtn.disabled = !allFilled;
      }
    }

    form.addEventListener("input", onInputOrChange);
    form.addEventListener("change", onInputOrChange);

    if (
      state.name &&
      state.email &&
      state.phone &&
      state.sex &&
      (state.sex !== "Other" || state.otherSex)
    ) {
      nextBtn.disabled = false;
    }

    nextBtn.addEventListener("click", () => {
      state.name = form.name.value;
      state.email = form.email.value;
      state.phone = form.phone.value;
      const selected = form.querySelector("input[name='sex']:checked").value;
      state.sex = selected;
      state.otherSex = selected === "Other" ? otherSex.value.trim() : "";
      renderPaymentPage();
    });

    backBtn.addEventListener("click", renderFlightDetails);
  }

  // ---------- PAGE 4: Payment Info ----------
  function renderPaymentPage() {
    state.step = 4;
    container.innerHTML = `
        ${renderProgress()}
        <h3>Payment Information</h3>
        <form id="payment-form" class="step-form">
          <label>Card Number: <input type="text" id="cardNumber" required value="${state.cardNumber}"></label>
          <label>Name on Card: <input type="text" id="cardName" required value="${state.cardName}"></label>
          <label>Security Code: <input type="text" id="securityCode" required value="${state.securityCode}"></label>
          <div class="nav-buttons">
            <button type="button" id="back-btn">← Back</button>
            <button type="submit" id="book-btn" disabled>Book Flight</button>
          </div>
        </form>
      `;

    const form = document.getElementById("payment-form");
    const bookBtn = document.getElementById("book-btn");
    const backBtn = document.getElementById("back-btn");

    form.addEventListener("input", () => {
      const filled =
        form.cardNumber.value.trim() &&
        form.cardName.value.trim() &&
        form.securityCode.value.trim();
      bookBtn.disabled = !filled;
    });

    if (state.cardNumber && state.cardName && state.securityCode) {
      bookBtn.disabled = false;
    }

    form.addEventListener("submit", e => {
      e.preventDefault();
      state.cardNumber = form.cardNumber.value;
      state.cardName = form.cardName.value;
      state.securityCode = form.securityCode.value;
      container.innerHTML = `
          ${renderProgress()}
          <h3>Thank you, ${state.name}!</h3>
          <p>Your flight has been successfully booked.</p>
        `;
      postComplete({ "webpage": "flights" });
      const websiteVersion = location.pathname.split("/")[1] || "";
      if (websiteVersion === countWebsiteVersion) {
        let flightsCounts = Number(localStorage.getItem("flights"));
        flightsCounts++;
        localStorage.setItem("flights", flightsCounts);
        if (flightsCounts >= 3) {
          // Redirect to completion page
          redirectToCompletionPage("flights");
        }
      }
    });

    backBtn.addEventListener("click", renderTravelerInfo);
  }
}
