import { countWebsiteVersion, postComplete, redirectToCompletionPage } from '../script.js';

const productDatabase = [
    { id: 1, name: 'Wireless Headphones', category: 'electronics', price: 99.99, emoji: '🎧', description: 'Premium noise-canceling headphones with 30hr battery' },
    { id: 2, name: 'Smart Watch', category: 'electronics', price: 299.99, emoji: '⌚', description: 'Fitness tracking and notifications on your wrist' },
    { id: 3, name: 'Running Shoes', category: 'sports', price: 79.99, emoji: '👟', description: 'Lightweight running shoes with superior cushioning' },
    { id: 4, name: 'Coffee Maker', category: 'home', price: 129.99, emoji: '☕', description: 'Programmable coffee maker with thermal carafe' },
    { id: 5, name: 'Laptop Stand', category: 'electronics', price: 49.99, emoji: '💻', description: 'Ergonomic aluminum laptop stand' },
    { id: 6, name: 'Yoga Mat', category: 'sports', price: 34.99, emoji: '🧘', description: 'Non-slip yoga mat with carrying strap' },
    { id: 7, name: 'Winter Jacket', category: 'clothing', price: 149.99, emoji: '🧥', description: 'Insulated winter jacket for cold weather' },
    { id: 8, name: 'Plant Pot Set', category: 'home', price: 24.99, emoji: '🪴', description: 'Set of 3 ceramic pots with drainage' },
    { id: 9, name: 'Programming Book', category: 'books', price: 44.99, emoji: '📚', description: 'Learn modern JavaScript fundamentals' },
    { id: 10, name: 'Backpack', category: 'clothing', price: 59.99, emoji: '🎒', description: 'Water-resistant backpack with laptop compartment' },
    { id: 11, name: 'Bluetooth Speaker', category: 'electronics', price: 69.99, emoji: '🔊', description: 'Portable speaker with 360° sound' },
    { id: 12, name: 'Tennis Racket', category: 'sports', price: 119.99, emoji: '🎾', description: 'Professional-grade tennis racket' },
    { id: 13, name: 'LED Desk Lamp', category: 'home', price: 39.99, emoji: '💡', description: 'Adjustable LED lamp with USB charging' },
    { id: 14, name: 'Sunglasses', category: 'clothing', price: 89.99, emoji: '🕶️', description: 'UV protection polarized sunglasses' },
    { id: 15, name: 'Cookbook', category: 'books', price: 29.99, emoji: '📖', description: 'Easy recipes for busy weeknights' },
    { id: 16, name: 'Dumbbells', category: 'sports', price: 89.99, emoji: '🏋️', description: 'Adjustable dumbbell set 5-25 lbs' },
    { id: 17, name: 'Throw Pillows', category: 'home', price: 34.99, emoji: '🛋️', description: 'Set of 2 decorative throw pillows' },
    { id: 18, name: 'Hoodie', category: 'clothing', price: 54.99, emoji: '👕', description: 'Comfortable cotton blend hoodie' },
    { id: 19, name: 'Science Fiction Novel', category: 'books', price: 16.99, emoji: '📕', description: 'Award-winning sci-fi adventure' },
    { id: 20, name: 'Mechanical Keyboard RGB', category: 'electronics', price: 139.99, emoji: '⌨️', description: 'Mechanical keyboard with RGB lighting and Cherry MX switches' },
    { id: 21, name: 'Budget Membrane Keyboard', category: 'electronics', price: 24.99, emoji: '⌨️', description: 'Affordable membrane keyboard for everyday use' },
    { id: 22, name: 'Compact 60% Keyboard', category: 'electronics', price: 79.99, emoji: '⌨️', description: 'Space-saving 60% mechanical keyboard with hot-swap switches' },
    { id: 23, name: 'Wireless Gaming Keyboard', category: 'electronics', price: 159.99, emoji: '⌨️', description: 'Low-latency wireless gaming keyboard with per-key RGB' },
    { id: 24, name: 'Ergonomic Split Keyboard', category: 'electronics', price: 189.99, emoji: '⌨️', description: 'Split ergonomic design reduces wrist strain' },
    { id: 25, name: 'Basic USB Keyboard', category: 'electronics', price: 19.99, emoji: '⌨️', description: 'Simple plug-and-play USB keyboard' },
    { id: 26, name: 'TKL Mechanical Keyboard', category: 'electronics', price: 109.99, emoji: '⌨️', description: 'Tenkeyless mechanical keyboard with blue switches' },
    { id: 27, name: 'Premium Aluminum Keyboard', category: 'electronics', price: 199.99, emoji: '⌨️', description: 'CNC machined aluminum case with custom keycaps' },
    { id: 28, name: 'RGB Membrane Keyboard', category: 'electronics', price: 44.99, emoji: '⌨️', description: 'Budget-friendly RGB membrane keyboard' },
    { id: 29, name: 'Wireless Compact Keyboard', category: 'electronics', price: 49.99, emoji: '⌨️', description: 'Bluetooth keyboard compatible with multiple devices' },
];

let currentProducts = [];
let currentQuery = '';
let cart = [];

export function init() {
    // Load shop.css
    if (!document.querySelector('link[href*="shop.css"]')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'css/shop.css';
        document.head.appendChild(link);
    }

    // Create cart button if it doesn't exist
    let tmpCartButton = document.getElementById('cart-button');
    if (!tmpCartButton) {
        tmpCartButton = document.createElement('button');
        tmpCartButton.id = 'cart-button';
        tmpCartButton.className = 'cart-button';
        tmpCartButton.innerHTML = '🛒 <span class="cart-count" id="cart-count">0</span>';
        document.body.appendChild(tmpCartButton);
    }

    // DOM elements
    const searchPage = document.getElementById('search-page');
    const productsPage = document.getElementById('products-page');
    const cartPage = document.getElementById('cart-page');
    const checkoutPage = document.getElementById('checkout-page');
    const confirmationPage = document.getElementById('confirmation-page');
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const searchFormResults = document.getElementById('search-form-results');
    const searchInputResults = document.getElementById('search-input-results');
    const productsGrid = document.getElementById('products-grid');
    const searchTerm = document.getElementById('search-term');
    const backBtn = document.getElementById('back-btn');
    const cartBackBtn = document.getElementById('cart-back-btn');
    const checkoutBackBtn = document.getElementById('checkout-back-btn');
    const continueShoppingBtn = document.getElementById('continue-shopping-btn');
    const noResults = document.getElementById('no-results');
    const sortSelect = document.getElementById('sort-select');
    const categorySelect = document.getElementById('category-select');
    const priceSelect = document.getElementById('price-select');
    const resultsCount = document.getElementById('results-count');
    const content = document.getElementById('content');
    const cartButton = document.getElementById('cart-button');
    const cartCount = document.getElementById('cart-count');
    const cartEmpty = document.getElementById('cart-empty');
    const cartContent = document.getElementById('cart-content');
    const cartItems = document.getElementById('cart-items');
    const cartSubtotal = document.getElementById('cart-subtotal');
    const cartTax = document.getElementById('cart-tax');
    const cartTotal = document.getElementById('cart-total');
    const checkoutItems = document.getElementById('checkout-items');
    const checkoutSubtotal = document.getElementById('checkout-subtotal');
    const checkoutShipping = document.getElementById('checkout-shipping');
    const checkoutTax = document.getElementById('checkout-tax');
    const checkoutTotal = document.getElementById('checkout-total');
    const placeOrderBtn = document.getElementById('place-order-btn');
    const cardNumberInput = document.getElementById('card-number');
    const expiryInput = document.getElementById('expiry');
    const cvvInput = document.getElementById('cvv');

    // Track which page we came from to return to it
    let previousPage = searchPage;

    // Cart functions
    function addToCart(productId) {
        const product = productDatabase.find(p => p.id === productId);
        if (!product) return;

        const existingItem = cart.find(item => item.id === productId);

        if (existingItem) {
            existingItem.quantity++;
        } else {
            cart.push({ ...product, quantity: 1 });
        }

        updateCartCount();
        showCartNotification(`Added ${product.name} to cart!`);
    }

    function removeFromCart(productId) {
        cart = cart.filter(item => item.id !== productId);
        updateCartCount();
        renderCart();
    }

    function updateQuantity(productId, newQuantity) {
        const item = cart.find(item => item.id === productId);
        if (item) {
            if (newQuantity <= 0) {
                removeFromCart(productId);
            } else {
                item.quantity = newQuantity;
                renderCart();
                updateCartCount();
            }
        }
    }

    function updateCartCount() {
        const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
        cartCount.textContent = totalItems;

        if (totalItems > 0) {
            cartCount.classList.add('has-items');
        } else {
            cartCount.classList.remove('has-items');
        }
    }

    function showCartNotification(message) {
        // Simple notification - could be enhanced with a toast/snackbar
        const notification = document.createElement('div');
        notification.className = 'cart-notification';
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => notification.classList.add('show'), 10);
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }

    function renderCart() {
        if (cart.length === 0) {
            cartEmpty.style.display = 'block';
            cartContent.style.display = 'none';
            return;
        }

        cartEmpty.style.display = 'none';
        cartContent.style.display = 'flex';

        cartItems.innerHTML = cart.map(item => `
            <div class="cart-item">
                <div class="cart-item-image">${item.emoji}</div>
                <div class="cart-item-details">
                    <h4>${item.name}</h4>
                    <p>${item.description}</p>
                    <div class="cart-item-price">$${item.price.toFixed(2)} each</div>
                </div>
                <div class="cart-item-controls">
                    <div class="quantity-controls">
                        <button class="qty-btn" data-product-id="${item.id}" data-action="decrease">−</button>
                        <span class="quantity">${item.quantity}</span>
                        <button class="qty-btn" data-product-id="${item.id}" data-action="increase">+</button>
                    </div>
                    <div class="item-total">$${(item.price * item.quantity).toFixed(2)}</div>
                    <button class="remove-btn" data-product-id="${item.id}">Remove</button>
                </div>
            </div>
        `).join('');

        // Calculate totals
        const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const tax = subtotal * 0.1;
        const total = subtotal + tax;

        cartSubtotal.textContent = `$${subtotal.toFixed(2)}`;
        cartTax.textContent = `$${tax.toFixed(2)}`;
        cartTotal.textContent = `$${total.toFixed(2)}`;

        // Add event listeners to cart controls
        document.querySelectorAll('.qty-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const productId = parseInt(btn.dataset.productId);
                const action = btn.dataset.action;
                const item = cart.find(i => i.id === productId);

                if (action === 'increase') {
                    updateQuantity(productId, item.quantity + 1);
                } else {
                    updateQuantity(productId, item.quantity - 1);
                }
            });
        });

        document.querySelectorAll('.remove-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const productId = parseInt(btn.dataset.productId);
                const item = cart.find(i => i.id === productId);
                removeFromCart(productId);
                showCartNotification(`Removed ${item.name} from cart`);
            });
        });
    }

    function renderCheckout() {
        const shipping = 9.99;
        const subtotal = cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
        const tax = (subtotal + shipping) * 0.1;
        const total = subtotal + shipping + tax;

        // Render order items
        checkoutItems.innerHTML = cart.map(item => `
            <div class="checkout-item">
                <div class="checkout-item-info">
                    <span class="checkout-item-emoji">${item.emoji}</span>
                    <div>
                        <div class="checkout-item-name">${item.name}</div>
                        <div class="checkout-item-qty">Qty: ${item.quantity}</div>
                    </div>
                </div>
                <div class="checkout-item-price">$${(item.price * item.quantity).toFixed(2)}</div>
            </div>
        `).join('');

        // Update totals
        checkoutSubtotal.textContent = `$${subtotal.toFixed(2)}`;
        checkoutShipping.textContent = `$${shipping.toFixed(2)}`;
        checkoutTax.textContent = `$${tax.toFixed(2)}`;
        checkoutTotal.textContent = `$${total.toFixed(2)}`;
    }

    function formatCardNumber(value) {
        const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
        const matches = v.match(/\d{4,16}/g);
        const match = (matches && matches[0]) || '';
        const parts = [];

        for (let i = 0; i < match.length; i += 4) {
            parts.push(match.substring(i, i + 4));
        }

        if (parts.length) {
            return parts.join(' ');
        } else {
            return value;
        }
    }

    function formatExpiry(value) {
        const v = value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');

        if (v.length >= 2) {
            return v.slice(0, 2) + '/' + v.slice(2, 4);
        }

        return v;
    }

    function validateCheckoutForms() {
        const shippingForm = document.getElementById('shipping-form');
        const paymentForm = document.getElementById('payment-form');

        // Check all required fields
        const allInputs = [...shippingForm.querySelectorAll('input[required]'),
        ...paymentForm.querySelectorAll('input[required]')];

        for (let input of allInputs) {
            if (!input.value.trim()) {
                input.focus();
                showCartNotification('Please fill in all required fields');
                return false;
            }
        }

        // Validate email
        const email = document.getElementById('email');
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email.value)) {
            email.focus();
            showCartNotification('Please enter a valid email address');
            return false;
        }

        // Validate card number
        const cardNumber = cardNumberInput.value.replace(/\s/g, '');
        if (cardNumber.length < 13 || cardNumber.length > 16) {
            cardNumberInput.focus();
            showCartNotification('Please enter a valid card number');
            return false;
        }

        // Validate expiry
        const expiry = expiryInput.value;
        if (!expiry.match(/^\d{2}\/\d{2}$/)) {
            expiryInput.focus();
            showCartNotification('Please enter expiry date in MM/YY format');
            return false;
        }

        // Validate CVV
        const cvv = cvvInput.value;
        if (cvv.length < 3 || cvv.length > 4) {
            cvvInput.focus();
            showCartNotification('Please enter a valid CVV');
            return false;
        }

        return true;
    }

    function placeOrder() {
        if (!validateCheckoutForms()) {
            return;
        }

        // Generate order number
        const orderNumber = 'ORD-' + Date.now().toString().slice(-8);
        const email = document.getElementById('email').value;

        // Show confirmation page
        document.getElementById('order-number').textContent = orderNumber;
        document.getElementById('confirmation-email').textContent = email;

        // Clear cart
        cart = [];
        updateCartCount();

        // Show confirmation
        showPage(confirmationPage, checkoutPage);
    }

    // Search products
    function searchProducts(query) {
        const keywords = query.toLowerCase().trim().split(/\s+/).filter(k => k.length > 0);

        if (keywords.length === 0) return productDatabase;

        return productDatabase.filter(product => {
            const searchText = `${product.name} ${product.description} ${product.category}`.toLowerCase();
            const searchWords = searchText.split(/\s+/);

            // Check if all keywords match
            return keywords.every(keyword => {
                // Direct substring match
                if (searchText.includes(keyword)) return true;

                // Check for partial word matches (handles plurals)
                return searchWords.some(word => {
                    // Check if word starts with keyword or keyword starts with word
                    // This handles: "keyboard" matches "keyboards" and vice versa
                    return word.startsWith(keyword) || keyword.startsWith(word);
                });
            });
        });
    }

    // Sort products
    function sortProducts(products, sortBy) {
        const sorted = [...products];
        switch (sortBy) {
            case 'price-low':
                return sorted.sort((a, b) => a.price - b.price);
            case 'price-high':
                return sorted.sort((a, b) => b.price - a.price);
            case 'name':
                return sorted.sort((a, b) => a.name.localeCompare(b.name));
            default:
                return sorted;
        }
    }

    // Filter by category
    function filterByCategory(products, category) {
        if (category === 'all') return products;
        return products.filter(p => p.category === category);
    }

    // Filter by price
    function filterByPrice(products, priceRange) {
        if (priceRange === 'all') return products;

        const [min, max] = priceRange.split('-').map(Number);
        return products.filter(p => p.price >= min && p.price <= max);
    }

    // Render products
    function renderProducts() {
        const sortBy = sortSelect.value;
        const category = categorySelect.value;
        const priceRange = priceSelect.value;

        let filtered = filterByCategory(currentProducts, category);
        filtered = filterByPrice(filtered, priceRange);
        let sorted = sortProducts(filtered, sortBy);

        resultsCount.textContent = `${sorted.length} result${sorted.length !== 1 ? 's' : ''}`;

        if (sorted.length === 0) {
            productsGrid.style.display = 'none';
            noResults.style.display = 'block';
            return;
        }

        productsGrid.style.display = 'grid';
        noResults.style.display = 'none';

        productsGrid.innerHTML = sorted.map(product => `
            <div class="product-card">
                <div class="product-image">${product.emoji}</div>
                <div class="product-info">
                    <h3 class="product-name">${product.name}</h3>
                    <p class="product-description">${product.description}</p>
                    <div class="product-footer">
                        <span class="product-price">$${product.price.toFixed(2)}</span>
                        <button class="add-to-cart" data-product-id="${product.id}">Add to Cart</button>
                    </div>
                </div>
            </div>
        `).join('');

        // Add event listeners to add-to-cart buttons
        document.querySelectorAll('.add-to-cart').forEach(btn => {
            btn.addEventListener('click', () => {
                const productId = parseInt(btn.dataset.productId);
                addToCart(productId);
            });
        });
    }

    // Page transition within shop
    function showPage(pageToShow, pageToHide) {
        content.classList.add('fade-out');

        setTimeout(() => {
            pageToHide.classList.remove('active');
            pageToShow.classList.add('active');
            content.classList.remove('fade-out');
            content.classList.add('fade-in');

            // Track previous page (but not if we're going to cart)
            if (pageToShow !== cartPage && pageToShow !== checkoutPage && pageToShow !== confirmationPage) {
                previousPage = pageToShow;
            }

            setTimeout(() => {
                content.classList.remove('fade-in');
            }, 400);
        }, 200);
    }

    // Perform search function
    function performSearch(query) {
        currentQuery = query;
        currentProducts = searchProducts(currentQuery);
        searchTerm.textContent = currentQuery;

        // Reset filters
        sortSelect.value = 'relevance';
        categorySelect.value = 'all';
        priceSelect.value = 'all';

        renderProducts();

        // Update the results page search input to match
        searchInputResults.value = currentQuery;
    }

    // Event listeners
    searchForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();

        if (query) {
            performSearch(query);
            showPage(productsPage, searchPage);
        }
    });

    searchFormResults.addEventListener('submit', (e) => {
        e.preventDefault();
        const query = searchInputResults.value.trim();

        if (query) {
            performSearch(query);
        }
    });

    backBtn.addEventListener('click', (e) => {
        e.preventDefault();
        showPage(searchPage, productsPage);
        searchInput.value = '';
        searchInput.focus();
    });

    cartButton.addEventListener('click', () => {
        const currentPage = document.querySelector('.shop-page.active');
        renderCart();
        showPage(cartPage, currentPage);
        postComplete({ "webpage": "shop" });
        const websiteVersion = location.pathname.split("/")[1] || "";
        if (websiteVersion === countWebsiteVersion) {
            let shopCounts = Number(localStorage.getItem("shop"));
            shopCounts++;
            localStorage.setItem("shop", shopCounts);
            if (shopCounts >= 3) {
                // Redirect to completion page
                redirectToCompletionPage("shop");
            }
        }
    });

    cartBackBtn.addEventListener('click', () => {
        showPage(previousPage, cartPage);
    });

    checkoutBackBtn.addEventListener('click', () => {
        showPage(cartPage, checkoutPage);
    });

    continueShoppingBtn.addEventListener('click', () => {
        showPage(searchPage, confirmationPage);
        searchInput.value = '';
        searchInput.focus();
    });

    placeOrderBtn.addEventListener('click', () => {
        placeOrder();
    });

    // Card number formatting
    cardNumberInput.addEventListener('input', (e) => {
        e.target.value = formatCardNumber(e.target.value);
    });

    // Expiry formatting
    expiryInput.addEventListener('input', (e) => {
        e.target.value = formatExpiry(e.target.value);
    });

    // CVV - numbers only
    cvvInput.addEventListener('input', (e) => {
        e.target.value = e.target.value.replace(/[^0-9]/g, '');
    });

    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('checkout-btn')) {
            if (cart.length === 0) {
                showCartNotification('Your cart is empty!');
                return;
            }
            renderCheckout();
            showPage(checkoutPage, cartPage);
        }
    });

    sortSelect.addEventListener('change', renderProducts);
    categorySelect.addEventListener('change', renderProducts);
    priceSelect.addEventListener('change', renderProducts);

    // Focus search input on load
    searchInput.focus();
}

// Cleanup function to remove cart button when leaving shop page
export function cleanup() {
    const cartButton = document.getElementById('cart-button');
    if (cartButton && cartButton.parentNode) {
        cartButton.parentNode.removeChild(cartButton);
    }
}
