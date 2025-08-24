document.addEventListener('DOMContentLoaded', function () {
    let itemIndex = 0;

    function escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    function initializeSelect2Product(selector) {
        $(selector).select2({
            ajax: {
                url: '/products/autocomplete/',
                dataType: 'json',
                delay: 250,
                data: params => ({ q: params.term }),
                processResults: data => ({ results: data.results }),
                cache: true
            },
            placeholder: '-- Custom Item --',
            allowClear: true,
            minimumInputLength: 1
        }).on('select2:select', async function (e) {
            // This is the most reliable event for Select2
            const data = e.params.data;
            const productId = data.id;
            const index = $(this).data('index');
            const row = this.closest('tr');
            const nameInput = row.querySelector(`input[name='product_name_${index}']`);
            const priceInput = row.querySelector(`input[name='unit_price_${index}']`);

            if (productId) {
                try {
                    // Make a dedicated fetch call to get the price
                    const res = await fetch(`/get_product_price/${productId}/`);
                    if (!res.ok) throw new Error('Network response was not ok.');
                    const priceData = await res.json();
                    
                    priceInput.value = priceData.price;
                    nameInput.value = priceData.name;

                } catch (err) {
                    console.error('Failed to fetch product price:', err);
                    priceInput.value = '';
                }
            } else {
                // Handle case where custom item is selected (product ID is empty)
                priceInput.value = '';
                nameInput.value = data.name || data.text; // Use the value from Select2
            }
            
            toggleManualFields(row, index);
            calculateTotal();
        });
        
        // Handle clear event
        $(selector).on('select2:clear', function (e) {
            const index = $(this).data('index');
            const row = this.closest('tr');
            const nameInput = row.querySelector(`input[name='product_name_${index}']`);
            const priceInput = row.querySelector(`input[name='unit_price_${index}']`);
            nameInput.value = '';
            priceInput.value = '';
            toggleManualFields(row, index);
            calculateTotal();
        });
    }

    function toggleManualFields(row, index) {
        const productSelect = row.querySelector(`[name='product_id_${index}']`);
        const nameInput = row.querySelector(`[name='product_name_${index}']`);
        const priceInput = row.querySelector(`[name='unit_price_${index}']`);

        if (productSelect && nameInput && priceInput) {
            if (productSelect.value) {
                // If a product is selected, hide the custom name input and make price read-only
                nameInput.parentElement.style.display = 'none';
                priceInput.readOnly = true;
            } else {
                // If no product is selected, show the custom name input and make price editable
                nameInput.parentElement.style.display = '';
                priceInput.readOnly = false;
            }
        }
    }

    function addInvoiceItemRow(data = {}) {
        const tbody = document.getElementById('itemRows');
        const row = document.createElement('tr');
        row.className = 'item-row border-t dark:border-gray-600';

        const productId = data.product_id || '';
        const productName = data.product_name || '';
        const quantity = data.quantity || 1;
        const unitPrice = data.unit_price || '';
        const subtotal = (quantity * unitPrice).toFixed(2);

        row.innerHTML = `
            <td class="p-2">
                <select name="product_id_${itemIndex}" class="product-dropdown select2-product" data-index="${itemIndex}" style="width: 100%;">
                    <option value="">-- Custom Item --</option>
                </select>
            </td>
            <td class="p-2">
                <input type="text" name="product_name_${itemIndex}" class="w-full p-1 border rounded" placeholder="Enter name" value="${escapeHTML(productName)}">
            </td>
            <td class="p-2">
                <input type="number" name="quantity_${itemIndex}" class="quantity w-full p-1 border rounded" value="${quantity}" min="1">
            </td>
            <td class="p-2">
                <input type="number" step="0.01" name="unit_price_${itemIndex}" class="unit-price w-full p-1 border rounded" value="${unitPrice}">
            </td>
            <td class="p-2">
                <input type="text" name="subtotal_${itemIndex}" class="subtotal w-full p-1 border rounded bg-gray-100" value="${subtotal}" readonly>
            </td>
            <td class="p-2 text-center">
                <button type="button" class="remove-item text-red-600 hover:text-red-800">✖</button>
            </td>
        `;

        tbody.appendChild(row);

        const selectSelector = `select[name='product_id_${itemIndex}']`;
        const $select = $(selectSelector);

        // Initialize Select2
        initializeSelect2Product($select);

        // If product exists, manually inject it into Select2 and trigger change to fetch price
        if (productId) {
            const option = new Option(productName || '-- Selected Product --', productId, true, true);
            $select.append(option).trigger('change');
        }

        // Attach listeners for quantity and price changes
        attachListeners(row);
        
        toggleManualFields(row, itemIndex);
        itemIndex++;
    }

    function attachListeners(row) {
        row.querySelector('.remove-item')?.addEventListener('click', e => {
            e.target.closest('tr').remove();
            calculateTotal();
        });

        row.querySelectorAll('.quantity, .unit-price').forEach(input => {
            input.addEventListener('input', calculateTotal);
        });
    }

    function calculateTotal() {
        let subtotalTotal = 0;
        document.querySelectorAll('.item-row').forEach(row => {
            const qty = parseFloat(row.querySelector('.quantity')?.value || 0);
            const price = parseFloat(row.querySelector('.unit-price')?.value || 0);
            const subtotal = qty * price;
            row.querySelector('.subtotal').value = subtotal.toFixed(2);
            subtotalTotal += subtotal;
        });

        const discountAmount = parseFloat(document.getElementById('discount-amount-input')?.value || 0);
        const managerDiscountAmount = parseFloat(document.getElementById('manager-discount-amount-input')?.value || 0);
        
        const totalAmount = subtotalTotal - discountAmount - managerDiscountAmount;
        
        document.getElementById('subtotalDisplay').value = subtotalTotal.toFixed(2);
        document.getElementById('totalDisplay').value = totalAmount.toFixed(2);

        // Update amount remaining
        updateAmountRemaining();
    }
    
    function updateAmountRemaining() {
        const totalAmount = parseFloat(document.getElementById('totalDisplay')?.value || 0);
        const amountPaid = parseFloat(document.getElementById('amount-paid-input')?.value || 0);
        const amountRemaining = totalAmount - amountPaid;
        document.getElementById('amount-remaining-display').value = amountRemaining.toFixed(2);
    }
    
    // Listen for discount and amount paid changes
    document.getElementById('discount-amount-input')?.addEventListener('input', calculateTotal);
    document.getElementById('manager-discount-amount-input')?.addEventListener('input', calculateTotal);
    document.getElementById('amount-paid-input')?.addEventListener('input', updateAmountRemaining);

    // Init
    document.getElementById('addItemBtn')?.addEventListener('click', addInvoiceItemRow);

    if (window.initialInvoiceItems && Array.isArray(window.initialInvoiceItems)) {
        window.initialInvoiceItems.forEach(item => {
            addInvoiceItemRow(item);
        });
    } else {
        addInvoiceItemRow();
    }

    // Toggle Company Address
    const addressBtn = document.getElementById("edit-company-address-btn");
    const addressDisplay = document.getElementById("company-address-display");
    const addressInput = document.getElementById("company-address-input");
    if (addressBtn) {
        addressBtn.addEventListener("click", () => {
            addressDisplay.classList.add("hidden");
            addressInput.classList.remove("hidden");
        });
    }

    // Toggle Company Phone
    const phoneBtn = document.getElementById("edit-company-phone-btn");
    const phoneDisplay = document.getElementById("company-phone-display");
    const phoneInput = document.getElementById("company-phone-input");
    if (phoneBtn) {
        phoneBtn.addEventListener("click", () => {
            phoneDisplay.classList.add("hidden");
            phoneInput.classList.remove("hidden");
        });
    }

    // Initial calculation on page load
    calculateTotal();
});