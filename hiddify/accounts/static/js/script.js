// Show Alert Box
setTimeout(function () {
  var alertBox = document.getElementById("popup-alert");
  if (alertBox) {
    var bsAlert = new bootstrap.Alert(alertBox);
    bsAlert.close();
  }
}, 5000);

// Copy Link to Clipboard Script
// Function to copy the link to clipboard
function copyLinkToClipboard(link) {
  // Create a temporary input element to hold the link
  const tempInput = document.createElement("input");
  tempInput.value = link;
  document.body.appendChild(tempInput);

  // Select the link and copy it to clipboard
  tempInput.select();
  document.execCommand("copy");

  // Remove the temporary input element
  document.body.removeChild(tempInput);

  // Notify the user
  alert("کپی شد: " + link);
}

// Attach event listeners to all images with QR codes
document.querySelectorAll('img[id^="qrCodeImage_"]').forEach(function (img) {
  img.addEventListener("click", function () {
    // Get the link stored in the data-link attribute
    const link = this.getAttribute("data-link");

    // Copy the link to clipboard
    copyLinkToClipboard(link);
  });
});
document.querySelectorAll('a[id^="invite_code"]').forEach(function (a) {
  a.addEventListener("click", function () {
    const link = this.getAttribute("invite-code");

    // Copy the link to clipboard
    copyLinkToClipboard(link);
  });
});

// Popover Script
const popoverTriggerList = document.querySelectorAll(
  '[data-bs-toggle="popover"]'
);
const popoverList = [...popoverTriggerList].map(
  (popoverTriggerEl) => new bootstrap.Popover(popoverTriggerEl)
);

function confirmDelete() {
  if (confirm("آیا از حذف سفارش اطمینان دارید؟")) {
    document
      .querySelector(
        'form[action="{% url "delete_order" config.last_order.id %}"]'
      )
      .submit();
  }
}

function toggleEditForm() {
  const editForm = document.getElementById("editForm");
  if (editForm.style.display === "none") {
    editForm.style.display = "block";
  } else {
    editForm.style.display = "none";
  }
}


function showPaymentForm(cardId) {
  document.getElementById('defaultView_' + cardId).style.display = 'none';
  document.getElementById('paymentFormView_' + cardId).style.display = 'block';
}

function cancelPaymentForm(cardId) {
  document.getElementById('paymentFormView_' + cardId).style.display = 'none';  // Hide the payment form
  document.getElementById('defaultView_' + cardId).style.display = 'block';     // Show the default view
  document.getElementById('qrCodeSection_' + cardId).style.display = 'block';   // Show the QR code section again
}

function togglePaymentForm(cardId) {
  const defaultView = document.getElementById('defaultView_' + cardId);
  const paymentFormView = document.getElementById('paymentFormView_' + cardId);
  const qrCodeSection = document.getElementById('qrCodeSection_' + cardId);

  if (paymentFormView.style.display === 'none' || paymentFormView.style.display === '') {
    // Show payment form and hide default view and QR code section
    defaultView.style.display = 'none';
    paymentFormView.style.display = 'block';
    qrCodeSection.style.display = 'none';
  } else {
    // Hide payment form and show default view and QR code section
    paymentFormView.style.display = 'none';
    defaultView.style.display = 'block';
    qrCodeSection.style.display = 'block';
  }
}

document.addEventListener('DOMContentLoaded', function () {
  // Select all toggle buttons
  const toggleButtons = document.querySelectorAll('.toggle-details');
  
  // Add click event listeners to each button
  toggleButtons.forEach(function (button) {
      button.addEventListener('click', function () {
          // Get the target payment details row
          const target = document.querySelector(button.getAttribute('data-target'));
          
          // Toggle the visibility of the payment details row
          if (target.style.display === 'none' || target.style.display === '') {
              target.style.display = 'table-row';  // Show row
          } else {
              target.style.display = 'none';  // Hide row
          }
      });
  });
});


// JavaScript to handle form submission with appropriate value for confirm_payment
document
  .querySelectorAll(".confirm-btn, .reject-btn")
  .forEach(function (button) {
    button.addEventListener("click", function () {
      const form = this.closest("form");
      const hiddenInput = form.querySelector("#confirmPaymentInput");
      hiddenInput.value = this.getAttribute("data-value");
      form.submit();
    });
  });

  