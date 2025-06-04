// D:\lazordy\lazordy\inventory\static\inventory\js\invoice_admin_status_logic.js

(function($) {
    $(document).ready(function() {
        var $statusField = $('#id_status');
        var $amountPaidField = $('#id_amount_paid');
        var $amountRemainingField = $('#id_amount_remaining'); // This is readonly, but good to reference
        var $paymentDetailsFieldset = $('.field-amount_paid').closest('.form-row').parent().parent(); // Adjust selector as needed to get the fieldset

        function togglePaymentFields() {
            var selectedStatus = $statusField.val();

            if (selectedStatus === 'uncompleted' || selectedStatus === 'paid') {
                $paymentDetailsFieldset.show();
                // If it's 'paid', you might want to disable amount_paid
                // But generally, the model logic sets it to 0 or total_amount, so direct disabling might not be needed.
                // For simplicity, we'll keep it enabled if shown.
            } else {
                $paymentDetailsFieldset.hide();
                // Optionally, clear values if hidden, to avoid confusion on save
                // $amountPaidField.val('0.00');
            }
        }

        // Initial state on page load
        togglePaymentFields();

        // Bind to status field change
        $statusField.on('change', togglePaymentFields);

        // Optional: Auto-calculate Amount Remaining in Admin Form (client-side)
        // This is for immediate feedback, the server-side save() method is the source of truth.
        var $totalAmountField = $('#id_total_amount'); // Ensure this field exists and is updated by other JS or is always available
        // Note: The total_amount field is 'readonly' in admin.py, so its value comes from the server.
        // It's probably better to let the server-side save handle total_amount and amount_remaining.
        // If you want dynamic calculation here, you'd need to fetch product prices in JS.
        // For simplicity and relying on server-side logic, we'll skip complex dynamic calculation here.
        // We'll focus on just showing/hiding the fields.

        // You could add a listener here if you want to update amount_remaining
        // as the user types into amount_paid.
        $amountPaidField.on('input', function() {
            var total = parseFloat($totalAmountField.val() || 0);
            var paid = parseFloat($amountPaidField.val() || 0);
            var remaining = (total - paid).toFixed(2); // Keep 2 decimal places

            // Update the readonly amount_remaining field display
            // You might need to find the specific element if it's not a direct input
            // For example, if it's rendered as a <p> or <span> for readonly fields
            // Inspect your admin form HTML to get the exact selector for the displayed value.
            // For standard Django admin readonly fields, it's often a <div> containing the value.
            $('.field-amount_remaining .readonly').text(remaining);
        });

        // Trigger the initial calculation if amount_paid is pre-filled on load
        $amountPaidField.trigger('input');
    });
})(django.jQuery);