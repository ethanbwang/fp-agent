import { countWebsiteVersion, postComplete, redirectToCompletionPage } from '../script.js';

export function init() {
    // Load organize.css
    if (!document.querySelector('link[href*="sort.css"]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'css/sort.css';
        document.head.appendChild(link);
    }

    // Word bank - diverse items that could fit different categories
    const wordBank = [
        "Tree", "Computer", "Dog", "Cloud", "Smartphone",
        "River", "Fire", "Garden", "Bridge", "Mountain",
        "Sunset", "Plastic", "Rain", "Skyscraper", "Thunder",
        "Diamond", "Ocean", "Bread", "Lightning", "Park",
        "Glass", "Wind", "Electricity", "Farm", "Volcano",
        "Satellite", "Snow", "Cotton", "Highway", "Cave",
        "Radio", "Earthquake", "Paper", "Desert", "Dam",
        "Coral", "Concrete", "Fog", "Canal", "Forest", "Pearl",
        "Cheese", "Ice", "Fabric", "Trail", "Lake", "Wax"
    ];

    let isEditing = false;
    let draggedCard = null;

    const editBtn = document.getElementById('edit-btn');
    const cardsPool = document.getElementById('cards-pool');
    const columns = document.querySelectorAll('.column');

    // Initialize with 8 random words
    function initializeCards() {
        cardsPool.innerHTML = '';
        const selectedWords = getRandomWords(wordBank, 8);

        selectedWords.forEach((word) => {
            const card = createCard(word);
            card.id = `card-${word}`;
            cardsPool.appendChild(card);
        });
    }

    // Get random words from the bank
    function getRandomWords(bank, count) {
        let words = [];
        while (words.length < count) {
            const word = bank[Math.floor(Math.random() * bank.length)];
            if (!words.includes(word)) {
                words.push(word);
            }
        }
        return words;
    }

    // Create a card element
    function createCard(word) {
        const card = document.createElement('div');
        card.className = 'card';
        card.textContent = word;
        card.draggable = false;
        card.dataset.word = word;

        return card;
    }

    // Toggle edit mode
    editBtn.addEventListener('click', () => {
        if (isEditing) {
            // Save and lock
            isEditing = false;
            editBtn.textContent = 'Edit';
            editBtn.classList.remove('saving');
            lockAllCards();
            removeDropListeners();
            postComplete({ "webpage": "sort" });
            const websiteVersion = location.pathname.split("/")[1] || "";
            if (websiteVersion === countWebsiteVersion) {
                let sortCounts = Number(localStorage.getItem("sort"));
                sortCounts++;
                localStorage.setItem("sort", sortCounts);
                if (sortCounts >= 3) {
                    // Redirect to completion page
                    redirectToCompletionPage("sort");
                }
            }
        } else {
            // Enable editing
            isEditing = true;
            editBtn.textContent = 'Save';
            editBtn.classList.add('saving');
            unlockAllCards();
            addDropListeners();
        }
    });

    function lockAllCards() {
        const allCards = document.querySelectorAll('.card');
        allCards.forEach(card => {
            card.draggable = false;
            card.classList.add('locked');
        });
    }

    function unlockAllCards() {
        const allCards = document.querySelectorAll('.card');
        allCards.forEach(card => {
            card.draggable = true;
            card.classList.remove('locked');
            addCardDragListeners(card);
        });
    }

    function addCardDragListeners(card) {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
    }

    function handleDragStart(e) {
        if (!isEditing) return;

        draggedCard = e.target;
        e.target.classList.add('dragging');
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', e.target.innerHTML);
    }

    function handleDragEnd(e) {
        e.target.classList.remove('dragging');
        draggedCard = null;
    }

    function addDropListeners() {
        // Add listeners to all columns and the pool
        [...columns, cardsPool].forEach(zone => {
            zone.addEventListener('dragover', handleDragOver);
            zone.addEventListener('dragenter', handleDragEnter);
            zone.addEventListener('dragleave', handleDragLeave);
            zone.addEventListener('drop', handleDrop);
        });
    }

    function removeDropListeners() {
        [...columns, cardsPool].forEach(zone => {
            zone.removeEventListener('dragover', handleDragOver);
            zone.removeEventListener('dragenter', handleDragEnter);
            zone.removeEventListener('dragleave', handleDragLeave);
            zone.removeEventListener('drop', handleDrop);
        });
    }

    function handleDragOver(e) {
        if (!isEditing) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
        return false;
    }

    function handleDragEnter(e) {
        if (!isEditing) return;
        const column = e.target.closest('.column');
        if (column) {
            column.classList.add('drag-over');
        } else if (e.target.classList.contains('cards-pool')) {
            e.target.classList.add('drag-over');
        }
    }

    function handleDragLeave(e) {
        if (!isEditing) return;
        const column = e.target.closest('.column');
        if (column) {
            // Only remove if we're actually leaving the entire column
            if (!column.contains(e.relatedTarget)) {
                column.classList.remove('drag-over');
            }
        } else if (e.target.classList.contains('cards-pool')) {
            if (!e.target.contains(e.relatedTarget)) {
                e.target.classList.remove('drag-over');
            }
        }
    }

    function handleDrop(e) {
        if (!isEditing || !draggedCard) return;

        e.stopPropagation();
        e.preventDefault();

        const column = e.target.closest('.column');
        const dropZone = column
            ? column.querySelector('.column-content')
            : (e.target.classList.contains('cards-pool') ? e.target : e.target.closest('.cards-pool'));

        if (dropZone && draggedCard.parentNode !== dropZone) {
            dropZone.appendChild(draggedCard);
        }

        // Remove drag-over class from all zones
        [...columns, cardsPool].forEach(zone => {
            zone.classList.remove('drag-over');
        });

        // Update pool empty state
        updatePoolState();

        return false;
    }

    function updatePoolState() {
        if (cardsPool.children.length === 0) {
            cardsPool.classList.add('empty');
        } else {
            cardsPool.classList.remove('empty');
        }
    }

    // Initialize the page
    initializeCards();
    if (!isEditing) {
        lockAllCards();
    } else {
        unlockAllCards();
    }
    updatePoolState();
}

// Cleanup function to remove event listeners when navigating away
export function cleanup() {
    // Remove any global event listeners if needed
    console.log('Cleaning up sort page');
}
