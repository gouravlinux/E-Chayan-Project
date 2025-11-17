// Wait for the document to be fully loaded
document.addEventListener("DOMContentLoaded", function() {
    
    // Find all the toggle icons on the page
    const toggleIcons = document.querySelectorAll(".toggle-password-icon");

    toggleIcons.forEach(icon => {
        icon.addEventListener("click", function() {
            // Get the input field this icon is related to
            // It's the <input> element just before the icon
            const passwordInput = this.previousElementSibling;

            // Check the current type of the input
            if (passwordInput.type === "password") {
                // Change type to "text" (to show it)
                passwordInput.type = "text";
                
                // Change the icon from "eye-slash" to "eye"
                this.classList.remove("bi-eye-slash");
                this.classList.add("bi-eye");
            } else {
                // Change type back to "password" (to hide it)
                passwordInput.type = "password";
                
                // Change the icon from "eye" to "eye-slash"
                this.classList.remove("bi-eye");
                this.classList.add("bi-eye-slash");
            }
        });
    });

});