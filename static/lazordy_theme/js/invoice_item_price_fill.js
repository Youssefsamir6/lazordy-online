// D:\lazordy\lazordy_theme\js\invoice_item_price_fill.js
(function($) {
    "use strict";

    $(document).ready(function() {
        console.log("✅ invoice_item_price_fill.js is active and listening for Select2 events.");

        // CORRECTED getInlinePrefix FUNCTION
        function getInlinePrefix(element) {
            const $select = $(element);
            const nameAttr = $select.attr('name');

            if (nameAttr) {
                // This regex is more general and captures any formset prefix (e.g., "items-0-")
                const match = nameAttr.match(/^(.+-\d+)-product$/);
                if (match) {
                    return match[1] + '-';
                }
            }

            console.warn('⚠️ Could not determine prefix from element:', element);
            return null;
        }

        // Fetches product data from the Django API.
        function fetchProductData(productId, prefix) {
            if (!productId || !prefix) {
                console.warn('⚠️ fetchProductData called without a valid product ID or prefix.');
                return;
            }

            const $unitPriceInput = $(`[name="${prefix}unit_price"]`);
            const $productNameInput = $(`[name="${prefix}product_name"]`);
            const url = `/inventory/api/product/${productId}/price/`;

            console.log(`🔍 Fetching data for product ID: ${productId} from URL: ${url}`);

            $.ajax({
                url: url,
                type: 'GET',
                dataType: 'json',
                success: function(data) {
                    console.log(`✅ API call successful. Received data:`, data);
                    if (data.price !== undefined && data.price !== null) {
                        $unitPriceInput.val(data.price).trigger('input').trigger('change');
                        console.log(`✅ Set unit price to: ${data.price}`);
                    } else {
                        $unitPriceInput.val('').trigger('input').trigger('change');
                        console.warn('⚠️ API response did not contain a price.');
                    }
                    if (data.name !== undefined && data.name !== null) {
                        $productNameInput.val(data.name);
                        console.log(`✅ Set product name to: ${data.name}`);
                    } else {
                        $productNameInput.val('');
                        console.warn('⚠️ API response did not contain a name.');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('❌ Error fetching product data:', status, error, xhr.responseText);
                    $unitPriceInput.val('').trigger('input').trigger('change');
                    $productNameInput.val('');
                }
            });
        }

        // Setup handlers for all product dropdowns on the page, including new ones.
        function setupHandlers($container) {
            $container.find('select[name$="-product"], select[id$="-product"]').each(function() {
                const $select = $(this);

                // Use the select2:select event, which is triggered reliably.
                $select.on('select2:select', function(e) {
                    const productId = e.params.data.id;
                    const prefix = getInlinePrefix(this);
                    if (prefix) {
                        console.log(`🎯 Product selected via Select2, ID: ${productId}, prefix: ${prefix}`);
                        fetchProductData(productId, prefix);
                    } else {
                        console.warn('⚠️ Could not determine prefix for Select2 selection');
                    }
                });

                // Also handle the case where a selection is cleared
                $select.on('select2:unselect', function(e) {
                    const prefix = getInlinePrefix(this);
                    if (prefix) {
                        console.log('🎯 Product unselected, clearing fields.');
                        $(`[name="${prefix}unit_price"]`).val('').trigger('input').trigger('change');
                        $(`[name="${prefix}product_name"]`).val('');
                    }
                });

                // Initialize if a product is already selected on page load
                if ($select.val()) {
                    const prefix = getInlinePrefix(this);
                    if (prefix) {
                        console.log(`🔄 Initializing existing product: ${$select.val()}`);
                        fetchProductData($select.val(), prefix);
                    }
                }
            });
        }
        
        // Listen for new formsets being added and set up handlers for them.
        $(document).on('formset:added', function(event, row) {
            console.log('🆕 New formset added, setting up handlers.');
            setupHandlers($(row));
        });

        // Setup handlers for all initial formsets on page load.
        setupHandlers($(document));
    });

})(django.jQuery);