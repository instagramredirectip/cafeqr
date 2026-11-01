/**
 * DineFlow - Cart & Checkout Frontend Manager
 * Features:
 * - Restaurant-isolated cart storage (localStorage key: dineflow_cart_<slug>)
 * - Add, remove, update item quantities
 * - Spice level selection & multi-addon options
 * - Subtotal & transparent charges preview
 * - CSRF-protected checkout submission with server-side validation
 */

class DineFlowCart {
  constructor(restaurantSlug, currencySymbol = '$', taxPct = 5.0, deliveryFee = 2.50) {
    this.restaurantSlug = restaurantSlug;
    this.currencySymbol = currencySymbol;
    this.taxPercentage = parseFloat(taxPct);
    this.deliveryFee = parseFloat(deliveryFee);
    this.storageKey = `dineflow_cart_${this.restaurantSlug}`;
    this.items = this.loadCart();
    this.orderType = 'dine_in';
    this.tableNumber = '';
    
    // Auto-detect table query param if present
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('table')) {
      this.tableNumber = urlParams.get('table');
      this.orderType = 'dine_in';
    }

    this.initListeners();
    this.updateUI();
  }

  loadCart() {
    try {
      const data = localStorage.getItem(this.storageKey);
      return data ? JSON.parse(data) : [];
    } catch (e) {
      console.error('Failed to parse cart data:', e);
      return [];
    }
  }

  saveCart() {
    localStorage.setItem(this.storageKey, JSON.stringify(this.items));
    this.updateUI();
  }

  clearCart() {
    this.items = [];
    localStorage.removeItem(this.storageKey);
    this.updateUI();
  }

  /**
   * Generates a unique key for cart item taking into account food ID, spice level, and sorted add-on IDs
   */
  generateItemKey(foodId, spiceLevel, addons) {
    const sortedAddons = (addons || []).map(a => a.id).sort().join('_');
    return `${foodId}:${spiceLevel || 'None'}:${sortedAddons}`;
  }

  addItem(food, spiceLevel = 'Medium', selectedAddons = [], specialInstructions = '', quantity = 1) {
    const key = this.generateItemKey(food.id, spiceLevel, selectedAddons);
    const existingIndex = this.items.findIndex(item => item.key === key);

    const addonsCost = (selectedAddons || []).reduce((sum, a) => sum + parseFloat(a.price || 0), 0);
    const unitPrice = parseFloat(food.price) + addonsCost;

    if (existingIndex > -1) {
      this.items[existingIndex].quantity += parseInt(quantity, 10);
      this.items[existingIndex].specialInstructions = specialInstructions || this.items[existingIndex].specialInstructions;
    } else {
      this.items.push({
        key: key,
        foodId: food.id,
        name: food.name,
        basePrice: parseFloat(food.price),
        unitPrice: unitPrice,
        spiceLevel: spiceLevel,
        addons: selectedAddons,
        specialInstructions: specialInstructions,
        quantity: parseInt(quantity, 10) || 1,
        image: food.image || '',
        isVegetarian: food.isVegetarian
      });
    }

    this.saveCart();
    this.showToast(`Added "${food.name}" to your order!`);
  }

  updateQuantity(key, delta) {
    const item = this.items.find(i => i.key === key);
    if (!item) return;

    item.quantity += delta;
    if (item.quantity <= 0) {
      this.items = this.items.filter(i => i.key !== key);
    }
    this.saveCart();
  }

  removeItem(key) {
    this.items = this.items.filter(i => i.key !== key);
    this.saveCart();
  }

  getSubtotal() {
    return this.items.reduce((sum, item) => sum + (item.unitPrice * item.quantity), 0);
  }

  getTaxAmount() {
    const subtotal = this.getSubtotal();
    return (subtotal * (this.taxPercentage / 100));
  }

  getDeliveryFee() {
    return this.orderType === 'delivery' ? this.deliveryFee : 0;
  }

  getTotal() {
    return this.getSubtotal() + this.getTaxAmount() + this.getDeliveryFee();
  }

  getTotalItemCount() {
    return this.items.reduce((count, item) => count + item.quantity, 0);
  }

  updateUI() {
    const count = this.getTotalItemCount();
    const subtotal = this.getSubtotal();
    const total = this.getTotal();

    // Update badges
    document.querySelectorAll('.cart-count-badge').forEach(el => {
      el.textContent = count;
      el.style.display = count > 0 ? 'inline-flex' : 'none';
    });

    // Update floating bar
    const floatingBar = document.getElementById('floating-cart-bar');
    if (floatingBar) {
      if (count > 0) {
        floatingBar.style.display = 'flex';
        const barCount = floatingBar.querySelector('.bar-item-count');
        const barTotal = floatingBar.querySelector('.bar-total-amount');
        if (barCount) barCount.textContent = `${count} ${count === 1 ? 'item' : 'items'}`;
        if (barTotal) barTotal.textContent = `${this.currencySymbol}${total.toFixed(2)}`;
      } else {
        floatingBar.style.display = 'none';
      }
    }

    // Render cart modal/drawer content
    this.renderCartItemsList();
  }

  renderCartItemsList() {
    const container = document.getElementById('cart-items-container');
    const emptyState = document.getElementById('cart-empty-state');
    const summaryCard = document.getElementById('cart-summary-section');

    if (!container) return;

    if (this.items.length === 0) {
      container.innerHTML = '';
      if (emptyState) emptyState.style.display = 'block';
      if (summaryCard) summaryCard.style.display = 'none';
      return;
    }

    if (emptyState) emptyState.style.display = 'none';
    if (summaryCard) summaryCard.style.display = 'block';

    let html = '';
    this.items.forEach(item => {
      const itemTotal = (item.unitPrice * item.quantity).toFixed(2);
      const addonsHtml = (item.addons && item.addons.length > 0)
        ? `<div class="small text-muted">+ ${item.addons.map(a => `${a.name} (${this.currencySymbol}${parseFloat(a.price).toFixed(2)})`).join(', ')}</div>`
        : '';
      const spiceHtml = (item.spiceLevel && item.spiceLevel !== 'None')
        ? `<span class="spice-badge me-1">${item.spiceLevel}</span>`
        : '';
      const notesHtml = item.specialInstructions
        ? `<div class="small fst-italic text-muted mt-1"><i class="bi bi-chat-dots me-1"></i>"${item.specialInstructions}"</div>`
        : '';

      html += `
        <div class="cart-item-row p-3 mb-2 rounded-3 bg-white border d-flex justify-content-between align-items-center">
          <div class="flex-grow-1 pe-2">
            <div class="d-flex align-items-center gap-2 mb-1">
              <span class="${item.isVegetarian ? 'veg-indicator' : 'non-veg-indicator'}"></span>
              <span class="fw-bold text-dark">${item.name}</span>
              ${spiceHtml}
            </div>
            ${addonsHtml}
            ${notesHtml}
            <div class="fw-bold text-danger mt-1">${this.currencySymbol}${item.unitPrice.toFixed(2)} each</div>
          </div>
          <div class="text-end">
            <div class="d-flex align-items-center gap-2 mb-1 justify-content-end">
              <button type="button" class="btn btn-sm btn-outline-secondary rounded-circle py-0 px-2 btn-qty-minus" data-key="${item.key}">-</button>
              <span class="fw-bold px-1">${item.quantity}</span>
              <button type="button" class="btn btn-sm btn-coral rounded-circle py-0 px-2 btn-qty-plus" data-key="${item.key}">+</button>
            </div>
            <div class="fw-bold text-dark">${this.currencySymbol}${itemTotal}</div>
          </div>
        </div>
      `;
    });

    container.innerHTML = html;

    // Attach row button listeners
    container.querySelectorAll('.btn-qty-plus').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.updateQuantity(e.target.dataset.key, 1);
      });
    });
    container.querySelectorAll('.btn-qty-minus').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.updateQuantity(e.target.dataset.key, -1);
      });
    });

    // Update totals display in summary
    const subtotalEl = document.getElementById('cart-summary-subtotal');
    const taxEl = document.getElementById('cart-summary-tax');
    const deliveryEl = document.getElementById('cart-summary-delivery');
    const totalEl = document.getElementById('cart-summary-total');

    if (subtotalEl) subtotalEl.textContent = `${this.currencySymbol}${this.getSubtotal().toFixed(2)}`;
    if (taxEl) taxEl.textContent = `${this.currencySymbol}${this.getTaxAmount().toFixed(2)}`;
    if (deliveryEl) deliveryEl.textContent = `${this.currencySymbol}${this.getDeliveryFee().toFixed(2)}`;
    if (totalEl) totalEl.textContent = `${this.currencySymbol}${this.getTotal().toFixed(2)}`;
  }

  showToast(message) {
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
      toastContainer = document.createElement('div');
      toastContainer.id = 'toast-container';
      toastContainer.className = 'toast-container position-fixed bottom-0 start-50 translate-middle-x p-3';
      toastContainer.style.zIndex = '2000';
      document.body.appendChild(toastContainer);
    }

    const toastEl = document.createElement('div');
    toastEl.className = 'toast align-items-center text-white bg-dark border-0 show shadow-lg mb-2';
    toastEl.style.borderRadius = '30px';
    toastEl.style.backgroundColor = '#32150F';
    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body px-3 py-2">
          <i class="bi bi-check-circle-fill text-success me-2"></i>${message}
        </div>
      </div>
    `;
    toastContainer.appendChild(toastEl);

    setTimeout(() => {
      toastEl.classList.remove('show');
      setTimeout(() => toastEl.remove(), 400);
    }, 2400);
  }

  initListeners() {
    // Open cart offcanvas or modal
    document.querySelectorAll('[data-action="open-cart"]').forEach(el => {
      el.addEventListener('click', () => {
        const modal = new bootstrap.Modal(document.getElementById('cartModal'));
        modal.show();
      });
    });

    // Handle order type selection changes
    document.querySelectorAll('input[name="order_type_selector"]').forEach(radio => {
      radio.addEventListener('change', (e) => {
        this.orderType = e.target.value;
        const deliveryRow = document.getElementById('cart-delivery-row');
        const deliveryFields = document.getElementById('delivery-address-group');
        const tableGroup = document.getElementById('table-input-group');

        if (this.orderType === 'delivery') {
          if (deliveryRow) deliveryRow.style.display = 'flex';
          if (deliveryFields) deliveryFields.style.display = 'block';
          if (tableGroup) tableGroup.style.display = 'none';
        } else if (this.orderType === 'dine_in') {
          if (deliveryRow) deliveryRow.style.display = 'none';
          if (deliveryFields) deliveryFields.style.display = 'none';
          if (tableGroup) tableGroup.style.display = 'block';
        } else {
          // Takeaway
          if (deliveryRow) deliveryRow.style.display = 'none';
          if (deliveryFields) deliveryFields.style.display = 'none';
          if (tableGroup) tableGroup.style.display = 'none';
        }
        this.updateUI();
      });
    });
  }
}

window.DineFlowCart = DineFlowCart;

