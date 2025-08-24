// This file has been deprecated to avoid conflicts with invoice_item_price_fill.js
// which provides more comprehensive functionality including price autofill
console.log("⚠️ admin_invoiceitem_autofill.js is deprecated and inactive");

// Commenting out the original functionality to prevent conflicts
/*
document.addEventListener('DOMContentLoaded', function () {
    function bindProductChangeHandlers() {
        document.querySelectorAll('select[id$="-product"]').forEach(selectEl => {
            selectEl.removeEventListener('change', onProductChange); // Avoid multiple binds
            selectEl.addEventListener('change', onProductChange);
        });
    }

    function onProductChange(event) {
        const selectEl = event.target;
        const productId = selectEl.value;
        const nameInputId = selectEl.id.replace('-product', '-product_name');
        const nameInput = document.getElementById(nameInputId);

        if (productId && nameInput) {
            fetch(`/inventory/api/product/${productId}/name/`)
                .then(response => response.json())
                .then(data => {
                    if (data.name) {
                        nameInput.value = data.name;
                    }
                })
                .catch(error => {
                    console.error("Error fetching product name:", error);
                });
        }
    }

    // Initial bind
    bindProductChangeHandlers();

    // Handle added inlines (for dynamically added rows)
    if (typeof django !== "undefined" && django.jQuery) {
        django.jQuery(document).on('formset:added', function () {
            bindProductChangeHandlers();
        });
    }
});
*/
