// static/inventory/js/invoice_item_price_fill.js

(function($) {
    $(document).ready(function() {
        // Function to get the prefix for inline forms (e.g., 'items-0-')
        function getInlinePrefix(element) {
            console.log("Debug: getInlinePrefix called with element:", element);
            // Find the closest ancestor that is an inline form row.
            // This class is consistently applied to dynamic inline rows.
            const $row = $(element).closest('.form-row.dynamic-items');
            console.log(`Debug: closest .form-row.dynamic-items found: ${$row.attr('id')} (length: ${$row.length})`);

            if ($row.length) {
                // The input fields inside this row will have IDs like 'id_items-0-product',
                // so we need the 'items-0-' part. We can extract it from any input/select ID within the row.
                const firstInputId = $row.find('input, select').first().attr('id');
                if (firstInputId) {
                    const match = firstInputId.match(/(items-\d+-)/);
                    if (match) {
                        console.log("Debug: Derived prefix:", match[0]);
                        return match[0];
                    }
                }
            }
            console.error("Debug: Could not determine inline prefix for element:", element, ". Closest row found:", $row);
            return null;
        }

        // --- 1. Autocomplete Product Price ---
        // Listen for 'select2:select' event on the product <select> element.
        // This event is specifically fired by Select2 *after* a selection is made and the underlying <select>'s value is updated.
        $(document).on('select2:select', 'select[id$="-product"].admin-autocomplete', function(e) {
            const $selectElement = $(this);
            const productId = $selectElement.val(); // Get the selected product ID
            const prefix = getInlinePrefix($selectElement); // Get the prefix for this inline row

            console.log("Debug: Product select2:select event triggered.");
            console.log("Debug: Event target element ID:", $selectElement.attr('id'));
            console.log("Debug: Retrieved Product ID:", productId);
            console.log("Debug: Retrieved Prefix:", prefix);
            console.log("Debug: Select2 event data (e.params.data):", e.params.data); // Inspect the data passed by Select2

            if (!prefix) {
                // Error already logged by getInlinePrefix if it fails
                return;
            }

            const $unitPriceInput = $(`#id_${prefix}unit_price`); // Target the unit_price input in this row
            console.log("Debug: Targeted unit price input ID:", $unitPriceInput.attr('id'), "Element found:", $unitPriceInput.length > 0);

            if (productId) {
                const url = `/inventory/get_product_price/${productId}/`; // ⭐ ENSURE THIS URL MATCHES YOUR inventory/urls.py ⭐
                console.log(`Debug: Attempting to fetch price for product ID: ${productId} from URL: ${url}`);

                $.ajax({
                    url: url,
                    success: function(data) {
                        if (data.price !== undefined && data.price !== null) { // Ensure price property exists and is not null
                            console.log(`Debug: Received price: ${data.price} for product ID: ${productId}`);
                            $unitPriceInput.val(data.price).trigger('input'); // Set price and trigger 'input' to recalculate subtotal
                        } else {
                            console.log(`Debug: API returned no valid price data for product ID: ${productId}. Response:`, data);
                            $unitPriceInput.val('').trigger('input'); // Clear if no price
                        }
                    },
                    error: function(xhr, status, error) {
                        console.error('Error fetching product price:', status, error);
                        console.log('Response Text:', xhr.responseText); // Show the server's response content
                        $unitPriceInput.val('').trigger('input'); // Clear on AJAX error
                    }
                });
            } else {
                // If product ID is empty (e.g., user cleared selection), clear unit price
                console.log("Debug: Product ID is empty, clearing unit price.");
                $unitPriceInput.val('').trigger('input');
            }
        });


        // --- 2. Calculate Item Subtotal and Update Total Amount ---
        function updateItemSubtotalAndInvoiceTotal(prefix) {
            const $unitPriceInput = $(`#id_${prefix}unit_price`);
            const $quantityInput = $(`#id_${prefix}quantity`);
            const $subtotalInput = $(`#id_${prefix}subtotal`);

            let unitPrice = parseFloat($unitPriceInput.val()) || 0;
            let quantity = parseInt($quantityInput.val()) || 0;

            let subtotal = (unitPrice * quantity).toFixed(2); // Keep 2 decimal places
            $subtotalInput.val(subtotal); // Update the subtotal field
            console.log(`Debug: Item Subtotal updated for ${prefix}: ${subtotal}`);

            updateInvoiceTotal(); // Call the main invoice total function
        }

        // --- 3. Main Invoice Total Calculation ---
        function updateInvoiceTotal() {
            let grandTotal = 0;
            // Iterate over each inline row that is not marked for deletion
            $('.form-row.dynamic-items:not(.deleted):not(.empty-form)').each(function() {
                // Get prefix from any input within the row to ensure we get the correct prefix
                const prefix = getInlinePrefix($(this).find('input, select').first());
                if (prefix) {
                    const $subtotalInput = $(`#id_${prefix}subtotal`);
                    grandTotal += parseFloat($subtotalInput.val()) || 0;
                }
            });

            const $discountInput = $('#id_discount_amount');
            // ⭐ IMPORTANT CHANGE HERE: Correctly target the display element for total amount (the div with class 'readonly') ⭐
            const $totalAmountDisplay = $('.form-row.field-total_amount .readonly');

            let discount = parseFloat($discountInput.val()) || 0;
            let finalTotal = (grandTotal - discount).toFixed(2);

            // ⭐ IMPORTANT CHANGE HERE: Use .text() to update the content of the div ⭐
            $totalAmountDisplay.text(finalTotal);
            console.log(`Debug: Invoice Total updated: ${finalTotal}`);
        }

        // --- Event Listeners for Dynamic Updates ---

        // Listen for 'input' (as user types) or 'change' (on blur or select change)
        // for quantity and unit_price fields within inline forms.
        $(document).on('input change', 'input[id$="-quantity"], input[id$="-unit_price"]', function() {
            const prefix = getInlinePrefix(this);
            if (prefix) {
                updateItemSubtotalAndInvoiceTotal(prefix);
            }
        });

        // Listen for 'input' or 'change' on the main invoice's discount_amount field.
        $(document).on('input change', '#id_discount_amount', function() {
            updateInvoiceTotal();
        });

        // Event listener for when a new inline is added (Django admin's 'add another' button)
        $(document).on('formset:added', function(event, row) {
            console.log("Debug: Formset added event triggered.");
            // When a new row is added, find its product select field.
            const $newProductSelect = row.find('select[id$="-product"].admin-autocomplete');
            if ($newProductSelect.length && $newProductSelect.val()) {
                // If the new row was added with a pre-selected product (e.g., loaded from DB),
                // manually trigger the select2:select event.
                // We pass `e.params.data` structure for consistency, though product ID is enough.
                $newProductSelect.trigger('select2:select', { data: { id: $newProductSelect.val(), text: $newProductSelect.find('option:selected').text() } });
            } else {
                // For a truly empty new row, ensure initial subtotal is 0 and update total.
                const prefix = getInlinePrefix(row); // Use the row itself to get prefix for new empty row
                if (prefix) {
                    updateItemSubtotalAndInvoiceTotal(prefix);
                }
            }
        });

        // Event listener for when an inline is deleted (Django admin's 'delete' checkbox)
        $(document).on('formset:removed', function(event, row) {
            console.log("Debug: Formset removed event triggered.");
            updateInvoiceTotal(); // Re-calculate overall total after a row is removed
        });

        // --- Initial Calculations on Page Load ---
        console.log("Debug: Page loaded. Performing initial calculations.");
        // On page load, iterate through existing form rows and calculate their subtotals
        // and update the grand total.
        $('.form-row.dynamic-items:not(.empty-form)').each(function() {
            const prefix = getInlinePrefix($(this).find('select[id$="-product"].admin-autocomplete'));
            if (prefix) {
                // Trigger 'input' on quantity to ensure subtotal is calculated for pre-filled forms
                $(this).find(`#id_${prefix}quantity`).trigger('input');
            }
        });
        
        // Finally, ensure the overall invoice total is updated.
        updateInvoiceTotal();
    });
})(django.jQuery); // Use django.jQuery to avoid conflicts with other JS libraries